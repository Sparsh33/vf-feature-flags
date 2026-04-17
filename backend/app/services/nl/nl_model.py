"""Pydantic models for the natural-language flag builder domain."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NLMessage(BaseModel):
    role: str  # "user" | "assistant"
    content: str
    ts: datetime = Field(default_factory=_utcnow)


class ExtractedParams(BaseModel):
    """Draft flag params accumulated across the conversation.

    All fields are optional — filled progressively as the user answers clarifying questions.
    """

    flag_key: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    default_value: Optional[Any] = None
    cohorts: Optional[List[Dict[str, Any]]] = None
    parameters_schema: Optional[Dict[str, Any]] = None


class NLSession(BaseModel):
    id: Optional[str] = None
    client_id: str
    user_id: str
    messages: List[NLMessage] = Field(default_factory=list)
    extracted: ExtractedParams = Field(default_factory=ExtractedParams)
    compaction_count: int = 0
    last_compacted_summary: Optional[str] = None
    status: str = "active"  # "active" | "committed" | "abandoned"
    committed_flag_id: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class NLChatRequest(BaseModel):
    session_id: Optional[str] = None
    message: str


class NLChatResponse(BaseModel):
    session_id: str
    reply: str
    extracted: ExtractedParams
    draft_flag: Optional[Dict[str, Any]] = None
    ready_to_commit: bool = False
    committed_flag_id: Optional[str] = None
    compacted: bool = False
