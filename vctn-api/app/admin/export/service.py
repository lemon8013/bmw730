"""app.admin.export — business logic.

An export job is a real record that walks through a real state machine:
``PENDING`` is created, and a failed job may be retried back to ``PENDING``.
File generation itself is out of scope for the management layer, but the record
and its transitions are genuine. The record is persisted in the frozen
``sys_export_job`` table, so every column written here exists in the DDL.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.export.model import ExportJob
from app.admin.export.repository import ExportTaskRepository
from app.admin.export.schema import CreateExportTaskRequest, ExportTaskResponse
from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.shared.audit.service import AuditService
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams

RESOURCE_TYPE: str = "sys_export_job"


class ExportTaskService:
    """Manage administrative export jobs."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = ExportTaskRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def create(
        self, *, actor_id: int, actor_username: str, payload: CreateExportTaskRequest
    ) -> ExportTaskResponse:
        row = await self._repository.create(
            export_type=payload.export_type,
            status="PENDING",
            requested_by=int(actor_id),
            filter_json=payload.filter_json,
            created_at=datetime.datetime.now(datetime.UTC),
        )
        await self._audit.record(
            self._session,
            action="EXPORT_TASK_CREATE",
            operator_id=int(actor_id),
            operator_username=actor_username,
            resource_type=RESOURCE_TYPE,
            resource_id=row.id,
            after_data={"export_type": payload.export_type},
            ip=None,
            user_agent=None,
        )
        await write_operation_log(
            self._session,
            operation="EXPORT_TASK_CREATE",
            result=RESULT_SUCCESS,
            operator_id=int(actor_id),
            resource_type=RESOURCE_TYPE,
            resource_id=str(int(row.id)),
        )
        await self._session.commit()
        return self._to_response(row)

    async def list(
        self, *, export_type: str | None, status: str | None, page: PageParams
    ) -> Page[ExportTaskResponse]:
        rows, total = await self._repository.list(
            export_type=export_type, status=status, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get(self, task_id: int) -> ExportTaskResponse:
        row = await self._repository.get(task_id)
        if row is None:
            raise NotFoundError("export job not found")
        return self._to_response(row)

    async def retry(
        self, *, task_id: int, actor_id: int, actor_username: str
    ) -> ExportTaskResponse:
        """Return a FAILED job to PENDING so it can be picked up again."""
        row = await self._repository.get(task_id)
        if row is None:
            raise NotFoundError("export job not found")
        if str(row.status) != "FAILED":
            raise BusinessRuleError("only a failed export job can be retried")
        row.status = "PENDING"
        row.file_id = None
        row.row_count = None
        row.error_message = None
        row.started_at = None
        row.finished_at = None
        await self._repository.flush()
        await self._audit.record(
            self._session,
            action="EXPORT_TASK_RETRY",
            operator_id=int(actor_id),
            operator_username=actor_username,
            resource_type=RESOURCE_TYPE,
            resource_id=row.id,
            before_data={"status": "FAILED"},
            after_data={"status": "PENDING"},
        )
        await write_operation_log(
            self._session,
            operation="EXPORT_TASK_RETRY",
            result=RESULT_SUCCESS,
            operator_id=int(actor_id),
            resource_type=RESOURCE_TYPE,
            resource_id=str(int(row.id)),
        )
        await self._session.commit()
        return self._to_response(row)

    def _to_response(self, row: ExportJob) -> ExportTaskResponse:
        return ExportTaskResponse(
            id=str(int(row.id)),
            export_type=str(row.export_type),
            status=str(row.status),
            file_id=None if row.file_id is None else str(int(row.file_id)),
            requested_by=None if row.requested_by is None else str(int(row.requested_by)),
            row_count=None if row.row_count is None else int(row.row_count),
            error_message=row.error_message,
            filter_json=row.filter_json,
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
        )
