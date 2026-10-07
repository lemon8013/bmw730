"""One audit entry point for every ops action.

Spec 22 requires that ops configuration changes and ops actions are audited, and
spec 25 adds ``ops_operation_record`` as the ops readable projection. Writing
both by hand in every service would eventually drift, so every ops service calls
:meth:`OpsAuditRecorder.record` instead: it appends the authoritative
``sys_audit_log`` row **and** the ops readable row inside the same transaction.

Nothing in this module updates an existing row — audit is append-only.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.ops.audit.model import OpsOperationRecord
from app.shared.audit.service import RESULT_SUCCESS, AuditService
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.tracing.context import get_request_id, get_trace_id


class OpsAuditRecorder:
    """Writes the authoritative audit row and the ops readable row together."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def record(
        self,
        *,
        action: str,
        actor: Principal,
        resource_type: str,
        resource_id: int | None = None,
        result: str = RESULT_SUCCESS,
        error_message: str | None = None,
        before_data: dict[str, Any] | None = None,
        after_data: dict[str, Any] | None = None,
    ) -> None:
        """Append the audit trail for one ops action."""
        await self._audit.record(
            self._session,
            action=action,
            result=result,
            actor=actor,
            operator_username=actor.username,
            resource_type=resource_type,
            resource_id=resource_id,
            before_data=before_data,
            after_data=after_data,
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        self._session.add(
            OpsOperationRecord(
                id=new_id(),
                operator_id=actor.subject_id if actor.is_admin else None,
                operator_username=actor.username,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                result=result,
                error_message=error_message,
                ip_address=actor.ip,
                user_agent=actor.user_agent,
                trace_id=get_trace_id(),
                request_id=get_request_id(),
                before_data=before_data,
                after_data=after_data,
            )
        )
        await self._session.flush()
