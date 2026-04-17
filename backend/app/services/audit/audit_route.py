"""HTTP routes for reading audit logs."""

from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.services.audit.audit_controller import AuditController
from app.services.audit.audit_model import AuditLogListResponse
from app.services.auth.auth_model import UserPublic
from app.services.auth.dependencies import get_current_user

router = APIRouter()


def _get_controller() -> AuditController:
    return AuditController()


@router.get("/", response_model=AuditLogListResponse)
async def list_audit_logs(
    resource_type: Optional[str] = Query(default=None),
    resource_id: Optional[str] = Query(default=None),
    action: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    skip: int = Query(default=0, ge=0),
    current_user: UserPublic = Depends(get_current_user),
    controller: AuditController = Depends(_get_controller),
) -> AuditLogListResponse:
    return await controller.list_logs(
        client_id=current_user.client_id,
        resource_type=resource_type,
        resource_id=resource_id,
        action=action,
        limit=limit,
        skip=skip,
    )
