"""Auth-specific fixtures: ensure auth indexes on the mock mongo per test."""

import pytest

from app.services.auth.repositories.client_repository import ensure_client_indexes
from app.services.auth.repositories.user_repository import ensure_user_indexes


@pytest.fixture(autouse=True)
async def _apply_auth_indexes(_mock_mongo):
    await ensure_user_indexes()
    await ensure_client_indexes()
    yield
