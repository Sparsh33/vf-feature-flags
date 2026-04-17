"""Tests for the analytics Celery task."""

from datetime import datetime, timezone
from unittest.mock import patch

from app.services.analytics.repositories.analytics_repository import AnalyticsRepository
from app.services.analytics.tasks import _record_eval_event_async


async def test_record_eval_event_async_deserializes_ts_and_inserts():
    ts = datetime(2026, 1, 1, 10, 30, tzinfo=timezone.utc)
    payload = {
        "client_id": "client-1",
        "flag_id": "flag-1",
        "flag_key": "feat.new",
        "cohort_id": "c1",
        "cohort_name": "control",
        "reason": "computed",
        "ts": ts.isoformat(),
    }
    with (
        patch("app.services.analytics.tasks.mongodb.connect", return_value=None),
        patch("app.services.analytics.tasks.mongodb.close", return_value=None),
    ):
        await _record_eval_event_async(payload)
    repository = AnalyticsRepository()
    collection = await repository._get_collection()
    stored = await collection.find_one({"client_id": "client-1"})
    assert stored is not None
    assert stored["flag_key"] == "feat.new"
    assert stored["cohort_name"] == "control"
    assert stored["reason"] == "computed"
    stored_ts = stored["ts"]
    if stored_ts.tzinfo is None:
        stored_ts = stored_ts.replace(tzinfo=timezone.utc)
    assert stored_ts == ts


async def test_record_eval_event_async_handles_fallback_payload():
    ts = datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc)
    payload = {
        "client_id": "client-1",
        "flag_id": "flag-1",
        "flag_key": "feat.new",
        "cohort_id": None,
        "cohort_name": None,
        "reason": "not_found",
        "ts": ts.isoformat(),
    }
    with (
        patch("app.services.analytics.tasks.mongodb.connect", return_value=None),
        patch("app.services.analytics.tasks.mongodb.close", return_value=None),
    ):
        await _record_eval_event_async(payload)
    repository = AnalyticsRepository()
    collection = await repository._get_collection()
    stored = await collection.find_one({"reason": "not_found"})
    assert stored is not None
    assert stored["cohort_id"] is None
    assert stored["cohort_name"] is None
