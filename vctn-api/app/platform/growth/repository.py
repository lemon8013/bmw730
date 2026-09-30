"""app.platform.growth — data access."""

from __future__ import annotations

import datetime
from collections.abc import Sequence

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.growth.model import (
    BizGrowthEvent,
    BizGrowthRule,
    BizUserGrowthAccount,
    BizUserGrowthTransaction,
)
from app.platform.levels.model import BizUserLevel


class GrowthRepository:
    """Data access for growth accounts, events, rules and the ledger."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def account(self, user_id: int) -> BizUserGrowthAccount | None:
        return await self._session.get(BizUserGrowthAccount, user_id)

    async def account_for_update(self, user_id: int) -> BizUserGrowthAccount | None:
        result = await self._session.execute(
            select(BizUserGrowthAccount)
            .where(BizUserGrowthAccount.user_id == user_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def create_account(self, user_id: int) -> BizUserGrowthAccount:
        row = BizUserGrowthAccount(
            user_id=user_id, total_growth_points=0, current_level_id=None, version=0
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def event_by_key(self, idempotency_key: str) -> BizGrowthEvent | None:
        result = await self._session.execute(
            select(BizGrowthEvent).where(BizGrowthEvent.idempotency_key == idempotency_key)
        )
        return result.scalar_one_or_none()

    async def event_by_event_id(self, event_id: str) -> BizGrowthEvent | None:
        result = await self._session.execute(
            select(BizGrowthEvent).where(BizGrowthEvent.event_id == event_id)
        )
        return result.scalar_one_or_none()

    async def add_event(self, **fields: object) -> BizGrowthEvent:
        row = BizGrowthEvent(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def add_transaction(self, **fields: object) -> BizUserGrowthTransaction:
        row = BizUserGrowthTransaction(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def transactions(
        self, user_id: int, *, limit: int, offset: int
    ) -> tuple[list[BizUserGrowthTransaction], int]:
        total = int(
            (
                await self._session.execute(
                    select(func.count(BizUserGrowthTransaction.id)).where(
                        BizUserGrowthTransaction.user_id == user_id
                    )
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(BizUserGrowthTransaction)
                    .where(BizUserGrowthTransaction.user_id == user_id)
                    .order_by(
                        BizUserGrowthTransaction.created_at.desc(),
                        BizUserGrowthTransaction.id.desc(),
                    )
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def daily_event_count(self, user_id: int, event_code: str, *, day: datetime.date) -> int:
        start = datetime.datetime.combine(day, datetime.time.min, tzinfo=datetime.UTC)
        end = start + datetime.timedelta(days=1)
        result = await self._session.execute(
            select(func.count(BizGrowthEvent.id)).where(
                BizGrowthEvent.user_id == user_id,
                BizGrowthEvent.event_code == event_code,
                BizGrowthEvent.occurred_at >= start,
                BizGrowthEvent.occurred_at < end,
            )
        )
        return int(result.scalar_one())

    async def last_event_at(self, user_id: int, event_code: str) -> datetime.datetime | None:
        result = await self._session.execute(
            select(func.max(BizGrowthEvent.occurred_at)).where(
                BizGrowthEvent.user_id == user_id, BizGrowthEvent.event_code == event_code
            )
        )
        return result.scalar_one()

    async def enabled_rules(self) -> list[BizGrowthRule]:
        result = await self._session.execute(
            select(BizGrowthRule).where(
                BizGrowthRule.enabled.is_(True), BizGrowthRule.deleted_at.is_(None)
            )
        )
        return list(result.scalars())

    async def rule_by_event_code(self, event_code: str) -> BizGrowthRule | None:
        result = await self._session.execute(
            select(BizGrowthRule).where(
                BizGrowthRule.event_code == event_code,
                BizGrowthRule.enabled.is_(True),
                BizGrowthRule.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_rule(self, rule_id: int) -> BizGrowthRule | None:
        result = await self._session.execute(
            select(BizGrowthRule).where(
                BizGrowthRule.id == rule_id, BizGrowthRule.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()

    async def list_rules(self) -> list[BizGrowthRule]:
        result = await self._session.execute(
            select(BizGrowthRule)
            .where(BizGrowthRule.deleted_at.is_(None))
            .order_by(BizGrowthRule.id)
        )
        return list(result.scalars())

    async def levels(self) -> Sequence[BizUserLevel]:
        result = await self._session.execute(
            select(BizUserLevel)
            .where(BizUserLevel.status == "ACTIVE", BizUserLevel.deleted_at.is_(None))
            .order_by(BizUserLevel.level_no)
        )
        return result.scalars().all()
