"""Async SQLAlchemy engine factory and connectivity probe."""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings


def build_engine(settings: Settings) -> AsyncEngine:
    """Create the async engine from settings.

    Raises:
        ValueError: when DATABASE_URL is not configured.
    """
    url = settings.DATABASE_URL.strip()
    if not url:
        raise ValueError("DATABASE_URL is not configured")
    return create_async_engine(
        url,
        echo=settings.APP_DEBUG,
        pool_pre_ping=True,
    )


async def check_connection(engine: AsyncEngine) -> None:
    """Execute a trivial statement to prove the database is reachable."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
