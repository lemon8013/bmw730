"""app.platform.users — data access."""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.users.model import BizUser, BizUserProfile


class PlatformUserRepository:
    """Data access for business users and their profiles."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, user_id: int) -> BizUser | None:
        result = await self._session.execute(
            select(BizUser).where(BizUser.id == user_id, BizUser.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_profile(self, user_id: int) -> BizUserProfile | None:
        return await self._session.get(BizUserProfile, user_id)

    async def upsert_profile(self, user_id: int, values: dict[str, object]) -> BizUserProfile:
        row = await self.get_profile(user_id)
        now = datetime.datetime.now(datetime.UTC)
        if row is None:
            row = BizUserProfile(user_id=user_id, **values)  # type: ignore[arg-type]
            self._session.add(row)
        else:
            for key, value in values.items():
                setattr(row, key, value)
        row.updated_at = now
        await self._session.flush()
        return row

    async def update_user(self, user: BizUser, values: dict[str, object]) -> BizUser:
        for key, value in values.items():
            setattr(user, key, value)
        user.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        return user
