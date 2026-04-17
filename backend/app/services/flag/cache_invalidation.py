"""Redis cache invalidation helper for flag evaluations."""

import logging

from app.database.redis_client import redis_client

_CACHE_KEY_PREFIX = "ff"
_SCAN_BATCH = 500
_logger = logging.getLogger("vf_ff.flag.cache")


async def invalidate_flag_cache(client_id: str, flag_key: str) -> None:
    """Delete all Redis keys matching `ff:{client_id}:{flag_key}:*`.

    Uses SCAN + DELETE. Any Redis failure is logged and swallowed so that a
    Redis outage never blocks the primary write path.
    """
    pattern = f"{_CACHE_KEY_PREFIX}:{client_id}:{flag_key}:*"
    try:
        redis = redis_client.get()
    except RuntimeError:
        _logger.warning("Redis unavailable; skipping cache invalidation for %s", pattern)
        return
    try:
        keys_to_delete = []
        async for key in redis.scan_iter(match=pattern, count=100):
            keys_to_delete.append(key)
            if len(keys_to_delete) >= _SCAN_BATCH:
                await redis.delete(*keys_to_delete)
                keys_to_delete = []
        if keys_to_delete:
            await redis.delete(*keys_to_delete)
    except Exception as exc:
        _logger.warning("Flag cache invalidation failed for %s: %s", pattern, exc)
