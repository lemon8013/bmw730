"""app.tools.jobs — data access.

The canonical ``sys_job`` model lives in :mod:`app.system.jobs.model`; this
repository operates on it directly so there is a single table mapping. The job
state machine (PENDING -> RUNNING -> SUCCESS/FAILED) is enforced in the service;
here we only read and mutate rows, locking the claimed row with
``FOR UPDATE SKIP LOCKED`` so several workers never take the same job.
"""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.ids import new_id
from app.system.jobs.model import SysJob

JOB_STATUS_PENDING: str = "PENDING"
JOB_STATUS_RUNNING: str = "RUNNING"
JOB_STATUS_SUCCESS: str = "SUCCESS"
JOB_STATUS_FAILED: str = "FAILED"


class ToolJobRepository:
    """Data access for asynchronous tool jobs (``sys_job``)."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **fields: object) -> SysJob:
        job = SysJob(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(job)
        await self._session.flush()
        return job

    async def get(self, job_id: int) -> SysJob | None:
        return await self._session.get(SysJob, job_id)

    async def list_by(
        self, *, status: str | None, job_type: str | None, limit: int, offset: int
    ) -> tuple[list[SysJob], int]:
        conditions = []
        if status is not None:
            conditions.append(SysJob.status == status)
        if job_type is not None:
            conditions.append(SysJob.job_type == job_type)

        count_stmt = select(func.count(SysJob.id)).where(*conditions)
        total = int((await self._session.execute(count_stmt)).scalar_one())
        rows = (
            (
                await self._session.execute(
                    select(SysJob)
                    .where(*conditions)
                    .order_by(SysJob.priority.desc(), SysJob.available_at, SysJob.id)
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def claim_next(
        self, *, now: datetime.datetime, job_types: list[str] | None = None
    ) -> SysJob | None:
        """Atomically take one runnable job and mark it RUNNING."""
        conditions = [
            SysJob.status == JOB_STATUS_PENDING,
            SysJob.available_at <= now,
        ]
        if job_types:
            conditions.append(SysJob.job_type.in_(job_types))

        candidate = (
            await self._session.execute(
                select(SysJob)
                .where(*conditions)
                .order_by(SysJob.priority.desc(), SysJob.available_at, SysJob.id)
                .limit(1)
                .with_for_update(skip_locked=True)
            )
        ).scalar_one_or_none()
        if candidate is None:
            return None
        candidate.status = JOB_STATUS_RUNNING
        candidate.started_at = now
        await self._session.flush()
        return candidate

    async def mark_success(self, job: SysJob, *, now: datetime.datetime) -> None:
        job.status = JOB_STATUS_SUCCESS
        job.finished_at = now
        await self._session.flush()

    async def mark_failure(
        self, job: SysJob, *, error: str, now: datetime.datetime, requeue: bool
    ) -> None:
        job.attempt_count = int(job.attempt_count or 0) + 1
        job.last_error = error[:4000] if error else None
        if requeue:
            job.status = JOB_STATUS_PENDING
            job.available_at = now
        else:
            job.status = JOB_STATUS_FAILED
        await self._session.flush()

    async def mark_pending(self, job: SysJob, *, now: datetime.datetime) -> None:
        job.status = JOB_STATUS_PENDING
        job.attempt_count = 0
        job.last_error = None
        job.started_at = None
        job.finished_at = None
        job.available_at = now
        await self._session.flush()
