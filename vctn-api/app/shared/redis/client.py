"""Async Redis client factory and connectivity probe."""

from __future__ import annotations

import redis.asyncio as aioredis

from app.core.config import Settings


def build_redis(settings: Settings) -> aioredis.Redis:
    """Create the async Redis client from settings.

    Raises:
        ValueError: when REDIS_URL is not configured.
    """
    url = settings.REDIS_URL.strip()
    if not url:
        raise ValueError("REDIS_URL is not configured")
    return aioredis.from_url(url, encoding="utf-8", decode_responses=True)


async def check_connection(client: aioredis.Redis) -> None:
    """Send a PING to prove Redis is reachable."""
    await client.ping()
