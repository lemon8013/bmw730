"""app.tools.access — access policy, quota and rate limits.

A tool's lifecycle status (DRAFT/TESTING/ACTIVE/DISABLED) and its access policy
are independent: a policy can allow guests while the tool is still in testing,
and an active tool can deny everyone. Both are evaluated here.
"""

from __future__ import annotations

import datetime

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.shared.rate_limit.service import RateLimitService
from app.tools.access.model import ToolAccessPolicy
from app.tools.access.schema import ToolAccessResponse
from app.tools.catalog.model import Tool

SUBJECT_GUEST: str = "GUEST"
SUBJECT_USER: str = "USER"
ACTIVE_STATUS: str = "ACTIVE"


class ToolAccessService:
    """Resolve whether a caller may run a tool and how much of it."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        redis: aioredis.Redis | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._session = session
        self._settings = settings or get_settings()
        self._rate_limit = RateLimitService(redis, self._settings) if redis is not None else None

    async def policy_for(self, tool_id: int, subject_type: str) -> ToolAccessPolicy | None:
        result = await self._session.execute(
            select(ToolAccessPolicy).where(
                ToolAccessPolicy.tool_id == tool_id,
                ToolAccessPolicy.subject_type == subject_type,
            )
        )
        return result.scalar_one_or_none()

    async def resolve(
        self, tool_id: int, *, is_guest: bool, ip: str | None = None
    ) -> ToolAccessResponse:
        """Return the access decision for a caller."""
        tool = await self._session.get(Tool, tool_id)
        if tool is None or str(tool.status) != ACTIVE_STATUS:
            raise NotFoundError("tool is not available")

        subject_type = SUBJECT_GUEST if is_guest else SUBJECT_USER
        policy = await self.policy_for(tool_id, subject_type)
        enabled = bool(policy.enabled) if policy is not None else not is_guest
        if policy is not None and not bool(policy.enabled):
            raise BusinessRuleError("the tool is not available for this caller")

        default_quota = (
            self._settings.TOOL_GUEST_DAILY_QUOTA
            if is_guest
            else self._settings.TOOL_USER_DAILY_QUOTA
        )
        daily_limit = (
            int(policy.daily_limit)
            if policy is not None and policy.daily_limit is not None
            else default_quota
        )
        used_today = 0
        if self._rate_limit is not None:
            used_today = await self._rate_limit.remaining_quota(
                subject=subject_type.lower(),
                tool_id=tool_id,
                stat_date=datetime.datetime.now(datetime.UTC).date().isoformat(),
                limit=daily_limit,
            )
            used_today = max(0, daily_limit - used_today)

        return ToolAccessResponse(
            tool_id=str(tool_id),
            subject_type=subject_type,
            enabled=enabled,
            daily_limit=daily_limit,
            used_today=used_today,
            remaining=max(0, daily_limit - used_today),
            rate_limit_per_minute=(
                None if policy is None or policy.rate_limit_per_minute is None
                else int(policy.rate_limit_per_minute)
            ),
            concurrency_limit=(
                None if policy is None or policy.concurrency_limit is None
                else int(policy.concurrency_limit)
            ),
        )

    async def enforce_quota(
        self, tool_id: int, *, is_guest: bool, user_id: int | None, ip: str | None
    ) -> None:
        """Consume one unit of quota and enforce the per minute rate limit."""
        subject_type = SUBJECT_GUEST if is_guest else SUBJECT_USER
        policy = await self.policy_for(tool_id, subject_type)
        default_quota = (
            self._settings.TOOL_GUEST_DAILY_QUOTA
            if is_guest
            else self._settings.TOOL_USER_DAILY_QUOTA
        )
        daily_limit = (
            int(policy.daily_limit)
            if policy is not None and policy.daily_limit is not None
            else default_quota
        )
        per_minute = (
            int(policy.rate_limit_per_minute)
            if policy is not None and policy.rate_limit_per_minute is not None
            else (
                self._settings.RATE_LIMIT_TOOL_GUEST_PER_WINDOW
                if is_guest
                else self._settings.RATE_LIMIT_TOOL_USER_PER_WINDOW
            )
        )
        subject = f"{subject_type.lower()}:{user_id}" if user_id is not None else f"guest:{ip}"
        if self._rate_limit is not None:
            await self._rate_limit.enforce(
                bucket="tool", subject=subject, limit=per_minute
            )
            await self._rate_limit.consume_quota(
                subject=subject_type.lower(),
                tool_id=tool_id,
                stat_date=datetime.datetime.now(datetime.UTC).date().isoformat(),
                limit=daily_limit,
                ttl_seconds=24 * 3600,
            )
