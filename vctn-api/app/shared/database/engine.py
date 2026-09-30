"""Async SQLAlchemy engine factory and connectivity probe.

Every engine option (pool sizing, timeouts, echo) comes from
:class:`app.core.config.Settings`; nothing is hard coded here.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings


def build_engine(settings: Settings) -> AsyncEngine:
    """Create the async engine from settings.

    Raises:
        ValueError: when the PostgreSQL connection is not configured.
    """
    url = settings.database_url
    if not url:
        raise ValueError(
            "PostgreSQL is not configured: set DB_HOST/DB_NAME/DB_USER or DATABASE_URL"
        )
    return create_async_engine(
        url,
        echo=settings.resolved_db_echo,
        pool_pre_ping=settings.DB_POOL_PRE_PING,
        pool_size=settings.DB_POOL_SIZE,
        max_overflow=settings.DB_MAX_OVERFLOW,
        pool_timeout=settings.DB_POOL_TIMEOUT_SECONDS,
        pool_recycle=settings.DB_POOL_RECYCLE_SECONDS,
    )


async def check_connection(engine: AsyncEngine) -> None:
    """Execute a trivial statement to prove the database is reachable."""
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
