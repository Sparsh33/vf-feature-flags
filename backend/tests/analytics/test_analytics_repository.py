"""Tests for AnalyticsRepository."""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.analytics.analytics_model import AnalyticsEvent
from app.services.analytics.repositories.analytics_repository import AnalyticsRepository


def _make_event(
    client_id: str = "client-1",
    flag_id: str = "flag-1",
    flag_key: str = "feat.new",
    cohort_id: str = "c1",
    cohort_name: str = "control",
    reason: str = "computed",
    ts: datetime | None = None,
) -> AnalyticsEvent:
    return AnalyticsEvent(
        client_id=client_id,
        flag_id=flag_id,
        flag_key=flag_key,
        cohort_id=cohort_id,
        cohort_name=cohort_name,
        reason=reason,
        ts=ts or datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
    )


async def test_insert_persists_event():
    repository = AnalyticsRepository()
    event = _make_event()
    await repository.insert(event)
    collection = await repository._get_collection()
    stored = await collection.find_one({"client_id": "client-1"})
    assert stored is not None
    assert stored["flag_id"] == "flag-1"
    assert stored["cohort_name"] == "control"
    assert stored["reason"] == "computed"


async def test_aggregate_by_cohort_counts_and_orders_desc():
    repository = AnalyticsRepository()
    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    for _ in range(3):
        await repository.insert(_make_event(cohort_id="c1", cohort_name="control", ts=base))
    for _ in range(5):
        await repository.insert(_make_event(cohort_id="c2", cohort_name="variant", ts=base))
    await repository.insert(
        _make_event(cohort_id=None, cohort_name=None, reason="not_found", ts=base)
    )
    from_ts = base - timedelta(hours=1)
    to_ts = base + timedelta(hours=1)
    rows = await repository.aggregate_by_cohort("client-1", "flag-1", from_ts, to_ts)
    counts = [(row["cohort_name"], row["count"]) for row in rows]
    assert counts[0] == ("variant", 5)
    assert counts[1] == ("control", 3)
    assert (None, 1) in counts


async def test_aggregate_by_cohort_is_client_scoped():
    repository = AnalyticsRepository()
    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    await repository.insert(_make_event(client_id="client-1", ts=base))
    await repository.insert(_make_event(client_id="client-2", ts=base))
    from_ts = base - timedelta(hours=1)
    to_ts = base + timedelta(hours=1)
    rows_1 = await repository.aggregate_by_cohort("client-1", "flag-1", from_ts, to_ts)
    rows_2 = await repository.aggregate_by_cohort("client-2", "flag-1", from_ts, to_ts)
    assert sum(row["count"] for row in rows_1) == 1
    assert sum(row["count"] for row in rows_2) == 1


async def test_aggregate_filters_by_time_range():
    repository = AnalyticsRepository()
    old_ts = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    new_ts = datetime(2026, 1, 2, 0, 0, tzinfo=timezone.utc)
    await repository.insert(_make_event(ts=old_ts))
    await repository.insert(_make_event(ts=new_ts))
    rows = await repository.aggregate_by_cohort(
        "client-1",
        "flag-1",
        from_ts=datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc),
        to_ts=datetime(2026, 1, 3, 0, 0, tzinfo=timezone.utc),
    )
    assert sum(row["count"] for row in rows) == 1


async def test_time_series_buckets_by_hour():
    repository = AnalyticsRepository()
    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    await repository.insert(_make_event(cohort_name="control", ts=base))
    await repository.insert(_make_event(cohort_name="control", ts=base + timedelta(minutes=30)))
    await repository.insert(_make_event(cohort_name="variant", ts=base + timedelta(hours=2)))
    await repository.insert(
        _make_event(cohort_id=None, cohort_name=None, reason="not_found", ts=base)
    )
    await repository.insert(
        _make_event(
            cohort_id="ignored", cohort_name=None, reason="fallback", ts=base + timedelta(hours=2)
        )
    )
    from_ts = base - timedelta(hours=1)
    to_ts = base + timedelta(hours=5)
    buckets = await repository.time_series("client-1", "flag-1", from_ts, to_ts, "hour")
    assert len(buckets) == 2
    first = buckets[0]
    assert first["ts"] == datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    assert first["counts_by_cohort"]["control"] == 2
    assert first["counts_by_cohort"]["__not_found__"] == 1
    second = buckets[1]
    assert second["ts"] == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert second["counts_by_cohort"]["variant"] == 1
    assert second["counts_by_cohort"]["__fallback__"] == 1


async def test_time_series_rejects_bad_interval():
    repository = AnalyticsRepository()
    base = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError):
        await repository.time_series("client-1", "flag-1", base, base + timedelta(hours=1), "week")
