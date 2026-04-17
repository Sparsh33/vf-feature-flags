"""Client routes: API key rotation. Router exported without prefix (main.py adds it)."""

from fastapi import APIRouter, Depends

from app.services.auth.auth_controller import AuthController
from app.services.auth.auth_model import RotateApiKeyResponse, UserPublic
from app.services.auth.dependencies import get_current_user

router = APIRouter()


def _get_controller() -> AuthController:
    return AuthController()


@router.post("/rotate-api-key", response_model=RotateApiKeyResponse)
async def rotate_api_key(
    current_user: UserPublic = Depends(get_current_user),
    controller: AuthController = Depends(_get_controller),
) -> RotateApiKeyResponse:
    return await controller.rotate_api_key(current_user.client_id)
