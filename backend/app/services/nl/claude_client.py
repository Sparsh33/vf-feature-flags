"""Deprecated shim — kept for backwards compatibility.

The NL service now selects between Anthropic and Ollama via
``app.services.nl.providers.dispatcher``. This module re-exports the dispatcher
entry points plus the original Anthropic-specific helpers so existing imports
(and older tests) keep working. Import from ``providers`` in new code.
"""

import warnings

from app.services.nl.providers.anthropic_provider import (  # noqa: F401
    MAX_TOKENS,
    MODEL,
    TOOLS,
    _build_cached_system,
    _build_cached_tools,
    _get_client,
)
from app.services.nl.providers.base import merge_draft as _merge_draft  # noqa: F401
from app.services.nl.providers.dispatcher import chat_turn, summarize_for_compaction  # noqa: F401

warnings.warn(
    "app.services.nl.claude_client is deprecated; "
    "import from app.services.nl.providers.dispatcher instead.",
    DeprecationWarning,
    stacklevel=2,
)
