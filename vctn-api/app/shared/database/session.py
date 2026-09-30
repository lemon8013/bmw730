"""Async session factory and session scope.

The service layer owns the transaction boundary; repositories never commit.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


def build_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Create the async session factory bound to the given engine."""
    return async_sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)


@asynccontextmanager
async def session_scope(
    factory: async_sessionmaker[AsyncSession],
) -> AsyncIterator[AsyncSession]:
    """Yield a session for the duration of a unit of work."""
    async with factory() as session:
        yield session
