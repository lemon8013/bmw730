"""app.tools.jobs — request and response DTOs.

Every BIGINT identifier is exposed as a string. The job payload is an opaque JSONB
value and is echoed back as-is.
"""

from __future__ import annotations

import datetime
from typing import Any

from app.shared.response.dto import ApiModel, StringId


class ToolJobResponse(ApiModel):
    """One asynchronous tool job."""

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
    last_error: str | None = None
    trace_id: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    payload: dict[str, Any] | None = None


class ToolJobEnqueueRequest(ApiModel):
    """Enqueue a new job."""

    job_code: str
    job_name: str
    job_type: str
    payload: dict[str, Any] = {}
    priority: int = 0
    max_attempts: int = 3


class ToolJobListResponse(ApiModel):
    """A page of tool jobs."""

    items: list[ToolJobResponse] = []
    total: int = 0
    page: int = 1
    page_size: int = 20
