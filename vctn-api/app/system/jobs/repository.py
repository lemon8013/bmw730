"""app.system.jobs — data access.

Repositories never commit; the service layer owns the transaction boundary.
"""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.system.jobs.model import SysJob

JOB_STATUS_PENDING = "PENDING"


class JobRepository:
    """Data access for system job records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **fields: object) -> SysJob:
        row = SysJob(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, job_id: int) -> SysJob | None:
        return await self._session.get(SysJob, job_id)

    async def list_jobs(
        self, *, status: str | None, job_type: str | None, limit: int, offset: int
    ) -> tuple[list[SysJob], int]:
        conditions = []
        if status is not None:
            conditions.append(SysJob.status == status)
        if job_type is not None:
            conditions.append(SysJob.job_type == job_type)
        total = int(
            (
                await self._session.execute(
                    select(func.count(SysJob.id)).where(*conditions)
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(SysJob)
                    .where(*conditions)
                    .order_by(SysJob.created_at.desc(), SysJob.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def requeue(self, job_id: int, *, available_at: datetime.datetime) -> None:
        """Re-queue a job: reset it to PENDING so a worker picks it up again."""
        row = await self._session.get(SysJob, job_id)
        if row is None:
            return
        row.status = JOB_STATUS_PENDING
        row.available_at = available_at
        row.started_at = None
        row.finished_at = None
        row.last_error = None
        await self._session.flush()
