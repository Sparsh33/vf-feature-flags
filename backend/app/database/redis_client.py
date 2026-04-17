"""Async Redis singleton."""

import logging
from typing import Optional

from redis.asyncio import Redis, from_url

from app.config.settings import settings

logger = logging.getLogger(__name__)


class RedisClient:
    def __init__(self) -> None:
        self._client: Optional[Redis] = None

    async def connect(self) -> None:
        if self._client is not None:
            return
        self._client = from_url(settings.redis_url, decode_responses=True)
        logger.info("Redis connected")

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def get(self) -> Redis:
        if self._client is None:
            raise RuntimeError("Redis not initialized; call connect() first")
        return self._client

    async def ping(self) -> bool:
        try:
            if self._client is None:
                return False
            return bool(await self._client.ping())
        except Exception as exc:
            logger.warning("Redis ping failed: %s", exc)
            return False


redis_client = RedisClient()
