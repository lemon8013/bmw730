"""app.system.jobs — business logic.

The service records and mutates system job state. Mutations commit at the end of
the method (transaction boundary).
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.shared.ids import new_id
from app.shared.pagination.params import Page, PageParams
from app.system.jobs.model import SysJob
from app.system.jobs.repository import JobRepository
from app.system.jobs.schema import JobCreateRequest, JobResponse


class JobService:
    """System job management."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = JobRepository(session)

    async def create_job(self, request: JobCreateRequest) -> JobResponse:
        """Manually create a job record in PENDING state."""
        now = datetime.datetime.now(datetime.UTC)
        row = await self._repository.create(
            id=new_id(),
            job_code=request.job_code,
            job_name=request.job_name,
            job_type=request.job_type,
            payload=request.payload,
            status="PENDING",
            priority=request.priority,
            attempt_count=0,
            max_attempts=request.max_attempts,
            available_at=now,
            created_at=now,
            updated_at=now,
        )
        await self._session.commit()
        return self._to_response(row)

    async def list_jobs(
        self, *, page: PageParams, status: str | None = None, job_type: str | None = None
    ) -> Page[JobResponse]:
        rows, total = await self._repository.list_jobs(
            status=status, job_type=job_type, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get_job(self, job_id: int) -> JobResponse:
        row = await self._repository.get(job_id)
        if row is None:
            raise NotFoundError("job not found")
        return self._to_response(row)

    async def retry_job(self, job_id: int) -> JobResponse:
        """Re-queue a job by setting its status back to PENDING."""
        row = await self._repository.get(job_id)
        if row is None:
            raise NotFoundError("job not found")
        await self._repository.requeue(job_id, available_at=datetime.datetime.now(datetime.UTC))
        await self._session.commit()
        refreshed = await self._repository.get(job_id)
        assert refreshed is not None
        return self._to_response(refreshed)

    def _to_response(self, row: SysJob) -> JobResponse:
        return JobResponse(
            id=str(int(row.id)),
            job_code=row.job_code,
            job_name=row.job_name,
            job_type=row.job_type,
            payload=row.payload,
            status=row.status,
            priority=int(row.priority),
            attempt_count=int(row.attempt_count),
            max_attempts=int(row.max_attempts),
            available_at=row.available_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            last_error=row.last_error,
            trace_id=row.trace_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
