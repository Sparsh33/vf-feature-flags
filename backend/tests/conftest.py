"""Shared pytest fixtures: in-memory Mongo + httpx AsyncClient."""

from typing import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.database import config as db_config


@pytest.fixture(autouse=True)
def _mock_mongo(monkeypatch):
    """Replace the real motor client with a mongomock-motor client."""
    mock_client = AsyncMongoMockClient()
    db_config.mongodb._client = mock_client  # type: ignore[attr-defined]
    db_config.mongodb._database = mock_client["vf_feature_flags_test"]  # type: ignore[attr-defined]
    yield
    db_config.mongodb._client = None  # type: ignore[attr-defined]
    db_config.mongodb._database = None  # type: ignore[attr-defined]


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as async_client:
        yield async_client
