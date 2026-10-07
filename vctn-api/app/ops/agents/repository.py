"""app.ops.agents — data access.

Repository methods never commit and never decide business rules: they only read
and write rows. Credential verification, status semantics and the transaction
belong to the service layer.
"""

from __future__ import annotations

import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ops.agents.model import OpsAgent, OpsAgentHeartbeat
from app.ops.hosts.model import OpsHost
from app.ops.metrics.model import OpsMetricSample


class AgentRepository:
    """Data access for agents, heartbeats and the projected metric samples."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        enabled: bool | None = None,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsAgent], int]:
        base = select(OpsAgent).where(OpsAgent.deleted_at.is_(None))
        if keyword:
            base = base.where(
                OpsAgent.agent_code.ilike(f"%{keyword}%")
                | OpsAgent.agent_name.ilike(f"%{keyword}%")
            )
        if status:
            base = base.where(OpsAgent.status == status)
        if enabled is not None:
            base = base.where(OpsAgent.enabled.is_(enabled))
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
                    base.order_by(OpsAgent.agent_code.asc()).limit(limit).offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def get(self, agent_id: int) -> OpsAgent | None:
        row = await self._session.get(OpsAgent, agent_id)
        if row is None or row.deleted_at is not None:
            return None
        return row

    async def get_by_code(self, agent_code: str) -> OpsAgent | None:
        result = await self._session.execute(
            select(OpsAgent).where(
                OpsAgent.agent_code == agent_code, OpsAgent.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, **fields: object) -> OpsAgent:
        row = OpsAgent(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def update(self, row: OpsAgent, **fields: object) -> None:
        for key, value in fields.items():
            setattr(row, key, value)
        await self._session.flush()

    async def add_heartbeat(self, **fields: object) -> OpsAgentHeartbeat:
        row = OpsAgentHeartbeat(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def list_heartbeats(
        self,
        *,
        agent_id: int,
        since: datetime.datetime,
        limit: int,
        offset: int,
    ) -> tuple[list[OpsAgentHeartbeat], int]:
        base = select(OpsAgentHeartbeat).where(
            OpsAgentHeartbeat.agent_id == agent_id,
            OpsAgentHeartbeat.collected_at >= since,
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
                    base.order_by(OpsAgentHeartbeat.collected_at.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def add_metric_samples(self, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        self._session.add_all(
            [OpsMetricSample(**fields) for fields in rows]  # type: ignore[arg-type]
        )
        await self._session.flush()

    async def get_host(self, host_id: int) -> OpsHost | None:
        row = await self._session.get(OpsHost, host_id)
        if row is None or row.deleted_at is not None:
            return None
        return row
