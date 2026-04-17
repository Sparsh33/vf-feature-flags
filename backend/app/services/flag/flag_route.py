"""HTTP routes for flag + cohort CRUD."""

from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status

from app.middleware.request_context import RequestContextManager
from app.services.auth.dependencies import get_current_user
from app.services.flag.flag_controller import FlagController
from app.services.flag.flag_model import (
    FlagConfig,
    FlagCreateRequest,
    FlagListResponse,
    FlagUpdateRequest,
)


# Header-based shim kept ONLY as a FastAPI dependency override for tests
# (see `backend/tests/flag/conftest.py`). It is not wired into any route —
# production paths always use the JWT-based `get_current_user`.
async def fallback_current_user(
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
    x_client_id: Optional[str] = Header(default=None, alias="X-Client-Id"),
) -> Dict[str, Any]:
    if not x_user_id or not x_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-User-Id or X-Client-Id header",
        )
    RequestContextManager.set_user_id(x_user_id)
    RequestContextManager.set_client_id(x_client_id)
    return {"user_id": x_user_id, "client_id": x_client_id}


router = APIRouter()
_controller = FlagController()


@router.post("", response_model=FlagConfig, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=FlagConfig, status_code=status.HTTP_201_CREATED)
async def create_flag(
    request: FlagCreateRequest,
    _user: Dict[str, Any] = Depends(get_current_user),
) -> FlagConfig:
    return await _controller.create_flag(request)


@router.get("", response_model=FlagListResponse)
@router.get("/", response_model=FlagListResponse)
async def list_flags(
    status_filter: Optional[str] = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    _user: Dict[str, Any] = Depends(get_current_user),
) -> FlagListResponse:
    return await _controller.list_flags(status_filter=status_filter, limit=limit, skip=skip)


@router.get("/{flag_id}", response_model=FlagConfig)
async def get_flag(
    flag_id: str,
    _user: Dict[str, Any] = Depends(get_current_user),
) -> FlagConfig:
    return await _controller.get_flag(flag_id)


@router.patch("/{flag_id}", response_model=FlagConfig)
async def update_flag(
    flag_id: str,
    request: FlagUpdateRequest,
    _user: Dict[str, Any] = Depends(get_current_user),
) -> FlagConfig:
    return await _controller.update_flag(flag_id, request)


@router.delete("/{flag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_flag(
    flag_id: str,
    _user: Dict[str, Any] = Depends(get_current_user),
) -> Response:
    await _controller.delete_flag(flag_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
