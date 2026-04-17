"""Tests for Redis cache invalidation on write operations."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.flag.flag_model import FlagUpdateRequest


@pytest.fixture
def invalidate_mock():
    with patch("app.services.flag.flag_service.invalidate_flag_cache", new=AsyncMock()) as mock:
        yield mock


async def test_create_invokes_cache_invalidation(service, create_request, invalidate_mock):
    flag = await service.create_flag(create_request)
    invalidate_mock.assert_awaited_once_with("client-a", flag.flag_key)


async def test_update_invokes_cache_invalidation(service, create_request, invalidate_mock):
    created = await service.create_flag(create_request)
    invalidate_mock.reset_mock()
    await service.update_flag(created.id, FlagUpdateRequest(name="Renamed"))
    invalidate_mock.assert_awaited_once_with("client-a", created.flag_key)


async def test_delete_invokes_cache_invalidation(service, create_request, invalidate_mock):
    created = await service.create_flag(create_request)
    invalidate_mock.reset_mock()
    await service.delete_flag(created.id)
    invalidate_mock.assert_awaited_once_with("client-a", created.flag_key)


async def test_cache_invalidation_scans_and_deletes(_mock_redis):
    _mock_redis.scan_iter = _async_iter(
        ["ff:client-a:new_feature:hash1", "ff:client-a:new_feature:hash2"]
    )
    _mock_redis.delete = AsyncMock(return_value=2)
    from app.services.flag.cache_invalidation import invalidate_flag_cache

    await invalidate_flag_cache("client-a", "new_feature")
    _mock_redis.delete.assert_awaited()
    call_args = _mock_redis.delete.call_args.args
    assert "ff:client-a:new_feature:hash1" in call_args
    assert "ff:client-a:new_feature:hash2" in call_args


async def test_cache_invalidation_swallows_redis_errors(_mock_redis):
    async def _boom(*_args, **_kwargs):
        raise RuntimeError("redis down")
        yield  # pragma: no cover

    _mock_redis.scan_iter = _boom
    from app.services.flag.cache_invalidation import invalidate_flag_cache

    await invalidate_flag_cache("client-a", "new_feature")


async def test_cache_invalidation_noop_when_redis_not_initialized(monkeypatch):
    from app.database import redis_client as redis_client_module
    from app.services.flag.cache_invalidation import invalidate_flag_cache

    monkeypatch.setattr(redis_client_module.redis_client, "_client", None)
    await invalidate_flag_cache("client-a", "new_feature")


def _async_iter(items):
    async def _gen(*_args, **_kwargs):
        for item in items:
            yield item

    return _gen
