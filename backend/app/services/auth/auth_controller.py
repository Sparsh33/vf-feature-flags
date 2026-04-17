"""Auth HTTP controller: delegates to service, maps domain exceptions to HTTP."""

from fastapi import HTTPException, status

from app.common.errors import ConflictError, InvalidCredentials, UserNotFound
from app.common.logging_helpers import LoggingData
from app.services.auth.auth_model import (
    LoginRequest,
    LoginResponse,
    RotateApiKeyResponse,
    SignupRequest,
    SignupResponse,
    UserPublic,
)
from app.services.auth.auth_service import AuthService
from app.services.auth.logging_shim import log_error


class AuthController:
    def __init__(self, service: AuthService | None = None) -> None:
        self._service = service or AuthService()

    async def signup(self, request: SignupRequest) -> SignupResponse:
        try:
            return await self._service.signup(request)
        except ConflictError as exc:
            log_error(LoggingData(message="signup conflict", error=exc))
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        except Exception as exc:
            log_error(LoggingData(message="signup error", error=exc))
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="signup failed",
            ) from exc

    async def login(self, request: LoginRequest) -> LoginResponse:
        try:
            return await self._service.login(request)
        except InvalidCredentials as exc:
            log_error(LoggingData(message="login failed", error=exc))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid email or password",
            ) from exc

    async def me(self, current_user: UserPublic) -> UserPublic:
        return current_user

    async def rotate_api_key(self, client_id: str) -> RotateApiKeyResponse:
        try:
            return await self._service.rotate_api_key(client_id)
        except UserNotFound as exc:
            log_error(LoggingData(message="rotate_api_key not found", error=exc))
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="client not found"
            ) from exc
