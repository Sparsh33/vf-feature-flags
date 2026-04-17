"""Tests for AuditRepository: insert, list with filters, cross-client isolation."""

from datetime import datetime, timedelta, timezone

from app.services.audit.audit_model import AuditLog
from app.services.audit.repositories.audit_repository import AuditRepository


def _make_log(
    client_id: str = "client-a",
    action: str = "flag.create",
    resource_type: str = "flag",
    resource_id: str = "flag-1",
    ts_offset_seconds: int = 0,
) -> AuditLog:
    return AuditLog(
        client_id=client_id,
        actor_user_id="user-1",
        actor_ip="127.0.0.1",
        actor_user_agent="pytest",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before=None,
        after={"name": "greeting"},
        ts=datetime.now(timezone.utc) + timedelta(seconds=ts_offset_seconds),
    )


async def test_insert_returns_log_with_id():
    repository = AuditRepository()
    log = _make_log()
    inserted = await repository.insert(log)
    assert inserted.id is not None
    assert inserted.client_id == "client-a"
    assert inserted.action == "flag.create"


async def test_list_logs_returns_recent_first():
    repository = AuditRepository()
    await repository.insert(_make_log(ts_offset_seconds=0))
    await repository.insert(_make_log(ts_offset_seconds=10))
    await repository.insert(_make_log(ts_offset_seconds=20))
    logs, total = await repository.list_logs(
        client_id="client-a",
        resource_type=None,
        resource_id=None,
        action=None,
        limit=50,
        skip=0,
    )
    assert total == 3
    assert len(logs) == 3
    assert logs[0].ts >= logs[1].ts >= logs[2].ts


async def test_list_logs_filters_by_action():
    repository = AuditRepository()
    await repository.insert(_make_log(action="flag.create"))
    await repository.insert(_make_log(action="flag.update"))
    await repository.insert(_make_log(action="flag.delete"))
    logs, total = await repository.list_logs(
        client_id="client-a",
        resource_type=None,
        resource_id=None,
        action="flag.update",
        limit=50,
        skip=0,
    )
    assert total == 1
    assert logs[0].action == "flag.update"


async def test_list_logs_filters_by_resource():
    repository = AuditRepository()
    await repository.insert(_make_log(resource_type="flag", resource_id="flag-1"))
    await repository.insert(_make_log(resource_type="flag", resource_id="flag-2"))
    await repository.insert(_make_log(resource_type="user", resource_id="user-1"))
    logs, total = await repository.list_logs(
        client_id="client-a",
        resource_type="flag",
        resource_id="flag-1",
        action=None,
        limit=50,
        skip=0,
    )
    assert total == 1
    assert logs[0].resource_type == "flag"
    assert logs[0].resource_id == "flag-1"


async def test_list_logs_pagination():
    repository = AuditRepository()
    for index in range(5):
        await repository.insert(_make_log(ts_offset_seconds=index))
    first_page, total = await repository.list_logs(
        client_id="client-a",
        resource_type=None,
        resource_id=None,
        action=None,
        limit=2,
        skip=0,
    )
    second_page, _ = await repository.list_logs(
        client_id="client-a",
        resource_type=None,
        resource_id=None,
        action=None,
        limit=2,
        skip=2,
    )
    assert total == 5
    assert len(first_page) == 2
    assert len(second_page) == 2
    assert {log.id for log in first_page}.isdisjoint({log.id for log in second_page})


async def test_list_logs_cross_client_isolation():
    repository = AuditRepository()
    await repository.insert(_make_log(client_id="client-a"))
    await repository.insert(_make_log(client_id="client-a"))
    await repository.insert(_make_log(client_id="client-b"))
    logs_a, total_a = await repository.list_logs(
        client_id="client-a",
        resource_type=None,
        resource_id=None,
        action=None,
        limit=50,
        skip=0,
    )
    logs_b, total_b = await repository.list_logs(
        client_id="client-b",
        resource_type=None,
        resource_id=None,
        action=None,
        limit=50,
        skip=0,
    )
    assert total_a == 2
    assert total_b == 1
    assert all(log.client_id == "client-a" for log in logs_a)
    assert all(log.client_id == "client-b" for log in logs_b)


async def test_ensure_indexes_creates_expected_indexes():
    repository = AuditRepository()
    await repository.ensure_indexes()
    collection = await repository._get_collection()
    index_info = await collection.index_information()
    index_keys = [tuple(info["key"]) for info in index_info.values()]
    assert (("client_id", 1), ("ts", -1)) in index_keys
    assert (
        ("client_id", 1),
        ("resource_type", 1),
        ("resource_id", 1),
        ("ts", -1),
    ) in index_keys
    assert (("client_id", 1), ("action", 1), ("ts", -1)) in index_keys
