"""HTTP routes for the NL flag builder. Router exported without prefix (main.py adds it)."""

from fastapi import APIRouter, Depends

from app.middleware.request_context import RequestContextManager
from app.services.auth.auth_model import UserPublic
from app.services.auth.dependencies import get_current_user
from app.services.nl.nl_controller import NLController
from app.services.nl.nl_model import NLChatRequest, NLChatResponse

router = APIRouter()


async def _resolve_identity(
    current_user: UserPublic = Depends(get_current_user),
) -> None:
    RequestContextManager.set_client_id(current_user.client_id)
    RequestContextManager.set_user_id(current_user.id)


def _get_controller() -> NLController:
    return NLController()


@router.post("/chat", response_model=NLChatResponse)
async def chat(
    request: NLChatRequest,
    controller: NLController = Depends(_get_controller),
    _identity: None = Depends(_resolve_identity),
) -> NLChatResponse:
    return await controller.chat(request)
