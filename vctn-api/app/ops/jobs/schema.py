"""app.ops.jobs — request and response DTOs.

Existing job tables (``sys_job`` / ``sys_job_definition``) are reused as they
are; this module adds no table. It also never carries ``sys_job.payload``: that
column holds business data an operator does not need to monitor a run, and it is
exactly the kind of value that must not be exposed to a monitoring screen.
"""

from __future__ import annotations

import datetime
from typing import Final

from pydantic import Field

from app.shared.response.dto import ApiModel, StringId

PENDING: Final[str] = "PENDING"
RUNNING: Final[str] = "RUNNING"
SUCCESS: Final[str] = "SUCCESS"
FAILED: Final[str] = "FAILED"
CANCELLED: Final[str] = "CANCELLED"

JOB_STATUSES: Final[tuple[str, ...]] = (PENDING, RUNNING, SUCCESS, FAILED, CANCELLED)

#: Statuses a manual retry is meaningful for.
RETRYABLE_STATUSES: Final[tuple[str, ...]] = (FAILED, CANCELLED)

#: Statuses a manual stop is meaningful for.
STOPPABLE_STATUSES: Final[tuple[str, ...]] = (PENDING, RUNNING)


class JobRunResponse(ApiModel):
    """One ``sys_job`` run."""

    id: StringId
    job_code: str
    job_name: str
    job_type: str
    status: str
    priority: int
    attempt_count: int
    max_attempts: int
    available_at: datetime.datetime
    started_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None
    duration_seconds: float | None = None
    last_error: str | None = None
    trace_id: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class JobStatisticsResponse(ApiModel):
    """Aggregated outcome of the job runs created inside one UTC window.

    ``timeout_count`` counts the runs that exhausted their retry budget without
    ever succeeding (``attempt_count >= max_attempts``), which is how the frozen
    ``sys_job`` columns express a run that never completed in time.
    ``consecutive_failed_count`` counts how many of the newest runs are
    ``FAILED`` before the first run that is not.
    """

    days: int
    window_start: datetime.datetime
    window_end: datetime.datetime
    total: int = 0
    status_counts: dict[str, int] = Field(default_factory=dict)
    success_count: int = 0
    failed_count: int = 0
    cancelled_count: int = 0
    running_count: int = 0
    pending_count: int = 0
    success_rate: float = 0.0
    failure_rate: float = 0.0
    avg_duration_seconds: float | None = None
    max_duration_seconds: float | None = None
    timeout_count: int = 0
    consecutive_failed_count: int = 0
