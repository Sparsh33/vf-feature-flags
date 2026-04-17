"""Business logic for analytics: aggregation reads + async event emission."""

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.common.logging_helpers import LoggingData, log_warning
from app.middleware.request_context import RequestContextManager
from app.services.analytics.analytics_model import (
    CohortStats,
    FlagAnalyticsResponse,
    FlagAnalyticsTimeSeriesResponse,
    TimeSeriesBucket,
)
from app.services.analytics.repositories.analytics_repository import (
    VALID_INTERVALS,
    AnalyticsRepository,
)

DEFAULT_WINDOW_HOURS = 24


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _resolve_client_id() -> str:
    client_id = RequestContextManager.get_client_id()
    if not client_id:
        raise ValueError("client_id missing from request context")
    return client_id


def _resolve_range(
    from_ts: Optional[datetime],
    to_ts: Optional[datetime],
) -> tuple[datetime, datetime]:
    resolved_to = to_ts or _utcnow()
    resolved_from = from_ts or resolved_to - timedelta(hours=DEFAULT_WINDOW_HOURS)
    if resolved_from > resolved_to:
        raise ValueError("from_ts must be <= to_ts")
    return resolved_from, resolved_to


async def _resolve_flag_key(client_id: str, flag_id: str) -> str:
    repository = AnalyticsRepository()
    return await repository.get_latest_flag_key(client_id=client_id, flag_id=flag_id)


async def get_flag_analytics(
    flag_id: str,
    from_ts: Optional[datetime],
    to_ts: Optional[datetime],
) -> FlagAnalyticsResponse:
    client_id = _resolve_client_id()
    resolved_from, resolved_to = _resolve_range(from_ts, to_ts)
    repository = AnalyticsRepository()
    raw_rows = await repository.aggregate_by_cohort(
        client_id=client_id,
        flag_id=flag_id,
        from_ts=resolved_from,
        to_ts=resolved_to,
    )
    total = sum(row["count"] for row in raw_rows)
    per_cohort = [
        CohortStats(
            cohort_id=row.get("cohort_id"),
            cohort_name=row.get("cohort_name"),
            count=row["count"],
            percentage=(row["count"] / total * 100.0) if total else 0.0,
        )
        for row in raw_rows
    ]
    flag_key = await _resolve_flag_key(client_id, flag_id)
    return FlagAnalyticsResponse(
        flag_id=flag_id,
        flag_key=flag_key,
        total_requests=total,
        per_cohort=per_cohort,
        time_range={"from": resolved_from, "to": resolved_to},
    )


async def get_flag_time_series(
    flag_id: str,
    from_ts: Optional[datetime],
    to_ts: Optional[datetime],
    interval: str,
) -> FlagAnalyticsTimeSeriesResponse:
    if interval not in VALID_INTERVALS:
        raise ValueError(f"invalid interval: {interval}")
    client_id = _resolve_client_id()
    resolved_from, resolved_to = _resolve_range(from_ts, to_ts)
    repository = AnalyticsRepository()
    raw_buckets = await repository.time_series(
        client_id=client_id,
        flag_id=flag_id,
        from_ts=resolved_from,
        to_ts=resolved_to,
        interval=interval,
    )
    buckets = [
        TimeSeriesBucket(ts=row["ts"], counts_by_cohort=row["counts_by_cohort"])
        for row in raw_buckets
    ]
    flag_key = await _resolve_flag_key(client_id, flag_id)
    return FlagAnalyticsTimeSeriesResponse(
        flag_id=flag_id,
        flag_key=flag_key,
        interval=interval,
        buckets=buckets,
    )


def emit_analytics_event(
    flag_id: str,
    flag_key: str,
    client_id: str,
    cohort_id: Optional[str],
    cohort_name: Optional[str],
    reason: str,
) -> None:
    """Fire-and-forget helper for eval service. Never raises."""
    try:
        from app.services.analytics.tasks import record_eval_event

        payload = {
            "client_id": client_id,
            "flag_id": flag_id,
            "flag_key": flag_key,
            "cohort_id": cohort_id,
            "cohort_name": cohort_name,
            "reason": reason,
            "ts": datetime.utcnow().isoformat(),
        }
        record_eval_event.delay(payload)
    except Exception as exc:
        log_warning(
            LoggingData(
                message="analytics.emit_event_failed",
                context={
                    "flag_id": flag_id,
                    "flag_key": flag_key,
                    "client_id": client_id,
                    "error": str(exc),
                },
            )
        )
