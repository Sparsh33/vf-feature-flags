"""HTTP routes for the analytics domain."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.middleware.request_context import RequestContextManager
from app.services.analytics.analytics_model import (
    FlagAnalyticsResponse,
    FlagAnalyticsTimeSeriesResponse,
)
from app.services.analytics.analytics_service import (
    get_flag_analytics,
    get_flag_time_series,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# TEMP: until `app.services.auth.dependencies.get_current_user` exists (Phase 2A),
# resolve client_id from X-Client-Id header and populate request context.
async def get_current_user(
    x_client_id: Optional[str] = Header(default=None, alias="X-Client-Id"),
) -> str:
    if not x_client_id:
        raise HTTPException(status_code=401, detail="missing X-Client-Id header")
    RequestContextManager.set_client_id(x_client_id)
    return x_client_id


@router.get("/flags/{flag_id}", response_model=FlagAnalyticsResponse)
async def read_flag_analytics(
    flag_id: str,
    from_ts: Optional[datetime] = Query(default=None),
    to_ts: Optional[datetime] = Query(default=None),
    _: str = Depends(get_current_user),
) -> FlagAnalyticsResponse:
    try:
        return await get_flag_analytics(flag_id=flag_id, from_ts=from_ts, to_ts=to_ts)
    except ValueError as exc:
        logger.warning("Bad analytics request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/flags/{flag_id}/time-series",
    response_model=FlagAnalyticsTimeSeriesResponse,
)
async def read_flag_time_series(
    flag_id: str,
    from_ts: Optional[datetime] = Query(default=None),
    to_ts: Optional[datetime] = Query(default=None),
    interval: str = Query(default="hour"),
    _: str = Depends(get_current_user),
) -> FlagAnalyticsTimeSeriesResponse:
    try:
        return await get_flag_time_series(
            flag_id=flag_id,
            from_ts=from_ts,
            to_ts=to_ts,
            interval=interval,
        )
    except ValueError as exc:
        logger.warning("Bad time-series request: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
