"""app.ops.logs — request and response DTOs.

The four streams stay separate tables (``sys_access_log``,
``sys_application_log``, ``sys_security_log``, ``sys_operation_log``); this
module adds no table of its own and instead projects every stream onto one
shape so a single screen can search, open and reconstruct a trace.

Nothing here carries a raw request or response body, and every nested metadata
payload has already passed through :func:`app.ops.logs.service._sanitise`.
"""

from __future__ import annotations

import datetime
from typing import Final

from pydantic import Field

from app.shared.response.dto import (
    METADATA_COLUMN_ALIAS,
    ApiModel,
    OptionalIpAddress,
    OptionalStringId,
    StringId,
)

ACCESS: Final[str] = "ACCESS"
APPLICATION: Final[str] = "APPLICATION"
SECURITY: Final[str] = "SECURITY"
OPERATION: Final[str] = "OPERATION"

LOG_TYPES: Final[tuple[str, ...]] = (ACCESS, APPLICATION, SECURITY, OPERATION)
DEFAULT_LOG_TYPE: Final[str] = ACCESS


class LogEntryResponse(ApiModel):
    """One log record projected onto the unified ops shape.

    Fields the addressed stream does not own stay ``None``: only
    application records carry a level, only security and operation records
    carry a result, and only access records carry an HTTP outcome.
    """

    log_type: str
    id: StringId
    trace_id: str | None = None
    request_id: str | None = None
    created_at: datetime.datetime
    summary: str
    level: str | None = None
    result: str | None = None
    actor_user_id: OptionalStringId = None
    ip: OptionalIpAddress = None
    user_agent: str | None = None
    method: str | None = None
    path: str | None = None
    status_code: int | None = None
    duration_ms: int | None = None
    logger_name: str | None = None
    exception_type: str | None = None
    error_code: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    metadata: dict | None = Field(default=None, validation_alias=METADATA_COLUMN_ALIAS)


class LogContextItem(ApiModel):
    """One record of a trace, whatever stream it belongs to."""

    log_type: str
    id: StringId
    trace_id: str | None = None
    request_id: str | None = None
    created_at: datetime.datetime
    summary: str
    level: str | None = None
    result: str | None = None
    metadata: dict | None = None


class LogContextResponse(ApiModel):
    """Every record of one trace across the four streams, oldest first."""

    trace_id: str
    total: int = 0
    items: list[LogContextItem] = Field(default_factory=list)
