"""app.ops.audit — business logic.

The ops audit projection is read-only. There is deliberately no mutation here:
``ops_operation_record`` is append-only, it is written by
:class:`app.ops.audit.recorder.OpsAuditRecorder` inside the transaction of the
action that produced it, and an operator must never be able to rewrite the trail
through the API.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.ops.audit.model import OpsOperationRecord
from app.ops.audit.repository import AuditRepository
from app.ops.audit.schema import AuditRecordResponse
from app.shared.pagination.params import Page, PageParams


class AuditService:
    """Read access to the ops operation records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = AuditRepository(session)

    async def list_records(
        self,
        *,
        action: str | None = None,
        resource_type: str | None = None,
        operator_username: str | None = None,
        result: str | None = None,
        trace_id: str | None = None,
        start_at: datetime.datetime | None = None,
        end_at: datetime.datetime | None = None,
        page: PageParams,
    ) -> Page[AuditRecordResponse]:
        rows, total = await self._repository.list(
            action=action,
            resource_type=resource_type,
            operator_username=operator_username,
            result=result,
            trace_id=trace_id,
            start_at=start_at,
            end_at=end_at,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get_record(self, record_id: int) -> AuditRecordResponse:
        row = await self._repository.get(record_id)
        if row is None:
            raise NotFoundError("audit record not found")
        return self._to_response(row)

    def _to_response(self, row: OpsOperationRecord) -> AuditRecordResponse:
        return AuditRecordResponse(
            id=str(int(row.id)),
            operator_id=str(int(row.operator_id)) if row.operator_id else None,
            operator_username=row.operator_username,
            action=str(row.action),
            resource_type=str(row.resource_type),
            resource_id=str(int(row.resource_id)) if row.resource_id else None,
            result=str(row.result),
            error_message=row.error_message,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            trace_id=row.trace_id,
            request_id=row.request_id,
            before_data=row.before_data,
            after_data=row.after_data,
            created_at=row.created_at,
        )
