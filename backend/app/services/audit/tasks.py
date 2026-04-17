"""Celery task to persist audit events asynchronously."""

import asyncio
from typing import Any, Dict

from celery.exceptions import Retry
from pymongo.errors import PyMongoError

from app.common.logging_helpers import LoggingData, log_error, log_warning
from app.database.config import mongodb
from app.services.audit.audit_model import AuditLog
from app.services.audit.repositories.audit_repository import AuditRepository
from celery_app import celery


async def _run_insert(payload: Dict[str, Any]) -> None:
    await mongodb.connect()
    log = AuditLog(**payload)
    repository = AuditRepository()
    await repository.insert(log)


def _safe_log_warning(message: str, context: Dict[str, Any]) -> None:
    try:
        log_warning(LoggingData(message=message, context=context))
    except Exception:
        pass


def _safe_log_error(message: str, context: Dict[str, Any], error: Exception) -> None:
    try:
        log_error(LoggingData(message=message, context=context, error=error))
    except Exception:
        pass


@celery.task(name="audit.record", bind=True, max_retries=3, default_retry_delay=5)
def record_audit_event(self, payload: Dict[str, Any]) -> None:  # type: ignore[no-untyped-def]
    """Persist an audit event. Retries on transient Mongo errors."""
    try:
        asyncio.run(_run_insert(payload))
    except PyMongoError as exc:
        _safe_log_warning(
            "audit.record transient error; will retry",
            {"action": payload.get("action"), "attempt": self.request.retries},
        )
        raise self.retry(exc=exc)
    except Retry:
        raise
    except Exception as exc:
        _safe_log_error(
            "audit.record failed permanently",
            {"action": payload.get("action")},
            exc,
        )
        raise
