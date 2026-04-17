"""HTTP routes for the analytics domain."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.services.analytics.analytics_controller import AnalyticsController
from app.services.analytics.analytics_model import (
    FlagAnalyticsResponse,
    FlagAnalyticsTimeSeriesResponse,
)
from app.services.auth.auth_model import UserPublic
from app.services.auth.dependencies import get_current_user

router = APIRouter()


def _get_controller() -> AnalyticsController:
    return AnalyticsController()


@router.get("/flags/{flag_id}", response_model=FlagAnalyticsResponse)
async def read_flag_analytics(
    flag_id: str,
    from_ts: Optional[datetime] = Query(default=None),
    to_ts: Optional[datetime] = Query(default=None),
    current_user: UserPublic = Depends(get_current_user),
    controller: AnalyticsController = Depends(_get_controller),
) -> FlagAnalyticsResponse:
    return await controller.get_flag_analytics(
        client_id=current_user.client_id,
        flag_id=flag_id,
        from_ts=from_ts,
        to_ts=to_ts,
    )


@router.get(
    "/flags/{flag_id}/time-series",
    response_model=FlagAnalyticsTimeSeriesResponse,
)
async def read_flag_time_series(
    flag_id: str,
    from_ts: Optional[datetime] = Query(default=None),
    to_ts: Optional[datetime] = Query(default=None),
    interval: str = Query(default="hour"),
    current_user: UserPublic = Depends(get_current_user),
    controller: AnalyticsController = Depends(_get_controller),
) -> FlagAnalyticsTimeSeriesResponse:
    return await controller.get_flag_time_series(
        client_id=current_user.client_id,
        flag_id=flag_id,
        from_ts=from_ts,
        to_ts=to_ts,
        interval=interval,
    )
