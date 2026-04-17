"""Repository for the `audit_logs` MongoDB collection."""

from typing import Any, Dict, List, Optional, Tuple

from app.database.base_repository import BaseRepository
from app.services.audit.audit_model import AuditLog


class AuditRepository(BaseRepository):
    COLLECTION_NAME = "audit_logs"

    async def ensure_indexes(self) -> None:
        collection = await self._get_collection()
        await collection.create_index([("client_id", 1), ("ts", -1)])
        await collection.create_index(
            [("client_id", 1), ("resource_type", 1), ("resource_id", 1), ("ts", -1)]
        )
        await collection.create_index([("client_id", 1), ("action", 1), ("ts", -1)])

    async def insert(self, log: AuditLog) -> AuditLog:
        collection = await self._get_collection()
        payload = log.model_dump(exclude={"id"})
        result = await collection.insert_one(payload)
        log.id = str(result.inserted_id)
        return log

    async def list_logs(
        self,
        client_id: str,
        resource_type: Optional[str],
        resource_id: Optional[str],
        action: Optional[str],
        limit: int,
        skip: int,
    ) -> Tuple[List[AuditLog], int]:
        collection = await self._get_collection()
        query: Dict[str, Any] = {"client_id": client_id}
        if resource_type is not None:
            query["resource_type"] = resource_type
        if resource_id is not None:
            query["resource_id"] = resource_id
        if action is not None:
            query["action"] = action
        total = await collection.count_documents(query)
        cursor = collection.find(query).sort("ts", -1).skip(skip).limit(limit)
        documents = await cursor.to_list(length=limit)
        logs: List[AuditLog] = []
        for document in documents:
            stripped = self._strip_mongo_id(document)
            if stripped is not None:
                logs.append(AuditLog(**stripped))
        return logs, total
