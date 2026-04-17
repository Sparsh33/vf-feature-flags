"""Shared Pydantic base models."""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MongoModel(BaseModel):
    """Base model for documents persisted to MongoDB.

    - `id` maps to Mongo's `_id` via alias; use `model_dump(by_alias=True)` on writes.
    - `created_at` / `updated_at` auto-populated.
    """

    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)

    id: Optional[str] = Field(default=None, alias="_id")
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
