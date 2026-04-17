"""Celery tasks for recording analytics events asynchronously."""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict

from pymongo.errors import AutoReconnect, ConnectionFailure, NetworkTimeout

from app.database.config import mongodb
from app.services.analytics.analytics_model import AnalyticsEvent
from app.services.analytics.repositories.analytics_repository import AnalyticsRepository
from celery_app import celery

logger = logging.getLogger(__name__)

TRANSIENT_MONGO_ERRORS = (AutoReconnect, ConnectionFailure, NetworkTimeout)


@celery.task(
    name="analytics.record_eval_event",
    bind=True,
    max_retries=3,
    default_retry_delay=5,
)
def record_eval_event(self, payload: Dict[str, Any]) -> None:
    """Persist an analytics event from an eval call.

    Payload: {client_id, flag_id, flag_key, cohort_id, cohort_name, reason, ts}
    where `ts` is an ISO-8601 string.
    """
    try:
        asyncio.run(_record_eval_event_async(payload))
    except TRANSIENT_MONGO_ERRORS as exc:
        logger.warning("Transient mongo error recording analytics event: %s", exc)
        raise self.retry(exc=exc)
    except Exception as exc:
        logger.exception("Failed to record analytics event: %s", exc)
        raise


async def _record_eval_event_async(payload: Dict[str, Any]) -> None:
    await mongodb.connect()
    ts_value = payload.get("ts")
    if isinstance(ts_value, str):
        ts = datetime.fromisoformat(ts_value)
    elif isinstance(ts_value, datetime):
        ts = ts_value
    else:
        raise ValueError(f"invalid ts in payload: {ts_value!r}")
    event = AnalyticsEvent(
        client_id=payload["client_id"],
        flag_id=payload["flag_id"],
        flag_key=payload["flag_key"],
        cohort_id=payload.get("cohort_id"),
        cohort_name=payload.get("cohort_name"),
        reason=payload["reason"],
        ts=ts,
    )
    repository = AnalyticsRepository()
    await repository.insert(event)
