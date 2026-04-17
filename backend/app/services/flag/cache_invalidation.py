"""Redis cache invalidation helper for flag evaluations."""

from app.common.logging_helpers import LoggingData, log_warning
from app.database.redis_client import redis_client

_CACHE_KEY_PREFIX = "ff"
_SCAN_BATCH = 500


async def invalidate_flag_cache(client_id: str, flag_key: str) -> None:
    """Delete all Redis keys matching `ff:{client_id}:{flag_key}:*`.

    Uses SCAN + DELETE. Any Redis failure is logged and swallowed so that a
    Redis outage never blocks the primary write path.
    """
    pattern = f"{_CACHE_KEY_PREFIX}:{client_id}:{flag_key}:*"
    try:
        redis = redis_client.get()
    except RuntimeError:
        log_warning(
            LoggingData(
                message="flag.cache.redis_unavailable",
                context={"pattern": pattern, "client_id": client_id, "flag_key": flag_key},
            )
        )
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
        log_warning(
            LoggingData(
                message="flag.cache.invalidation_failed",
                context={
                    "pattern": pattern,
                    "client_id": client_id,
                    "flag_key": flag_key,
                    "error": str(exc),
                },
            )
        )
