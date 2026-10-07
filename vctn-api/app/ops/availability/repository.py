"""app.ops.availability — 数据访问。

探测结果只由采集任务写入，本模块对结果只提供分页读。Repository 不提交事务，
也不判断"超时/间隔是否合理"，那是 service 层的策略。
"""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.availability.model import OpsAvailabilityCheck, OpsAvailabilityResult


class AvailabilityRepository:
    """可用性探测与结果的数据访问。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        keyword: str | None = None,
        check_type: str | None = None,
        service_id: int | None = None,
        environment: str | None = None,
        enabled: bool | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsAvailabilityCheck], int]:
        base = select(OpsAvailabilityCheck).where(OpsAvailabilityCheck.deleted_at.is_(None))
        if keyword:
            base = base.where(
                OpsAvailabilityCheck.check_code.ilike(f"%{keyword}%")
                | OpsAvailabilityCheck.name.ilike(f"%{keyword}%")
            )
        if check_type:
            base = base.where(OpsAvailabilityCheck.check_type == check_type)
        if service_id is not None:
            base = base.where(OpsAvailabilityCheck.service_id == service_id)
        if environment:
            base = base.where(OpsAvailabilityCheck.environment == environment)
        if enabled is not None:
            base = base.where(OpsAvailabilityCheck.enabled == enabled)
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
                    base.order_by(OpsAvailabilityCheck.check_code.asc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get(self, check_id: int) -> OpsAvailabilityCheck | None:
        row = await self._session.get(OpsAvailabilityCheck, check_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def get_by_code(self, check_code: str) -> OpsAvailabilityCheck | None:
        result = await self._session.execute(
            select(OpsAvailabilityCheck).where(
                OpsAvailabilityCheck.check_code == check_code,
                OpsAvailabilityCheck.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields: object) -> OpsAvailabilityCheck:
        row = OpsAvailabilityCheck(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update(self, row: OpsAvailabilityCheck, **fields: object) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()

    async def soft_delete(self, row: OpsAvailabilityCheck) -> None:
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()

    async def list_results(
        self,
        *,
        check_id: int,
        since: datetime.datetime | None = None,
        success: bool | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsAvailabilityResult], int]:
        # 结果表没有软删标记：它是事实流水，只按时间窗淘汰，不做逻辑删除。
        base = select(OpsAvailabilityResult).where(OpsAvailabilityResult.check_id == check_id)
        if since is not None:
            base = base.where(OpsAvailabilityResult.checked_at >= since)
        if success is not None:
            base = base.where(OpsAvailabilityResult.success == success)
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
                    base.order_by(OpsAvailabilityResult.checked_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total
