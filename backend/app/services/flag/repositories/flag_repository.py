"""Repository for the `flags` collection. All queries are client-scoped."""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING, ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.common.errors import FlagAlreadyExists
from app.database.base_repository import BaseRepository
from app.database.config import mongodb
from app.database.indexes import register_index_builder
from app.services.flag.flag_model import FlagConfig

_logger = logging.getLogger("vf_ff.flag.repo")


class FlagRepository(BaseRepository):
    COLLECTION_NAME = "flags"

    async def insert(self, flag: FlagConfig) -> FlagConfig:
        collection = await self._get_collection()
        document = flag.model_dump(exclude={"id"})
        try:
            result = await collection.insert_one(document)
        except DuplicateKeyError as exc:
            _logger.warning(
                "Duplicate flag_key insert: client_id=%s flag_key=%s",
                flag.client_id,
                flag.flag_key,
            )
            raise FlagAlreadyExists(
                f"Flag with key '{flag.flag_key}' already exists for client"
            ) from exc
        flag.id = str(result.inserted_id)
        return flag

    async def get_by_key(self, client_id: str, flag_key: str) -> Optional[FlagConfig]:
        collection = await self._get_collection()
        document = await collection.find_one(
            {"client_id": client_id, "flag_key": flag_key, "is_deleted": False}
        )
        return self._to_model(document)

    async def get_by_id(self, client_id: str, flag_id: str) -> Optional[FlagConfig]:
        object_id = self._coerce_object_id(flag_id)
        if object_id is None:
            return None
        collection = await self._get_collection()
        document = await collection.find_one(
            {"_id": object_id, "client_id": client_id, "is_deleted": False}
        )
        return self._to_model(document)

    async def list_flags(
        self,
        client_id: str,
        status: Optional[str],
        limit: int,
        skip: int,
    ) -> Tuple[List[FlagConfig], int]:
        collection = await self._get_collection()
        query: Dict[str, Any] = {"client_id": client_id, "is_deleted": False}
        if status is not None:
            query["status"] = status
        total = await collection.count_documents(query)
        cursor = collection.find(query).sort("updated_at", DESCENDING).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        flags = [self._to_model(document) for document in documents]
        return [flag for flag in flags if flag is not None], total

    async def update(
        self, client_id: str, flag_id: str, updates: Dict[str, Any]
    ) -> Optional[FlagConfig]:
        object_id = self._coerce_object_id(flag_id)
        if object_id is None:
            return None
        collection = await self._get_collection()
        updates = dict(updates)
        updates["updated_at"] = datetime.now(timezone.utc)
        document = await collection.find_one_and_update(
            {"_id": object_id, "client_id": client_id, "is_deleted": False},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        return self._to_model(document)

    async def soft_delete(self, client_id: str, flag_id: str) -> bool:
        object_id = self._coerce_object_id(flag_id)
        if object_id is None:
            return False
        collection = await self._get_collection()
        result = await collection.update_one(
            {"_id": object_id, "client_id": client_id, "is_deleted": False},
            {"$set": {"is_deleted": True, "updated_at": datetime.now(timezone.utc)}},
        )
        return result.modified_count == 1

    def _coerce_object_id(self, flag_id: str) -> Optional[ObjectId]:
        try:
            return ObjectId(flag_id)
        except (InvalidId, TypeError):
            return None

    def _to_model(self, document: Optional[Dict[str, Any]]) -> Optional[FlagConfig]:
        if document is None:
            return None
        stripped = self._strip_mongo_id(dict(document))
        if stripped is None:
            return None
        return FlagConfig(**stripped)


async def ensure_flag_indexes() -> None:
    try:
        collection = mongodb.get_database()["flags"]
        await collection.create_index(
            [("client_id", ASCENDING), ("flag_key", ASCENDING), ("is_deleted", ASCENDING)],
            name="flags_client_key_active_unique",
            unique=True,
            partialFilterExpression={"is_deleted": False},
        )
        await collection.create_index(
            [("client_id", ASCENDING), ("is_deleted", ASCENDING), ("status", ASCENDING)],
            name="flags_client_deleted_status",
        )
        await collection.create_index(
            [("client_id", ASCENDING), ("updated_at", DESCENDING)],
            name="flags_client_updated_at",
        )
    except Exception as exc:  # pragma: no cover - defensive
        _logger.warning("Failed to create indexes for flags collection: %s", exc)


register_index_builder(ensure_flag_indexes)
