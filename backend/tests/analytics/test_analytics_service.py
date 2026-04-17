"""Tests for the analytics service layer."""

from datetime import datetime, timedelta, timezone

import pytest

from app.middleware.request_context import RequestContextManager
from app.services.analytics.analytics_model import AnalyticsEvent
from app.services.analytics.analytics_service import (
    get_flag_analytics,
    get_flag_time_series,
)
from app.services.analytics.repositories.analytics_repository import AnalyticsRepository


@pytest.fixture(autouse=True)
def _set_client_context():
    RequestContextManager.set_client_id("client-1")
    yield
    RequestContextManager.set_client_id("")


def _make_event(
    cohort_id: str | None = "c1",
    cohort_name: str | None = "control",
    reason: str = "computed",
    ts: datetime | None = None,
) -> AnalyticsEvent:
    return AnalyticsEvent(
        client_id="client-1",
        flag_id="flag-1",
        flag_key="feat.new",
        cohort_id=cohort_id,
        cohort_name=cohort_name,
        reason=reason,
        ts=ts or datetime.now(timezone.utc),
    )


async def test_get_flag_analytics_computes_percentages():
    repository = AnalyticsRepository()
    now = datetime.now(timezone.utc)
    for _ in range(3):
        await repository.insert(_make_event(cohort_name="control", ts=now))
    for _ in range(1):
        await repository.insert(_make_event(cohort_name="variant", ts=now))
    response = await get_flag_analytics(flag_id="flag-1", from_ts=None, to_ts=None)
    assert response.total_requests == 4
    assert response.flag_key == "feat.new"
    control = next(cohort for cohort in response.per_cohort if cohort.cohort_name == "control")
    variant = next(cohort for cohort in response.per_cohort if cohort.cohort_name == "variant")
    assert control.count == 3
    assert control.percentage == pytest.approx(75.0)
    assert variant.percentage == pytest.approx(25.0)


async def test_get_flag_analytics_default_window_is_last_24h():
    repository = AnalyticsRepository()
    now = datetime.now(timezone.utc)
    await repository.insert(_make_event(ts=now - timedelta(hours=1)))
    await repository.insert(_make_event(ts=now - timedelta(hours=48)))
    response = await get_flag_analytics(flag_id="flag-1", from_ts=None, to_ts=None)
    assert response.total_requests == 1
    delta = response.time_range["to"] - response.time_range["from"]
    assert abs(delta - timedelta(hours=24)) < timedelta(seconds=5)


async def test_get_flag_analytics_empty_returns_zero_total():
    response = await get_flag_analytics(flag_id="flag-1", from_ts=None, to_ts=None)
    assert response.total_requests == 0
    assert response.per_cohort == []


async def test_get_flag_time_series_rejects_invalid_interval():
    with pytest.raises(ValueError):
        await get_flag_time_series(flag_id="flag-1", from_ts=None, to_ts=None, interval="week")


async def test_get_flag_time_series_returns_buckets():
    repository = AnalyticsRepository()
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    await repository.insert(_make_event(cohort_name="control", ts=now - timedelta(hours=2)))
    await repository.insert(_make_event(cohort_name="variant", ts=now - timedelta(hours=1)))
    response = await get_flag_time_series(
        flag_id="flag-1", from_ts=None, to_ts=None, interval="hour"
    )
    assert response.interval == "hour"
    assert len(response.buckets) == 2


async def test_service_raises_when_client_id_missing():
    RequestContextManager.set_client_id("")
    with pytest.raises(ValueError):
        await get_flag_analytics(flag_id="flag-1", from_ts=None, to_ts=None)
