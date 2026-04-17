"""Controller for the evaluation endpoint — maps service errors to HTTP."""

from typing import Any, Dict

from fastapi import HTTPException, Response, status

from app.common.errors import FlagNotFound
from app.common.logging_helpers import LoggingData, log_error
from app.services.eval.eval_model import EvalResponse
from app.services.eval.eval_service import (
    REASON_FALLBACK,
    REASON_NOT_FOUND,
    REASON_SERVICE_ERROR,
    FlagEvalError,
    FlagLoadError,
    evaluate,
)


async def handle_evaluate(
    client_id: str, flag_key: str, body: Dict[str, Any], response: Response
) -> EvalResponse:
    try:
        return await evaluate(client_id=client_id, flag_key=flag_key, body=body)
    except FlagNotFound as exc:
        log_error(
            LoggingData(
                message="eval.flag_not_found",
                context={"flag_key": flag_key, "client_id": client_id},
                error=exc,
            )
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=EvalResponse(
                value=None, cohort_id=None, cohort_name=None, reason=REASON_NOT_FOUND
            ).model_dump(),
        ) from exc
    except FlagEvalError as exc:
        log_error(
            LoggingData(
                message="eval.evaluation_failed",
                context={"flag_key": flag_key, "client_id": client_id},
                error=exc,
            )
        )
        response.headers["X-FF-Fallback"] = "true"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=EvalResponse(
                value=exc.default_value,
                cohort_id=None,
                cohort_name=None,
                reason=REASON_FALLBACK,
            ).model_dump(),
            headers={"X-FF-Fallback": "true"},
        ) from exc
    except FlagLoadError as exc:
        log_error(
            LoggingData(
                message="eval.flag_load_failed",
                context={"flag_key": flag_key, "client_id": client_id},
                error=exc,
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=EvalResponse(
                value=None, cohort_id=None, cohort_name=None, reason=REASON_SERVICE_ERROR
            ).model_dump(),
        ) from exc
    except Exception as exc:
        log_error(
            LoggingData(
                message="eval.unexpected_error",
                context={"flag_key": flag_key, "client_id": client_id},
                error=exc,
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=EvalResponse(
                value=None, cohort_id=None, cohort_name=None, reason=REASON_SERVICE_ERROR
            ).model_dump(),
        ) from exc
