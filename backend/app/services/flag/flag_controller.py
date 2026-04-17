"""HTTP-facing controller for the flag domain. Maps service errors to HTTP."""

from typing import Optional

from fastapi import HTTPException, status

from app.common.errors import FlagAlreadyExists, FlagNotFound, InvalidCohortSum, ValidationError
from app.common.logging_helpers import LoggingData, log_info
from app.services.flag.flag_model import (
    FlagConfig,
    FlagCreateRequest,
    FlagListResponse,
    FlagUpdateRequest,
)
from app.services.flag.flag_service import FlagService


class FlagController:
    def __init__(self, service: Optional[FlagService] = None) -> None:
        self._service = service or FlagService()

    async def create_flag(self, request: FlagCreateRequest) -> FlagConfig:
        try:
            return await self._service.create_flag(request)
        except InvalidCohortSum as exc:
            log_info(
                LoggingData(
                    message="flag.create.invalid_cohort_sum",
                    context={"error": str(exc)},
                )
            )
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
        except ValidationError as exc:
            log_info(
                LoggingData(
                    message="flag.create.validation_error",
                    context={"error": str(exc)},
                )
            )
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
        except FlagAlreadyExists as exc:
            log_info(
                LoggingData(
                    message="flag.create.duplicate",
                    context={"error": str(exc)},
                )
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    async def update_flag(self, flag_id: str, request: FlagUpdateRequest) -> FlagConfig:
        try:
            return await self._service.update_flag(flag_id, request)
        except FlagNotFound as exc:
            log_info(
                LoggingData(
                    message="flag.update.not_found",
                    context={"flag_id": flag_id, "error": str(exc)},
                )
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
        except InvalidCohortSum as exc:
            log_info(
                LoggingData(
                    message="flag.update.invalid_cohort_sum",
                    context={"flag_id": flag_id, "error": str(exc)},
                )
            )
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
        except ValidationError as exc:
            log_info(
                LoggingData(
                    message="flag.update.validation_error",
                    context={"flag_id": flag_id, "error": str(exc)},
                )
            )
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    async def get_flag(self, flag_id: str) -> FlagConfig:
        try:
            return await self._service.get_flag(flag_id)
        except FlagNotFound as exc:
            log_info(
                LoggingData(
                    message="flag.get.not_found",
                    context={"flag_id": flag_id, "error": str(exc)},
                )
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))

    async def list_flags(
        self,
        status_filter: Optional[str],
        limit: int,
        skip: int,
    ) -> FlagListResponse:
        try:
            return await self._service.list_flags(status=status_filter, limit=limit, skip=skip)
        except ValidationError as exc:
            log_info(
                LoggingData(
                    message="flag.list.validation_error",
                    context={"error": str(exc)},
                )
            )
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    async def delete_flag(self, flag_id: str) -> None:
        try:
            await self._service.delete_flag(flag_id)
        except FlagNotFound as exc:
            log_info(
                LoggingData(
                    message="flag.delete.not_found",
                    context={"flag_id": flag_id, "error": str(exc)},
                )
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
