"""Redis connection factory.

Phase 0 only establishes and probes the connection. Cache, session, quota, rate
limit, distributed lock, idempotency and tool-quota keys are NOT implemented
here: their key and TTL specification is not frozen yet.
"""

from __future__ import annotations

from dataclasses import dataclass

import redis.asyncio as aioredis

from app.core.config import Settings
from app.shared.redis.client import build_redis, check_connection


@dataclass(slots=True)
class RedisFactory:
    """Creates and validates Redis clients for the application."""

    settings: Settings

    def create(self) -> aioredis.Redis:
        """Build a new Redis client."""
        return build_redis(self.settings)

    async def health_check(self, client: aioredis.Redis) -> None:
        """Raise when Redis is not reachable."""
        await check_connection(client)
