"""Per-request context stored in contextvars and populated by middleware."""

import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

_user_id: ContextVar[Optional[str]] = ContextVar("_user_id", default=None)
_client_id: ContextVar[Optional[str]] = ContextVar("_client_id", default=None)
_request_id: ContextVar[Optional[str]] = ContextVar("_request_id", default=None)
_actor_info: ContextVar[Optional[Dict[str, Any]]] = ContextVar("_actor_info", default=None)


class RequestContextManager:
    @staticmethod
    def get_user_id() -> Optional[str]:
        return _user_id.get()

    @staticmethod
    def set_user_id(value: str) -> None:
        _user_id.set(value)

    @staticmethod
    def get_client_id() -> Optional[str]:
        return _client_id.get()

    @staticmethod
    def set_client_id(value: str) -> None:
        _client_id.set(value)

    @staticmethod
    def get_request_id() -> Optional[str]:
        return _request_id.get()

    @staticmethod
    def set_request_id(value: str) -> None:
        _request_id.set(value)

    @staticmethod
    def get_actor_info() -> Dict[str, Any]:
        info = _actor_info.get()
        if info is None:
            return {
                "user_id": _user_id.get(),
                "client_id": _client_id.get(),
                "ip": None,
                "user_agent": None,
            }
        return {
            "user_id": _user_id.get(),
            "client_id": _client_id.get(),
            "ip": info.get("ip"),
            "user_agent": info.get("user_agent"),
        }

    @staticmethod
    def set_actor_info(ip: str, user_agent: str) -> None:
        _actor_info.set({"ip": ip, "user_agent": user_agent})


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
        RequestContextManager.set_request_id(request_id)
        ip = request.client.host if request.client else ""
        user_agent = request.headers.get("user-agent", "")
        RequestContextManager.set_actor_info(ip=ip, user_agent=user_agent)
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response
