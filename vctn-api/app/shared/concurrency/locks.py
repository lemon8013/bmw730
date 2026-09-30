"""Concurrency primitives.

Three different tools are used, chosen per scenario as the Spec requires:

* ``SELECT ... FOR UPDATE`` for row level money/point-like balances
* optimistic locking through a ``version`` column for accounts that are read
  and written in the same request
* a Redis lock (acquired and released with Lua so the release cannot delete
  another holder's lock) for cross-process critical sections such as job
  execution or export generation

A "read then plain UPDATE" is never used to move a balance.
"""

from __future__ import annotations

import asyncio
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

import redis.asyncio as aioredis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import ConcurrencyError
from app.shared.redis.keys import lock_key

_RELEASE_SCRIPT: Final[str] = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
end
return 0
"""

_ACQUIRE_SCRIPT: Final[str] = """
if redis.call('EXISTS', KEYS[1]) == 0 then
    redis.call('SET', KEYS[1], ARGV[1], 'PX', ARGV[2])
    return 1
end
return 0
"""


@asynccontextmanager
async def redis_lock(
    client: aioredis.Redis,
    name: str,
    *,
    ttl_seconds: float | None = None,
    settings: Settings | None = None,
) -> AsyncIterator[None]:
    """Hold a Redis lock for the duration of the block.

    Raises:
        ConcurrencyError: when the lock could not be acquired in time.
    """
    resolved = settings or get_settings()
    ttl_ms = int((ttl_seconds or resolved.REDIS_LOCK_TTL_SECONDS) * 1000)
    key = lock_key(name=name)
    token = secrets.token_hex(16)
    acquired = False
    for _ in range(max(1, resolved.REDIS_LOCK_RETRY_TIMES)):
        acquired = bool(await client.eval(_ACQUIRE_SCRIPT, 1, key, token, str(ttl_ms)))
        if acquired:
            break
        await asyncio.sleep(resolved.REDIS_LOCK_RETRY_INTERVAL_SECONDS)
    if not acquired:
        raise ConcurrencyError(f"could not acquire the lock '{name}'")
    try:
        yield
    finally:
        await client.eval(_RELEASE_SCRIPT, 1, key, token)


async def select_for_update(
    session: AsyncSession,
    model: type,
    primary_key: object,
) -> object | None:
    """Lock a row for the rest of the transaction and return it."""
    result = await session.execute(select(model).where(model.id == primary_key).with_for_update())
    return result.scalar_one_or_none()


def next_version(current: int | None) -> int:
    """Return the next optimistic lock version."""
    return (current or 0) + 1


def assert_version(expected: int | None, actual: int | None) -> None:
    """Raise when an optimistic lock version moved underneath the caller."""
    if expected != actual:
        raise ConcurrencyError("the resource was modified by another request")
