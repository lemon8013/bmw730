"""Rate limiting backed by Redis.

The counter and its expiry are moved in a single Lua script: an ``INCR``
followed by a separate ``EXPIRE`` can lose the ``EXPIRE`` when the process dies
in between and leave a key that blocks the caller forever. The script performs
both steps atomically.

The exact limits are not frozen by the Spec; every limit is configuration.

Fail-open by contract: this service is reached through ``OptionalRedisDep``,
whose documented promise is that an endpoint must still serve its business
purpose when Redis is unavailable. A broken Redis therefore degrades to "no
limit" — a warning is logged — instead of turning every guarded endpoint,
including registration and login, into a 500.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import redis.asyncio as aioredis

from app.core.config import Settings, get_settings
from app.core.exceptions import QuotaExceededError, RateLimitError
from app.shared.redis.keys import quota_key, rate_limit_key

logger = logging.getLogger(__name__)

_CONSUME_SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then
    redis.call('PEXPIRE', KEYS[1], ARGV[1])
end
return current
"""


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    """Outcome of a rate limit check."""

    allowed: bool
    current: int
    limit: int
    remaining: int


class RateLimitService:
    """Fixed window rate limiting with atomic Redis increments."""

    def __init__(self, client: aioredis.Redis, settings: Settings | None = None) -> None:
        self._client = client
        self._settings = settings or get_settings()

    @property
    def enabled(self) -> bool:
        return self._settings.RATE_LIMIT_ENABLED

    async def _consume(self, key: str, ttl_ms: int) -> int | None:
        """Run the consume script, returning ``None`` when Redis is unusable.

        Only the bucket name is logged — never the key, which embeds the
        subject (an IP or a user id).
        """
        try:
            return int(await self._client.eval(_CONSUME_SCRIPT, 1, key, str(ttl_ms)))
        except (aioredis.RedisError, OSError) as failure:
            logger.warning(
                "rate limit backend unavailable, failing open: %s", type(failure).__name__
            )
            return None

    async def _read(self, key: str) -> int | None:
        """Read a counter, returning ``None`` when Redis is unusable."""
        try:
            raw = await self._client.get(key)
        except (aioredis.RedisError, OSError) as failure:
            logger.warning(
                "rate limit backend unavailable, failing open: %s", type(failure).__name__
            )
            return None
        return int(raw) if raw else 0

    async def check(
        self,
        *,
        bucket: str,
        subject: str,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> RateLimitDecision:
        """Consume one unit and report whether the caller stays within limits."""
        resolved_limit = limit if limit is not None else self._settings.RATE_LIMIT_API_PER_WINDOW
        window = window_seconds or self._settings.RATE_LIMIT_WINDOW_SECONDS
        if not self.enabled:
            return RateLimitDecision(True, 0, resolved_limit, resolved_limit)

        key = rate_limit_key(bucket=bucket, subject=subject)
        current = await self._consume(key, int(window * 1000))
        if current is None:
            # Redis is down: allow, and report a full window rather than a
            # fabricated count the caller could mistake for real usage.
            return RateLimitDecision(True, 0, resolved_limit, resolved_limit)
        allowed = current <= resolved_limit
        return RateLimitDecision(
            allowed=allowed,
            current=current,
            limit=resolved_limit,
            remaining=max(0, resolved_limit - current),
        )

    async def enforce(
        self,
        *,
        bucket: str,
        subject: str,
        limit: int | None = None,
        window_seconds: int | None = None,
    ) -> RateLimitDecision:
        """Consume one unit and raise when the caller exceeds the limit."""
        decision = await self.check(
            bucket=bucket, subject=subject, limit=limit, window_seconds=window_seconds
        )
        if not decision.allowed:
            raise RateLimitError(
                f"rate limit exceeded for '{bucket}'",
                data={
                    "limit": decision.limit,
                    "window_seconds": window_seconds or self._settings.RATE_LIMIT_WINDOW_SECONDS,
                },
            )
        return decision

    async def consume_quota(
        self,
        *,
        subject: str,
        tool_id: int,
        stat_date: str,
        limit: int,
        ttl_seconds: int,
    ) -> int:
        """Consume one unit of a daily quota and return the used amount.

        Raises:
            QuotaExceededError: when the daily quota is exhausted.
        """
        key = quota_key(subject=subject, tool_id=tool_id, stat_date=stat_date)
        used = await self._consume(key, int(ttl_seconds * 1000))
        if used is None:
            return 0
        if used > limit:
            # Give the unit back so a rejected caller does not burn quota.
            try:
                await self._client.decr(key)
            except (aioredis.RedisError, OSError):
                logger.warning("could not return the rejected quota unit")
            raise QuotaExceededError(f"daily quota of {limit} executions is exhausted")
        return used

    async def remaining_quota(
        self, *, subject: str, tool_id: int, stat_date: str, limit: int
    ) -> int:
        """Return how many units of the daily quota are left."""
        key = quota_key(subject=subject, tool_id=tool_id, stat_date=stat_date)
        used = await self._read(key)
        if used is None:
            return max(0, limit)
        return max(0, limit - used)
