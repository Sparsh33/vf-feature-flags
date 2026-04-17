"""MongoDB repository for the `users` collection."""

from typing import Optional

from bson import ObjectId
from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError

from app.database.base_repository import BaseRepository
from app.database.config import mongodb
from app.database.indexes import register_index_builder
from app.services.auth.auth_model import User


class UserRepository(BaseRepository):
    COLLECTION_NAME = "users"

    async def insert(self, user: User) -> User:
        collection = await self._get_collection()
        document = user.model_dump(exclude={"id"})
        result = await collection.insert_one(document)
        user.id = str(result.inserted_id)
        return user

    async def find_by_email(self, email: str) -> Optional[User]:
        collection = await self._get_collection()
        document = await collection.find_one({"email": email, "is_deleted": False})
        if document is None:
            return None
        return self._document_to_user(document)

    async def find_by_id(self, user_id: str) -> Optional[User]:
        collection = await self._get_collection()
        try:
            object_id = ObjectId(user_id)
        except Exception:
            return None
        document = await collection.find_one({"_id": object_id, "is_deleted": False})
        if document is None:
            return None
        return self._document_to_user(document)

    def _document_to_user(self, document: dict) -> User:
        document["id"] = str(document.pop("_id"))
        return User(**document)


async def ensure_user_indexes() -> None:
    collection = mongodb.get_database()["users"]
    await collection.create_index(
        [("email", ASCENDING), ("is_deleted", ASCENDING)],
        unique=True,
        partialFilterExpression={"is_deleted": False},
        name="uniq_email_active",
    )


register_index_builder(ensure_user_indexes)

__all__ = ["UserRepository", "DuplicateKeyError", "ensure_user_indexes"]
