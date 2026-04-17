"""Pydantic models for the flag + cohort domain."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Cohort(BaseModel):
    id: Optional[str] = None
    name: str
    percentage: float
    value: Any = None


class FlagConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True, arbitrary_types_allowed=True)
    id: Optional[str] = None
    client_id: str
    flag_key: str
    name: str
    description: Optional[str] = None
    default_value: Any = None
    cohorts: List[Cohort] = Field(default_factory=list)
    parameters_schema: Optional[Dict[str, Any]] = None
    is_deleted: bool = False
    status: str = "active"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)
    created_by: Optional[str] = None
    updated_by: Optional[str] = None


class FlagCreateRequest(BaseModel):
    flag_key: str
    name: str
    description: Optional[str] = None
    default_value: Any = None
    cohorts: List[Cohort] = Field(default_factory=list)
    parameters_schema: Optional[Dict[str, Any]] = None
    status: str = "active"


class FlagUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    default_value: Optional[Any] = None
    cohorts: Optional[List[Cohort]] = None
    parameters_schema: Optional[Dict[str, Any]] = None
    status: Optional[str] = None


class FlagListResponse(BaseModel):
    flags: List[FlagConfig]
    total: int
