"""app.admin.logs — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class ApplicationLogResponse(ApiModel):
    """One application log record (masked)."""

    id: StringId
    trace_id: str | None = None
    level: str
    logger_name: str | None = None
    message: str
    exception_type: str | None = None
    metadata: dict | None = None
    created_at: datetime.datetime


class LogsSummaryResponse(ApiModel):
    """Per-stream row counts."""

    audit: int = 0
    security: int = 0
    operation: int = 0
    access: int = 0
    application: int = 0


class LogExportTriggerResponse(ApiModel):
    """Confirmation that an export task was created for a log query."""

    task_id: StringId
    task_type: str
    status: str
