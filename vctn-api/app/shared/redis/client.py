"""Async Redis client factory and connectivity probe.

Encoding, response decoding and pooling options come from
:class:`app.core.config.Settings`; nothing is hard coded here.
"""

from __future__ import annotations

from typing import Any

import redis.asyncio as aioredis

from app.core.config import Settings


def build_redis(settings: Settings) -> aioredis.Redis:
    """Create the async Redis client from settings.

    Raises:
        ValueError: when the Redis connection is not configured.
    """
    url = settings.redis_url
    if not url:
        raise ValueError("Redis is not configured: set REDIS_HOST or REDIS_URL")

    options: dict[str, Any] = {
        "encoding": settings.REDIS_ENCODING,
        "decode_responses": settings.REDIS_DECODE_RESPONSES,
    }
    # ``None`` keeps the redis library default for the remaining knobs.
    if settings.REDIS_MAX_CONNECTIONS is not None:
        options["max_connections"] = settings.REDIS_MAX_CONNECTIONS
    if settings.REDIS_SOCKET_TIMEOUT_SECONDS is not None:
        options["socket_timeout"] = settings.REDIS_SOCKET_TIMEOUT_SECONDS

    return aioredis.from_url(url, **options)


async def check_connection(client: aioredis.Redis) -> None:
    """Send a PING to prove Redis is reachable."""
    await client.ping()
