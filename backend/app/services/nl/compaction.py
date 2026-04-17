"""Compaction logic: summarize long conversations while preserving extracted params."""

from app.services.nl.claude_client import summarize_for_compaction
from app.services.nl.nl_model import NLMessage, NLSession

MODEL_INPUT_BUDGET = 200_000
COMPACTION_TRIGGER = 0.70


def should_compact(input_tokens_used: int) -> bool:
    return input_tokens_used >= int(MODEL_INPUT_BUDGET * COMPACTION_TRIGGER)


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
