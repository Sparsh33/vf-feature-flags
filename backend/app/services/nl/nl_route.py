"""HTTP routes for the NL flag builder. Router exported without prefix (main.py adds it)."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status

from app.middleware.request_context import RequestContextManager
from app.services.nl.nl_controller import NLController
from app.services.nl.nl_model import NLChatRequest, NLChatResponse

router = APIRouter()


# TEMP: header-based identity until full auth integration lands. Proper JWT enforcement
# will replace this via Depends(get_current_user) once auth middleware is wired end-to-end.
async def _resolve_identity(
    x_client_id: Optional[str] = Header(default=None, alias="X-Client-Id"),
    x_user_id: Optional[str] = Header(default=None, alias="X-User-Id"),
) -> None:
    if not x_client_id or not x_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: X-Client-Id and X-User-Id required",
        )
    RequestContextManager.set_client_id(x_client_id)
    RequestContextManager.set_user_id(x_user_id)


def _get_controller() -> NLController:
    return NLController()


@router.post("/chat", response_model=NLChatResponse)
async def chat(
    request: NLChatRequest,
    controller: NLController = Depends(_get_controller),
    _identity: None = Depends(_resolve_identity),
) -> NLChatResponse:
    return await controller.chat(request)
