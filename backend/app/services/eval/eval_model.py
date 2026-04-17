"""Pydantic models for the evaluation endpoint."""

from typing import Any, Optional

from pydantic import BaseModel


class EvalResponse(BaseModel):
    value: Any = None
    cohort_id: Optional[str] = None
    cohort_name: Optional[str] = None
    reason: str
