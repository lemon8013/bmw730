"""app.tools.jobs — business logic.

The service is the transaction boundary: every mutating method commits. The
state machine mirrors the ``sys_job`` lifecycle — ``PENDING -> RUNNING ->
SUCCESS/FAILED`` — and ``fail`` keeps the job ``PENDING`` for another attempt
while attempts remain. ``enqueue`` / ``claim_next`` are the hooks the runtime's
ASYNC mode (or any worker) uses to push and pull work; they are real, not stubs.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.shared.tracing.context import get_trace_id
from app.system.jobs.model import SysJob
from app.tools.jobs.repository import (
    JOB_STATUS_PENDING,
    JOB_STATUS_RUNNING,
    JOB_STATUS_SUCCESS,
    ToolJobRepository,
)
from app.tools.jobs.schema import ToolJobEnqueueRequest, ToolJobListResponse, ToolJobResponse

JOB_TYPE_TOOL_EXECUTE: str = "TOOL_EXECUTE"


class ToolJobService:
    """Asynchronous tool job management."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = ToolJobRepository(session)
        self._settings = settings or get_settings()

    async def enqueue(
        self,
        *,
        job_code: str,
        job_name: str,
        job_type: str,
        payload: dict,
        priority: int = 0,
        max_attempts: int | None = None,
    ) -> int:
        """Create a PENDING job and commit it."""
        now = datetime.datetime.now(datetime.UTC)
        job = await self._repository.create(
            job_code=job_code,
            job_name=job_name,
            job_type=job_type,
            payload=payload,
            status=JOB_STATUS_PENDING,
            priority=priority,
            attempt_count=0,
            max_attempts=max_attempts or self._settings.OUTBOX_MAX_ATTEMPTS,
            available_at=now,
            trace_id=get_trace_id(),
        )
        await self._session.commit()
        return int(job.id)

    async def enqueue_from_request(self, request: ToolJobEnqueueRequest) -> int:
        """Convenience wrapper around :meth:`enqueue` taking a DTO."""
        return await self.enqueue(
            job_code=request.job_code,
            job_name=request.job_name,
            job_type=request.job_type,
            payload=request.payload,
            priority=request.priority,
            max_attempts=request.max_attempts,
        )

    async def get(self, job_id: int) -> ToolJobResponse:
        job = await self._repository.get(job_id)
        if job is None:
            raise NotFoundError("job not found")
        return self._to_response(job)

    async def list_jobs(
        self, *, status: str | None, job_type: str | None, page: int, page_size: int
    ) -> ToolJobListResponse:
        rows, total = await self._repository.list_by(
            status=status,
            job_type=job_type,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return ToolJobListResponse(
            items=[self._to_response(row) for row in rows],
            total=total,
            page=page,
            page_size=page_size,
        )

    async def claim_next(
        self, *, job_types: list[str] | None = None
    ) -> ToolJobResponse | None:
        """Take one runnable job. Returns ``None`` when the queue is empty."""
        now = datetime.datetime.now(datetime.UTC)
        job = await self._repository.claim_next(now=now, job_types=job_types)
        if job is None:
            return None
        await self._session.commit()
        return self._to_response(job)

    async def complete(self, job_id: int) -> ToolJobResponse:
        """Mark a RUNNING job SUCCESS."""
        job = await self._require(job_id, expected={JOB_STATUS_RUNNING})
        now = datetime.datetime.now(datetime.UTC)
        await self._repository.mark_success(job, now=now)
        await self._session.commit()
        return self._to_response(job)

    async def fail(self, job_id: int, *, error: str) -> ToolJobResponse:
        """Record a failure and either requeue or fail the job."""
        job = await self._require(job_id, expected={JOB_STATUS_RUNNING, JOB_STATUS_PENDING})
        now = datetime.datetime.now(datetime.UTC)
        max_attempts = int(job.max_attempts or 0)
        attempts_after = int(job.attempt_count or 0) + 1
        requeue = attempts_after < max_attempts
        await self._repository.mark_failure(job, error=error, now=now, requeue=requeue)
        await self._session.commit()
        return self._to_response(job)

    async def retry(self, job_id: int) -> ToolJobResponse:
        """Reset a FAILED (or any) job back to PENDING for another attempt."""
        job = await self._require(job_id, expected=None)
        if str(job.status) == JOB_STATUS_SUCCESS:
            raise BusinessRuleError("a succeeded job cannot be retried")
        now = datetime.datetime.now(datetime.UTC)
        await self._repository.mark_pending(job, now=now)
        await self._session.commit()
        return self._to_response(job)

    async def _require(self, job_id: int, *, expected: set[str] | None) -> SysJob:
        job = await self._repository.get(job_id)
        if job is None:
            raise NotFoundError("job not found")
        if expected is not None and str(job.status) not in expected:
            raise BusinessRuleError(
                f"job is in state '{job.status}'; expected one of {sorted(expected)}"
            )
        return job

    def _to_response(self, job: SysJob) -> ToolJobResponse:
        return ToolJobResponse(
            id=str(int(job.id)),
            job_code=str(job.job_code),
            job_name=str(job.job_name),
            job_type=str(job.job_type),
            status=str(job.status),
            priority=int(job.priority or 0),
            attempt_count=int(job.attempt_count or 0),
            max_attempts=int(job.max_attempts or 0),
            available_at=job.available_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            last_error=job.last_error,
            trace_id=job.trace_id,
            created_at=job.created_at,
            updated_at=job.updated_at,
            payload=job.payload,
        )
