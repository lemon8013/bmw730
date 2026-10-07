"""app.ops.scheduler — one replica runs a tick, the others skip it.

Every periodic job writes to the same database. Running the same rollup or the
same retention purge from two replicas at once wastes work at best and produces
double counting at worst, so each tick first takes a PostgreSQL advisory lock:

* the lock is **session scoped** and held on a connection of its own for the
  whole tick, so a crash releases it automatically when the connection drops;
* it is taken with ``pg_try_advisory_lock``, never the blocking variant — a
  replica that loses the race skips the tick instead of queueing behind it;
* on any other backend (SQLite in tests) there is nothing to coordinate, so the
  lock reports "acquired" and leaves the caller's behaviour unchanged.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@asynccontextmanager
async def job_lock(engine: AsyncEngine, lock_id: int) -> AsyncIterator[bool]:
    """Hold an advisory lock for the duration of the block.

    Yields ``True`` when this process owns the tick and ``False`` when another
    replica already does. The caller must treat ``False`` as "skip", never as
    "run anyway".
    """
    if engine.dialect.name != "postgresql":
        yield True
        return

    async with engine.connect() as connection:
        acquired = bool(
            (
                await connection.execute(
                    text("SELECT pg_try_advisory_lock(:lock_id)"), {"lock_id": lock_id}
                )
            ).scalar()
        )
        try:
            yield acquired
        finally:
            if acquired:
                await connection.execute(
                    text("SELECT pg_advisory_unlock(:lock_id)"), {"lock_id": lock_id}
                )
