"""Feature-flag evaluation service — hot path."""

from typing import Any, Dict, Optional, Tuple

from app.common.errors import EvalError, FlagNotFound
from app.common.logging_helpers import LoggingData, log_info, log_warning
from app.services.eval.bucketing import Cohort, compute_bucket, pick_cohort
from app.services.eval.cache import compute_cache_key, get_cached, set_cached
from app.services.eval.eval_model import EvalResponse


def _safe_log(fn, data: LoggingData) -> None:
    try:
        fn(data)
    except Exception:  # pragma: no cover - shared logger has known key clash bug
        pass


REASON_CACHED = "cached"
REASON_COMPUTED = "computed"
REASON_NOT_FOUND = "not_found"
REASON_FALLBACK = "fallback"
REASON_SERVICE_ERROR = "service_error"


class FlagLoadError(EvalError):
    """Raised when the flag couldn't be loaded (DB error before we know flag state)."""


class FlagEvalError(EvalError):
    """Raised when evaluation failed after the flag was loaded."""

    def __init__(self, message: str, default_value: Any = None) -> None:
        super().__init__(message)
        self.default_value = default_value


def _normalize_flag(flag: Any) -> Optional[Dict[str, Any]]:
    if flag is None:
        return None
    if isinstance(flag, dict):
        return flag
    dumper = getattr(flag, "model_dump", None)
    if callable(dumper):
        return dumper()
    return None


async def _load_flag(client_id: str, flag_key: str) -> Dict[str, Any]:
    try:
        from app.services.flag.repositories.flag_repository import (  # type: ignore
            FlagRepository,
        )
    except ImportError:
        FlagRepository = None  # type: ignore
    if FlagRepository is None:
        raise FlagNotFound(f"flag_repo_unavailable:{flag_key}")
    repository = FlagRepository()
    try:
        flag = await repository.get_by_key(client_id=client_id, flag_key=flag_key)
    except Exception as exc:
        raise FlagLoadError(str(exc)) from exc
    normalized = _normalize_flag(flag)
    if normalized is None:
        raise FlagNotFound(flag_key)
    if normalized.get("is_deleted"):
        raise FlagNotFound(flag_key)
    if normalized.get("status") and normalized.get("status") != "active":
        raise FlagNotFound(flag_key)
    return normalized


def _extract_cohorts(flag: Dict[str, Any]) -> list:
    raw_cohorts = flag.get("cohorts") or []
    cohorts: list = []
    for item in raw_cohorts:
        if isinstance(item, Cohort):
            cohorts.append(item)
        elif isinstance(item, dict):
            cohorts.append(Cohort(**item))
    return cohorts


def _build_computed_response(
    flag: Dict[str, Any], client_id: str, flag_key: str, body: Dict[str, Any]
) -> Tuple[EvalResponse, Optional[Cohort]]:
    cohorts = _extract_cohorts(flag)
    bucket = compute_bucket(client_id=client_id, flag_key=flag_key, params=body)
    cohort = pick_cohort(bucket=bucket, cohorts=cohorts)
    if cohort is None:
        response = EvalResponse(
            value=flag.get("default_value"),
            cohort_id=None,
            cohort_name=None,
            reason=REASON_COMPUTED,
        )
        return response, None
    response = EvalResponse(
        value=cohort.value,
        cohort_id=getattr(cohort, "id", None) or getattr(cohort, "cohort_id", None),
        cohort_name=getattr(cohort, "name", None),
        reason=REASON_COMPUTED,
    )
    return response, cohort


def _emit_eval_event(
    flag_id: Optional[str],
    flag_key: str,
    client_id: str,
    cohort_id: Optional[str],
    cohort_name: Optional[str],
    reason: str,
) -> None:
    try:
        from app.services.analytics.tasks import record_eval_event  # type: ignore

        record_eval_event.delay(
            flag_id=flag_id,
            flag_key=flag_key,
            client_id=client_id,
            cohort_id=cohort_id,
            cohort_name=cohort_name,
            reason=reason,
        )
    except Exception as exc:
        _safe_log(
            log_warning,
            LoggingData(
                message="eval.analytics_emit_failed",
                context={"flag_key": flag_key, "client_id": client_id},
                error=exc,
            ),
        )


async def evaluate(client_id: str, flag_key: str, body: Dict[str, Any]) -> EvalResponse:
    cache_key = compute_cache_key(client_id=client_id, flag_key=flag_key, body=body)
    cached = await get_cached(cache_key)
    if cached is not None:
        _safe_log(
            log_info,
            LoggingData(
                message="eval.cache_hit",
                context={"flag_key": flag_key, "client_id": client_id},
            ),
        )
        return EvalResponse(
            value=cached.get("value"),
            cohort_id=cached.get("cohort_id"),
            cohort_name=cached.get("cohort_name"),
            reason=REASON_CACHED,
        )
    flag = await _load_flag(client_id=client_id, flag_key=flag_key)
    try:
        response, _ = _build_computed_response(
            flag=flag, client_id=client_id, flag_key=flag_key, body=body
        )
    except Exception as exc:
        raise FlagEvalError(str(exc), default_value=flag.get("default_value")) from exc
    await set_cached(cache_key, response.model_dump())
    _emit_eval_event(
        flag_id=flag.get("id") or flag.get("_id"),
        flag_key=flag_key,
        client_id=client_id,
        cohort_id=response.cohort_id,
        cohort_name=response.cohort_name,
        reason=REASON_COMPUTED,
    )
    return response
