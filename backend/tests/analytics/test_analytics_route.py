"""HTTP endpoint tests for the analytics routes."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, Header, HTTPException
from httpx import ASGITransport, AsyncClient

from app.middleware.request_context import RequestContextManager
from app.services.analytics.analytics_model import AnalyticsEvent
from app.services.analytics.analytics_route import router as analytics_router
from app.services.analytics.repositories.analytics_repository import AnalyticsRepository
from app.services.auth.auth_model import UserPublic
from app.services.auth.dependencies import get_current_user


async def _header_current_user(
    x_client_id: str = Header(default=None, alias="X-Client-Id"),
) -> UserPublic:
    if not x_client_id:
        raise HTTPException(status_code=401, detail="Unauthorized: X-Client-Id required")
    RequestContextManager.set_client_id(x_client_id)
    return UserPublic(
        id="test-user",
        email="test@example.com",
        client_id=x_client_id,
        role="admin",
    )


@pytest.fixture
async def analytics_client():
    app = FastAPI()
    app.include_router(analytics_router, prefix="/api/analytics")
    # Override the JWT-based auth dependency with a simple header-based one for testing.
    app.dependency_overrides[get_current_user] = _header_current_user
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client


async def _seed_event(client_id: str, cohort_name: str, ts: datetime) -> None:
    repository = AnalyticsRepository()
    await repository.insert(
        AnalyticsEvent(
            client_id=client_id,
            flag_id="flag-1",
            flag_key="feat.new",
            cohort_id="c1",
            cohort_name=cohort_name,
            reason="computed",
            ts=ts,
        )
    )


async def test_get_flag_analytics_returns_expected_shape(analytics_client):
    now = datetime.now(timezone.utc)
    await _seed_event("client-1", "control", now - timedelta(minutes=10))
    await _seed_event("client-1", "variant", now - timedelta(minutes=5))
    response = await analytics_client.get(
        "/api/analytics/flags/flag-1",
        headers={"X-Client-Id": "client-1"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["flag_id"] == "flag-1"
    assert payload["flag_key"] == "feat.new"
    assert payload["total_requests"] == 2
    assert {row["cohort_name"] for row in payload["per_cohort"]} == {"control", "variant"}
    assert "from" in payload["time_range"] and "to" in payload["time_range"]


async def test_get_flag_analytics_is_client_scoped(analytics_client):
    now = datetime.now(timezone.utc)
    await _seed_event("client-1", "control", now - timedelta(minutes=1))
    await _seed_event("client-2", "control", now - timedelta(minutes=1))
    response = await analytics_client.get(
        "/api/analytics/flags/flag-1",
        headers={"X-Client-Id": "client-2"},
    )
    assert response.status_code == 200
    assert response.json()["total_requests"] == 1


async def test_get_flag_analytics_requires_client_header(analytics_client):
    response = await analytics_client.get("/api/analytics/flags/flag-1")
    assert response.status_code == 401


async def test_time_series_endpoint_shape(analytics_client):
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    await _seed_event("client-1", "control", now - timedelta(hours=1))
    await _seed_event("client-1", "variant", now - timedelta(hours=2))
    response = await analytics_client.get(
        "/api/analytics/flags/flag-1/time-series",
        headers={"X-Client-Id": "client-1"},
        params={"interval": "hour"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["interval"] == "hour"
    assert isinstance(payload["buckets"], list)
    assert len(payload["buckets"]) == 2


async def test_time_series_rejects_invalid_interval(analytics_client):
    response = await analytics_client.get(
        "/api/analytics/flags/flag-1/time-series",
        headers={"X-Client-Id": "client-1"},
        params={"interval": "week"},
    )
    assert response.status_code == 400
