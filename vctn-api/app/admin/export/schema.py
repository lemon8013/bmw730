"""app.admin.export — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class ExportTaskResponse(ApiModel):
    """One export task record."""

    id: StringId
    task_type: str
    status: str
    file_id: str | None = None
    requested_by: StringId
    progress: int
    error_message: str | None = None
    params: dict | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
    finished_at: datetime.datetime | None = None


class CreateExportTaskRequest(ApiModel):
    """Create an export task."""

    task_type: str
    params: dict | None = None
