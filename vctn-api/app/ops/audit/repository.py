"""app.ops.audit — data access.

``ops_operation_record`` is append-only, so this repository only ever reads:
there is no ``create``, ``update`` or ``delete`` method, and adding one would
break the audit guarantee. Records are also never filtered by ``deleted_at``
because the table has no such column — an audit row is never removed through the
API, only by the frozen retention job.

Repository methods never commit; the read path has no transaction to own.
"""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.audit.model import OpsOperationRecord


class AuditRepository:
    """Read-only data access for the ops operation records."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        action: str | None = None,
        resource_type: str | None = None,
        operator_username: str | None = None,
        result: str | None = None,
        trace_id: str | None = None,
        start_at: datetime.datetime | None = None,
        end_at: datetime.datetime | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsOperationRecord], int]:
        base = select(OpsOperationRecord)
        if action:
            base = base.where(OpsOperationRecord.action == action)
        if resource_type:
            base = base.where(OpsOperationRecord.resource_type == resource_type)
        if operator_username:
            base = base.where(
                OpsOperationRecord.operator_username.ilike(f"%{operator_username}%")
            )
        if result:
            base = base.where(OpsOperationRecord.result == result)
        if trace_id:
            base = base.where(OpsOperationRecord.trace_id == trace_id)
        if start_at is not None:
            base = base.where(OpsOperationRecord.created_at >= start_at)
        if end_at is not None:
            base = base.where(OpsOperationRecord.created_at <= end_at)
        total = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(base.subquery())
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    base.order_by(OpsOperationRecord.created_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get(self, record_id: int) -> OpsOperationRecord | None:
        return await self._session.get(OpsOperationRecord, record_id)
