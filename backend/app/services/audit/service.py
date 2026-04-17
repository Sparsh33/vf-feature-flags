"""Public audit service API for other domains."""

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.common.logging_helpers import LoggingData, log_warning
from app.middleware.request_context import RequestContextManager
from app.services.audit.tasks import record_audit_event


def _safe_log_warning(message: str, context: Dict[str, Any]) -> None:
    try:
        log_warning(LoggingData(message=message, context=context))
    except Exception:
        # Logging must never break audit_emit's no-raise contract.
        pass


def audit_emit(
    action: str,
    resource_type: str,
    resource_id: str,
    before: Optional[Dict[str, Any]] = None,
    after: Optional[Dict[str, Any]] = None,
) -> None:
    """Queue an audit event. Reads actor info from RequestContextManager. Never raises."""
    actor = RequestContextManager.get_actor_info()
    client_id = actor.get("client_id")
    if not client_id:
        _safe_log_warning(
            "audit_emit skipped: client_id missing from request context",
            {"action": action, "resource_type": resource_type},
        )
        return
    payload: Dict[str, Any] = {
        "client_id": client_id,
        "actor_user_id": actor.get("user_id"),
        "actor_ip": actor.get("ip"),
        "actor_user_agent": actor.get("user_agent"),
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "before": before,
        "after": after,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    try:
        record_audit_event.delay(payload)
    except Exception as exc:
        _safe_log_warning(
            "audit_emit: failed to enqueue celery task",
            {"action": action, "error": str(exc)},
        )
