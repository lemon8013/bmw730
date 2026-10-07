"""app.ops.jobs — business logic.

Reading job runs needs no transaction, but ``retry`` and ``stop`` are high risk
operations: they change scheduling state on behalf of an operator, so each one
validates that the current status allows the requested action, writes the ops
audit record and the operation log, and only then commits.

The service is intentionally thin about execution: it never runs a job itself.
A retry re-queues the existing row through the enqueue mechanism already
provided by ``app.system.jobs``, and a stop simply marks the run cancelled — no
new queue dependency is introduced.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, NotFoundError, ValidationError
from app.ops.audit.recorder import OpsAuditRecorder
from app.ops.jobs.repository import JobMonitorRepository
from app.ops.jobs.schema import (
    CANCELLED,
    FAILED,
    PENDING,
    RETRYABLE_STATUSES,
    RUNNING,
    STOPPABLE_STATUSES,
    SUCCESS,
    JobRunResponse,
    JobStatisticsResponse,
)
from app.shared.auth.context import Principal
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams
from app.system.jobs.model import SysJob
from app.system.jobs.repository import JobRepository

_MIN_STATISTICS_DAYS = 1


class JobMonitorService:
    """Monitoring and manual intervention on background job runs."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = JobMonitorRepository(session)
        self._settings = settings or get_settings()
        self._audit = OpsAuditRecorder(session, self._settings)
        # The existing enqueue mechanism: resetting a row to PENDING is what
        # makes its worker pick it up again.
        self._system_jobs = JobRepository(session)

    async def list_jobs(
        self,
        *,
        status: str | None = None,
        definition_code: str | None = None,
        start_at: datetime.datetime | None = None,
        end_at: datetime.datetime | None = None,
        page: PageParams,
    ) -> Page[JobRunResponse]:
        rows, total = await self._repository.list(
            status=status,
            definition_code=definition_code,
            start_at=start_at,
            end_at=end_at,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get_job(self, job_id: int) -> JobRunResponse:
        row = await self._repository.get(job_id)
        if row is None:
            raise NotFoundError("job not found")
        return self._to_response(row)

    async def statistics(self, *, days: int) -> JobStatisticsResponse:
        """Aggregate outcome, duration and failure streaks of recent runs."""
        if days < _MIN_STATISTICS_DAYS:
            raise ValidationError("days must be a positive number of days")
        window_end = datetime.datetime.now(datetime.UTC)
        window_start = window_end - datetime.timedelta(days=days)
        counts = await self._repository.count_by_status(start_at=window_start)
        avg_duration, max_duration = await self._repository.duration_summary(
            start_at=window_start
        )
        total = sum(counts.values())
        success_count = counts.get(SUCCESS, 0)
        failed_count = counts.get(FAILED, 0)
        return JobStatisticsResponse(
            days=days,
            window_start=window_start,
            window_end=window_end,
            total=total,
            status_counts=counts,
            success_count=success_count,
            failed_count=failed_count,
            cancelled_count=counts.get(CANCELLED, 0),
            running_count=counts.get(RUNNING, 0),
            pending_count=counts.get(PENDING, 0),
            success_rate=_rate(success_count, total),
            failure_rate=_rate(failed_count, total),
            avg_duration_seconds=avg_duration,
            max_duration_seconds=max_duration,
            timeout_count=await self._repository.count_retry_exhausted(
                start_at=window_start
            ),
            consecutive_failed_count=await self._repository.count_consecutive_failures(
                start_at=window_start
            ),
        )

    async def retry_job(self, actor: Principal, job_id: int) -> JobRunResponse:
        """Re-queue a failed or cancelled run so its worker picks it up again."""
        row = await self._repository.get(job_id)
        if row is None:
            raise NotFoundError("job not found")
        current_status = str(row.status)
        if current_status not in RETRYABLE_STATUSES:
            raise BusinessRuleError(f"a job in status {current_status} cannot be retried")
        attempt_count = int(row.attempt_count or 0)
        max_attempts = int(row.max_attempts or 0)
        if attempt_count >= max_attempts:
            raise BusinessRuleError("the job already exhausted its retry budget")
        now = datetime.datetime.now(datetime.UTC)
        await self._system_jobs.requeue(job_id, available_at=now)
        await self._repository.mark_retried(row, at=now)
        await self._audit.record(
            action="OPS_JOB_RETRY",
            actor=actor,
            resource_type="sys_job",
            resource_id=int(row.id),
            before_data={"status": current_status, "attempt_count": attempt_count},
            after_data={
                "status": PENDING,
                "attempt_count": attempt_count + 1,
                "available_at": now.isoformat(),
            },
        )
        await write_operation_log(
            self._session,
            operation="OPS_JOB_RETRY",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="sys_job",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    async def stop_job(self, actor: Principal, job_id: int) -> JobRunResponse:
        """Cancel a run that has not finished yet."""
        row = await self._repository.get(job_id)
        if row is None:
            raise NotFoundError("job not found")
        current_status = str(row.status)
        if current_status not in STOPPABLE_STATUSES:
            raise BusinessRuleError(f"a job in status {current_status} cannot be stopped")
        now = datetime.datetime.now(datetime.UTC)
        await self._repository.cancel(row, at=now)
        await self._audit.record(
            action="OPS_JOB_STOP",
            actor=actor,
            resource_type="sys_job",
            resource_id=int(row.id),
            before_data={"status": current_status},
            after_data={"status": CANCELLED, "finished_at": now.isoformat()},
        )
        await write_operation_log(
            self._session,
            operation="OPS_JOB_STOP",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="sys_job",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    def _to_response(self, row: SysJob) -> JobRunResponse:
        return JobRunResponse(
            id=str(int(row.id)),
            job_code=str(row.job_code),
            job_name=str(row.job_name),
            job_type=str(row.job_type),
            status=str(row.status),
            priority=int(row.priority or 0),
            attempt_count=int(row.attempt_count or 0),
            max_attempts=int(row.max_attempts or 0),
            available_at=row.available_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            duration_seconds=_duration_seconds(row.started_at, row.finished_at),
            last_error=row.last_error,
            trace_id=row.trace_id,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )


def _duration_seconds(
    started_at: datetime.datetime | None, finished_at: datetime.datetime | None
) -> float | None:
    if started_at is None or finished_at is None:
        return None
    return (finished_at - started_at).total_seconds()


def _rate(count: int, total: int) -> float:
    if not total:
        return 0.0
    return count / total
