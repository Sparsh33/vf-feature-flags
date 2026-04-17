"""Ollama (OpenAI-compatible) provider for the NL flag builder.

Talks to Ollama 0.3+'s ``/v1/chat/completions`` endpoint via the ``openai``
Python SDK. Tool-calls use OpenAI function-calling format; multiple tool calls
per turn are merged, with later ``update_flag_draft`` calls overriding earlier
fields.
"""

import json
from typing import Any, Dict, List, Tuple

from openai import AsyncOpenAI

from app.config.settings import settings
from app.services.nl.providers.base import (
    CONFIRM_FLAG_PARAMETERS,
    TOOL_CONFIRM_FLAG,
    TOOL_CONFIRM_FLAG_DESCRIPTION,
    TOOL_UPDATE_FLAG_DRAFT,
    TOOL_UPDATE_FLAG_DRAFT_DESCRIPTION,
    UPDATE_FLAG_DRAFT_PARAMETERS,
    merge_draft,
)

MAX_TOKENS = 2048
SUMMARY_MAX_TOKENS = 1024
# Ollama accepts any non-empty string for api_key on its OpenAI-compatible endpoint.
OLLAMA_API_KEY_PLACEHOLDER = "ollama"

TOOLS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": TOOL_UPDATE_FLAG_DRAFT,
            "description": TOOL_UPDATE_FLAG_DRAFT_DESCRIPTION,
            "parameters": UPDATE_FLAG_DRAFT_PARAMETERS,
        },
    },
    {
        "type": "function",
        "function": {
            "name": TOOL_CONFIRM_FLAG,
            "description": TOOL_CONFIRM_FLAG_DESCRIPTION,
            "parameters": CONFIRM_FLAG_PARAMETERS,
        },
    },
]


def _get_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        base_url=f"{settings.ollama_base_url.rstrip('/')}/v1",
        api_key=OLLAMA_API_KEY_PLACEHOLDER,
    )


def _parse_tool_arguments(raw_arguments: Any) -> Dict[str, Any]:
    """Tool-call args arrive as a JSON string on the OpenAI schema; decode safely."""
    if raw_arguments is None or raw_arguments == "":
        return {}
    if isinstance(raw_arguments, dict):
        return raw_arguments
    try:
        parsed = json.loads(raw_arguments)
    except (TypeError, json.JSONDecodeError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


async def chat_turn(
    system_prompt: str,
    history: List[Dict[str, Any]],
    user_message: str,
) -> Tuple[str, Dict[str, Any], bool, int]:
    """Execute one chat turn against Ollama via the OpenAI-compatible API."""
    client = _get_client()
    messages: List[Dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    response = await client.chat.completions.create(
        model=settings.ollama_model,
        max_tokens=MAX_TOKENS,
        tools=TOOLS,
        messages=messages,
    )
    choice = response.choices[0]
    message = choice.message
    assistant_text = message.content or ""
    merged_draft: Dict[str, Any] = {}
    confirm_called = False
    tool_calls = getattr(message, "tool_calls", None) or []
    for tool_call in tool_calls:
        function = getattr(tool_call, "function", None)
        if function is None:
            continue
        name = getattr(function, "name", "")
        arguments = _parse_tool_arguments(getattr(function, "arguments", None))
        if name == TOOL_UPDATE_FLAG_DRAFT:
            merge_draft(merged_draft, arguments)
        elif name == TOOL_CONFIRM_FLAG:
            confirm_called = True
    usage = getattr(response, "usage", None)
    input_tokens = int(getattr(usage, "prompt_tokens", 0) or 0) if usage is not None else 0
    return assistant_text, merged_draft, confirm_called, input_tokens


async def summarize_for_compaction(
    messages: List[Dict[str, Any]], extracted: Dict[str, Any]
) -> str:
    """Produce a compact conversation summary that preserves extracted params verbatim."""
    client = _get_client()
    extracted_json = json.dumps(extracted, default=str, sort_keys=True)
    compaction_prompt = (
        "You are compressing a feature-flag design conversation. Produce a short paragraph "
        "summary that preserves:\n"
        "- All extracted params (restate them verbatim as JSON at the end).\n"
        "- The user's explicit goals and decisions.\n"
        "- Any open questions still pending.\n"
        "The extracted params so far are:\n"
        f"{extracted_json}\n\n"
        "Output format:\n"
        "<one-paragraph narrative summary>\n\n"
        f"EXTRACTED_PARAMS_JSON: {extracted_json}\n"
    )
    transcript_lines: List[str] = []
    for msg in messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if isinstance(content, list):
            content = " ".join(part.get("text", "") for part in content if isinstance(part, dict))
        transcript_lines.append(f"{role.upper()}: {content}")
    transcript = "\n".join(transcript_lines)
    response = await client.chat.completions.create(
        model=settings.ollama_model,
        max_tokens=SUMMARY_MAX_TOKENS,
        messages=[
            {"role": "system", "content": compaction_prompt},
            {"role": "user", "content": f"Conversation so far:\n{transcript}"},
        ],
    )
    return response.choices[0].message.content or ""
