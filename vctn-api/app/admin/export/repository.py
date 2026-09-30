"""app.admin.export — data access.

Repository owns no transaction; the service layer commits.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.export.model import SysExportTask
from app.shared.ids import new_id


class ExportTaskRepository:
    """Data access for administrative export tasks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **fields: object) -> SysExportTask:
        row = SysExportTask(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, task_id: int) -> SysExportTask | None:
        return await self._session.get(SysExportTask, task_id)

    async def list(
        self, *, task_type: str | None, status: str | None, limit: int, offset: int
    ) -> tuple[list[SysExportTask], int]:
        conditions: list[object] = []
        if task_type:
            conditions.append(SysExportTask.task_type == task_type)
        if status:
            conditions.append(SysExportTask.status == status)
        total = int(
            (
                await self._session.execute(
                    select(func.count(SysExportTask.id)).where(*conditions)
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(SysExportTask)
                    .where(*conditions)
                    .order_by(SysExportTask.created_at.desc(), SysExportTask.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def flush(self) -> None:
        await self._session.flush()
