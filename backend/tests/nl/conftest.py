"""Shared fixtures for NL tests: mock anthropic client and request context."""

from typing import Any, Callable, Dict, List, Tuple

import pytest

from app.middleware.request_context import RequestContextManager
from app.services.nl import claude_client, nl_service


@pytest.fixture(autouse=True)
def _set_context():
    """Populate request context with a test client + user."""
    RequestContextManager.set_client_id("client-a")
    RequestContextManager.set_user_id("user-1")
    yield
    RequestContextManager.set_client_id("")
    RequestContextManager.set_user_id("")


@pytest.fixture
def mock_chat_turn(monkeypatch):
    """Install a scripted replacement for claude_client.chat_turn.

    Usage:
        mock_chat_turn([
            ("reply text", {"flag_key": "x"}, False, 100),
            ("next reply", {"cohorts": [...]}, True, 200),
        ])
    """

    def _install(scripted: List[Tuple[str, Dict[str, Any], bool, int]]) -> List[Dict[str, Any]]:
        calls: List[Dict[str, Any]] = []
        iterator = iter(scripted)

        async def _fake_chat_turn(system_prompt, history, user_message):
            calls.append(
                {
                    "system_prompt": system_prompt,
                    "history": list(history),
                    "user_message": user_message,
                }
            )
            try:
                return next(iterator)
            except StopIteration:
                return ("", {}, False, 0)

        monkeypatch.setattr(claude_client, "chat_turn", _fake_chat_turn)
        monkeypatch.setattr(nl_service.claude_client, "chat_turn", _fake_chat_turn)
        return calls

    return _install


@pytest.fixture
def mock_summarize(monkeypatch):
    """Install a deterministic compaction summary generator."""

    def _install(summary_fn: Callable[[List[Dict[str, Any]], Dict[str, Any]], str]):
        async def _fake_summarize(messages, extracted):
            return summary_fn(messages, extracted)

        monkeypatch.setattr(claude_client, "summarize_for_compaction", _fake_summarize)
        from app.services.nl import compaction as compaction_module

        monkeypatch.setattr(compaction_module, "summarize_for_compaction", _fake_summarize)

    return _install
