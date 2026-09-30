"""app.admin.audit — business logic."""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.audit.repository import AuditLogRepository
from app.admin.audit.schema import (
    AccessLogResponse,
    AuditLogResponse,
    OperationLogResponse,
    SecurityLogResponse,
    TraceResponse,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.shared.pagination.params import Page, PageParams


def _as_text(value: object | None) -> str | None:
    return None if value is None else str(value)


class AuditQueryService:
    """Read side of the five log streams."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = AuditLogRepository(session)
        self._settings = settings or get_settings()

    async def audit_logs(
        self,
        *,
        action: str | None = None,
        operator_id: int | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        result: str | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        page: PageParams,
    ) -> Page[AuditLogResponse]:
        rows, total = await self._repository.search_audit_logs(
            action=action,
            operator_id=operator_id,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            start=start,
            end=end,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[AuditLogResponse.model_validate(row) for row in rows],
            total=total,
            params=page,
        )

    async def audit_log(self, log_id: int) -> AuditLogResponse:
        row = await self._repository.get_audit_log(log_id)
        if row is None:
            raise NotFoundError("audit log not found")
        return AuditLogResponse.model_validate(row)

    async def security_logs(
        self,
        *,
        event_type: str | None = None,
        user_id: int | None = None,
        result: str | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        page: PageParams,
    ) -> Page[SecurityLogResponse]:
        rows, total = await self._repository.search_security_logs(
            event_type=event_type,
            user_id=user_id,
            result=result,
            start=start,
            end=end,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[SecurityLogResponse.model_validate(row) for row in rows],
            total=total,
            params=page,
        )

    async def operation_logs(
        self,
        *,
        operation: str | None = None,
        operator_id: int | None = None,
        resource_type: str | None = None,
        result: str | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        page: PageParams,
    ) -> Page[OperationLogResponse]:
        rows, total = await self._repository.search_operation_logs(
            operation=operation,
            operator_id=operator_id,
            resource_type=resource_type,
            result=result,
            start=start,
            end=end,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[OperationLogResponse.model_validate(row) for row in rows],
            total=total,
            params=page,
        )

    async def access_logs(
        self,
        *,
        method: str | None = None,
        path: str | None = None,
        status_code: int | None = None,
        user_id: int | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        page: PageParams,
    ) -> Page[AccessLogResponse]:
        rows, total = await self._repository.search_access_logs(
            method=method,
            path=path,
            status_code=status_code,
            user_id=user_id,
            start=start,
            end=end,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[AccessLogResponse.model_validate(row) for row in rows],
            total=total,
            params=page,
        )

    async def trace(self, trace_id: str) -> TraceResponse:
        """Return every stream's rows that carry one trace id."""
        audit_rows, _ = await self._repository.search_audit_logs(
            trace_id=trace_id, limit=self._settings.OUTBOX_BATCH_SIZE, offset=0
        )
        security_rows, _ = await self._repository.search_security_logs(
            trace_id=trace_id, limit=self._settings.OUTBOX_BATCH_SIZE, offset=0
        )
        operation_rows, _ = await self._repository.search_operation_logs(
            trace_id=trace_id, limit=self._settings.OUTBOX_BATCH_SIZE, offset=0
        )
        access_rows, _ = await self._repository.search_access_logs(
            trace_id=trace_id, limit=self._settings.OUTBOX_BATCH_SIZE, offset=0
        )
        return TraceResponse(
            trace_id=trace_id,
            audit_logs=[AuditLogResponse.model_validate(row) for row in audit_rows],
            security_logs=[SecurityLogResponse.model_validate(row) for row in security_rows],
            operation_logs=[OperationLogResponse.model_validate(row) for row in operation_rows],
            access_logs=[AccessLogResponse.model_validate(row) for row in access_rows],
        )
