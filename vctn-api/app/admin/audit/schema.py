"""app.admin.audit — request and response DTOs."""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import (
    METADATA_COLUMN_ALIAS,
    ApiModel,
    OptionalIpAddress,
    OptionalStringId,
    StringId,
)


class AuditLogResponse(ApiModel):
    """One audit record."""

    id: StringId
    trace_id: str | None = None
    request_id: str | None = None
    operator_id: OptionalStringId = None
    operator_username: str | None = None
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    before_data: dict | None = None
    after_data: dict | None = None
    result: str
    error_code: str | None = None
    ip: OptionalIpAddress = None
    user_agent: str | None = None
    created_at: datetime.datetime


class SecurityLogResponse(ApiModel):
    """One security log record."""

    id: StringId
    trace_id: str | None = None
    user_id: OptionalStringId = None
    event_type: str
    result: str
    error_code: str | None = None
    ip: OptionalIpAddress = None
    user_agent: str | None = None
    metadata: dict | None = Field(default=None, validation_alias=METADATA_COLUMN_ALIAS)
    created_at: datetime.datetime


class OperationLogResponse(ApiModel):
    """One operation log record."""

    id: StringId
    trace_id: str | None = None
    request_id: str | None = None
    operator_id: OptionalStringId = None
    operation: str
    resource_type: str | None = None
    resource_id: str | None = None
    result: str
    metadata: dict | None = Field(default=None, validation_alias=METADATA_COLUMN_ALIAS)
    created_at: datetime.datetime


class AccessLogResponse(ApiModel):
    """One access log record."""

    id: StringId
    trace_id: str | None = None
    request_id: str | None = None
    user_id: OptionalStringId = None
    method: str
    path: str
    status_code: int | None = None
    ip: OptionalIpAddress = None
    user_agent: str | None = None
    duration_ms: int | None = None
    created_at: datetime.datetime


class TraceResponse(ApiModel):
    """Everything recorded for one trace id."""

    trace_id: str
    audit_logs: list[AuditLogResponse] = []
    security_logs: list[SecurityLogResponse] = []
    operation_logs: list[OperationLogResponse] = []
    access_logs: list[AccessLogResponse] = []
