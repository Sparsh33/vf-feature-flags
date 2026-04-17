"""Provider dispatcher.

Reads ``settings.nl_provider`` at call time and forwards to the matching
provider module. The NL service imports ``chat_turn`` / ``summarize_for_compaction``
from here and never touches provider modules directly, so the backend can be
switched via config without any code changes.
"""

from typing import Any, Dict, List, Tuple

from app.config.settings import settings
from app.services.nl.providers import anthropic_provider, ollama_provider

PROVIDER_OLLAMA = "ollama"
PROVIDER_ANTHROPIC = "anthropic"


def _resolve_provider():
    provider_name = (settings.nl_provider or PROVIDER_OLLAMA).lower()
    if provider_name == PROVIDER_ANTHROPIC:
        return anthropic_provider
    if provider_name == PROVIDER_OLLAMA:
        return ollama_provider
    raise ValueError(
        f"Unknown nl_provider '{settings.nl_provider}'. "
        f"Expected one of: '{PROVIDER_OLLAMA}', '{PROVIDER_ANTHROPIC}'."
    )


async def chat_turn(
    system_prompt: str,
    history: List[Dict[str, Any]],
    user_message: str,
) -> Tuple[str, Dict[str, Any], bool, int]:
    """Delegate one chat turn to the configured provider."""
    provider = _resolve_provider()
    return await provider.chat_turn(system_prompt, history, user_message)


async def summarize_for_compaction(
    messages: List[Dict[str, Any]], extracted: Dict[str, Any]
) -> str:
    """Delegate compaction summarisation to the configured provider."""
    provider = _resolve_provider()
    return await provider.summarize_for_compaction(messages, extracted)
