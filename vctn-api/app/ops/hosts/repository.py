"""app.ops.hosts — data access.

Repository methods never commit and never decide business rules: they only read
and write rows, the service layer owns the transaction and the policy.
"""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.hosts.model import OpsEnvironment, OpsHost, OpsHostGroup


class HostRepository:
    """Data access for hosts, host groups and environments."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        environment: str | None = None,
        host_group_id: int | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsHost], int]:
        base = select(OpsHost).where(OpsHost.deleted_at.is_(None))
        if keyword:
            base = base.where(OpsHost.hostname.ilike(f"%{keyword}%"))
        if status:
            base = base.where(OpsHost.status == status)
        if environment:
            base = base.where(OpsHost.environment == environment)
        if host_group_id is not None:
            base = base.where(OpsHost.host_group_id == host_group_id)
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
                    base.order_by(OpsHost.hostname.asc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get(self, host_id: int) -> OpsHost | None:
        row = await self._session.get(OpsHost, host_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def get_by_hostname(self, hostname: str) -> OpsHost | None:
        result = await self._session.execute(
            select(OpsHost).where(
                OpsHost.hostname == hostname, OpsHost.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields: object) -> OpsHost:
        row = OpsHost(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update(self, row: OpsHost, **fields: object) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()

    async def soft_delete(self, row: OpsHost) -> None:
        row.deleted_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()

    async def list_groups(self) -> list[OpsHostGroup]:
        rows = (
            await self._session.execute(
                select(OpsHostGroup)
                .where(OpsHostGroup.deleted_at.is_(None))
                .order_by(OpsHostGroup.sort_order.asc(), OpsHostGroup.id.asc())
            )
        ).scalars()
        return list(rows)

    async def list_environments(self) -> list[OpsEnvironment]:
        rows = (
            await self._session.execute(
                select(OpsEnvironment)
                .where(OpsEnvironment.deleted_at.is_(None))
                .order_by(OpsEnvironment.sort_order.asc(), OpsEnvironment.id.asc())
            )
        ).scalars()
        return list(rows)
