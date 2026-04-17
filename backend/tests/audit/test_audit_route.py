"""Tests for the audit list endpoint."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, Header, HTTPException
from httpx import ASGITransport, AsyncClient

from app.services.audit import audit_route as audit_route_module
from app.services.audit.audit_model import AuditLog
from app.services.audit.audit_route import router as audit_router
from app.services.audit.repositories.audit_repository import AuditRepository


async def _header_client_id(x_client_id: str = Header(default=None, alias="X-Client-Id")) -> str:
    if not x_client_id:
        raise HTTPException(status_code=401, detail="Unauthorized: X-Client-Id required")
    return x_client_id


@pytest.fixture
async def audit_client():
    app = FastAPI()
    app.include_router(audit_router, prefix="/api/audit")
    # Override the JWT-based auth dependency with a simple header-based one for testing.
    app.dependency_overrides[audit_route_module._resolve_client_id] = _header_client_id
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


def _log(
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


async def test_list_endpoint_happy_path(audit_client):
    repository = AuditRepository()
    await repository.insert(_log(ts_offset_seconds=0))
    await repository.insert(_log(ts_offset_seconds=5))
    response = await audit_client.get("/api/audit/", headers={"X-Client-Id": "client-a"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["logs"]) == 2


async def test_list_endpoint_filters_by_action(audit_client):
    repository = AuditRepository()
    await repository.insert(_log(action="flag.create"))
    await repository.insert(_log(action="flag.update"))
    response = await audit_client.get(
        "/api/audit/",
        params={"action": "flag.update"},
        headers={"X-Client-Id": "client-a"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["logs"][0]["action"] == "flag.update"


async def test_list_endpoint_filters_by_resource(audit_client):
    repository = AuditRepository()
    await repository.insert(_log(resource_type="flag", resource_id="flag-1"))
    await repository.insert(_log(resource_type="user", resource_id="user-9"))
    response = await audit_client.get(
        "/api/audit/",
        params={"resource_type": "user", "resource_id": "user-9"},
        headers={"X-Client-Id": "client-a"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["logs"][0]["resource_type"] == "user"


async def test_list_endpoint_pagination(audit_client):
    repository = AuditRepository()
    for index in range(5):
        await repository.insert(_log(ts_offset_seconds=index))
    response = await audit_client.get(
        "/api/audit/",
        params={"limit": 2, "skip": 0},
        headers={"X-Client-Id": "client-a"},
    )
    body = response.json()
    assert body["total"] == 5
    assert len(body["logs"]) == 2


async def test_list_endpoint_scoped_to_client(audit_client):
    repository = AuditRepository()
    await repository.insert(_log(client_id="client-a"))
    await repository.insert(_log(client_id="client-b"))
    response = await audit_client.get("/api/audit/", headers={"X-Client-Id": "client-b"})
    body = response.json()
    assert body["total"] == 1


async def test_list_endpoint_requires_client_id(audit_client):
    response = await audit_client.get("/api/audit/")
    assert response.status_code == 401
