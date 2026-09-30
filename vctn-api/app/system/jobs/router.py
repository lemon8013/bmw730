"""app.system.jobs — HTTP endpoints.

Mounted by the application at the ``/system/jobs`` prefix. Job management endpoints
require the ``SYSTEM_JOB_MANAGE`` admin permission.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.logging.writers import write_operation_log
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse
from app.system.jobs.schema import JobCreateRequest, JobResponse
from app.system.jobs.service import JobService

router = APIRouter(tags=["system:jobs"])


@router.get(
    "",
    response_model=ApiResponse[Page[JobResponse]],
    summary="List system jobs",
    dependencies=[Depends(require_permission("SYSTEM_JOB_MANAGE"))],
)
async def list_jobs(
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    status: str | None = Query(default=None),
    job_type: str | None = Query(default=None),
) -> ApiResponse[Page[JobResponse]]:
    return success(
        await JobService(session).list_jobs(
            page=PageParams(page=page, page_size=page_size),
            status=status,
            job_type=job_type,
        )
    )


@router.get(
    "/{job_id}",
    response_model=ApiResponse[JobResponse],
    summary="Get a system job",
    dependencies=[Depends(require_permission("SYSTEM_JOB_MANAGE"))],
)
async def get_job(
    job_id: int,
    session: DbSessionDep,
) -> ApiResponse[JobResponse]:
    return success(await JobService(session).get_job(job_id))


@router.post(
    "",
    response_model=ApiResponse[JobResponse],
    summary="Create a system job record",
)
async def create_job(
    payload: JobCreateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("SYSTEM_JOB_MANAGE")),
) -> ApiResponse[JobResponse]:
    result = await JobService(session).create_job(payload)
    await write_operation_log(
        session,
        operation="JOB_CREATE",
        result="SUCCESS",
        operator_id=principal.subject_id,
        resource_type="sys_job",
        resource_id=result.id,
        metadata={"job_type": payload.job_type, "job_code": payload.job_code},
    )
    await session.commit()
    return success(result)


@router.post(
    "/{job_id}/retry",
    response_model=ApiResponse[JobResponse],
    summary="Re-queue a system job",
)
async def retry_job(
    job_id: int,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("SYSTEM_JOB_MANAGE")),
) -> ApiResponse[JobResponse]:
    result = await JobService(session).retry_job(job_id)
    await write_operation_log(
        session,
        operation="JOB_RETRY",
        result="SUCCESS",
        operator_id=principal.subject_id,
        resource_type="sys_job",
        resource_id=str(job_id),
    )
    await session.commit()
    return success(result)
