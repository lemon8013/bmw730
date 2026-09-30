"""FastAPI dependencies.

Infrastructure-level dependencies only. Permission enforcement must go through
the authorization layer once it exists; Phase 0 does not provide one.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.exceptions import ServiceUnavailableError


def get_app_settings() -> Settings:
    """Return the process wide settings."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


def get_engine(request: Request) -> AsyncEngine:
    """Return the engine bound to the running application."""
    engine: AsyncEngine | None = getattr(request.app.state, "engine", None)
    if engine is None:
        raise ServiceUnavailableError("database is not configured")
    return engine


def get_redis(request: Request) -> aioredis.Redis:
    """Return the Redis client bound to the running application."""
    client: aioredis.Redis | None = getattr(request.app.state, "redis", None)
    if client is None:
        raise ServiceUnavailableError("redis is not configured")
    return client


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    """Yield a database session; the service layer owns the transaction."""
    factory: async_sessionmaker[AsyncSession] | None = getattr(
        request.app.state, "session_factory", None
    )
    if factory is None:
        raise ServiceUnavailableError("database is not configured")
    async with factory() as session:
        yield session


EngineDep = Annotated[AsyncEngine, Depends(get_engine)]
RedisDep = Annotated[aioredis.Redis, Depends(get_redis)]
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
