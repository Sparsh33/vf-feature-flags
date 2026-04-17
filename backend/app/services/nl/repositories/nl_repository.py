"""Repository for the `nl_sessions` MongoDB collection. All queries are client-scoped."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import ASCENDING, DESCENDING, ReturnDocument

from app.common.logging_helpers import LoggingData, log_error
from app.database.base_repository import BaseRepository
from app.database.config import mongodb
from app.database.indexes import register_index_builder
from app.services.nl.nl_model import NLMessage, NLSession


class NLRepository(BaseRepository):
    COLLECTION_NAME = "nl_sessions"

    async def create(self, session: NLSession) -> NLSession:
        collection = await self._get_collection()
        document = session.model_dump(exclude={"id"})
        result = await collection.insert_one(document)
        session.id = str(result.inserted_id)
        return session

    async def get(self, session_id: str, client_id: str) -> Optional[NLSession]:
        object_id = self._coerce_object_id(session_id)
        if object_id is None:
            return None
        collection = await self._get_collection()
        document = await collection.find_one({"_id": object_id, "client_id": client_id})
        return self._to_model(document)

    async def update(
        self, session_id: str, client_id: str, updates: Dict[str, Any]
    ) -> Optional[NLSession]:
        object_id = self._coerce_object_id(session_id)
        if object_id is None:
            return None
        collection = await self._get_collection()
        patch = dict(updates)
        patch["updated_at"] = datetime.now(timezone.utc)
        document = await collection.find_one_and_update(
            {"_id": object_id, "client_id": client_id},
            {"$set": patch},
            return_document=ReturnDocument.AFTER,
        )
        return self._to_model(document)

    async def append_message(self, session_id: str, client_id: str, msg: NLMessage) -> None:
        object_id = self._coerce_object_id(session_id)
        if object_id is None:
            return
        collection = await self._get_collection()
        await collection.update_one(
            {"_id": object_id, "client_id": client_id},
            {
                "$push": {"messages": msg.model_dump()},
                "$set": {"updated_at": datetime.now(timezone.utc)},
            },
        )

    async def replace_messages(
        self,
        session_id: str,
        client_id: str,
        messages: List[NLMessage],
        summary: str,
    ) -> None:
        object_id = self._coerce_object_id(session_id)
        if object_id is None:
            return
        collection = await self._get_collection()
        await collection.update_one(
            {"_id": object_id, "client_id": client_id},
            {
                "$set": {
                    "messages": [msg.model_dump() for msg in messages],
                    "last_compacted_summary": summary,
                    "updated_at": datetime.now(timezone.utc),
                },
                "$inc": {"compaction_count": 1},
            },
        )

    def _coerce_object_id(self, session_id: str) -> Optional[ObjectId]:
        try:
            return ObjectId(session_id)
        except (InvalidId, TypeError):
            return None

    def _to_model(self, document: Optional[Dict[str, Any]]) -> Optional[NLSession]:
        if document is None:
            return None
        stripped = self._strip_mongo_id(dict(document))
        if stripped is None:
            return None
        return NLSession(**stripped)


async def ensure_nl_indexes() -> None:
    try:
        collection = mongodb.get_database()["nl_sessions"]
        await collection.create_index(
            [("client_id", ASCENDING), ("user_id", ASCENDING), ("updated_at", DESCENDING)],
            name="nl_sessions_client_user_updated",
        )
        await collection.create_index(
            [("client_id", ASCENDING), ("status", ASCENDING)],
            name="nl_sessions_client_status",
        )
    except Exception as exc:  # pragma: no cover - defensive
        log_error(
            LoggingData(
                message="Failed to create indexes for nl_sessions collection",
                error=exc,
            )
        )


register_index_builder(ensure_nl_indexes)
