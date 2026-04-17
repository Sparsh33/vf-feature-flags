"""Deterministic bucketing for flag evaluation."""

import json
from typing import Any, Dict, List, Optional

import xxhash

try:
    from app.services.flag.flag_model import Cohort  # type: ignore
except ImportError:  # pragma: no cover - fallback until flag service ships
    from pydantic import BaseModel

    class Cohort(BaseModel):  # type: ignore[no-redef]
        id: Optional[str] = None
        name: Optional[str] = None
        percentage: float = 0.0
        value: Any = None


BUCKET_RESOLUTION = 10000


def canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)


def compute_bucket(client_id: str, flag_key: str, params: Dict[str, Any]) -> int:
    payload = client_id + flag_key + canonical_json(params)
    return xxhash.xxh64(payload.encode("utf-8")).intdigest() % BUCKET_RESOLUTION


def _cohort_percentage(cohort: Cohort) -> float:
    raw = getattr(cohort, "percentage", 0.0)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return 0.0


def pick_cohort(bucket: int, cohorts: List[Cohort]) -> Optional[Cohort]:
    if not cohorts:
        return None
    cumulative = 0
    for cohort in cohorts:
        cumulative += int(round(_cohort_percentage(cohort) * 100))
        if bucket < cumulative:
            return cohort
    return cohorts[-1]
