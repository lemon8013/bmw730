"""Audit service.

Every privileged or state changing action is recorded in ``sys_audit_log``,
including the failures: a ``PermissionDeniedError`` is audited with
``result = FAILURE``.

Audit records never contain a password, an MFA secret, a raw token or a raw
user input: payloads pass through :func:`app.shared.security.masking.mask_mapping`
first.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.audit.model import SysAuditLog
from app.core.config import Settings, get_settings
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_FAILURE, RESULT_SUCCESS
from app.shared.security.masking import mask_mapping
from app.shared.tracing.context import get_request_id, get_trace_id

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids an import cycle
    from app.shared.auth.context import Principal


class AuditService:
    """Writes audit records inside the caller's transaction."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def record(
        self,
        session: AsyncSession,
        *,
        action: str,
        result: str = RESULT_SUCCESS,
        operator_id: int | None = None,
        operator_username: str | None = None,
        resource_type: str | None = None,
        resource_id: str | int | None = None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
        error_code: str | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
        actor: Principal | None = None,
    ) -> SysAuditLog:
        """Append one audit record to the current transaction.

        ``sys_audit_log.operator_id`` is a foreign key to ``sys_user(id)``, so a
        platform business user must never be written to the column. Pass
        ``actor`` and the id is stored for operators only; for a platform user
        the subject is kept in ``after_data`` instead.
        """
        if not self._settings.AUDIT_ENABLED:
            return SysAuditLog()  # never persisted; callers only use the return value loosely
        resolved_operator_id = operator_id
        resolved_username = operator_username
        payload = dict(after_data) if after_data else {}
        if actor is not None:
            resolved_username = actor.username
            if actor.is_admin:
                resolved_operator_id = actor.subject_id
            else:
                resolved_operator_id = None
                payload["subject_id"] = str(actor.subject_id)
                payload["subject_type"] = actor.subject_type
        row = SysAuditLog(
            id=new_id(),
            trace_id=get_trace_id(),
            request_id=get_request_id(),
            operator_id=resolved_operator_id,
            operator_username=resolved_username,
            action=action,
            resource_type=resource_type,
            resource_id=None if resource_id is None else str(resource_id),
            before_data=mask_mapping(before_data) if before_data else None,
            after_data=mask_mapping(payload) if payload else None,
            result=result,
            error_code=error_code,
            ip=ip,
            user_agent=user_agent,
        )
        session.add(row)
        await session.flush()
        return row

    async def record_failure(
        self,
        session: AsyncSession,
        *,
        action: str,
        error_code: str | None = None,
        operator_id: int | None = None,
        operator_username: str | None = None,
        resource_type: str | None = None,
        resource_id: str | int | None = None,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> SysAuditLog:
        """Append a ``FAILURE`` audit record."""
        return await self.record(
            session,
            action=action,
            result=RESULT_FAILURE,
            error_code=error_code,
            operator_id=operator_id,
            operator_username=operator_username,
            resource_type=resource_type,
            resource_id=resource_id,
            ip=ip,
            user_agent=user_agent,
        )
