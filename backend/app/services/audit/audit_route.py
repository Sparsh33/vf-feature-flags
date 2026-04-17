"""HTTP routes for reading audit logs."""

from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.common.logging_helpers import LoggingData, log_error
from app.services.audit.audit_model import AuditLogListResponse, AuditLogResponse
from app.services.audit.repositories.audit_repository import AuditRepository

router = APIRouter()

try:
    from app.services.auth.auth_model import UserPublic
    from app.services.auth.dependencies import get_current_user

    async def _resolve_client_id(
        current_user: UserPublic = Depends(get_current_user),
    ) -> str:
        if not current_user.client_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return current_user.client_id

except ImportError:
    # TEMP until Phase 2A merges: fallback to X-Client-Id header when auth dependency missing.
    async def _resolve_client_id(  # type: ignore[no-redef]
        x_client_id: Optional[str] = Header(default=None, alias="X-Client-Id"),
    ) -> str:
        if not x_client_id:
            raise HTTPException(status_code=401, detail="Unauthorized: X-Client-Id required")
        return x_client_id


@router.get("/", response_model=AuditLogListResponse)
async def list_audit_logs(
    resource_type: Optional[str] = Query(default=None),
    resource_id: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    client_id: str = Depends(_resolve_client_id),
) -> AuditLogListResponse:
    try:
        repository = AuditRepository()
        logs, total = await repository.list_logs(
            client_id=client_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            limit=limit,
            skip=skip,
        )
    except Exception as exc:
        try:
            log_error(
                LoggingData(
                    message="list_audit_logs failed",
                    context={"client_id": client_id, "action": action},
                    error=exc,
                )
            )
        except Exception:
            pass
        raise HTTPException(status_code=500, detail="Failed to list audit logs") from exc
    responses = [
        AuditLogResponse(
            id=log.id or "",
            actor_user_id=log.actor_user_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            before=log.before,
            after=log.after,
            ts=log.ts,
        )
        for log in logs
    ]
    return AuditLogListResponse(logs=responses, total=total)
