"""FastAPI dependencies for auth: `get_current_user` (JWT) and `get_current_client` (API key)."""

from typing import Optional

from fastapi import Depends, Header, HTTPException, status

from app.common.errors import InvalidApiKey
from app.middleware.request_context import RequestContextManager
from app.services.auth.auth_model import ClientPublic, UserPublic
from app.services.auth.auth_service import AuthService
from app.services.auth.security import decode_access_token

_BEARER_PREFIX = "bearer "


def _get_auth_service() -> AuthService:
    return AuthService()


async def get_current_user(
    authorization: Optional[str] = Header(default=None),
    service: AuthService = Depends(_get_auth_service),
) -> UserPublic:
    if not authorization or not authorization.lower().startswith(_BEARER_PREFIX):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    token = authorization[len(_BEARER_PREFIX) :].strip()
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid or expired token"
        )
    try:
        user_public = await service.get_user_public(payload.sub)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="user not found"
        ) from exc
    RequestContextManager.set_user_id(user_public.id)
    RequestContextManager.set_client_id(user_public.client_id)
    return user_public


async def get_current_client(
    x_client_api_key: Optional[str] = Header(default=None, alias="X-Client-API-Key"),
    service: AuthService = Depends(_get_auth_service),
) -> ClientPublic:
    if not x_client_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing api key")
    try:
        _client_record, client_public = await service.resolve_client_by_api_key(x_client_api_key)
    except InvalidApiKey as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid api key"
        ) from exc
    RequestContextManager.set_client_id(client_public.id)
    return client_public
