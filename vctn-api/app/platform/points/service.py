"""app.platform.points — business logic.

A point balance is money-like: it is never moved by a plain
"read then UPDATE". The account row is locked with ``SELECT ... FOR UPDATE``, the
ledger row is written in the same transaction and the ``version`` column is
advanced, so a concurrent spend can never overdraw the account.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, ConflictError
from app.platform.growth.repository import GrowthRepository
from app.platform.points.model import BizPointTransaction, BizUserPointAccount
from app.platform.points.repository import PointRepository
from app.platform.points.schema import (
    PointAccountResponse,
    PointAdjustResponse,
    PointTransactionResponse,
)
from app.shared.audit.service import AuditService
from app.shared.ids import new_id
from app.shared.pagination.params import Page, PageParams


class PointService:
    """Point accounting."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = PointRepository(session)
        self._growth = GrowthRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def ensure_account(self, user_id: int) -> BizUserPointAccount:
        """Return the point account, creating it on first use.

        The growth account is created first because every point-bearing user is
        also a growth-bearing one. It is done through the repository primitives
        rather than ``GrowthService`` so no accounting round trip is involved.
        """
        row = await self._repository.account_for_update(user_id)
        if row is not None:
            return row
        if await self._growth.account_for_update(user_id) is None:
            await self._growth.create_account(user_id)
        return await self._repository.create_account(user_id)

    async def account(self, user_id: int) -> PointAccountResponse:
        row = await self.ensure_account(user_id)
        return PointAccountResponse(
            user_id=str(int(row.user_id)),
            balance=int(row.balance or 0),
            total_earned=int(row.total_earned or 0),
            total_spent=int(row.total_spent or 0),
            version=int(row.version or 0),
            updated_at=row.updated_at,
        )

    async def transactions(
        self, user_id: int, *, page: PageParams
    ) -> Page[PointTransactionResponse]:
        rows, total = await self._repository.transactions(
            user_id, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[self._to_transaction(row) for row in rows], total=total, params=page
        )

    async def earn(
        self,
        *,
        user_id: int,
        points: int,
        transaction_type: str = "EARN",
        source_type: str = "SYSTEM",
        source_id: str | None = None,
        reason: str | None = None,
        idempotency_key: str | None = None,
        event_code: str | None = None,
    ) -> PointTransactionResponse:
        """Add points to an account."""
        if points <= 0:
            raise BusinessRuleError("the amount to earn must be positive")
        return await self._move(
            user_id=user_id,
            delta=points,
            transaction_type=transaction_type,
            source_type=source_type,
            source_id=source_id,
            reason=reason,
            idempotency_key=idempotency_key,
            event_code=event_code,
        )

    async def spend(
        self,
        *,
        user_id: int,
        points: int,
        transaction_type: str = "SPEND",
        source_type: str = "SYSTEM",
        source_id: str | None = None,
        reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> PointTransactionResponse:
        """Subtract points from an account, refusing an overdraft."""
        if points <= 0:
            raise BusinessRuleError("the amount to spend must be positive")
        return await self._move(
            user_id=user_id,
            delta=-points,
            transaction_type=transaction_type,
            source_type=source_type,
            source_id=source_id,
            reason=reason,
            idempotency_key=idempotency_key,
        )

    async def adjust(
        self,
        *,
        actor_id: int,
        actor_username: str,
        user_id: int,
        delta_points: int,
        reason: str,
        ip: str | None = None,
        user_agent: str | None = None,
    ) -> PointAdjustResponse:
        """Administrative adjustment, always audited."""
        if delta_points == 0:
            raise BusinessRuleError("the adjustment must not be zero")
        transaction = await self._move(
            user_id=user_id,
            delta=delta_points,
            transaction_type="EARN" if delta_points > 0 else "SPEND",
            source_type="ADMIN",
            source_id=str(actor_id),
            reason=reason,
            idempotency_key=None,
        )
        await self._audit.record(
            self._session,
            action="USER_POINT_ADJUST",
            operator_id=actor_id,
            operator_username=actor_username,
            resource_type="biz_user_point_account",
            resource_id=user_id,
            after_data={
                "delta_points": delta_points,
                "balance": transaction.balance_after,
                "reason": reason,
            },
            ip=ip,
            user_agent=user_agent,
        )
        await self._session.commit()
        return PointAdjustResponse(
            user_id=str(user_id),
            delta_points=delta_points,
            balance=transaction.balance_after,
            transaction_id=transaction.id,
        )

    async def _move(
        self,
        *,
        user_id: int,
        delta: int,
        transaction_type: str,
        source_type: str,
        source_id: str | None,
        reason: str | None,
        idempotency_key: str | None,
        event_code: str | None = None,
    ) -> PointTransactionResponse:
        key = idempotency_key or f"{source_type}:{source_id}:{transaction_type}:{uuid.uuid4().hex}"
        existing = await self._repository.transaction_by_key(key)
        if existing is not None:
            return self._to_transaction(existing)

        account = await self.ensure_account(user_id)
        if event_code:
            rule = await self._repository.enabled_rule_for(event_code)
            if rule is not None and rule.daily_limit is not None:
                used = await self._repository.daily_count(
                    user_id, event_code, day=datetime.datetime.now(datetime.UTC).date()
                )
                if used >= int(rule.daily_limit):
                    raise BusinessRuleError(f"the daily limit for '{event_code}' has been reached")
        balance = int(account.balance or 0) + delta
        if balance < 0:
            raise ConflictError("the point balance is insufficient")

        account.balance = balance
        account.total_earned = int(account.total_earned or 0) + (delta if delta > 0 else 0)
        account.total_spent = int(account.total_spent or 0) + (-delta if delta < 0 else 0)
        account.version = int(account.version or 0) + 1
        row = await self._repository.add_transaction(
            id=new_id(),
            user_id=user_id,
            event_id=str(uuid.uuid4().hex),
            idempotency_key=key,
            delta_points=delta,
            balance_after=balance,
            transaction_type=transaction_type,
            source_type=source_type,
            source_id=source_id,
            reason=reason,
            metadata={"event_code": event_code} if event_code else None,
        )
        await self._session.flush()
        return self._to_transaction(row)

    def _to_transaction(self, row: BizPointTransaction) -> PointTransactionResponse:
        return PointTransactionResponse(
            id=str(int(row.id)),
            user_id=str(int(row.user_id)),
            event_id=row.event_id,
            delta_points=int(row.delta_points),
            balance_after=int(row.balance_after),
            transaction_type=str(row.transaction_type),
            source_type=row.source_type,
            source_id=row.source_id,
            reason=row.reason,
            created_at=row.created_at,
        )
