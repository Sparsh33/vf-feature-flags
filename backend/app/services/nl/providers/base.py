"""Provider interface contracts for the NL flag builder.

Any LLM backend plugged into the NL service must conform to these two callables.
They use ``Protocol`` (structural typing) so providers don't need to subclass.
"""

from typing import Any, Awaitable, Dict, List, Protocol, Tuple


class ChatTurn(Protocol):
    """Execute one chat turn with the underlying provider.

    Returns ``(assistant_text, tool_calls_merged_draft, confirm_flag_called,
    input_tokens_used)``. ``tool_calls_merged_draft`` holds any fields extracted
    via an ``update_flag_draft`` tool call; ``confirm_flag_called`` is True iff
    the model invoked the ``confirm_flag`` tool.
    """

    def __call__(
        self,
        system_prompt: str,
        history: List[Dict[str, Any]],
        user_message: str,
    ) -> Awaitable[Tuple[str, Dict[str, Any], bool, int]]: ...


class SummarizeForCompaction(Protocol):
    """Produce a compact conversation summary that preserves extracted params."""

    def __call__(
        self,
        messages: List[Dict[str, Any]],
        extracted: Dict[str, Any],
    ) -> Awaitable[str]: ...


# Shared tool name constants so every provider maps to the same logical actions.
TOOL_UPDATE_FLAG_DRAFT = "update_flag_draft"
TOOL_CONFIRM_FLAG = "confirm_flag"

TOOL_UPDATE_FLAG_DRAFT_DESCRIPTION = (
    "Update the current flag draft with parameters extracted from the conversation. "
    "Call this whenever new info is gathered."
)
TOOL_CONFIRM_FLAG_DESCRIPTION = (
    "Called ONLY when the user has explicitly confirmed the flag config is ready "
    "to save (e.g. 'save it', 'looks good, commit', 'yes, create it')."
)

# JSON schema for ``update_flag_draft`` arguments — shared across providers so
# Anthropic and Ollama accept the same shape.
UPDATE_FLAG_DRAFT_PARAMETERS: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "flag_key": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "default_value": {},
        "cohorts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "percentage": {"type": "number"},
                    "value": {},
                },
                "required": ["name", "percentage", "value"],
            },
        },
        "parameters_schema": {"type": "object"},
    },
}

CONFIRM_FLAG_PARAMETERS: Dict[str, Any] = {"type": "object", "properties": {}}


def merge_draft(target: Dict[str, Any], source: Dict[str, Any]) -> None:
    """Merge non-null fields from ``source`` into ``target`` in-place."""
    for key, value in source.items():
        if value is not None:
            target[key] = value
