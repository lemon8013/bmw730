"""Alembic environment.

``target_metadata`` is ``Base.metadata`` from the ORM models, which are the
Python mirror of the frozen PostgreSQL DDL baseline. Importing the model
registry here guarantees every table is registered before Alembic compares the
metadata against the database.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Importing the registry populates Base.metadata with all 79 tables.
import app.shared.database.models  # noqa: F401
from app.core.config import get_settings
from app.shared.database.base import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

_settings = get_settings()
if not _settings.is_database_configured:
    missing = _settings.missing_database_fields
    detail = f"; missing: {', '.join(missing)}" if missing else ""
    raise RuntimeError(
        "PostgreSQL is not configured. Fill DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD "
        f"(or DATABASE_URL) in vctn-api/.env{detail}"
    )

# Escape percent signs: configparser would otherwise interpolate them.
config.set_main_option("sqlalchemy.url", _settings.database_url.replace("%", "%%"))


def run_migrations_offline() -> None:
    """Run migrations without a live connection."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations through an async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations against a live database."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
