"""app.admin.logs — data access.

Reuses the five log-stream tables already defined by ``app.admin.audit``
(``sys_audit_log`` / ``sys_security_log`` / ``sys_operation_log`` /
``sys_access_log`` / ``sys_application_log``). No new log table is created.

The repository only reads; it never writes, and it never returns sensitive
values — masking is applied one layer up, in the service.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.audit.model import (
    SysAccessLog,
    SysApplicationLog,
    SysAuditLog,
    SysOperationLog,
    SysSecurityLog,
)

LOG_TYPES: tuple[str, ...] = ("audit", "security", "operation", "access", "application")

_MODEL_FOR: dict[str, Any] = {
    "audit": SysAuditLog,
    "security": SysSecurityLog,
    "operation": SysOperationLog,
    "access": SysAccessLog,
    "application": SysApplicationLog,
}

# Text column used for the generic keyword filter, per stream.
_TEXT_COLUMN: dict[str, Any] = {
    "audit": SysAuditLog.action,
    "security": SysSecurityLog.event_type,
    "operation": SysOperationLog.operation,
    "access": SysAccessLog.path,
    "application": SysApplicationLog.message,
}

# User/operator column used for the generic user filter, per stream.
_USER_COLUMN: dict[str, Any] = {
    "audit": SysAuditLog.operator_id,
    "security": SysSecurityLog.user_id,
    "operation": SysOperationLog.operator_id,
    "access": SysAccessLog.user_id,
    "application": None,
}


class LogsQueryRepository:
    """Read side across the five log streams."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for name, model in _MODEL_FOR.items():
            count = await self._session.execute(select(func.count(model.id)))
            out[name] = int(count.scalar_one() or 0)
        return out

    async def search(
        self,
        log_type: str,
        *,
        start: Any | None,
        end: Any | None,
        level: str | None,
        result: str | None,
        keyword: str | None,
        user_id: int | None,
        limit: int,
        offset: int,
    ) -> tuple[list[Any], int]:
        model = _MODEL_FOR[log_type]
        conditions: list[Any] = []
        if start is not None:
            conditions.append(model.created_at >= start)
        if end is not None:
            conditions.append(model.created_at <= end)
        if log_type == "application":
            if level:
                conditions.append(SysApplicationLog.level == level)
        else:
            if result:
                conditions.append(model.result == result)
        if keyword:
            conditions.append(_TEXT_COLUMN[log_type].like(f"%{keyword}%"))
        user_col = _USER_COLUMN[log_type]
        if user_id is not None and user_col is not None:
            conditions.append(user_col == user_id)

        total = int(
            (
                await self._session.execute(
                    select(func.count(model.id)).where(*conditions)
                )
            ).scalar_one()
        )
        rows = (
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
