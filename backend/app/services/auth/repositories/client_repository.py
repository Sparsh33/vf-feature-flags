"""MongoDB repository for the `clients` collection."""

from typing import List, Optional

from bson import ObjectId
from pymongo import ASCENDING

from app.database.base_repository import BaseRepository
from app.database.config import mongodb
from app.database.indexes import register_index_builder
from app.services.auth.auth_model import Client


class ClientRepository(BaseRepository):
    COLLECTION_NAME = "clients"

    async def insert(self, client: Client) -> Client:
        collection = await self._get_collection()
        document = client.model_dump(exclude={"id"})
        result = await collection.insert_one(document)
        client.id = str(result.inserted_id)
        return client

    async def find_by_id(self, client_id: str) -> Optional[Client]:
        collection = await self._get_collection()
        try:
            object_id = ObjectId(client_id)
        except Exception:
            return None
        document = await collection.find_one({"_id": object_id, "is_deleted": False})
        if document is None:
            return None
        return self._document_to_client(document)

    async def find_candidates_by_prefix(self, prefix: str) -> List[Client]:
        collection = await self._get_collection()
        cursor = collection.find({"api_key_prefix": prefix, "is_deleted": False})
        results: List[Client] = []
        async for document in cursor:
            results.append(self._document_to_client(document))
        return results

    async def update_api_key(self, client_id: str, new_prefix: str, new_hash: str) -> bool:
        collection = await self._get_collection()
        try:
            object_id = ObjectId(client_id)
        except Exception:
            return False
        result = await collection.update_one(
            {"_id": object_id, "is_deleted": False},
            {"$set": {"api_key_prefix": new_prefix, "api_key_hash": new_hash}},
        )
        return result.matched_count > 0

    async def delete_by_id(self, client_id: str) -> bool:
        collection = await self._get_collection()
        try:
            object_id = ObjectId(client_id)
        except Exception:
            return False
        result = await collection.delete_one({"_id": object_id})
        return result.deleted_count > 0

    def _document_to_client(self, document: dict) -> Client:
        document["id"] = str(document.pop("_id"))
        return Client(**document)


async def ensure_client_indexes() -> None:
    collection = mongodb.get_database()["clients"]
    await collection.create_index(
        [("api_key_prefix", ASCENDING), ("is_deleted", ASCENDING)],
        name="api_key_prefix_active",
    )


register_index_builder(ensure_client_indexes)

__all__ = ["ClientRepository", "ensure_client_indexes"]
