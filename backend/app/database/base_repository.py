"""Base repository class shared by all domains."""

from typing import Any, ClassVar, Dict, Optional

from motor.motor_asyncio import AsyncIOMotorCollection

from app.database.config import mongodb
from app.middleware.request_context import RequestContextManager


class BaseRepository:
    COLLECTION_NAME: ClassVar[str] = ""

    async def _get_collection(self) -> AsyncIOMotorCollection:
        if not self.COLLECTION_NAME:
            raise RuntimeError(f"{type(self).__name__} must set COLLECTION_NAME")
        return mongodb.get_database()[self.COLLECTION_NAME]

    def _strip_mongo_id(self, document: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if document is None:
            return None
        if "_id" in document:
            document["id"] = str(document.pop("_id"))
        return document

    def _resolve_client_id(self) -> str:
        client_id = RequestContextManager.get_client_id()
        if not client_id:
            raise RuntimeError("client_id missing from request context")
        return client_id
