"""Business logic for flag + cohort CRUD."""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.common.errors import FlagNotFound, InvalidCohortSum, ValidationError
from app.middleware.request_context import RequestContextManager
from app.services.flag.cache_invalidation import invalidate_flag_cache
from app.services.flag.flag_model import (
    Cohort,
    FlagConfig,
    FlagCreateRequest,
    FlagListResponse,
    FlagUpdateRequest,
)
from app.services.flag.repositories.flag_repository import FlagRepository

try:  # pragma: no cover - audit module may not exist yet
    from app.services.audit.service import audit_emit  # type: ignore
except ImportError:  # pragma: no cover - Phase 2D not ready
    audit_emit = None  # type: ignore

_FLAG_KEY_PATTERN = re.compile(r"^[a-z0-9_-]{1,100}$")
_ALLOWED_STATUSES = frozenset({"active", "draft"})
_COHORT_SUM_TOLERANCE = 0.01
_COHORT_SUM_TARGET = 100.0
_logger = logging.getLogger("vf_ff.flag.service")


class FlagService:
    def __init__(self, repository: Optional[FlagRepository] = None) -> None:
        self._repository = repository or FlagRepository()

    async def create_flag(self, request: FlagCreateRequest) -> FlagConfig:
        client_id = self._require_client_id()
        user_id = RequestContextManager.get_user_id()
        self._validate_flag_key(request.flag_key)
        self._validate_status(request.status)
        cohorts = self._assign_new_cohort_ids(request.cohorts)
        self._validate_cohorts(cohorts)
        now = datetime.now(timezone.utc)
        flag = FlagConfig(
            client_id=client_id,
            flag_key=request.flag_key,
            name=request.name,
            description=request.description,
            default_value=request.default_value,
            cohorts=cohorts,
            parameters_schema=request.parameters_schema,
            status=request.status,
            created_at=now,
            updated_at=now,
            created_by=user_id,
            updated_by=user_id,
        )
        inserted = await self._repository.insert(flag)
        await invalidate_flag_cache(client_id, inserted.flag_key)
        self._emit_audit("flag.created", inserted.id, {"flag_key": inserted.flag_key})
        return inserted

    async def update_flag(self, flag_id: str, request: FlagUpdateRequest) -> FlagConfig:
        client_id = self._require_client_id()
        existing = await self._repository.get_by_id(client_id, flag_id)
        if existing is None:
            raise FlagNotFound(f"Flag '{flag_id}' not found")
        updates: Dict[str, Any] = {}
        if request.name is not None:
            updates["name"] = request.name
        if request.description is not None:
            updates["description"] = request.description
        if request.default_value is not None:
            updates["default_value"] = request.default_value
        if request.parameters_schema is not None:
            updates["parameters_schema"] = request.parameters_schema
        if request.status is not None:
            self._validate_status(request.status)
            updates["status"] = request.status
        if request.cohorts is not None:
            merged = self._reconcile_cohorts(existing.cohorts, request.cohorts)
            self._validate_cohorts(merged)
            updates["cohorts"] = [cohort.model_dump() for cohort in merged]
        if not updates:
            return existing
        updates["updated_by"] = RequestContextManager.get_user_id()
        updated = await self._repository.update(client_id, flag_id, updates)
        if updated is None:
            raise FlagNotFound(f"Flag '{flag_id}' not found")
        await invalidate_flag_cache(client_id, updated.flag_key)
        self._emit_audit("flag.updated", updated.id, {"flag_key": updated.flag_key})
        return updated

    async def get_flag(self, flag_id: str) -> FlagConfig:
        client_id = self._require_client_id()
        flag = await self._repository.get_by_id(client_id, flag_id)
        if flag is None:
            raise FlagNotFound(f"Flag '{flag_id}' not found")
        return flag

    async def get_flag_by_key(self, flag_key: str) -> FlagConfig:
        client_id = self._require_client_id()
        flag = await self._repository.get_by_key(client_id, flag_key)
        if flag is None:
            raise FlagNotFound(f"Flag '{flag_key}' not found")
        return flag

    async def list_flags(
        self,
        status: Optional[str] = None,
        limit: int = 50,
        skip: int = 0,
    ) -> FlagListResponse:
        client_id = self._require_client_id()
        if status is not None:
            self._validate_status(status)
        flags, total = await self._repository.list_flags(client_id, status, limit, skip)
        return FlagListResponse(flags=flags, total=total)

    async def delete_flag(self, flag_id: str) -> None:
        client_id = self._require_client_id()
        existing = await self._repository.get_by_id(client_id, flag_id)
        if existing is None:
            raise FlagNotFound(f"Flag '{flag_id}' not found")
        deleted = await self._repository.soft_delete(client_id, flag_id)
        if not deleted:
            raise FlagNotFound(f"Flag '{flag_id}' not found")
        await invalidate_flag_cache(client_id, existing.flag_key)
        self._emit_audit("flag.deleted", flag_id, {"flag_key": existing.flag_key})

    def _require_client_id(self) -> str:
        client_id = RequestContextManager.get_client_id()
        if not client_id:
            raise ValidationError("client_id missing from request context")
        return client_id

    def _validate_flag_key(self, flag_key: str) -> None:
        if not _FLAG_KEY_PATTERN.match(flag_key or ""):
            raise ValidationError("flag_key must match ^[a-z0-9_-]{1,100}$")

    def _validate_status(self, status: str) -> None:
        if status not in _ALLOWED_STATUSES:
            raise ValidationError(f"status must be one of {sorted(_ALLOWED_STATUSES)}")

    def _validate_cohorts(self, cohorts: List[Cohort]) -> None:
        if not cohorts:
            raise InvalidCohortSum("cohorts must be non-empty and sum to 100")
        names_seen = set()
        for cohort in cohorts:
            if cohort.percentage <= 0 or cohort.percentage > 100:
                raise ValidationError(f"cohort '{cohort.name}' percentage must be in (0, 100]")
            if cohort.name in names_seen:
                raise ValidationError(f"duplicate cohort name '{cohort.name}' within flag")
            names_seen.add(cohort.name)
        total = sum(cohort.percentage for cohort in cohorts)
        if abs(total - _COHORT_SUM_TARGET) >= _COHORT_SUM_TOLERANCE:
            raise InvalidCohortSum(f"cohort percentages must sum to 100 (got {total})")

    def _assign_new_cohort_ids(self, cohorts: List[Cohort]) -> List[Cohort]:
        return [
            cohort.model_copy(update={"id": cohort.id or str(uuid.uuid4())}) for cohort in cohorts
        ]

    def _reconcile_cohorts(self, existing: List[Cohort], incoming: List[Cohort]) -> List[Cohort]:
        existing_by_name = {cohort.name: cohort for cohort in existing}
        reconciled: List[Cohort] = []
        for cohort in incoming:
            prior = existing_by_name.get(cohort.name)
            if prior is not None:
                reconciled.append(cohort.model_copy(update={"id": prior.id}))
            else:
                reconciled.append(cohort.model_copy(update={"id": str(uuid.uuid4())}))
        return reconciled

    def _emit_audit(self, action: str, flag_id: Optional[str], after: Dict[str, Any]) -> None:
        if audit_emit is None or flag_id is None:
            return
        try:
            audit_emit(
                action=action,
                resource_type="flag",
                resource_id=flag_id,
                after=after,
            )
        except Exception:  # pragma: no cover - audit must never break writes
            pass
