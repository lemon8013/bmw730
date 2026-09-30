"""app.admin.config — data access."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.config.model import SysConfig, SysFeatureFlag


class ConfigRepository:
    """Data access for configuration entries and feature flags."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_configs(self) -> list[SysConfig]:
        result = await self._session.execute(
            select(SysConfig)
            .where(SysConfig.deleted_at.is_(None))
            .order_by(SysConfig.config_group, SysConfig.config_key)
        )
        return list(result.scalars())

    async def get_config_by_key(self, key: str) -> SysConfig | None:
        result = await self._session.execute(
            select(SysConfig).where(
                func.lower(SysConfig.config_key) == key.lower(), SysConfig.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def list_flags(self) -> list[SysFeatureFlag]:
        result = await self._session.execute(
            select(SysFeatureFlag)
            .where(SysFeatureFlag.deleted_at.is_(None))
            .order_by(SysFeatureFlag.id)
        )
        return list(result.scalars())

    async def get_flag(self, flag_id: int) -> SysFeatureFlag | None:
        result = await self._session.execute(
            select(SysFeatureFlag).where(
                SysFeatureFlag.id == flag_id, SysFeatureFlag.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def exists_flag_key(self, key: str, *, exclude_id: int | None = None) -> bool:
        conditions = [
            func.lower(SysFeatureFlag.flag_key) == key.lower(),
            SysFeatureFlag.deleted_at.is_(None),
        ]
        if exclude_id is not None:
            conditions.append(SysFeatureFlag.id != exclude_id)
        result = await self._session.execute(
            select(func.count(SysFeatureFlag.id)).where(*conditions)
        )
        return int(result.scalar_one()) > 0

    def add_flag(self, flag: SysFeatureFlag) -> None:
        self._session.add(flag)
