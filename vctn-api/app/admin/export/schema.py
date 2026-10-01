"""app.admin.export — request and response DTOs.

Every field mirrors a column of the frozen ``sys_export_job`` table. A field
that has no column (for example a synthetic "progress" percentage) is not
exposed: the export state machine is expressed entirely through ``status`` plus
the ``started_at`` / ``finished_at`` timestamps.
"""

from __future__ import annotations

import datetime
from typing import Any

from app.shared.response.dto import ApiModel, StringId


class ExportTaskResponse(ApiModel):
    """One export job record."""

    id: StringId
    export_type: str
    status: str
    file_id: StringId | None = None
    requested_by: StringId | None = None
    row_count: int | None = None
    error_message: str | None = None
    filter_json: dict[str, Any] | None = None
    created_at: datetime.datetime
    started_at: datetime.datetime | None = None
    finished_at: datetime.datetime | None = None


class CreateExportTaskRequest(ApiModel):
    """Create an export job."""

    export_type: str
    filter_json: dict[str, Any] | None = None
