"""app.platform.tasks — data access."""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.growth.model import BizTask, BizUserTask


class TaskRepository:
    """Data access for tasks and user tasks."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active_tasks(self, *, now: datetime.datetime) -> list[BizTask]:
        result = await self._session.execute(
            select(BizTask).where(
                BizTask.status == "ACTIVE",
                BizTask.deleted_at.is_(None),
                (BizTask.start_at.is_(None)) | (BizTask.start_at <= now),
                (BizTask.end_at.is_(None)) | (BizTask.end_at >= now),
            ).order_by(BizTask.id)
        )
        return list(result.scalars())

    async def get_task(self, task_id: int) -> BizTask | None:
        result = await self._session.execute(
            select(BizTask).where(BizTask.id == task_id, BizTask.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def user_task_for_update(self, user_id: int, task_id: int) -> BizUserTask | None:
        result = await self._session.execute(
            select(BizUserTask)
            .where(BizUserTask.user_id == user_id, BizUserTask.task_id == task_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def create_user_task(self, **fields: object) -> BizUserTask:
        from app.shared.ids import new_id

        row = BizUserTask(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def user_tasks(self, user_id: int) -> list[BizUserTask]:
        result = await self._session.execute(
            select(BizUserTask)
            .where(BizUserTask.user_id == user_id)
            .order_by(BizUserTask.id.desc())
        )
        return list(result.scalars())
