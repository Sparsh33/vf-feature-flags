"""Anthropic Claude provider for the NL flag builder.

Uses Claude Sonnet 4.6 with tool use for structured extraction and prompt
caching on system prompt + tool definitions. Moved verbatim from the original
``claude_client.py`` — behaviour is unchanged.
"""

import json
from typing import Any, Dict, List, Tuple

import anthropic

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

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 2048

TOOLS: List[Dict[str, Any]] = [
    {
        "name": TOOL_UPDATE_FLAG_DRAFT,
        "description": TOOL_UPDATE_FLAG_DRAFT_DESCRIPTION,
        "input_schema": UPDATE_FLAG_DRAFT_PARAMETERS,
    },
    {
        "name": TOOL_CONFIRM_FLAG,
        "description": TOOL_CONFIRM_FLAG_DESCRIPTION,
        "input_schema": CONFIRM_FLAG_PARAMETERS,
    },
]


def _get_client() -> anthropic.AsyncAnthropic:
    return anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)


def _build_cached_tools() -> List[Dict[str, Any]]:
    """Return tool definitions with cache_control on the last tool to cache all of them."""
    cached = [dict(tool) for tool in TOOLS]
    cached[-1] = {**cached[-1], "cache_control": {"type": "ephemeral"}}
    return cached


def _build_cached_system(system_prompt: str) -> List[Dict[str, Any]]:
    return [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]


async def chat_turn(
    system_prompt: str,
    history: List[Dict[str, Any]],
    user_message: str,
) -> Tuple[str, Dict[str, Any], bool, int]:
    """Execute one chat turn with Claude.

    Returns (assistant_text, tool_calls_merged_draft, confirm_flag_called, input_tokens_used).
    """
    client = _get_client()
    messages: List[Dict[str, Any]] = list(history) + [{"role": "user", "content": user_message}]
    response = await client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=_build_cached_system(system_prompt),
        tools=_build_cached_tools(),
        messages=messages,
    )
    text_parts: List[str] = []
    merged_draft: Dict[str, Any] = {}
    confirm_called = False
    for block in response.content:
        block_type = getattr(block, "type", None)
        if block_type == "text":
            text_parts.append(getattr(block, "text", ""))
        elif block_type == "tool_use":
            tool_name = getattr(block, "name", "")
            tool_input = getattr(block, "input", {}) or {}
            if tool_name == TOOL_UPDATE_FLAG_DRAFT:
                merge_draft(merged_draft, tool_input)
            elif tool_name == TOOL_CONFIRM_FLAG:
                confirm_called = True
    usage = getattr(response, "usage", None)
    input_tokens = 0
    if usage is not None:
        input_tokens = (
            (getattr(usage, "input_tokens", 0) or 0)
            + (getattr(usage, "cache_read_input_tokens", 0) or 0)
            + (getattr(usage, "cache_creation_input_tokens", 0) or 0)
        )
    return "".join(text_parts), merged_draft, confirm_called, input_tokens


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
    response = await client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=compaction_prompt,
        messages=[{"role": "user", "content": f"Conversation so far:\n{transcript}"}],
    )
    parts: List[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(getattr(block, "text", ""))
    return "".join(parts)
