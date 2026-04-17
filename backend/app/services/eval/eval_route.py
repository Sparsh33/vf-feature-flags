"""HTTP route for the feature-flag evaluation endpoint."""

from typing import Any, Dict

from fastapi import APIRouter, Body, Depends, Response

from app.services.auth.dependencies import get_current_client
from app.services.eval.eval_controller import handle_evaluate
from app.services.eval.eval_model import EvalResponse

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
