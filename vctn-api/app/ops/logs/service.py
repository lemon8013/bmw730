"""app.ops.logs — business logic.

The four existing log streams are projected onto one shape here, and the shape
is what decides what may leave the process:

* no request or response body is ever returned — only the columns the streams
  already store (path, message, event type, operation ...);
* every nested metadata payload passes through :func:`_sanitise`, which replaces
  any value whose key name matches a sensitive pattern, case-insensitively, by
  ``'***'``. Keys such as ``password``, ``access_token``, ``Authorization``,
  ``api_key``, ``mfa_secret`` or ``refreshToken`` therefore reach the UI redacted
  no matter how they were written.

Read only: nothing here mutates state, so no endpoint writes an audit record.
"""

from __future__ import annotations

import datetime
from collections.abc import Callable
from typing import Any, Final

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.audit.model import (
    SysAccessLog,
    SysApplicationLog,
    SysOperationLog,
    SysSecurityLog,
)
from app.core.exceptions import NotFoundError, ValidationError
from app.ops.logs.repository import OpsLogRepository
from app.ops.logs.schema import (
    ACCESS,
    APPLICATION,
    DEFAULT_LOG_TYPE,
    LOG_TYPES,
    OPERATION,
    SECURITY,
    LogContextItem,
    LogContextResponse,
    LogEntryResponse,
)
from app.shared.pagination.params import Page, PageParams

#: Key fragments that must never leave the process in clear text. A key matches
#: case-insensitively and as a substring, so ``password``, ``Password``,
#: ``old_password``, ``accessToken`` and ``X-Api-Key`` are all covered.
#:
#: Header style names are spelled with a hyphen (``X-Api-Key``), so the match
#: normalises separators before comparing: only listing ``api_key`` would let a
#: real ``X-Api-Key`` header through in clear text.
SENSITIVE_KEY_FRAGMENTS: Final[frozenset[str]] = frozenset(
    {
        "password",
        "passwd",
        "token",
        "authorization",
        "api_key",
        "apikey",
        "secret",
        "mfa",
        "credential",
        "private_key",
        "cookie",
        "session_id",
    }
)

_REDACTED: Final[str] = "***"

#: Dimensions that exist for some streams only; asking for one where the table
#: has no such column is rejected instead of silently returning everything.
_UNSUPPORTED_HOST_DIMENSION: Final[str] = (
    "the log streams record no host dimension; filter by ip, trace_id or service instead"
)


def _sanitise(payload: dict[str, Any] | None) -> dict[str, Any] | None:
    """Redact every value whose key name matches a sensitive pattern.

    The walk is recursive so that a secret nested inside an audit payload cannot
    slip through, and comparison is case-insensitive on the key name.
    """
    if payload is None:
        return None
    cleaned: dict[str, Any] = {}
    for key, value in payload.items():
        if _is_sensitive_key(key):
            cleaned[key] = _REDACTED
            continue
        cleaned[key] = _sanitise_value(value)
    return cleaned


def _sanitise_value(value: Any) -> Any:
    if isinstance(value, dict):
        return _sanitise(value)
    if isinstance(value, list):
        return [_sanitise_value(item) for item in value]
    return value


def _is_sensitive_key(key: Any) -> bool:
    # ``X-Api-Key`` and ``api_key`` must both match, so separators are folded
    # to underscores before the fragment is looked up.
    lowered = str(key).lower().replace("-", "_")
    return any(fragment in lowered for fragment in SENSITIVE_KEY_FRAGMENTS)


