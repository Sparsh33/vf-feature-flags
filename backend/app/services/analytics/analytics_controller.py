"""HTTP controller for the analytics domain: delegates to service, maps exceptions."""

from datetime import datetime
from typing import Optional

from fastapi import HTTPException

from app.common.logging_helpers import LoggingData, log_error
from app.middleware.request_context import RequestContextManager
from app.services.analytics.analytics_model import (
    FlagAnalyticsResponse,
    FlagAnalyticsTimeSeriesResponse,
)
from app.services.analytics.analytics_service import get_flag_analytics, get_flag_time_series


class AnalyticsController:
    def __init__(self) -> None:
        pass

    async def get_flag_analytics(
        self,
        client_id: str,
        flag_id: str,
        from_ts: Optional[datetime],
        to_ts: Optional[datetime],
    ) -> FlagAnalyticsResponse:
        RequestContextManager.set_client_id(client_id)
        try:
            return await get_flag_analytics(flag_id=flag_id, from_ts=from_ts, to_ts=to_ts)
        except ValueError as exc:
            log_error(
                LoggingData(
                    message="analytics.get_flag_analytics.bad_request",
                    context={"client_id": client_id, "flag_id": flag_id},
                    error=exc,
                )
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    async def get_flag_time_series(
        self,
        client_id: str,
        flag_id: str,
        from_ts: Optional[datetime],
        to_ts: Optional[datetime],
        interval: str,
    ) -> FlagAnalyticsTimeSeriesResponse:
        RequestContextManager.set_client_id(client_id)
        try:
            return await get_flag_time_series(
                flag_id=flag_id,
                from_ts=from_ts,
                to_ts=to_ts,
                interval=interval,
            )
        except ValueError as exc:
            log_error(
                LoggingData(
                    message="analytics.get_flag_time_series.bad_request",
                    context={"client_id": client_id, "flag_id": flag_id, "interval": interval},
                    error=exc,
                )
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc
