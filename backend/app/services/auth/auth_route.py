"""Auth routes: signup, login, me. Router exported without prefix (main.py adds it)."""

from fastapi import APIRouter, Depends

from app.services.auth.auth_controller import AuthController
from app.services.auth.auth_model import (
    LoginRequest,
    LoginResponse,
    SignupRequest,
    SignupResponse,
    UserPublic,
)
from app.services.auth.dependencies import get_current_user

router = APIRouter()


def _get_controller() -> AuthController:
    return AuthController()


@router.post("/signup", response_model=SignupResponse)
async def signup(
    request: SignupRequest,
    controller: AuthController = Depends(_get_controller),
) -> SignupResponse:
    return await controller.signup(request)


@router.post("/login", response_model=LoginResponse)
async def login(
    request: LoginRequest,
    controller: AuthController = Depends(_get_controller),
) -> LoginResponse:
    return await controller.login(request)


@router.get("/me", response_model=UserPublic)
async def me(current_user: UserPublic = Depends(get_current_user)) -> UserPublic:
    return current_user
