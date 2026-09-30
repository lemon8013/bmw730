"""app.platform.growth — business logic.

Only this service may move a growth balance. Every other module raises an event
and lets :meth:`GrowthService.apply_event` do the accounting, which is what keeps
"business module must not UPDATE biz_user_growth_account" enforceable.

Concurrency: the account row is locked with ``SELECT ... FOR UPDATE`` and the
``version`` column is advanced, so two concurrent events can never both write a
balance computed from the same starting value.
"""

from __future__ import annotations

import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError
from app.platform.growth.model import BizUserGrowthAccount
from app.platform.growth.repository import GrowthRepository
from app.platform.growth.schema import (
    GrowthAccountResponse,
    GrowthEventResponse,
    GrowthTransactionResponse,
)
from app.platform.levels.model import BizUserLevel
from app.shared.audit.service import AuditService
from app.shared.events.codes import GrowthEventCode, OutboxEventType
from app.shared.ids import new_id
from app.shared.outbox.service import OutboxService
from app.shared.pagination.params import Page, PageParams


class GrowthService:
    """Growth accounting and level recalculation."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = GrowthRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)
        self._outbox = OutboxService(self._settings)

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------
    async def ensure_account(self, user_id: int) -> BizUserGrowthAccount:
        """Return the growth account, creating it on first use."""
        row = await self._repository.account_for_update(user_id)
        if row is None:
            row = await self._repository.create_account(user_id)
        return row

    async def account(self, user_id: int) -> GrowthAccountResponse:
        """Return the growth account of a user with its level context."""
        row = await self.ensure_account(user_id)
        levels = list(await self._repository.levels())
        current = _level_by_id(levels, row.current_level_id)
        next_level = _next_level(levels, int(row.total_growth_points or 0))
        return GrowthAccountResponse(
            user_id=str(int(row.user_id)),
            total_growth_points=int(row.total_growth_points or 0),
            current_level_id=None
            if row.current_level_id is None
            else str(int(row.current_level_id)),
            current_level_name=None if current is None else str(current.level_name),
            current_level_no=None if current is None else int(current.level_no),
            next_level_id=None if next_level is None else str(int(next_level.id)),
            next_level_name=None if next_level is None else str(next_level.level_name),
            next_level_points_required=(
                None
                if next_level is None
                else int(next_level.min_growth_points) - int(row.total_growth_points or 0)
            ),
            version=int(row.version or 0),
            updated_at=row.updated_at,
        )

    async def transactions(
        self, user_id: int, *, page: PageParams
    ) -> Page[GrowthTransactionResponse]:
        rows, total = await self._repository.transactions(
            user_id, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[
                GrowthTransactionResponse(
                    id=str(int(row.id)),
                    user_id=str(int(row.user_id)),
                    event_id=None if row.event_id is None else str(row.event_id),
                    delta_points=int(row.delta_points),
                    balance_after=int(row.balance_after),
                    transaction_type=str(row.transaction_type),
                    reason=row.reason,
                    created_at=row.created_at,
                )
                for row in rows
            ],
            total=total,
            params=page,
        )

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------
    async def apply_event(
        self,
        *,
        user_id: int,
        event_code: str,
        growth_points: int | None = None,
        source_type: str = "SYSTEM",
        source_id: str | None = None,
        reason: str | None = None,
        event_id: str | None = None,
        idempotency_key: str | None = None,
        occurred_at: datetime.datetime | None = None,
        operator_id: int | None = None,
    ) -> GrowthEventResponse:
        """Apply one growth event.

        The event is guarded twice: by ``event_id`` (unique) and by
        ``idempotency_key`` (unique), so a repeated reward is impossible even
        when the same event arrives from two different modules.
        """
        now = occurred_at or datetime.datetime.now(datetime.UTC)
        resolved_event_id = event_id or uuid.uuid4().hex
        resolved_key = (
            idempotency_key or f"{event_code}:{source_type}:{source_id}:{resolved_event_id}"
        )

        existing = await self._repository.event_by_key(resolved_key)
        if existing is None and event_id:
            existing = await self._repository.event_by_event_id(resolved_event_id)
        if existing is not None:
            account = await self.ensure_account(user_id)
            return GrowthEventResponse(
                event_id=str(existing.event_id),
                idempotency_key=str(existing.idempotency_key),
                user_id=str(user_id),
                event_code=str(existing.event_code),
                applied_points=int(existing.growth_points),
                total_growth_points=int(account.total_growth_points or 0),
                level_changed=False,
                created_duplicate=True,
            )

        points = await self._resolve_points(user_id, event_code, growth_points, now=now)
        event = await self._repository.add_event(
            id=new_id(),
            event_id=resolved_event_id,
            idempotency_key=resolved_key,
            user_id=user_id,
            event_code=event_code,
            source_type=source_type,
            source_id=source_id,
            growth_points=points,
            metadata={"reason": reason} if reason else None,
            occurred_at=now,
        )

        account = await self.ensure_account(user_id)
        balance = int(account.total_growth_points or 0) + points
        account.total_growth_points = balance
        account.version = int(account.version or 0) + 1
        await self._repository.add_transaction(
            id=new_id(),
            user_id=user_id,
            event_id=int(event.id),
            delta_points=points,
            balance_after=balance,
            transaction_type="EARN",
            reason=reason or event_code,
        )
        level_changed = await self._recalculate_level(user_id, balance, reason=reason)
        await self._session.flush()

        if operator_id is not None:
            await self._audit.record(
                self._session,
                action="USER_GROWTH_ADJUST",
                operator_id=operator_id,
                resource_type="biz_user_growth_account",
                resource_id=user_id,
                after_data={"event_code": event_code, "points": points, "balance": balance},
            )
        return GrowthEventResponse(
            event_id=str(event.event_id),
            idempotency_key=str(event.idempotency_key),
            user_id=str(user_id),
            event_code=event_code,
            applied_points=points,
            total_growth_points=balance,
            level_changed=level_changed,
            created_duplicate=False,
        )

    async def _resolve_points(
        self,
        user_id: int,
        event_code: str,
        growth_points: int | None,
        *,
        now: datetime.datetime,
    ) -> int:
        """Resolve the awarded points from the matching growth rule."""
        rule = await self._repository.rule_by_event_code(event_code)
        if rule is None:
            if growth_points is None:
                raise BusinessRuleError(f"no growth rule is defined for '{event_code}'")
            return int(growth_points)

        points = int(rule.growth_points)
        if rule.daily_limit is not None:
            used = await self._repository.daily_event_count(user_id, event_code, day=now.date())
            if used >= int(rule.daily_limit):
                raise BusinessRuleError(f"the daily limit for '{event_code}' has been reached")
        if rule.cooldown_seconds:
            last = await self._repository.last_event_at(user_id, event_code)
            if last is not None:
                elapsed = (now - last).total_seconds()
                if elapsed < int(rule.cooldown_seconds):
                    raise BusinessRuleError(f"'{event_code}' is still in its cooldown period")
        return points

    # ------------------------------------------------------------------
    # Levels
    # ------------------------------------------------------------------
    async def _recalculate_level(
        self, user_id: int, total_points: int, *, reason: str | None = None
    ) -> bool:
        """Move the user to the level their growth points now qualify for."""
        levels = list(await self._repository.levels())
        if not levels:
            return False
        target = _level_for_points(levels, total_points)
        account = await self._repository.account_for_update(user_id)
        if account is None:  # pragma: no cover - ensure_account runs before
            return False
        if account.current_level_id is not None and target is not None:
            if int(account.current_level_id) == int(target.id):
                return False
        if account.current_level_id is None and target is None:
            return False

        from app.platform.levels.repository import LevelRepository

        levels_repo = LevelRepository(self._session)
        await levels_repo.add_history(
            id=new_id(),
            user_id=user_id,
            from_level_id=account.current_level_id,
            to_level_id=None if target is None else int(target.id),
            growth_points=total_points,
            reason=reason or "GROWTH_RECALCULATE",
        )
        previous = account.current_level_id
        account.current_level_id = None if target is None else int(target.id)
        await self._session.flush()
        await self._outbox.publish(
            self._session,
            event_type=OutboxEventType.LEVEL_CHANGED,
            aggregate_type="biz_user",
            aggregate_id=user_id,
            payload={
                "user_id": user_id,
                "from_level_id": None if previous is None else str(int(previous)),
                "to_level_id": None if target is None else str(int(target.id)),
                "total_growth_points": total_points,
            },
        )
        return True

    async def recalculate(self, user_id: int) -> GrowthAccountResponse:
        """Recompute the level of a user from its current growth points."""
        account = await self.ensure_account(user_id)
        await self._recalculate_level(
            user_id, int(account.total_growth_points or 0), reason="MANUAL_RECALCULATE"
        )
        await self._session.commit()
        return await self.account(user_id)

    # ------------------------------------------------------------------
    # Outbox consumers
    # ------------------------------------------------------------------
    async def consume_tool_executed(self, payload: dict) -> None:
        """Award growth for a successful tool execution."""
        user_id = int(payload["user_id"])
        if user_id <= 0:
            return
        await self.apply_event(
            user_id=user_id,
            event_code=GrowthEventCode.TOOL_EXECUTION_SUCCESS,
            source_type="TOOL",
            source_id=str(payload.get("tool_id", "")),
            idempotency_key=f"tool:{payload.get('usage_event_id')}",
        )
        await self._session.commit()

    async def consume_blog_published(self, payload: dict) -> None:
        """Award growth for publishing an article."""
        await self.apply_event(
            user_id=int(payload["author_user_id"]),
            event_code=GrowthEventCode.BLOG_ARTICLE_PUBLISHED,
            source_type="BLOG",
            source_id=str(payload.get("article_id", "")),
            idempotency_key=f"blog-published:{payload.get('article_id')}",
        )
        await self._session.commit()

    async def consume_blog_comment(self, payload: dict) -> None:
        """Award growth for writing a comment."""
        await self.apply_event(
            user_id=int(payload["user_id"]),
            event_code=GrowthEventCode.BLOG_COMMENT_CREATED,
            source_type="BLOG",
            source_id=str(payload.get("comment_id", "")),
            idempotency_key=f"blog-comment:{payload.get('comment_id')}",
        )
        await self._session.commit()

    async def consume_blog_like_received(self, payload: dict) -> None:
        """Award growth to the author that received a like."""
        await self.apply_event(
            user_id=int(payload["author_user_id"]),
            event_code=GrowthEventCode.BLOG_LIKE_RECEIVED,
            source_type="BLOG",
            source_id=str(payload.get("article_id", "")),
            idempotency_key=(f"blog-like:{payload.get('article_id')}:{payload.get('user_id')}"),
        )
        await self._session.commit()

    async def consume_daily_login(self, payload: dict) -> None:
        """Award growth for the first login of a day."""
        await self.apply_event(
            user_id=int(payload["user_id"]),
            event_code=GrowthEventCode.DAILY_LOGIN,
            source_type="AUTH",
            source_id=payload.get("stat_date", ""),
            idempotency_key=f"daily-login:{payload.get('user_id')}:{payload.get('stat_date')}",
        )
        await self._session.commit()

    async def consume_register(self, payload: dict) -> None:
        """Create the account and award the registration bonus, if configured."""
        user_id = int(payload["user_id"])
        await self.ensure_account(user_id)
        rule = await self._repository.rule_by_event_code(GrowthEventCode.USER_REGISTER)
        if rule is not None:
            await self.apply_event(
                user_id=user_id,
                event_code=GrowthEventCode.USER_REGISTER,
                source_type="AUTH",
                source_id=str(user_id),
                idempotency_key=f"register:{user_id}",
            )
        await self._session.commit()


def _level_by_id(levels: list[BizUserLevel], level_id: object | None) -> BizUserLevel | None:
    if level_id is None:
        return None
    for row in levels:
        if int(row.id) == int(level_id):  # type: ignore[arg-type]
            return row
    return None


def _level_for_points(levels: list[BizUserLevel], points: int) -> BizUserLevel | None:
    chosen: BizUserLevel | None = None
    for row in levels:
        if int(row.min_growth_points) <= points:
            chosen = row
    return chosen


def _next_level(levels: list[BizUserLevel], points: int) -> BizUserLevel | None:
    for row in levels:
        if int(row.min_growth_points) > points:
            return row
    return None
