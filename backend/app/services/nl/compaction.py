"""Compaction logic: summarize long conversations while preserving extracted params."""

from app.config.settings import settings
from app.services.nl.nl_model import NLMessage, NLSession
from app.services.nl.providers.dispatcher import summarize_for_compaction


def _model_input_budget() -> int:
    return settings.nl_input_token_budget


def _compaction_trigger() -> float:
    return settings.nl_compaction_trigger


# Backwards-compatible module-level aliases. Tests and legacy code that imported
# these constants see the live settings values. Kept as dynamic lookups via
# ``__getattr__`` below so changing settings at runtime (e.g. in a fixture) is
# reflected immediately — static module attributes would cache the import-time value.
def __getattr__(name: str):
    if name == "MODEL_INPUT_BUDGET":
        return _model_input_budget()
    if name == "COMPACTION_TRIGGER":
        return _compaction_trigger()
    raise AttributeError(f"module 'compaction' has no attribute {name!r}")


def should_compact(input_tokens_used: int) -> bool:
    return input_tokens_used >= int(_model_input_budget() * _compaction_trigger())


async def compact_session(session: NLSession) -> NLSession:
    """Summarize session.messages into a single seeded assistant turn.

    Extracted params remain intact on the session; they are re-injected in every system
    prompt, so they are never dropped even if compaction summary text omits them.
    """
    history_dicts = [{"role": msg.role, "content": msg.content} for msg in session.messages]
    extracted_dict = session.extracted.model_dump()
    summary = await summarize_for_compaction(history_dicts, extracted_dict)
    seeded = NLMessage(
        role="assistant",
        content=f"[Compacted conversation summary]\n{summary}",
    )
    session.messages = [seeded]
    session.last_compacted_summary = summary
    session.compaction_count += 1
    return session
