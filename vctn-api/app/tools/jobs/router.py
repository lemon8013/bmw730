"""app.tools.jobs — HTTP endpoints.

Job management is admin only. The runtime ASYNC mode creates the rows directly
(see :mod:`app.tools.runtime.service`); this router lets an operator inspect the
queue and retry failed jobs.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.shared.authorization.dependencies import (
    AdminPrincipal,
    require_permission,
)
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse
from app.tools.jobs.schema import ToolJobListResponse, ToolJobResponse
from app.tools.jobs.service import ToolJobService

router = APIRouter()


def _service(session: DbSessionDep) -> ToolJobService:
    return ToolJobService(session)


@router.get(
    "/jobs",
    response_model=ApiResponse[ToolJobListResponse],
    dependencies=[Depends(require_permission("TOOL_MANAGE"))],
)
async def list_jobs(
    session: DbSessionDep,
    _: AdminPrincipal,
    status: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[ToolJobListResponse]:
    result = await _service(session).list_jobs(
        status=status,
        job_type=job_type,
        page=page,
        page_size=page_size,
    )
    return success(result)


@router.get(
    "/jobs/{job_id}",
    response_model=ApiResponse[ToolJobResponse],
    dependencies=[Depends(require_permission("TOOL_MANAGE"))],
)
async def get_job(
    job_id: str,
    session: DbSessionDep,
    _: AdminPrincipal,
) -> ApiResponse[ToolJobResponse]:
    return success(await _service(session).get(int(job_id)))


@router.post(
    "/jobs/{job_id}/retry",
    response_model=ApiResponse[ToolJobResponse],
    dependencies=[Depends(require_permission("TOOL_MANAGE"))],
)
async def retry_job(
    job_id: str,
    session: DbSessionDep,
    _: AdminPrincipal,
) -> ApiResponse[ToolJobResponse]:
    return success(await _service(session).retry(int(job_id)))
