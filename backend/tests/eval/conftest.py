"""Eval-package fixtures: stub redis_client.get() to avoid real connections."""

from typing import Dict, Optional
from unittest.mock import AsyncMock

import pytest

from app.database import redis_client as redis_module
from app.services.flag.flag_model import Cohort, FlagConfig


class _FakeRedis:
    """Minimal in-memory async fake supporting get/set with ex parameter."""

    def __init__(self) -> None:
        self.store: Dict[str, str] = {}
        self.raise_on_get = False
        self.raise_on_set = False

    async def get(self, key: str) -> Optional[str]:
        if self.raise_on_get:
            raise RuntimeError("redis get down")
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        if self.raise_on_set:
            raise RuntimeError("redis set down")
        self.store[key] = value
        return True


@pytest.fixture
def fake_redis(monkeypatch) -> _FakeRedis:
    fake = _FakeRedis()
    monkeypatch.setattr(redis_module.redis_client, "_client", fake, raising=False)
    monkeypatch.setattr(redis_module.redis_client, "get", lambda: fake)
    return fake


@pytest.fixture
def mock_flag_repo(monkeypatch) -> AsyncMock:
    """Mock FlagService.get_flag_by_key_for_eval so eval_service._load_flag succeeds.

    Retains the historical ``mock_flag_repo`` name — now wraps the service layer
    method instead of the repository, per the cross-domain boundary rule."""
    fake_loader = AsyncMock()
    monkeypatch.setattr(
        "app.services.flag.flag_service.FlagService.get_flag_by_key_for_eval",
        fake_loader,
    )
    return fake_loader


@pytest.fixture
def sample_flag() -> FlagConfig:
    return FlagConfig(
        id="flag-abc",
        flag_key="new_checkout",
        client_id="client-1",
        name="New Checkout",
        status="active",
        is_deleted=False,
        default_value=False,
        cohorts=[
            Cohort(id="c1", name="on", percentage=50.0, value=True),
            Cohort(id="c2", name="off", percentage=50.0, value=False),
        ],
    )
