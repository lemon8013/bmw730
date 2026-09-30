"""app.admin.logs — business logic.

Inspection entry point for the five separated log streams. The repository reads
the existing log tables directly; this service turns rows into DTOs and, crucially,
strips every sensitive value before it can leave the process:

* ``password`` / ``mfa_secret`` / ``secret`` / ``api_key`` / ``client_secret``
  are redacted entirely;
* tokens, JWTs and authorization headers are truncated;
* ``phone`` / ``email`` are masked;
* the masking is recursive, so values nested inside audit ``before_data`` /
  ``after_data`` or any stream's ``metadata`` payload are also cleaned.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.audit.schema import (
    AccessLogResponse,
    AuditLogResponse,
    OperationLogResponse,
    SecurityLogResponse,
    TraceResponse,
)
from app.admin.audit.service import AuditQueryService
from app.admin.export.schema import CreateExportTaskRequest
from app.admin.export.service import ExportTaskService
from app.admin.logs.repository import LOG_TYPES, LogsQueryRepository
from app.admin.logs.schema import (
    ApplicationLogResponse,
    LogsSummaryResponse,
)
from app.core.config import Settings, get_settings
from app.shared.pagination.params import Page, PageParams
from app.shared.response.dto import ApiModel
from app.shared.security.masking import mask_email, mask_phone, mask_token

_RESPONSE_FOR: dict[str, type[ApiModel]] = {
    "audit": AuditLogResponse,
    "security": SecurityLogResponse,
    "operation": OperationLogResponse,
    "access": AccessLogResponse,
    "application": ApplicationLogResponse,
}

_EXACT_SECRET = {
    "password",
    "new_password",
    "old_password",
    "confirm_password",
    "mfa_secret",
    "secret",
    "api_key",
    "apikey",
    "client_secret",
}


def _recursive_mask(value: Any) -> Any:
    """Redact sensitive keys wherever they appear in a (possibly nested) value."""
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in _EXACT_SECRET:
                cleaned[key] = "***"
            elif "token" in lowered or lowered == "authorization":
                cleaned[key] = mask_token(str(item)) if item is not None else None
            elif lowered in {"phone", "mobile", "telephone"}:
                cleaned[key] = mask_phone(str(item)) if item is not None else None
            elif lowered in {"email", "mail"}:
                cleaned[key] = mask_email(str(item)) if item is not None else None
            else:
                cleaned[key] = _recursive_mask(item)
        return cleaned
    if isinstance(value, list):
        return [_recursive_mask(item) for item in value]
    return value


def _sanitize(item: ApiModel) -> ApiModel:
    """Return a copy of ``item`` with every sensitive value redacted."""
    return item.__class__(**_recursive_mask(item.model_dump()))


class LogsQueryService:
    """Administrative inspection of the five log streams."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = LogsQueryRepository(session)
        self._audit_service = AuditQueryService(session)
        self._settings = settings or get_settings()

    async def summary(self) -> LogsSummaryResponse:
        counts = await self._repository.summary()
        return LogsSummaryResponse(
            audit=counts.get("audit", 0),
            security=counts.get("security", 0),
            operation=counts.get("operation", 0),
            access=counts.get("access", 0),
            application=counts.get("application", 0),
        )

    async def query(
        self,
        log_type: str,
        *,
        start: Any | None,
        end: Any | None,
        level: str | None,
        result: str | None,
        keyword: str | None,
        user_id: int | None,
        page: PageParams,
    ) -> Page[Any]:
        if log_type not in LOG_TYPES:
            from app.core.exceptions import ValidationError

            raise ValidationError(f"unknown log type: {log_type}")
        rows, total = await self._repository.search(
            log_type,
            start=start,
            end=end,
            level=level,
            result=result,
            keyword=keyword,
            user_id=user_id,
            limit=page.limit,
            offset=page.offset,
        )
        response_type = _RESPONSE_FOR[log_type]
        items = [self._to_masked(response_type, row) for row in rows]
        return Page.build(items=items, total=total, params=page)

    def _to_masked(self, response_type: type[ApiModel], row: Any) -> ApiModel:
        return _sanitize(response_type.model_validate(row))

    async def trace(self, trace_id: str) -> TraceResponse:
        """Return every stream's rows for one trace id, redacted."""
        raw = await self._audit_service.trace(trace_id)
        return TraceResponse(
            trace_id=raw.trace_id,
            audit_logs=[_sanitize(item) for item in raw.audit_logs],
            security_logs=[_sanitize(item) for item in raw.security_logs],
            operation_logs=[_sanitize(item) for item in raw.operation_logs],
            access_logs=[_sanitize(item) for item in raw.access_logs],
        )

    async def trigger_export(
        self, *, log_type: str, actor_id: int, actor_username: str, params: dict[str, Any]
    ) -> Any:
        """Create a real export task that captures this log query."""
        if log_type not in LOG_TYPES:
            from app.core.exceptions import ValidationError

            raise ValidationError(f"unknown log type: {log_type}")
        return await ExportTaskService(self._session).create(
            actor_id=actor_id,
            actor_username=actor_username,
            payload=CreateExportTaskRequest(task_type=f"LOG_{log_type.upper()}", params=params),
        )
