"""Log writers for the five separated log streams.

The Spec forbids merging the streams into one business log table, so each
stream has its own writer:

* ``sys_access_log``     - one row per HTTP request
* ``sys_security_log``   - authentication / authorization / abuse events
* ``sys_operation_log``  - business operations performed by an operator
* ``sys_audit_log``      - see :mod:`app.shared.audit.service`
* ``sys_application_log``- application log records

Writers that take a ``session`` only flush: they join the transaction owned by
the service layer and must never commit. :func:`write_access_log` runs after the
response, when the request transaction is already finished, so it owns a short
transaction of its own.

Retention periods are frozen by the Spec and are read from configuration.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Final

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.admin.audit.model import (
    SysAccessLog,
    SysApplicationLog,
    SysOperationLog,
    SysSecurityLog,
)
from app.core.config import Settings, get_settings
from app.shared.ids import new_id
from app.shared.security.masking import mask_mapping
from app.shared.tracing.context import get_request_id, get_trace_id

if TYPE_CHECKING:  # pragma: no cover - typing only, avoids an import cycle
    from app.shared.auth.context import Principal

_LOGGER: Final = logging.getLogger("vctn.logging")

RESULT_SUCCESS: Final[str] = "SUCCESS"
RESULT_FAILURE: Final[str] = "FAILURE"


def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any] | None:
    """Mask sensitive values before they can reach a log table."""
    if metadata is None:
        return None
    return mask_mapping(metadata)


async def write_security_log(
    session: AsyncSession,
    *,
    event_type: str,
    result: str,
    user_id: int | None = None,
    error_code: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append a security event to the current transaction."""
    session.add(
        SysSecurityLog(
            id=new_id(),
            trace_id=get_trace_id(),
            user_id=user_id,
            event_type=event_type,
            result=result,
            error_code=error_code,
            ip=ip,
            user_agent=user_agent,
            metadata_payload=_safe_metadata(metadata),
        )
    )
    await session.flush()


async def write_operation_log(
    session: AsyncSession,
    *,
    operation: str,
    result: str,
    operator_id: int | None = None,
    actor: Principal | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append an operation record to the current transaction.

    ``sys_operation_log.operator_id`` is a foreign key to ``sys_user(id)``, so
    only an operator may be stored in the column. Pass ``actor`` whenever the
    caller can be either an operator or a platform business user: the actor id
    is written for operators and, for platform users, is recorded in
    ``metadata`` instead of the restricted column.
    """
    resolved_operator_id = operator_id
    payload = dict(metadata) if metadata else {}
    if actor is not None:
        if actor.is_admin:
            resolved_operator_id = actor.subject_id
        else:
            resolved_operator_id = None
            payload["subject_id"] = str(actor.subject_id)
            payload["subject_type"] = actor.subject_type
    session.add(
        SysOperationLog(
            id=new_id(),
            trace_id=get_trace_id(),
            request_id=get_request_id(),
            operator_id=resolved_operator_id,
            operation=operation,
            resource_type=resource_type,
            resource_id=None if resource_id is None else str(resource_id),
            result=result,
            metadata_payload=_safe_metadata(payload),
        )
    )
    await session.flush()


async def write_application_log(
    session: AsyncSession,
    *,
    level: str,
    message: str,
    logger_name: str | None = None,
    exception_type: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append an application log record to the current transaction."""
    session.add(
        SysApplicationLog(
            id=new_id(),
            trace_id=get_trace_id(),
            level=level,
            logger_name=logger_name,
            message=message,
            exception_type=exception_type,
            metadata_payload=_safe_metadata(metadata),
        )
    )
    await session.flush()


async def write_access_log(
    factory: async_sessionmaker[AsyncSession],
    *,
    method: str,
    path: str,
    status_code: int | None = None,
    user_id: int | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    duration_ms: int | None = None,
    trace_id: str | None = None,
    request_id: str | None = None,
) -> None:
    """Persist one access log row in its own short transaction.

    A logging failure must never break the request that produced it, so the
    record is best effort: an error is reported through the application logger
    and swallowed.
    """
    try:
        async with factory() as session:
            session.add(
                SysAccessLog(
                    id=new_id(),
                    trace_id=trace_id,
                    request_id=request_id,
                    user_id=user_id,
                    method=method,
                    path=path,
                    status_code=status_code,
                    ip=ip,
                    user_agent=user_agent,
                    duration_ms=duration_ms,
                )
            )
            await session.commit()
    except Exception:  # noqa: BLE001 - logging must not break the request
        _LOGGER.warning("failed to persist the access log for %s %s", method, path)


async def purge_retired_logs(
    session: AsyncSession,
    *,
    now: datetime | None = None,
    settings: Settings | None = None,
) -> dict[str, int]:
    """Delete log rows that outlived their frozen retention period.

    Returns the number of deleted rows per stream.
    """
    resolved = settings or get_settings()
    reference = now or datetime.now(tz=None)
    streams: tuple[tuple[str, int, Any], ...] = (
        ("access_log", resolved.LOG_RETENTION_ACCESS_LOG_DAYS, SysAccessLog),
        ("security_log", resolved.LOG_RETENTION_SECURITY_LOG_DAYS, SysSecurityLog),
        ("operation_log", resolved.LOG_RETENTION_OPERATION_LOG_DAYS, SysOperationLog),
        ("application_log", resolved.LOG_RETENTION_APPLICATION_LOG_DAYS, SysApplicationLog),
    )
    purged: dict[str, int] = {}
    for name, retention_days, model in streams:
        deadline = reference - timedelta(days=retention_days)
        result = await session.execute(
            delete(model).where(model.created_at < deadline),
        )
        purged[name] = int(result.rowcount or 0)
    return purged
