"""Auth middleware — STUB. Phase 2A implements JWT + X-Client-API-Key validation."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class AuthMiddleware(BaseHTTPMiddleware):
    """Passthrough stub. Do not put real auth logic here until Phase 2A."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # TODO(Phase 2A): validate JWT (dashboard) / X-Client-API-Key (eval API)
        #   and populate RequestContextManager.set_user_id / set_client_id.
        return await call_next(request)
