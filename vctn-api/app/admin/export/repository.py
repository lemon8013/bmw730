"""app.admin.export — data access.

Repository owns no transaction; the service layer commits. Every column maps
1:1 onto the frozen ``sys_export_job`` table.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.export.model import ExportJob
from app.shared.ids import new_id


class ExportTaskRepository:
    """Data access for administrative export jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **fields: object) -> ExportJob:
        row = ExportJob(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def get(self, task_id: int) -> ExportJob | None:
        return await self._session.get(ExportJob, task_id)

    async def list(
        self, *, export_type: str | None, status: str | None, limit: int, offset: int
    ) -> tuple[list[ExportJob], int]:
        conditions: list[object] = []
        if export_type:
            conditions.append(ExportJob.export_type == export_type)
        if status:
            conditions.append(ExportJob.status == status)
        total = int(
            (
                await self._session.execute(
                    select(func.count(ExportJob.id)).where(*conditions)
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(ExportJob)
                    .where(*conditions)
                    .order_by(ExportJob.created_at.desc(), ExportJob.id.desc())
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
