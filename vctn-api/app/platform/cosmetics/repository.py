"""app.platform.cosmetics — data access."""

from __future__ import annotations

import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.cosmetics.model import BizCosmetic, BizUserCosmetic, BizUserEquipment

COSMETIC_SLOTS: tuple[str, ...] = (
    "avatar_cosmetic_id",
    "avatar_frame_cosmetic_id",
    "crown_cosmetic_id",
    "badge_cosmetic_id",
    "title_cosmetic_id",
    "name_effect_cosmetic_id",
)

SLOT_TYPE_BY_FIELD: dict[str, str] = {
    "avatar_cosmetic_id": "AVATAR",
    "avatar_frame_cosmetic_id": "AVATAR_FRAME",
    "crown_cosmetic_id": "CROWN",
    "badge_cosmetic_id": "BADGE",
    "title_cosmetic_id": "TITLE",
    "name_effect_cosmetic_id": "NAME_EFFECT",
}


class CosmeticRepository:
    """Data access for cosmetics, ownership and equipment."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_cosmetics(self) -> list[BizCosmetic]:
        result = await self._session.execute(
            select(BizCosmetic)
            .where(BizCosmetic.deleted_at.is_(None))
            .order_by(BizCosmetic.sort_order, BizCosmetic.id)
        )
        return list(result.scalars())

    async def get_cosmetic(self, cosmetic_id: int) -> BizCosmetic | None:
        result = await self._session.execute(
            select(BizCosmetic).where(
                BizCosmetic.id == cosmetic_id, BizCosmetic.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def owned_ids(self, user_id: int) -> set[int]:
        result = await self._session.execute(
            select(BizUserCosmetic.cosmetic_id).where(BizUserCosmetic.user_id == user_id)
        )
        return {int(row) for row in result.scalars()}

    async def owned(self, user_id: int) -> list[BizUserCosmetic]:
        result = await self._session.execute(
            select(BizUserCosmetic)
            .where(BizUserCosmetic.user_id == user_id)
            .order_by(BizUserCosmetic.obtained_at.desc(), BizUserCosmetic.id.desc())
        )
        return list(result.scalars())

    async def grant(
        self,
        *,
        user_id: int,
        cosmetic_id: int,
        source_type: str,
        source_id: str | None = None,
        obtained_at: datetime.datetime | None = None,
    ) -> BizUserCosmetic:
        from app.shared.ids import new_id

        row = BizUserCosmetic(
            id=new_id(),
            user_id=user_id,
            cosmetic_id=cosmetic_id,
            obtained_at=obtained_at or datetime.datetime.now(datetime.UTC),
            source_type=source_type,
            source_id=source_id,
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def revoke(self, user_id: int, cosmetic_id: int) -> int:
        from sqlalchemy import delete

        result = await self._session.execute(
            delete(BizUserCosmetic).where(
                BizUserCosmetic.user_id == user_id, BizUserCosmetic.cosmetic_id == cosmetic_id
            )
        )
        return int(result.rowcount or 0)

    async def equipment(self, user_id: int) -> BizUserEquipment:
        row = await self._session.get(BizUserEquipment, user_id)
        if row is None:
            row = BizUserEquipment(user_id=user_id)
            self._session.add(row)
            await self._session.flush()
        return row

    async def unequip_slot(self, user_id: int, cosmetic_id: int) -> None:
        row = await self.equipment(user_id)
        for field in COSMETIC_SLOTS:
            if getattr(row, field) is not None and int(getattr(row, field)) == cosmetic_id:
                setattr(row, field, None)
        await self._session.flush()
