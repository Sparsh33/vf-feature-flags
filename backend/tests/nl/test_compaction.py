"""Tests for the compaction module: threshold math + session summarization."""

import json
import re

from app.services.nl import compaction
from app.services.nl.compaction import (
    COMPACTION_TRIGGER,
    MODEL_INPUT_BUDGET,
    compact_session,
    should_compact,
)
from app.services.nl.nl_model import ExtractedParams, NLMessage, NLSession


def test_should_compact_below_threshold():
    assert should_compact(0) is False
    assert should_compact(int(MODEL_INPUT_BUDGET * COMPACTION_TRIGGER) - 1) is False


def test_should_compact_at_threshold():
    assert should_compact(int(MODEL_INPUT_BUDGET * COMPACTION_TRIGGER)) is True


def test_should_compact_above_threshold():
    assert should_compact(MODEL_INPUT_BUDGET) is True


async def test_compact_session_preserves_extracted(mock_summarize):
    def _summary(messages, extracted):
        return (
            "Discussed enabling dark mode for 50% of users.\n\n"
            f"EXTRACTED_PARAMS_JSON: {json.dumps(extracted, sort_keys=True)}"
        )

    mock_summarize(_summary)
    session = NLSession(
        client_id="client-a",
        user_id="user-1",
        messages=[
            NLMessage(role="user", content="hello"),
            NLMessage(role="assistant", content="hi"),
            NLMessage(role="user", content="flag key is dark_mode"),
        ],
        extracted=ExtractedParams(
            flag_key="dark_mode",
            name="Dark Mode",
            cohorts=[{"name": "on", "percentage": 50, "value": True}],
        ),
    )
    result = await compact_session(session)
    assert result.extracted.flag_key == "dark_mode"
    assert result.extracted.name == "Dark Mode"
    assert result.extracted.cohorts == [{"name": "on", "percentage": 50, "value": True}]
    assert result.compaction_count == 1
    assert result.last_compacted_summary is not None
    assert len(result.messages) == 1
    assert result.messages[0].role == "assistant"
    # Summary must re-state extracted params as JSON for recoverability.
    match = re.search(r"EXTRACTED_PARAMS_JSON:\s*(\{.*\})", result.last_compacted_summary)
    assert match is not None
    restated = json.loads(match.group(1))
    assert restated["flag_key"] == "dark_mode"
    assert restated["name"] == "Dark Mode"


async def test_compact_session_increments_counter(mock_summarize):
    mock_summarize(lambda msgs, extracted: "summary")
    session = NLSession(
        client_id="client-a",
        user_id="user-1",
        compaction_count=2,
        messages=[NLMessage(role="user", content="hi")],
    )
    result = await compact_session(session)
    assert result.compaction_count == 3


async def test_should_compact_exactly_at_70_percent():
    threshold = int(MODEL_INPUT_BUDGET * COMPACTION_TRIGGER)
    assert compaction.should_compact(threshold) is True
    assert compaction.should_compact(threshold - 1) is False
