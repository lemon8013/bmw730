"""app.platform.achievements — data access."""

from __future__ import annotations

from datetime import UTC

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.growth.model import BizAchievement, BizGrowthEvent, BizUserAchievement


class AchievementRepository:
    """Data access for achievements and unlocked achievements."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def active(self) -> list[BizAchievement]:
        result = await self._session.execute(
            select(BizAchievement)
            .where(BizAchievement.status == "ACTIVE", BizAchievement.deleted_at.is_(None))
            .order_by(BizAchievement.id)
        )
        return list(result.scalars())

    async def get(self, achievement_id: int) -> BizAchievement | None:
        result = await self._session.execute(
            select(BizAchievement).where(
                BizAchievement.id == achievement_id, BizAchievement.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def unlocked(self, user_id: int) -> list[BizUserAchievement]:
        result = await self._session.execute(
            select(BizUserAchievement)
            .where(BizUserAchievement.user_id == user_id)
            .order_by(BizUserAchievement.achieved_at.desc(), BizUserAchievement.id.desc())
        )
        return list(result.scalars())

    async def unlock(self, *, user_id: int, achievement_id: int) -> BizUserAchievement:
        from datetime import datetime

        from app.shared.ids import new_id

        row = BizUserAchievement(
            id=new_id(),
            user_id=user_id,
            achievement_id=achievement_id,
            achieved_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def event_count(self, user_id: int, event_code: str) -> int:
        """Return how many growth events of one code a user produced."""
        result = await self._session.execute(
            select(func.count(BizGrowthEvent.id)).where(
                BizGrowthEvent.user_id == user_id, BizGrowthEvent.event_code == event_code
            )
        )
        return int(result.scalar_one())
