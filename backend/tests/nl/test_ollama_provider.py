"""Tests for the Ollama provider using respx-mocked HTTP responses.

Covers: plain text reply, single tool call (``update_flag_draft``), multiple tool
calls merged in one turn (later-overrides-earlier), ``confirm_flag`` detection,
and prompt-token usage extraction. HTTP is mocked at the Ollama
``/v1/chat/completions`` endpoint so no real network calls are made.
"""

import json
from typing import Any, Dict, List

import httpx
import pytest
import respx

from app.config.settings import settings
from app.services.nl.providers import ollama_provider

OLLAMA_CHAT_ENDPOINT = "/v1/chat/completions"


def _build_response(
    content: str = "",
    tool_calls: List[Dict[str, Any]] | None = None,
    prompt_tokens: int = 0,
) -> Dict[str, Any]:
    """Assemble an OpenAI-shaped chat.completions response body."""
    message: Dict[str, Any] = {"role": "assistant", "content": content}
    if tool_calls is not None:
        message["tool_calls"] = tool_calls
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "model": settings.ollama_model,
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": 0,
            "total_tokens": prompt_tokens,
        },
    }


def _tool_call(name: str, arguments: Dict[str, Any], call_id: str = "call_1") -> Dict[str, Any]:
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


@pytest.fixture
def ollama_url() -> str:
    return f"{settings.ollama_base_url.rstrip('/')}/v1/chat/completions"


async def test_single_text_response(ollama_url):
    payload = _build_response(content="hello there", prompt_tokens=42)
    with respx.mock(assert_all_called=True) as mock:
        mock.post(ollama_url).mock(return_value=httpx.Response(200, json=payload))
        text, draft, confirm, tokens = await ollama_provider.chat_turn(
            system_prompt="sys", history=[], user_message="hi"
        )
    assert text == "hello there"
    assert draft == {}
    assert confirm is False
    assert tokens == 42


async def test_single_update_flag_draft_tool_call(ollama_url):
    tool_calls = [
        _tool_call("update_flag_draft", {"flag_key": "dark_mode", "name": "Dark Mode"}),
    ]
    payload = _build_response(tool_calls=tool_calls, prompt_tokens=120)
    with respx.mock(assert_all_called=True) as mock:
        mock.post(ollama_url).mock(return_value=httpx.Response(200, json=payload))
        text, draft, confirm, tokens = await ollama_provider.chat_turn(
            system_prompt="sys", history=[], user_message="make dark mode"
        )
    assert text == ""
    assert draft == {"flag_key": "dark_mode", "name": "Dark Mode"}
    assert confirm is False
    assert tokens == 120


async def test_two_tool_calls_in_one_turn_later_overrides(ollama_url):
    tool_calls = [
        _tool_call(
            "update_flag_draft",
            {"flag_key": "old_key", "name": "Old Name"},
            call_id="call_1",
        ),
        _tool_call(
            "update_flag_draft",
            {"flag_key": "new_key", "description": "added later"},
            call_id="call_2",
        ),
    ]
    payload = _build_response(content="updated", tool_calls=tool_calls, prompt_tokens=55)
    with respx.mock(assert_all_called=True) as mock:
        mock.post(ollama_url).mock(return_value=httpx.Response(200, json=payload))
        text, draft, confirm, tokens = await ollama_provider.chat_turn(
            system_prompt="sys", history=[], user_message="iterate"
        )
    assert text == "updated"
    # Later call overrides earlier flag_key; earlier name remains; description added.
    assert draft == {"flag_key": "new_key", "name": "Old Name", "description": "added later"}
    assert confirm is False
    assert tokens == 55


async def test_confirm_flag_triggered(ollama_url):
    tool_calls = [
        _tool_call("update_flag_draft", {"flag_key": "x"}, call_id="call_1"),
        _tool_call("confirm_flag", {}, call_id="call_2"),
    ]
    payload = _build_response(tool_calls=tool_calls, prompt_tokens=80)
    with respx.mock(assert_all_called=True) as mock:
        mock.post(ollama_url).mock(return_value=httpx.Response(200, json=payload))
        text, draft, confirm, tokens = await ollama_provider.chat_turn(
            system_prompt="sys", history=[], user_message="save it"
        )
    assert draft == {"flag_key": "x"}
    assert confirm is True
    assert tokens == 80


async def test_usage_tokens_missing_defaults_to_zero(ollama_url):
    payload = _build_response(content="ok")
    # Strip the usage block entirely to simulate older Ollama versions.
    payload.pop("usage")
    with respx.mock(assert_all_called=True) as mock:
        mock.post(ollama_url).mock(return_value=httpx.Response(200, json=payload))
        _, _, _, tokens = await ollama_provider.chat_turn(
            system_prompt="sys", history=[], user_message="hi"
        )
    assert tokens == 0


async def test_malformed_tool_arguments_are_ignored(ollama_url):
    # Malformed JSON in arguments should not crash; just yield empty args merged.
    tool_calls = [
        {
            "id": "call_bad",
            "type": "function",
            "function": {"name": "update_flag_draft", "arguments": "not-json"},
        }
    ]
    payload = _build_response(tool_calls=tool_calls, prompt_tokens=10)
    with respx.mock(assert_all_called=True) as mock:
        mock.post(ollama_url).mock(return_value=httpx.Response(200, json=payload))
        _, draft, confirm, tokens = await ollama_provider.chat_turn(
            system_prompt="sys", history=[], user_message="x"
        )
    assert draft == {}
    assert confirm is False
    assert tokens == 10


async def test_summarize_for_compaction_returns_content(ollama_url):
    payload = _build_response(content="short summary text", prompt_tokens=15)
    with respx.mock(assert_all_called=True) as mock:
        mock.post(ollama_url).mock(return_value=httpx.Response(200, json=payload))
        summary = await ollama_provider.summarize_for_compaction(
            messages=[{"role": "user", "content": "hi"}],
            extracted={"flag_key": "x"},
        )
    assert summary == "short summary text"


async def test_dispatcher_routes_to_ollama_when_configured(monkeypatch, ollama_url):
    """End-to-end: dispatcher with nl_provider='ollama' hits the Ollama HTTP path."""
    from app.services.nl.providers import dispatcher

    monkeypatch.setattr(settings, "nl_provider", "ollama")
    payload = _build_response(content="routed", prompt_tokens=7)
    with respx.mock(assert_all_called=True) as mock:
        mock.post(ollama_url).mock(return_value=httpx.Response(200, json=payload))
        text, _, _, tokens = await dispatcher.chat_turn(
            system_prompt="sys", history=[], user_message="hi"
        )
    assert text == "routed"
    assert tokens == 7


async def test_dispatcher_rejects_unknown_provider(monkeypatch):
    from app.services.nl.providers import dispatcher

    monkeypatch.setattr(settings, "nl_provider", "bogus")
    with pytest.raises(ValueError, match="Unknown nl_provider"):
        await dispatcher.chat_turn(system_prompt="sys", history=[], user_message="hi")
