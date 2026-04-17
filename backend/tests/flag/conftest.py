"""Fixtures shared across flag domain tests."""

from typing import AsyncIterator
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.database import redis_client as redis_client_module
from app.middleware.request_context import RequestContextManager
from app.services.flag.flag_model import Cohort, FlagCreateRequest
from app.services.flag.flag_service import FlagService


@pytest.fixture(autouse=True)
def _mock_redis(monkeypatch) -> AsyncMock:
    """Replace the real redis client with an AsyncMock so no real Redis is needed."""
    fake_redis = AsyncMock()

    async def _scan_iter(*_args, **_kwargs):
        if False:  # pragma: no cover - empty async generator
            yield None

    fake_redis.scan_iter = _scan_iter
    fake_redis.delete = AsyncMock(return_value=0)
    monkeypatch.setattr(redis_client_module.redis_client, "_client", fake_redis)
    return fake_redis


@pytest.fixture(autouse=True)
def _mock_audit_emit(monkeypatch) -> None:
    """Prevent the real audit_emit from trying to enqueue Celery tasks."""
    monkeypatch.setattr("app.services.flag.flag_service.audit_emit", lambda **kwargs: None)


@pytest.fixture(autouse=True)
def _request_context() -> None:
    """Populate request context with a default user + client for each test."""
    RequestContextManager.set_user_id("user-1")
    RequestContextManager.set_client_id("client-a")
    RequestContextManager.set_request_id("req-1")


@pytest_asyncio.fixture(autouse=True)
async def _ensure_flag_indexes() -> None:
    """Build the flag collection indexes so unique constraints fire in tests."""
    from app.services.flag.repositories.flag_repository import ensure_flag_indexes

    await ensure_flag_indexes()


@pytest.fixture
def service() -> FlagService:
    return FlagService()


@pytest.fixture
def cohorts_50_50() -> list[Cohort]:
    return [
        Cohort(id="", name="control", percentage=50.0, value=False),
        Cohort(id="", name="treatment", percentage=50.0, value=True),
    ]


@pytest.fixture
def create_request(cohorts_50_50) -> FlagCreateRequest:
    return FlagCreateRequest(
        flag_key="new_feature",
        name="New Feature",
        description="Gate for new feature",
        default_value=False,
        cohorts=cohorts_50_50,
        status="active",
    )


@pytest_asyncio.fixture
async def http_client() -> AsyncIterator[AsyncClient]:
    from app.services.flag.flag_route import fallback_current_user
    from main import app

    try:
        from app.services.auth.dependencies import get_current_user

        app.dependency_overrides[get_current_user] = fallback_current_user
    except ImportError:
        pass
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
    app.dependency_overrides.clear()
