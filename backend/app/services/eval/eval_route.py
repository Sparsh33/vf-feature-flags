"""HTTP route for the feature-flag evaluation endpoint."""

from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Request, Response, status

from app.middleware.request_context import RequestContextManager
from app.services.eval.eval_controller import handle_evaluate
from app.services.eval.eval_model import EvalResponse

try:
    from app.services.auth.dependencies import get_current_client  # type: ignore
except ImportError:  # pragma: no cover - TEMP until Phase 2A merges

    async def get_current_client(
        request: Request,
        x_client_api_key: str = Header(default="", alias="X-Client-API-Key"),
        x_client_id: str = Header(default="", alias="X-Client-Id"),
    ):
        # TEMP until Phase 2A merges — read X-Client-Id header directly
        if not x_client_api_key and not x_client_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing api key")
        client_id = x_client_id or x_client_api_key
        RequestContextManager.set_client_id(client_id)
        return client_id


router = APIRouter()


def _resolve_client_id(client: Any) -> str:
    if isinstance(client, str):
        return client
    client_id = getattr(client, "id", None)
    if isinstance(client_id, str) and client_id:
        return client_id
    return str(client)


@router.post("/evaluate/{flag_key}", response_model=EvalResponse)
async def evaluate_flag(
    flag_key: str,
    response: Response,
    body: Dict[str, Any] = Body(default_factory=dict),
    client: Any = Depends(get_current_client),
) -> EvalResponse:
    client_id = _resolve_client_id(client)
    return await handle_evaluate(
        client_id=client_id, flag_key=flag_key, body=body, response=response
    )
