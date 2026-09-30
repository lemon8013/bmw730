"""app.admin.export — business logic.

An export task is a real record that walks through a real state machine:
``PENDING`` is created, and a failed task may be retried back to ``PENDING``.
File generation itself is out of scope for the management layer, but the record
and its transitions are genuine.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.export.model import SysExportTask
from app.admin.export.repository import ExportTaskRepository
from app.admin.export.schema import CreateExportTaskRequest, ExportTaskResponse
from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.shared.audit.service import AuditService
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams


class ExportTaskService:
    """Manage administrative export tasks."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = ExportTaskRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def create(
        self, *, actor_id: int, actor_username: str, payload: CreateExportTaskRequest
    ) -> ExportTaskResponse:
        now = datetime.datetime.now(datetime.UTC)
        row = await self._repository.create(
            task_type=payload.task_type,
            status="PENDING",
            requested_by=int(actor_id),
            progress=0,
            params=payload.params,
            created_at=now,
            updated_at=now,
        )
        await self._audit.record(
            self._session,
            action="EXPORT_TASK_CREATE",
            operator_id=int(actor_id),
            operator_username=actor_username,
            resource_type="sys_export_task",
            resource_id=row.id,
            after_data={"task_type": payload.task_type},
            ip=None,
            user_agent=None,
        )
        await write_operation_log(
            self._session,
            operation="EXPORT_TASK_CREATE",
            result=RESULT_SUCCESS,
            operator_id=int(actor_id),
            resource_type="sys_export_task",
            resource_id=str(int(row.id)),
        )
        await self._session.commit()
        return self._to_response(row)

    async def list(
        self, *, task_type: str | None, status: str | None, page: PageParams
    ) -> Page[ExportTaskResponse]:
        rows, total = await self._repository.list(
            task_type=task_type, status=status, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get(self, task_id: int) -> ExportTaskResponse:
        row = await self._repository.get(task_id)
        if row is None:
            raise NotFoundError("export task not found")
        return self._to_response(row)

    async def retry(self, *, task_id: int, actor_id: int, actor_username: str) -> ExportTaskResponse:
        """Return a FAILED task to PENDING so it can be picked up again."""
        row = await self._repository.get(task_id)
        if row is None:
            raise NotFoundError("export task not found")
        if str(row.status) != "FAILED":
            raise BusinessRuleError("only a failed export task can be retried")
        now = datetime.datetime.now(datetime.UTC)
        row.status = "PENDING"
        row.progress = 0
        row.file_id = None
        row.error_message = None
        row.finished_at = None
        row.updated_at = now
        await self._repository.flush()
        await self._audit.record(
            self._session,
            action="EXPORT_TASK_RETRY",
            operator_id=int(actor_id),
            operator_username=actor_username,
            resource_type="sys_export_task",
            resource_id=row.id,
            before_data={"status": "FAILED"},
            after_data={"status": "PENDING"},
        )
        await write_operation_log(
            self._session,
            operation="EXPORT_TASK_RETRY",
            result=RESULT_SUCCESS,
            operator_id=int(actor_id),
            resource_type="sys_export_task",
            resource_id=str(int(row.id)),
        )
        await self._session.commit()
        return self._to_response(row)

    def _to_response(self, row: SysExportTask) -> ExportTaskResponse:
        return ExportTaskResponse(
            id=str(int(row.id)),
            task_type=str(row.task_type),
            status=str(row.status),
            file_id=row.file_id,
            requested_by=str(int(row.requested_by)),
            progress=int(row.progress or 0),
            error_message=row.error_message,
            params=row.params,
            created_at=row.created_at,
            updated_at=row.updated_at,
            finished_at=row.finished_at,
        )
