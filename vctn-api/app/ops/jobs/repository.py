"""app.ops.jobs — data access.

Reads and updates the existing ``sys_job`` table only; no table and no queue is
introduced here. Retrying reuses the enqueue mechanism already provided by
``app.system.jobs`` (resetting the row to ``PENDING`` so the existing worker
picks it up again), while the repository itself never commits — the service owns
the transaction.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.jobs.schema import CANCELLED, FAILED, SUCCESS
from app.system.jobs.model import SysJob


class JobMonitorRepository:
    """Data access for job monitoring."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        status: str | None,
        definition_code: str | None,
        start_at: datetime.datetime | None,
        end_at: datetime.datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[SysJob], int]:
        conditions: list[Any] = []
        if status:
            conditions.append(SysJob.status == status)
        if definition_code:
            conditions.append(SysJob.job_code == definition_code)
        if start_at is not None:
            conditions.append(SysJob.created_at >= start_at)
        if end_at is not None:
            conditions.append(SysJob.created_at <= end_at)
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

    async def get(self, job_id: int) -> SysJob | None:
        return await self._session.get(SysJob, job_id)

    async def count_by_status(self, *, start_at: datetime.datetime) -> dict[str, int]:
        rows = (
            await self._session.execute(
                select(SysJob.status, func.count(SysJob.id))
                .where(SysJob.created_at >= start_at)
                .group_by(SysJob.status)
            )
        ).all()
        return {str(status): int(count) for status, count in rows}

    async def duration_summary(
        self, *, start_at: datetime.datetime
    ) -> tuple[float | None, float | None]:
        """Average and maximum ``finished_at - started_at`` inside the window."""
        span = SysJob.finished_at - SysJob.started_at
        row = (
            await self._session.execute(
                select(func.avg(span), func.max(span)).where(
                    SysJob.created_at >= start_at,
                    SysJob.started_at.is_not(None),
                    SysJob.finished_at.is_not(None),
                )
            )
        ).first()
        if row is None:
            return None, None
        return _to_seconds(row[0]), _to_seconds(row[1])

    async def count_retry_exhausted(self, *, start_at: datetime.datetime) -> int:
        """Count runs that consumed their whole retry budget without success."""
        return int(
            (
                await self._session.execute(
                    select(func.count(SysJob.id)).where(
                        SysJob.created_at >= start_at,
                        SysJob.attempt_count >= SysJob.max_attempts,
                        SysJob.status != SUCCESS,
                    )
                )
            ).scalar_one()
        )

    async def count_consecutive_failures(self, *, start_at: datetime.datetime) -> int:
        """Count the newest runs that are ``FAILED`` before the first other one."""
        last_other = (
            select(func.max(SysJob.created_at))
            .where(SysJob.created_at >= start_at, SysJob.status != FAILED)
            .scalar_subquery()
        )
        return int(
            (
                await self._session.execute(
                    select(func.count(SysJob.id)).where(
                        SysJob.created_at >= start_at,
                        SysJob.status == FAILED,
                        SysJob.created_at >= func.coalesce(last_other, start_at),
                    )
                )
            ).scalar_one()
        )

    async def mark_retried(self, row: SysJob, *, at: datetime.datetime) -> None:
        """Account for one extra attempt of a re-queued run."""
        row.attempt_count = int(row.attempt_count or 0) + 1
        row.updated_at = at
        await self._session.flush()

    async def cancel(self, row: SysJob, *, at: datetime.datetime) -> None:
        """Mark a run as cancelled and finished at ``at``."""
        row.status = CANCELLED
        row.finished_at = at
        row.updated_at = at
        await self._session.flush()


def _to_seconds(value: Any) -> float | None:
    """Convert an ``interval`` aggregate into seconds."""
    if isinstance(value, datetime.timedelta):
        return value.total_seconds()
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None
