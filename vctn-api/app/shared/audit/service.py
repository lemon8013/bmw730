"""Audit service.

Every privileged or state changing action is recorded in ``sys_audit_log``,
including the failures: a ``PermissionDeniedError`` is audited with
``result = FAILURE``.

Audit records never contain a password, an MFA secret, a raw token or a raw
user input: payloads pass through :func:`app.shared.security.masking.mask_mapping`
first.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.audit.model import SysAuditLog
from app.core.config import Settings, get_settings
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_FAILURE, RESULT_SUCCESS
from app.shared.security.masking import mask_mapping
from app.shared.tracing.context import get_request_id, get_trace_id


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
    ) -> SysAuditLog:
        """Append one audit record to the current transaction."""
        if not self._settings.AUDIT_ENABLED:
            return SysAuditLog()  # never persisted; callers only use the return value loosely
        row = SysAuditLog(
            id=new_id(),
            trace_id=get_trace_id(),
            request_id=get_request_id(),
            operator_id=operator_id,
            operator_username=operator_username,
            action=action,
            resource_type=resource_type,
            resource_id=None if resource_id is None else str(resource_id),
            before_data=mask_mapping(before_data) if before_data else None,
            after_data=mask_mapping(after_data) if after_data else None,
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
