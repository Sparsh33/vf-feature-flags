"""Eval-package fixtures: stub redis_client.get() to avoid real connections."""

from typing import Any, Dict, Optional
from unittest.mock import AsyncMock

import pytest

from app.database import redis_client as redis_module


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
def mock_flag_repo(monkeypatch):
    """Install a fake FlagRepository so eval_service._load_flag succeeds."""
    import sys
    import types

    flag_pkg = sys.modules.get("app.services.flag")
    if flag_pkg is None:
        flag_pkg = types.ModuleType("app.services.flag")
        sys.modules["app.services.flag"] = flag_pkg
    repositories_pkg = types.ModuleType("app.services.flag.repositories")
    sys.modules["app.services.flag.repositories"] = repositories_pkg
    repo_module = types.ModuleType("app.services.flag.repositories.flag_repository")
    fake_repo = AsyncMock()

    class _FakeRepoCls:
        def __init__(self) -> None:
            self.get_by_key = fake_repo

    repo_module.FlagRepository = _FakeRepoCls  # type: ignore[attr-defined]
    sys.modules["app.services.flag.repositories.flag_repository"] = repo_module
    yield fake_repo
    sys.modules.pop("app.services.flag.repositories.flag_repository", None)
    sys.modules.pop("app.services.flag.repositories", None)


@pytest.fixture
def sample_flag() -> Dict[str, Any]:
    return {
        "id": "flag-abc",
        "flag_key": "new_checkout",
        "client_id": "client-1",
        "status": "active",
        "is_deleted": False,
        "default_value": False,
        "cohorts": [
            {"id": "c1", "name": "on", "percentage": 50.0, "value": True},
            {"id": "c2", "name": "off", "percentage": 50.0, "value": False},
        ],
    }
