"""Unit tests for the evaluation cache helpers."""

import pytest

from app.services.eval.cache import (
    CACHE_KEY_PREFIX,
    compute_cache_key,
    get_cached,
    set_cached,
)


def test_compute_cache_key_is_deterministic():
    key_a = compute_cache_key("client-1", "flag-x", {"a": 1, "b": 2})
    key_b = compute_cache_key("client-1", "flag-x", {"b": 2, "a": 1})
    assert key_a == key_b


def test_compute_cache_key_has_expected_prefix_and_parts():
    key = compute_cache_key("client-1", "flag-x", {"a": 1})
    assert key.startswith(f"{CACHE_KEY_PREFIX}client-1:flag-x:")
    tail = key.rsplit(":", 1)[-1]
    assert len(tail) == 32


def test_compute_cache_key_differs_per_client():
    key_a = compute_cache_key("client-1", "flag-x", {"u": "42"})
    key_b = compute_cache_key("client-2", "flag-x", {"u": "42"})
    assert key_a != key_b


def test_compute_cache_key_differs_per_flag():
    key_a = compute_cache_key("client-1", "flag-a", {"u": "42"})
    key_b = compute_cache_key("client-1", "flag-b", {"u": "42"})
    assert key_a != key_b


def test_compute_cache_key_differs_when_body_differs():
    assert compute_cache_key("c", "f", {"u": 1}) != compute_cache_key("c", "f", {"u": 2})


@pytest.mark.asyncio
async def test_cache_roundtrip_with_fake_redis(fake_redis):
    key = "ff:client-1:flag-x:abc"
    await set_cached(key, {"value": True, "reason": "computed"}, ttl_sec=60)
    result = await get_cached(key)
    assert result == {"value": True, "reason": "computed"}


@pytest.mark.asyncio
async def test_cache_miss_returns_none(fake_redis):
    assert await get_cached("ff:missing") is None


@pytest.mark.asyncio
async def test_cache_swallows_redis_errors_on_get(fake_redis):
    fake_redis.raise_on_get = True
    assert await get_cached("ff:anything") is None


@pytest.mark.asyncio
async def test_cache_swallows_redis_errors_on_set(fake_redis):
    fake_redis.raise_on_set = True
    # should NOT raise
    await set_cached("ff:anything", {"v": 1})
