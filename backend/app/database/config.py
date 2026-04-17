"""MongoDB singleton wrapper around motor's async client."""

import logging
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from app.config.settings import settings

logger = logging.getLogger(__name__)


class MongoDBConfig:
    def __init__(self) -> None:
        self._client: Optional[AsyncIOMotorClient] = None
        self._database: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        if self._client is not None:
            return
        self._client = AsyncIOMotorClient(settings.mongo_uri)
        self._database = self._client[settings.mongo_db]
        logger.info("MongoDB connected: db=%s", settings.mongo_db)

    async def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None
            self._database = None

    def get_database(self) -> AsyncIOMotorDatabase:
        if self._database is None:
            raise RuntimeError("MongoDB not initialized; call connect() first")
        return self._database

    async def ping(self) -> bool:
        try:
            if self._client is None:
                return False
            await self._client.admin.command("ping")
            return True
        except Exception as exc:
            logger.warning("MongoDB ping failed: %s", exc)
            return False


mongodb = MongoDBConfig()
