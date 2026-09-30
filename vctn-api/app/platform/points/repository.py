"""app.platform.points — data access."""

from __future__ import annotations

import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.points.model import (
    BizPointRule,
    BizPointTransaction,
    BizUserPointAccount,
)


class PointRepository:
    """Data access for point accounts, the ledger and point rules."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def account_for_update(self, user_id: int) -> BizUserPointAccount | None:
        result = await self._session.execute(
            select(BizUserPointAccount)
            .where(BizUserPointAccount.user_id == user_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def account(self, user_id: int) -> BizUserPointAccount | None:
        return await self._session.get(BizUserPointAccount, user_id)

    async def create_account(self, user_id: int) -> BizUserPointAccount:
        row = BizUserPointAccount(
            user_id=user_id, balance=0, total_earned=0, total_spent=0, version=0
        )
        self._session.add(row)
        await self._session.flush()
        return row

    async def transaction_by_key(self, idempotency_key: str) -> BizPointTransaction | None:
        result = await self._session.execute(
            select(BizPointTransaction).where(
                BizPointTransaction.idempotency_key == idempotency_key
            )
        )
        return result.scalar_one_or_none()

    async def add_transaction(self, **fields: object) -> BizPointTransaction:
        row = BizPointTransaction(**fields)  # type: ignore[arg-type]
        self._session.add(row)
        await self._session.flush()
        return row

    async def transactions(
        self, user_id: int, *, limit: int, offset: int
    ) -> tuple[list[BizPointTransaction], int]:
        total = int(
            (
                await self._session.execute(
                    select(func.count(BizPointTransaction.id)).where(
                        BizPointTransaction.user_id == user_id
                    )
                )
            ).scalar_one()
        )
        rows = (
            (
                await self._session.execute(
                    select(BizPointTransaction)
                    .where(BizPointTransaction.user_id == user_id)
                    .order_by(BizPointTransaction.created_at.desc(), BizPointTransaction.id.desc())
                    .limit(limit)
                    .offset(offset)
                )
            )
            .scalars()
            .all()
        )
        return list(rows), total

    async def daily_count(self, user_id: int, event_code: str, *, day: datetime.date) -> int:
        start = datetime.datetime.combine(day, datetime.time.min, tzinfo=datetime.UTC)
        end = start + datetime.timedelta(days=1)
        result = await self._session.execute(
            select(func.count(BizPointTransaction.id)).where(
                BizPointTransaction.user_id == user_id,
                BizPointTransaction.source_type == event_code,
                BizPointTransaction.created_at >= start,
                BizPointTransaction.created_at < end,
                BizPointTransaction.delta_points > 0,
            )
        )
        return int(result.scalar_one())

    async def list_rules(self) -> list[BizPointRule]:
        result = await self._session.execute(
            select(BizPointRule).where(BizPointRule.deleted_at.is_(None)).order_by(BizPointRule.id)
        )
        return list(result.scalars())

    async def enabled_rule_for(self, event_code: str) -> BizPointRule | None:
        result = await self._session.execute(
            select(BizPointRule).where(
                BizPointRule.event_code == event_code,
                BizPointRule.enabled.is_(True),
                BizPointRule.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_rule(self, rule_id: int) -> BizPointRule | None:
        result = await self._session.execute(
            select(BizPointRule).where(
                BizPointRule.id == rule_id, BizPointRule.deleted_at.is_(None)
            )
        )
        return result.scalar_one_or_none()
