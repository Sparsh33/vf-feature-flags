"""Tests for audit_emit: payload construction, actor info, graceful failure."""

from unittest.mock import patch

from app.middleware.request_context import RequestContextManager
from app.services.audit.service import audit_emit


def _set_request_context(client_id: str = "client-a", user_id: str = "user-1") -> None:
    RequestContextManager.set_client_id(client_id)
    RequestContextManager.set_user_id(user_id)
    RequestContextManager.set_actor_info(ip="10.0.0.1", user_agent="pytest-agent")


def test_audit_emit_calls_delay_with_actor_info():
    _set_request_context()
    with patch("app.services.audit.service.record_audit_event.delay") as mock_delay:
        audit_emit(
            action="flag.create",
            resource_type="flag",
            resource_id="flag-1",
            before=None,
            after={"name": "greeting"},
        )
    mock_delay.assert_called_once()
    payload = mock_delay.call_args[0][0]
    assert payload["client_id"] == "client-a"
    assert payload["actor_user_id"] == "user-1"
    assert payload["actor_ip"] == "10.0.0.1"
    assert payload["actor_user_agent"] == "pytest-agent"
    assert payload["action"] == "flag.create"
    assert payload["resource_type"] == "flag"
    assert payload["resource_id"] == "flag-1"
    assert payload["before"] is None
    assert payload["after"] == {"name": "greeting"}
    assert "ts" in payload


def test_audit_emit_without_client_id_skips():
    RequestContextManager.set_client_id("")
    with patch("app.services.audit.service.record_audit_event.delay") as mock_delay:
        audit_emit(action="flag.create", resource_type="flag", resource_id="flag-1")
    mock_delay.assert_not_called()


def test_audit_emit_swallows_celery_failure():
    _set_request_context()
    with patch(
        "app.services.audit.service.record_audit_event.delay",
        side_effect=RuntimeError("broker down"),
    ) as mock_delay:
        audit_emit(action="flag.update", resource_type="flag", resource_id="flag-1")
    mock_delay.assert_called_once()


def test_audit_emit_before_and_after_passthrough():
    _set_request_context()
    before = {"enabled": False}
    after = {"enabled": True}
    with patch("app.services.audit.service.record_audit_event.delay") as mock_delay:
        audit_emit(
            action="flag.update",
            resource_type="flag",
            resource_id="flag-42",
            before=before,
            after=after,
        )
    payload = mock_delay.call_args[0][0]
    assert payload["before"] == before
    assert payload["after"] == after
