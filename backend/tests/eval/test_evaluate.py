"""Integration-style unit tests for the evaluate() service function."""

import pytest

from app.common.errors import FlagNotFound
from app.services.eval.cache import compute_cache_key
from app.services.eval.eval_service import (
    REASON_CACHED,
    REASON_COMPUTED,
    FlagEvalError,
    FlagLoadError,
    evaluate,
)


@pytest.mark.asyncio
async def test_cache_hit_skips_db(fake_redis, mock_flag_repo, sample_flag):
    import json

    key = compute_cache_key("client-1", "new_checkout", {"user_id": "u1"})
    fake_redis.store[key] = json.dumps(
        {"value": True, "cohort_id": "c1", "cohort_name": "on", "reason": "computed"}
    )
    response = await evaluate("client-1", "new_checkout", {"user_id": "u1"})
    assert response.reason == REASON_CACHED
    assert response.value is True
    assert response.cohort_id == "c1"
    mock_flag_repo.assert_not_called()


@pytest.mark.asyncio
async def test_cache_miss_fetches_and_caches(fake_redis, mock_flag_repo, sample_flag):
    mock_flag_repo.return_value = sample_flag
    response = await evaluate("client-1", "new_checkout", {"user_id": "u1"})
    assert response.reason == REASON_COMPUTED
    assert response.cohort_id in {"c1", "c2"}
    # Cache should now be populated
    cache_key = compute_cache_key("client-1", "new_checkout", {"user_id": "u1"})
    assert cache_key in fake_redis.store


@pytest.mark.asyncio
async def test_flag_not_found_raises(fake_redis, mock_flag_repo):
    mock_flag_repo.return_value = None
    with pytest.raises(FlagNotFound):
        await evaluate("client-1", "missing_flag", {})


@pytest.mark.asyncio
async def test_redis_down_still_computes(fake_redis, mock_flag_repo, sample_flag):
    fake_redis.raise_on_get = True
    fake_redis.raise_on_set = True
    mock_flag_repo.return_value = sample_flag
    response = await evaluate("client-1", "new_checkout", {"user_id": "u1"})
    assert response.reason == REASON_COMPUTED
    assert response.value in {True, False}


@pytest.mark.asyncio
async def test_db_load_failure_raises_flagloaderror(fake_redis, mock_flag_repo):
    mock_flag_repo.side_effect = RuntimeError("mongo down")
    with pytest.raises(FlagLoadError):
        await evaluate("client-1", "new_checkout", {})


@pytest.mark.asyncio
async def test_bucketing_failure_returns_fallback_with_default(
    fake_redis, monkeypatch, mock_flag_repo, sample_flag
):
    mock_flag_repo.return_value = sample_flag

    def _boom(*args, **kwargs):
        raise RuntimeError("xxhash exploded")

    monkeypatch.setattr("app.services.eval.eval_service.compute_bucket", _boom)
    with pytest.raises(FlagEvalError) as exc_info:
        await evaluate("client-1", "new_checkout", {})
    assert exc_info.value.default_value is False


@pytest.mark.asyncio
async def test_analytics_emit_failure_does_not_break_eval(fake_redis, mock_flag_repo, sample_flag):
    """When the analytics task import/delay raises, eval must still return normally."""
    import sys
    import types

    analytics_module = types.ModuleType("app.services.analytics.tasks")

    class _BoomTask:
        @staticmethod
        def delay(*args, **kwargs):
            raise RuntimeError("celery down")

    analytics_module.record_eval_event = _BoomTask  # type: ignore[attr-defined]
    sys.modules["app.services.analytics.tasks"] = analytics_module
    mock_flag_repo.return_value = sample_flag
    try:
        response = await evaluate("client-1", "new_checkout", {"user_id": "u1"})
    finally:
        sys.modules.pop("app.services.analytics.tasks", None)
    assert response.reason == REASON_COMPUTED


@pytest.mark.asyncio
async def test_same_params_same_cohort(fake_redis, mock_flag_repo, sample_flag):
    mock_flag_repo.return_value = sample_flag
    params = {"user_id": "stable-user"}
    first = await evaluate("client-1", "new_checkout", params)
    # drop cache to force recomputation
    fake_redis.store.clear()
    second = await evaluate("client-1", "new_checkout", params)
    assert first.cohort_id == second.cohort_id
    assert first.value == second.value
