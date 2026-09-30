"""app.admin.audit — data access.

Each log stream keeps its own table, so each stream also keeps its own query.
The streams are never merged into one "business log".
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.audit.model import (
    SysAccessLog,
    SysApplicationLog,
    SysAuditLog,
    SysOperationLog,
    SysSecurityLog,
)


class AuditLogRepository:
    """Data access for the five log streams."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _window(
        statement: Select[Any],
        column: Any,
        *,
        start: datetime.datetime | None,
        end: datetime.datetime | None,
    ) -> Select[Any]:
        if start is not None:
            statement = statement.where(column >= start)
        if end is not None:
            statement = statement.where(column <= end)
        return statement

    async def search_audit_logs(
        self,
        *,
        action: str | None = None,
        operator_id: int | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        result: str | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        trace_id: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[SysAuditLog], int]:
        conditions: list[Any] = []
        if action:
            conditions.append(SysAuditLog.action == action)
        if operator_id is not None:
            conditions.append(SysAuditLog.operator_id == operator_id)
        if resource_type:
            conditions.append(SysAuditLog.resource_type == resource_type)
        if resource_id:
            conditions.append(SysAuditLog.resource_id == resource_id)
        if result:
            conditions.append(SysAuditLog.result == result)
        if trace_id:
            conditions.append(SysAuditLog.trace_id == trace_id)
        statement = self._window(
            select(SysAuditLog).where(*conditions), SysAuditLog.created_at, start=start, end=end
        )
        total = int(
            (
                await self._session.execute(select(func.count()).select_from(statement.subquery()))
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    statement.order_by(SysAuditLog.created_at.desc(), SysAuditLog.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get_audit_log(self, log_id: int) -> SysAuditLog | None:
        return await self._session.get(SysAuditLog, log_id)

    async def search_security_logs(
        self,
        *,
        event_type: str | None = None,
        user_id: int | None = None,
        result: str | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        trace_id: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[SysSecurityLog], int]:
        conditions: list[Any] = []
        if event_type:
            conditions.append(SysSecurityLog.event_type == event_type)
        if user_id is not None:
            conditions.append(SysSecurityLog.user_id == user_id)
        if result:
            conditions.append(SysSecurityLog.result == result)
        if trace_id:
            conditions.append(SysSecurityLog.trace_id == trace_id)
        statement = self._window(
            select(SysSecurityLog).where(*conditions),
            SysSecurityLog.created_at,
            start=start,
            end=end,
        )
        total = int(
            (
                await self._session.execute(select(func.count()).select_from(statement.subquery()))
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    statement.order_by(SysSecurityLog.created_at.desc(), SysSecurityLog.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def search_operation_logs(
        self,
        *,
        operation: str | None = None,
        operator_id: int | None = None,
        resource_type: str | None = None,
        result: str | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        trace_id: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[SysOperationLog], int]:
        conditions: list[Any] = []
        if operation:
            conditions.append(SysOperationLog.operation == operation)
        if operator_id is not None:
            conditions.append(SysOperationLog.operator_id == operator_id)
        if resource_type:
            conditions.append(SysOperationLog.resource_type == resource_type)
        if result:
            conditions.append(SysOperationLog.result == result)
        if trace_id:
            conditions.append(SysOperationLog.trace_id == trace_id)
        statement = self._window(
            select(SysOperationLog).where(*conditions),
            SysOperationLog.created_at,
            start=start,
            end=end,
        )
        total = int(
            (
                await self._session.execute(select(func.count()).select_from(statement.subquery()))
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    statement.order_by(SysOperationLog.created_at.desc(), SysOperationLog.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def search_access_logs(
        self,
        *,
        method: str | None = None,
        path: str | None = None,
        status_code: int | None = None,
        user_id: int | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        trace_id: str | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[SysAccessLog], int]:
        conditions: list[Any] = []
        if method:
            conditions.append(SysAccessLog.method == method.upper())
        if path:
            conditions.append(SysAccessLog.path.like(f"%{path}%"))
        if status_code is not None:
            conditions.append(SysAccessLog.status_code == status_code)
        if user_id is not None:
            conditions.append(SysAccessLog.user_id == user_id)
        if trace_id:
            conditions.append(SysAccessLog.trace_id == trace_id)
        statement = self._window(
            select(SysAccessLog).where(*conditions), SysAccessLog.created_at, start=start, end=end
        )
        total = int(
            (
                await self._session.execute(select(func.count()).select_from(statement.subquery()))
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    statement.order_by(SysAccessLog.created_at.desc(), SysAccessLog.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def application_logs_for_trace(self, trace_id: str) -> list[SysApplicationLog]:
        rows = (
            (
                await self._session.execute(
                    select(SysApplicationLog)
                    .where(SysApplicationLog.trace_id == trace_id)
                    .order_by(SysApplicationLog.created_at, SysApplicationLog.id)
                )
            )
            .scalars()
            .all()
        )
        return list(rows)
