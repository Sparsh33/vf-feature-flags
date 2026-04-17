"""Redis-backed evaluation cache. All errors are swallowed and logged."""

import hashlib
import json
from typing import Any, Dict, Optional

from app.common.logging_helpers import LoggingData, log_warning
from app.database.redis_client import redis_client
from app.services.eval.bucketing import canonical_json


def _safe_log_warning(message: str, context: Dict[str, Any], error: Exception) -> None:
    try:
        log_warning(LoggingData(message=message, context=context, error=error))
    except Exception:  # pragma: no cover - shared logger has known key clash bug
        pass


CACHE_KEY_PREFIX = "ff:"
CACHE_HASH_LENGTH = 32
DEFAULT_TTL_SECONDS = 15 * 60


def compute_cache_key(client_id: str, flag_key: str, body: Dict[str, Any]) -> str:
    body_repr = canonical_json(body) + client_id
    digest = hashlib.sha256(body_repr.encode("utf-8")).hexdigest()[:CACHE_HASH_LENGTH]
    return f"{CACHE_KEY_PREFIX}{client_id}:{flag_key}:{digest}"


async def get_cached(cache_key: str) -> Optional[Dict[str, Any]]:
    try:
        client = redis_client.get()
        raw = await client.get(cache_key)
    except Exception as exc:
        _safe_log_warning("eval_cache.get_failed", {"cache_key": cache_key}, exc)
        return None
    if raw is None:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError) as exc:
        _safe_log_warning("eval_cache.decode_failed", {"cache_key": cache_key}, exc)
        return None


async def set_cached(
    cache_key: str, value: Dict[str, Any], ttl_sec: int = DEFAULT_TTL_SECONDS
) -> None:
    try:
        client = redis_client.get()
        await client.set(cache_key, json.dumps(value, default=str), ex=ttl_sec)
    except Exception as exc:
        _safe_log_warning("eval_cache.set_failed", {"cache_key": cache_key}, exc)
