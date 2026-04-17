"""Read-side service for audit logs."""

from typing import List, Optional, Tuple

from app.services.audit.audit_model import AuditLog
from app.services.audit.repositories.audit_repository import AuditRepository


class AuditService:
    def __init__(self, repository: Optional[AuditRepository] = None) -> None:
        self._repository = repository or AuditRepository()

    async def list_logs(
        self,
        client_id: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> Tuple[List[AuditLog], int]:
        return await self._repository.list_logs(
            client_id=client_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            limit=limit,
            skip=skip,
        )
