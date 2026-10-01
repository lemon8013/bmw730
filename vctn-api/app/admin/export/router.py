"""app.admin.export — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.admin.export.schema import CreateExportTaskRequest, ExportTaskResponse
from app.admin.export.service import ExportTaskService
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


@router.post("/export/tasks", response_model=ApiResponse[ExportTaskResponse])
async def create_export_task(
    payload: CreateExportTaskRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("EXPORT_MANAGE")),
) -> ApiResponse[ExportTaskResponse]:
    return success(
        await ExportTaskService(session).create(
            actor_id=principal.subject_id,
            actor_username=principal.username,
            payload=payload,
        )
    )


@router.get("/export/tasks", response_model=ApiResponse[Page[ExportTaskResponse]])
async def list_export_tasks(
    session: DbSessionDep,
    export_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("EXPORT_MANAGE")),
) -> ApiResponse[Page[ExportTaskResponse]]:
    return success(
        await ExportTaskService(session).list(
            export_type=export_type,
            status=status,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get("/export/tasks/{task_id}", response_model=ApiResponse[ExportTaskResponse])
async def get_export_task(
    task_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("EXPORT_MANAGE")),
) -> ApiResponse[ExportTaskResponse]:
    return success(await ExportTaskService(session).get(int(task_id)))


@router.post("/export/tasks/{task_id}/retry", response_model=ApiResponse[ExportTaskResponse])
async def retry_export_task(
    task_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("EXPORT_MANAGE")),
) -> ApiResponse[ExportTaskResponse]:
    return success(
        await ExportTaskService(session).retry(
            task_id=int(task_id),
            actor_id=principal.subject_id,
            actor_username=principal.username,
        )
    )
