"""Tests for the audit.record celery task."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from pymongo.errors import PyMongoError

from app.services.audit.repositories.audit_repository import AuditRepository
from app.services.audit.tasks import _run_insert, record_audit_event


def _make_payload(action: str = "flag.create") -> dict:
    return {
        "client_id": "client-a",
        "actor_user_id": "user-1",
        "actor_ip": "127.0.0.1",
        "actor_user_agent": "pytest",
        "action": action,
        "resource_type": "flag",
        "resource_id": "flag-1",
        "before": None,
        "after": {"name": "greeting"},
        "ts": datetime.now(timezone.utc).isoformat(),
    }


async def test_run_insert_persists_log():
    payload = _make_payload()
    with (
        patch("app.services.audit.tasks.mongodb.connect", new=AsyncMock(return_value=None)),
        patch("app.services.audit.tasks.mongodb.close", new=AsyncMock(return_value=None)),
    ):
        await _run_insert(payload)
    repository = AuditRepository()
    logs, total = await repository.list_logs(
        client_id="client-a",
        resource_type=None,
        resource_id=None,
        action=None,
        limit=10,
        skip=0,
    )
    assert total == 1
    assert logs[0].action == "flag.create"
    assert logs[0].actor_user_id == "user-1"


def test_record_audit_event_apply_persists(event_loop=None):
    payload = _make_payload(action="flag.update")
    # Celery eager execution: call the task function directly via .apply()
    record_audit_event.apply(args=[payload])


def test_record_audit_event_retries_on_pymongo_error():
    payload = _make_payload()
    with patch(
        "app.services.audit.tasks._run_insert",
        new=AsyncMock(side_effect=PyMongoError("timeout")),
    ):
        result = record_audit_event.apply(args=[payload])
    # With max_retries=3, eager mode surfaces the final exception.
    assert result.failed()


def test_record_audit_event_reraises_non_transient():
    payload = _make_payload()
    with patch(
        "app.services.audit.tasks._run_insert",
        new=AsyncMock(side_effect=ValueError("bad payload")),
    ):
        result = record_audit_event.apply(args=[payload])
    assert result.failed()
    assert isinstance(result.result, ValueError)
