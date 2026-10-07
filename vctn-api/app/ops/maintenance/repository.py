"""app.ops.maintenance — 数据访问。

Repository 只读写行，不提交事务，也不判断时间区间是否合法：``ends_at`` 必须
大于 ``starts_at`` 是业务规则，归 service 层（库里另有 CHECK 约束兜底）。
"""

from __future__ import annotations

import datetime

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.maintenance.model import OpsMaintenanceWindow

#: A window of this scope suppresses every scope, whatever its ``scope_id``.
SCOPE_TYPE_GLOBAL: str = "GLOBAL"


class MaintenanceRepository:
    """维护窗口的数据访问。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        keyword: str | None = None,
        scope_type: str | None = None,
        scope_id: int | None = None,
        enabled: bool | None = None,
        active_at: datetime.datetime | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsMaintenanceWindow], int]:
        base = select(OpsMaintenanceWindow).where(OpsMaintenanceWindow.deleted_at.is_(None))
        if keyword:
            base = base.where(
                OpsMaintenanceWindow.window_code.ilike(f"%{keyword}%")
                | OpsMaintenanceWindow.title.ilike(f"%{keyword}%")
            )
        if scope_type:
            base = base.where(OpsMaintenanceWindow.scope_type == scope_type)
        if scope_id is not None:
            base = base.where(OpsMaintenanceWindow.scope_id == scope_id)
        if enabled is not None:
            base = base.where(OpsMaintenanceWindow.enabled == enabled)
        if active_at is not None:
            # 只保留覆盖该时刻的窗口：看板要靠它判断"当前是否在维护中"。
            base = base.where(
                OpsMaintenanceWindow.starts_at <= active_at,
                OpsMaintenanceWindow.ends_at >= active_at,
            )
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
                    base.order_by(OpsMaintenanceWindow.starts_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get(self, window_id: int) -> OpsMaintenanceWindow | None:
        row = await self._session.get(OpsMaintenanceWindow, window_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def find_suppressing(
        self,
        *,
        at: datetime.datetime,
        scope_type: str | None = None,
        scope_id: int | None = None,
    ) -> OpsMaintenanceWindow | None:
        """Return the window that suppresses ``scope_type/scope_id`` at ``at``.

        A ``GLOBAL`` window matches every scope; a scoped window only matches its
        own scope. An unknown or absent ``scope_id`` therefore only ever matches
        a global window.
        """
        covering = sa.and_(
            OpsMaintenanceWindow.starts_at <= at,
            OpsMaintenanceWindow.ends_at >= at,
        )
        scope_clause = OpsMaintenanceWindow.scope_type == SCOPE_TYPE_GLOBAL
        if scope_type and scope_id is not None:
            scope_clause = sa.or_(
                scope_clause,
                sa.and_(
                    OpsMaintenanceWindow.scope_type == scope_type,
                    OpsMaintenanceWindow.scope_id == scope_id,
                ),
            )
        result = await self._session.execute(
            select(OpsMaintenanceWindow)
            .where(
                OpsMaintenanceWindow.deleted_at.is_(None),
                OpsMaintenanceWindow.enabled.is_(True),
                OpsMaintenanceWindow.suppress_alerts.is_(True),
                covering,
                scope_clause,
            )
            .order_by(OpsMaintenanceWindow.starts_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, window_code: str) -> OpsMaintenanceWindow | None:
        result = await self._session.execute(
            select(OpsMaintenanceWindow).where(
                OpsMaintenanceWindow.window_code == window_code,
                OpsMaintenanceWindow.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields: object) -> OpsMaintenanceWindow:
        row = OpsMaintenanceWindow(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update(self, row: OpsMaintenanceWindow, **fields: object) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()

    async def soft_delete(self, row: OpsMaintenanceWindow) -> None:
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
