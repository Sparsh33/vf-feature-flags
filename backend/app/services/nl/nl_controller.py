"""Thin controller: delegates to nl_service and maps exceptions to HTTP."""

from fastapi import HTTPException, status

from app.common.errors import NLSessionNotFound
from app.common.logging_helpers import LoggingData, log_error
from app.services.nl import nl_service
from app.services.nl.nl_model import NLChatRequest, NLChatResponse


class NLController:
    async def chat(self, request: NLChatRequest) -> NLChatResponse:
        try:
            return await nl_service.chat(request)
        except NLSessionNotFound as exc:
            log_error(
                LoggingData(
                    message="NL session not found",
                    context={"session_id": request.session_id},
                    error=exc,
                )
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="session not found"
            ) from exc
        except ValueError as exc:
            log_error(
                LoggingData(
                    message="NL chat invalid request",
                    context={"session_id": request.session_id},
                    error=exc,
                )
            )
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        except Exception as exc:
            log_error(
                LoggingData(
                    message="NL chat failed",
                    context={"session_id": request.session_id},
                    error=exc,
                )
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="nl chat failed",
            ) from exc
