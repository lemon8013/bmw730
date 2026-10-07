"""app.ops.services — 数据访问。

Repository 只负责读写行，既不提交事务也不判断业务规则：事务归 service 层，
策略（如自环校验、状态码白名单）也归 service 层。
"""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.services.model import OpsService, OpsServiceDependency


class ServiceRepository:
    """服务与依赖边的数据访问。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        environment: str | None = None,
        service_type: str | None = None,
        host_id: int | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsService], int]:
        base = select(OpsService).where(OpsService.deleted_at.is_(None))
        if keyword:
            base = base.where(
                OpsService.service_code.ilike(f"%{keyword}%")
                | OpsService.service_name.ilike(f"%{keyword}%")
            )
        if status:
            base = base.where(OpsService.status == status)
        if environment:
            base = base.where(OpsService.environment == environment)
        if service_type:
            base = base.where(OpsService.service_type == service_type)
        if host_id is not None:
            base = base.where(OpsService.host_id == host_id)
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
                    base.order_by(OpsService.service_code.asc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get(self, service_id: int) -> OpsService | None:
        row = await self._session.get(OpsService, service_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def get_by_code(self, service_code: str) -> OpsService | None:
        result = await self._session.execute(
            select(OpsService).where(
                OpsService.service_code == service_code, OpsService.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields: object) -> OpsService:
        row = OpsService(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update(self, row: OpsService, **fields: object) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()

    async def soft_delete(self, row: OpsService) -> None:
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()

    async def list_dependencies(
        self, *, service_id: int, limit: int, offset: int
    ) -> tuple[list[OpsServiceDependency], int]:
        base = select(OpsServiceDependency).where(
            OpsServiceDependency.service_id == service_id,
            OpsServiceDependency.deleted_at.is_(None),
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
                    base.order_by(OpsServiceDependency.id.asc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get_dependency(
        self, *, service_id: int, dependency_id: int
    ) -> OpsServiceDependency | None:
        """取一条依赖边。

        同时限定 ``service_id`` 是为了让"改别的服务依赖"这类越界 id 直接落到
        404，而不是静默命中另一条记录。
        """
        result = await self._session.execute(
            select(OpsServiceDependency).where(
                OpsServiceDependency.id == dependency_id,
                OpsServiceDependency.service_id == service_id,
                OpsServiceDependency.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def find_dependency(
        self, *, service_id: int, depends_on_service_id: int
    ) -> OpsServiceDependency | None:
        result = await self._session.execute(
            select(OpsServiceDependency).where(
                OpsServiceDependency.service_id == service_id,
                OpsServiceDependency.depends_on_service_id == depends_on_service_id,
                OpsServiceDependency.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def create_dependency(self, **fields: object) -> OpsServiceDependency:
        row = OpsServiceDependency(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def soft_delete_dependency(self, row: OpsServiceDependency) -> None:
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
