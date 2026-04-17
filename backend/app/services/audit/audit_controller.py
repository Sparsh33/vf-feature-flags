"""HTTP controller for the audit domain: delegates to service, maps exceptions."""

from typing import Optional

from fastapi import HTTPException

from app.common.logging_helpers import LoggingData, log_error
from app.services.audit.audit_model import AuditLogListResponse, AuditLogResponse
from app.services.audit.audit_service import AuditService


class AuditController:
    def __init__(self, service: Optional[AuditService] = None) -> None:
        self._service = service or AuditService()

    async def list_logs(
        self,
        client_id: str,
        resource_type: Optional[str],
        resource_id: Optional[str],
        action: Optional[str],
        limit: int,
        skip: int,
    ) -> AuditLogListResponse:
        try:
            logs, total = await self._service.list_logs(
                client_id=client_id,
                resource_type=resource_type,
                resource_id=resource_id,
                action=action,
                limit=limit,
                skip=skip,
            )
        except Exception as exc:
            log_error(
                LoggingData(
                    message="audit.list_failed",
                    context={"client_id": client_id, "action": action},
                    error=exc,
                )
            )
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
