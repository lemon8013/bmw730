"""app.platform.levels — data access."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.levels.model import BizUserLevel, BizUserLevelBenefit, BizUserLevelHistory
from app.shared.ids import new_id


class LevelRepository:
    """Data access for levels, level benefits and level history."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_levels(self) -> list[BizUserLevel]:
        result = await self._session.execute(
            select(BizUserLevel)
            .where(BizUserLevel.deleted_at.is_(None))
            .order_by(BizUserLevel.level_no)
        )
        return list(result.scalars())

    async def get_level(self, level_id: int) -> BizUserLevel | None:
        result = await self._session.execute(
            select(BizUserLevel).where(
                BizUserLevel.id == level_id, BizUserLevel.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def add_history(self, **fields: object) -> BizUserLevelHistory:
        row = BizUserLevelHistory(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def history_of(self, user_id: int, *, limit: int) -> list[BizUserLevelHistory]:
        result = await self._session.execute(
            select(BizUserLevelHistory)
            .where(BizUserLevelHistory.user_id == user_id)
            .order_by(BizUserLevelHistory.created_at.desc(), BizUserLevelHistory.id.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def benefits_of(self, level_id: int) -> list[BizUserLevelBenefit]:
        result = await self._session.execute(
            select(BizUserLevelBenefit)
            .where(BizUserLevelBenefit.level_id == level_id)
            .order_by(BizUserLevelBenefit.id)
        )
        return list(result.scalars())

    async def enabled_benefits_of(self, level_id: int) -> list[BizUserLevelBenefit]:
        result = await self._session.execute(
            select(BizUserLevelBenefit).where(
                BizUserLevelBenefit.level_id == level_id,
                BizUserLevelBenefit.enabled.is_(True),
            )
        )
        return list(result.scalars())

    async def create_level(self, **fields: object) -> BizUserLevel:
        row = BizUserLevel(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def create_benefit(self, **fields: object) -> BizUserLevelBenefit:
        row = BizUserLevelBenefit(id=new_id(), **fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row
