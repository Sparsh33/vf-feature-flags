"""Pydantic models for the audit domain."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(BaseModel):
    id: Optional[str] = None
    client_id: str
    actor_user_id: Optional[str] = None
    actor_ip: Optional[str] = None
    actor_user_agent: Optional[str] = None
    action: str
    resource_type: str
    resource_id: str
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    ts: datetime = Field(default_factory=_utcnow)


class AuditLogResponse(BaseModel):
    id: str
    actor_user_id: Optional[str] = None
    action: str
    resource_type: str
    resource_id: str
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    ts: datetime


class AuditLogListResponse(BaseModel):
    logs: List[AuditLogResponse]
    total: int
