"""app.ops.jobs — HTTP endpoints.

Reads require ``OPS_JOB_VIEW``; ``retry`` and ``stop`` are high risk operations
and require ``OPS_JOB_MANAGE``. Each write validates that the current status
allows the action and is audited, so an impossible request fails with a business
rule error instead of silently mutating the row.

``/jobs/statistics`` is declared before ``/jobs/{job_id}`` so that FastAPI does
not match ``statistics`` as an identifier.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.jobs.schema import JobRunResponse, JobStatisticsResponse
from app.ops.jobs.service import JobMonitorService
from app.shared.authorization.dependencies import AdminPrincipal, require_permission
from app.shared.pagination.params import MAX_PAGE_SIZE, Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> JobMonitorService:
    return JobMonitorService(session)


@router.get(
    "/jobs",
    response_model=ApiResponse[Page[JobRunResponse]],
    dependencies=[Depends(require_permission("OPS_JOB_VIEW"))],
)
async def list_jobs(
    session: DbSessionDep,
    status: str | None = Query(default=None),
    definition_code: str | None = Query(default=None),
    start_at: datetime.datetime | None = Query(default=None),
    end_at: datetime.datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE),
) -> ApiResponse[Page[JobRunResponse]]:
    return success(
        await _service(session).list_jobs(
            status=status,
            definition_code=definition_code,
            start_at=start_at,
            end_at=end_at,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get(
    "/jobs/statistics",
    response_model=ApiResponse[JobStatisticsResponse],
    dependencies=[Depends(require_permission("OPS_JOB_VIEW"))],
)
async def get_job_statistics(
    session: DbSessionDep,
    days: int = Query(default=7, ge=1, le=366),
) -> ApiResponse[JobStatisticsResponse]:
    return success(await _service(session).statistics(days=days))


@router.get(
    "/jobs/{job_id}",
    response_model=ApiResponse[JobRunResponse],
    dependencies=[Depends(require_permission("OPS_JOB_VIEW"))],
)
async def get_job(job_id: str, session: DbSessionDep) -> ApiResponse[JobRunResponse]:
    return success(await _service(session).get_job(int(job_id)))


@router.post(
    "/jobs/{job_id}/retry",
    response_model=ApiResponse[JobRunResponse],
    dependencies=[Depends(require_permission("OPS_JOB_MANAGE"))],
)
async def retry_job(
    job_id: str, session: DbSessionDep, principal: AdminPrincipal
) -> ApiResponse[JobRunResponse]:
    return success(await _service(session).retry_job(principal, int(job_id)))


@router.post(
    "/jobs/{job_id}/stop",
    response_model=ApiResponse[JobRunResponse],
    dependencies=[Depends(require_permission("OPS_JOB_MANAGE"))],
)
async def stop_job(
    job_id: str, session: DbSessionDep, principal: AdminPrincipal
) -> ApiResponse[JobRunResponse]:
    return success(await _service(session).stop_job(principal, int(job_id)))
