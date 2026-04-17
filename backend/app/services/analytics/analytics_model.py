"""Pydantic models for the analytics domain."""

from datetime import datetime, timezone
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AnalyticsEvent(BaseModel):
    id: Optional[str] = None
    client_id: str
    flag_id: str
    flag_key: str
    cohort_id: Optional[str] = None
    cohort_name: Optional[str] = None
    reason: str
    ts: datetime = Field(default_factory=_utcnow)


class CohortStats(BaseModel):
    cohort_id: Optional[str] = None
    cohort_name: Optional[str] = None
    count: int
    percentage: float


class FlagAnalyticsResponse(BaseModel):
    flag_id: str
    flag_key: str
    total_requests: int
    per_cohort: List[CohortStats]
    time_range: Dict[str, datetime]


class TimeSeriesBucket(BaseModel):
    ts: datetime
    counts_by_cohort: Dict[str, int]


class FlagAnalyticsTimeSeriesResponse(BaseModel):
    flag_id: str
    flag_key: str
    interval: str
    buckets: List[TimeSeriesBucket]
