"""app.system.jobs — request and response DTOs.

System job management focuses on status records and queries for background jobs
(data aggregation, export, cleanup ...). The module records state only; actual
execution is performed elsewhere.
"""

from __future__ import annotations

import datetime
from typing import Any

from app.shared.response.dto import ApiModel, StringId


class JobCreateRequest(ApiModel):
    """Manually create a system job record."""

    job_code: str
    job_name: str
    job_type: str
    payload: dict[str, Any] | None = None
    priority: int = 0
    max_attempts: int = 3


class JobResponse(ApiModel):
    """A system job record."""

    id: StringId
    job_code: str
    job_name: str
    job_type: str
    payload: dict[str, Any] | None = None
    status: str
    priority: int
    attempt_count: int
    max_attempts: int
    available_at: datetime.datetime
    started_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None
    last_error: str | None = None
    trace_id: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