class OpsLogService:
    """Unified retrieval across the four existing log streams."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = OpsLogRepository(session)

    async def search(
        self,
        *,
        log_type: str = DEFAULT_LOG_TYPE,
        level: str | None = None,
        service: str | None = None,
        host: str | None = None,
        trace_id: str | None = None,
        request_id: str | None = None,
        keyword: str | None = None,
        ip: str | None = None,
        start_at: datetime.datetime | None = None,
        end_at: datetime.datetime | None = None,
        page: PageParams,
    ) -> Page[LogEntryResponse]:
        """Search one log stream, newest first."""
        resolved_type = self._resolve_log_type(log_type)
        self._reject_unsupported(
            resolved_type,
            level=level,
            service=service,
            request_id=request_id,
            ip=ip,
        )
        if host:
            raise ValidationError(_UNSUPPORTED_HOST_DIMENSION)
        if start_at is not None and end_at is not None and start_at > end_at:
            raise ValidationError("start_at must not be later than end_at")
        rows, total = await self._repository.search(
            resolved_type,
            start_at=start_at,
            end_at=end_at,
            level=level,
            service=service,
            trace_id=trace_id,
            request_id=request_id,
            keyword=keyword,
            ip=ip,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[_to_entry(resolved_type, row) for row in rows],
            total=total,
            params=page,
        )

    async def get(self, log_type: str, log_id: int) -> LogEntryResponse:
        """Return one record of the addressed stream."""
        resolved_type = self._resolve_log_type(log_type)
        row = await self._repository.get(resolved_type, log_id)
        if row is None:
            raise NotFoundError("log record not found")
        return _to_entry(resolved_type, row)

    async def context(self, trace_id: str, *, limit: int) -> LogContextResponse:
        """Return every record of one trace across the streams, oldest first."""
        if not trace_id:
            raise ValidationError("trace_id is required")
        rows = await self._repository.list_by_trace(trace_id, limit=limit)
        items = [
            _to_context_item(_to_entry(log_type, row)) for log_type, row in rows
        ]
        return LogContextResponse(trace_id=trace_id, total=len(items), items=items)

    @staticmethod
    def _resolve_log_type(log_type: str) -> str:
        resolved = (log_type or DEFAULT_LOG_TYPE).strip().upper()
        if resolved not in LOG_TYPES:
            raise ValidationError(f"log_type must be one of {list(LOG_TYPES)}")
        return resolved

    def _reject_unsupported(
        self,
        log_type: str,
        *,
        level: str | None,
        service: str | None,
        request_id: str | None,
        ip: str | None,
    ) -> None:
        """Refuse a filter the addressed stream simply cannot express."""
        for dimension, value in (
            ("level", level),
            ("service", service),
            ("request_id", request_id),
            ("ip", ip),
        ):
            if value and not self._repository.supports(log_type, dimension):
                raise ValidationError(
                    f"{log_type} logs cannot be filtered by {dimension}"
                )


def _to_entry(log_type: str, row: Any) -> LogEntryResponse:
    return _ENTRY_BUILDERS[log_type](row)


def _access_entry(row: SysAccessLog) -> LogEntryResponse:
    return LogEntryResponse(
        log_type=ACCESS,
        id=str(int(row.id)),
        trace_id=row.trace_id,
        request_id=row.request_id,
        created_at=row.created_at,
        summary=str(row.path),
        actor_user_id=str(int(row.user_id)) if row.user_id else None,
        ip=row.ip,
        user_agent=row.user_agent,
        method=str(row.method),
        path=str(row.path),
        status_code=row.status_code,
        duration_ms=row.duration_ms,
    )


def _application_entry(row: SysApplicationLog) -> LogEntryResponse:
    return LogEntryResponse(
        log_type=APPLICATION,
        id=str(int(row.id)),
        trace_id=row.trace_id,
        created_at=row.created_at,
        summary=str(row.message),
        level=str(row.level),
        logger_name=row.logger_name,
        exception_type=row.exception_type,
        metadata=_sanitise(row.metadata_payload),
    )


def _security_entry(row: SysSecurityLog) -> LogEntryResponse:
    return LogEntryResponse(
        log_type=SECURITY,
        id=str(int(row.id)),
        trace_id=row.trace_id,
        created_at=row.created_at,
        summary=str(row.event_type),
        result=str(row.result),
        actor_user_id=str(int(row.user_id)) if row.user_id else None,
        ip=row.ip,
        user_agent=row.user_agent,
        error_code=row.error_code,
        metadata=_sanitise(row.metadata_payload),
    )


def _operation_entry(row: SysOperationLog) -> LogEntryResponse:
    return LogEntryResponse(
        log_type=OPERATION,
        id=str(int(row.id)),
        trace_id=row.trace_id,
        request_id=row.request_id,
        created_at=row.created_at,
        summary=str(row.operation),
        result=str(row.result),
        actor_user_id=str(int(row.operator_id)) if row.operator_id else None,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        metadata=_sanitise(row.metadata_payload),
    )


_ENTRY_BUILDERS: Final[dict[str, Callable[[Any], LogEntryResponse]]] = {
    ACCESS: _access_entry,
    APPLICATION: _application_entry,
    SECURITY: _security_entry,
    OPERATION: _operation_entry,
}


def _to_context_item(entry: LogEntryResponse) -> LogContextItem:
    return LogContextItem(
        log_type=entry.log_type,
        id=entry.id,
        trace_id=entry.trace_id,
        request_id=entry.request_id,
        created_at=entry.created_at,
        summary=entry.summary,
        level=entry.level,
        result=entry.result,
        metadata=entry.metadata,
    )
