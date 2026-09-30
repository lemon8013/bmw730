"""app.platform.achievements — business logic.

An achievement is unlocked when its condition is satisfied by data the platform
already owns (for example "produce N growth events of one code"). The insert into
``biz_user_achievement`` is protected by ``UNIQUE(user_id, achievement_id)``, so
a repeated evaluation can never unlock the same achievement twice.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.platform.achievements.repository import AchievementRepository
from app.platform.achievements.schema import AchievementResponse, UserAchievementResponse
from app.platform.points.service import PointService
from app.shared.events.codes import OutboxEventType
from app.shared.outbox.service import OutboxService

STATUS_ACTIVE: str = "ACTIVE"


class AchievementService:
    """Achievement definitions and unlocking."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = AchievementRepository(session)
        self._settings = settings or get_settings()
        self._outbox = OutboxService(self._settings)

    async def list_achievements(self) -> list[AchievementResponse]:
        rows = await self._repository.active()
        return [
            AchievementResponse(
                id=str(int(row.id)),
                achievement_code=str(row.achievement_code),
                achievement_name=str(row.achievement_name),
                conditions=row.conditions,
                reward=row.reward,
                status=str(row.status),
            )
            for row in rows
        ]

    async def my_achievements(self, user_id: int) -> list[UserAchievementResponse]:
        rows = await self._repository.unlocked(user_id)
        names: dict[int, str] = {}
        for row in await self._repository.active():
            names[int(row.id)] = str(row.achievement_name)
        return [
            UserAchievementResponse(
                id=str(int(row.id)),
                user_id=str(int(row.user_id)),
                achievement_id=str(int(row.achievement_id)),
                achievement_name=names.get(int(row.achievement_id)),
                achieved_at=row.achieved_at,
            )
            for row in rows
        ]

    async def evaluate(self, user_id: int) -> list[int]:
        """Unlock every achievement whose condition the user now satisfies."""
        unlocked: list[int] = []
        for achievement in await self._repository.active():
            if not await self._condition_met(user_id, dict(achievement.conditions or {})):
                continue
            try:
                async with self._session.begin_nested():
                    await self._repository.unlock(
                        user_id=user_id, achievement_id=int(achievement.id)
                    )
            except IntegrityError:
                continue
            unlocked.append(int(achievement.id))
            await self._publish_and_reward(user_id, achievement)
        if unlocked:
            await self._session.commit()
        return unlocked

    async def _condition_met(self, user_id: int, conditions: dict[str, Any]) -> bool:
        event_code = conditions.get("event_code")
        if event_code is None:
            return False
        count = await self._repository.event_count(user_id, str(event_code))
        return count >= int(conditions.get("count", 1))

    async def _publish_and_reward(self, user_id: int, achievement: object) -> None:
        reward: dict[str, Any] = dict(getattr(achievement, "reward", None) or {})
        await self._outbox.publish(
            self._session,
            event_type=OutboxEventType.ACHIEVEMENT_UNLOCKED,
            aggregate_type="biz_achievement",
            aggregate_id=int(achievement.id),
            payload={
                "user_id": user_id,
                "achievement_id": int(achievement.id),
                "achievement_code": str(achievement.achievement_code),
                "reward": reward,
                "idempotency_key": f"achievement:{achievement.id}:{user_id}",
                "achieved_at": datetime.datetime.now(datetime.UTC).isoformat(),
            },
        )
        points = int(reward.get("points", 0))
        if points:
            await PointService(self._session, self._settings).earn(
                user_id=user_id,
                points=points,
                source_type="ACHIEVEMENT",
                source_id=str(achievement.id),
                reason=f"ACHIEVEMENT:{achievement.achievement_code}",
                idempotency_key=f"achievement-points:{achievement.id}:{user_id}",
            )
        await self._session.flush()

    async def consume_achievement_unlocked(self, payload: dict) -> None:
        """Outbox consumer: grant the achievement reward exactly once."""
        reward = dict(payload.get("reward") or {})
        points = int(reward.get("points", 0))
        if not points:
            return
        await PointService(self._session, self._settings).earn(
            user_id=int(payload["user_id"]),
            points=points,
            source_type="ACHIEVEMENT",
            source_id=str(payload.get("achievement_id", "")),
            reason=f"ACHIEVEMENT:{payload.get('achievement_code', '')}",
            idempotency_key=str(payload.get("idempotency_key")),
        )
        await self._session.commit()
