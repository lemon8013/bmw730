"""app.ops.logs — data access.

The four log streams created by ``app.admin.audit`` are reused as they are; this
module defines no table and no new column. The repository knows, per stream,
which column carries each filterable dimension and simply does not accept a
filter the addressed table cannot express — the service rejects those requests
before they reach SQL.

Read only, no commit, no business rule.
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.audit.model import (
    SysAccessLog,
    SysApplicationLog,
    SysOperationLog,
    SysSecurityLog,
)

_MODEL_FOR: dict[str, Any] = {
    "ACCESS": SysAccessLog,
    "APPLICATION": SysApplicationLog,
    "SECURITY": SysSecurityLog,
    "OPERATION": SysOperationLog,
}

#: Human readable text of a record, used by the generic keyword filter and as
#: the ``summary`` returned to the UI.
_TEXT_COLUMN_FOR: dict[str, Any] = {
    "ACCESS": SysAccessLog.path,
    "APPLICATION": SysApplicationLog.message,
    "SECURITY": SysSecurityLog.event_type,
    "OPERATION": SysOperationLog.operation,
}

#: Column holding the request id, for the streams that record one.
_REQUEST_ID_COLUMN_FOR: dict[str, Any] = {
    "ACCESS": SysAccessLog.request_id,
    "APPLICATION": None,
    "SECURITY": None,
    "OPERATION": SysOperationLog.request_id,
}

#: Column holding the client address.
_IP_COLUMN_FOR: dict[str, Any] = {
    "ACCESS": SysAccessLog.ip,
    "APPLICATION": None,
    "SECURITY": SysSecurityLog.ip,
    "OPERATION": None,
}

#: Whether the stream records a severity level.
_LEVEL_COLUMN_FOR: dict[str, Any] = {
    "ACCESS": None,
    "APPLICATION": SysApplicationLog.level,
    "SECURITY": None,
    "OPERATION": None,
}

#: Whether the stream records the emitting component.
_SERVICE_COLUMN_FOR: dict[str, Any] = {
    "ACCESS": None,
    "APPLICATION": SysApplicationLog.logger_name,
    "SECURITY": None,
    "OPERATION": None,
}


#: Every dimension the streams can be filtered by, per stream. A dimension whose
#: column is ``None`` cannot be expressed in SQL and is rejected upstream.
_FILTERABLE_COLUMN_FOR: dict[str, dict[str, Any]] = {
    "trace_id": {name: model.trace_id for name, model in _MODEL_FOR.items()},
    "request_id": _REQUEST_ID_COLUMN_FOR,
    "ip": _IP_COLUMN_FOR,
    "level": _LEVEL_COLUMN_FOR,
    "service": _SERVICE_COLUMN_FOR,
}


class OpsLogRepository:
    """Read side across the four reusable log streams."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def search(
        self,
        log_type: str,
        *,
        start_at: datetime.datetime | None,
        end_at: datetime.datetime | None,
        level: str | None,
        service: str | None,
        trace_id: str | None,
        request_id: str | None,
        keyword: str | None,
        ip: str | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Any], int]:
        model = _MODEL_FOR[log_type]
        conditions = self._conditions(
            log_type,
            start_at=start_at,
            end_at=end_at,
            level=level,
            service=service,
            trace_id=trace_id,
            request_id=request_id,
            keyword=keyword,
            ip=ip,
        )
        total = int(
            (
                await self._session.execute(select(func.count(model.id)).where(*conditions))
            ).scalar_one()
        )
        rows: Sequence[Any] = (
            (
                await self._session.execute(
                    select(model)
                    .where(*conditions)
                    .order_by(model.created_at.desc(), model.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get(self, log_type: str, log_id: int) -> Any | None:
        return await self._session.get(_MODEL_FOR[log_type], log_id)

    async def list_by_trace(self, trace_id: str, *, limit: int) -> list[tuple[str, Any]]:
        """Return the records of one trace, oldest first, across all streams."""
        found: list[tuple[str, Any]] = []
        for log_type, model in _MODEL_FOR.items():
            rows: Sequence[Any] = (
                (
                    await self._session.execute(
                        select(model)
                        .where(model.trace_id == trace_id)
                        .order_by(model.created_at.asc(), model.id.asc())
                        .limit(limit)
                    )
                )
                .scalars()
                .all()
            )
            found.extend((log_type, row) for row in rows)
        found.sort(key=lambda item: (item[1].created_at, int(item[1].id)))
        return found[:limit]

    def supports(self, log_type: str, dimension: str) -> bool:
        """Whether the addressed stream can be filtered by ``dimension``."""
        return _FILTERABLE_COLUMN_FOR[dimension].get(log_type) is not None

    def _conditions(
        self,
        log_type: str,
        *,
        start_at: datetime.datetime | None,
        end_at: datetime.datetime | None,
        level: str | None,
        service: str | None,
        trace_id: str | None,
        request_id: str | None,
        keyword: str | None,
        ip: str | None,
    ) -> list[Any]:
        model = _MODEL_FOR[log_type]
        conditions: list[Any] = []
        if start_at is not None:
            conditions.append(model.created_at >= start_at)
        if end_at is not None:
            conditions.append(model.created_at <= end_at)
        if trace_id:
            conditions.append(model.trace_id == trace_id)
        if request_id:
            request_id_column = _REQUEST_ID_COLUMN_FOR[log_type]
            if request_id_column is not None:
                conditions.append(request_id_column == request_id)
        if keyword:
            conditions.append(_TEXT_COLUMN_FOR[log_type].ilike(f"%{keyword}%"))
        if ip:
            ip_column = _IP_COLUMN_FOR[log_type]
            if ip_column is not None:
                # ``host()`` strips the netmask an INET column appends, so the
                # filter compares against exactly what the UI renders.
                conditions.append(func.host(ip_column) == ip)
        if level:
            level_column = _LEVEL_COLUMN_FOR[log_type]
            if level_column is not None:
                conditions.append(level_column == level)
        if service:
            service_column = _SERVICE_COLUMN_FOR[log_type]
            if service_column is not None:
                conditions.append(service_column.ilike(f"%{service}%"))
        return conditions
