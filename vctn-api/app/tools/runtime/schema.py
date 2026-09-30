"""app.tools.runtime — request and response DTOs."""

from __future__ import annotations

from typing import Any

from pydantic import Field

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class ToolExecuteRequest(ApiModel):
    """Execute one tool.

    ``inputs`` is the tool payload. Raw tool input is never written to a log, an
    audit record or a behaviour event: only the fact that an execution happened
    is recorded.
    """

    inputs: dict[str, Any] = Field(default_factory=dict)
    anonymous_id: str | None = Field(default=None, max_length=128)
    idempotency_key: str | None = Field(default=None, max_length=255)


class ToolExecuteResponse(ApiModel):
    """Result of one execution."""

    tool_id: StringId
    usage_event_id: OptionalStringId = None
    job_id: OptionalStringId = None
    success: bool
    output: Any = None
    duration_ms: int
    error_code: str | None = None
    error_message: str | None = None
    execution_mode: str
