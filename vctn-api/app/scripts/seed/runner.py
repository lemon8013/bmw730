"""Seed orchestration.

One seed run == one database transaction: if anything fails the whole run is
rolled back, so a partially initialised database is never left behind. Integrity
verification runs afterwards, in its own read-only session.
"""

from __future__ import annotations

import os
from collections.abc import Callable

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.scripts.seed.errors import (
    ADMIN_PASSWORD_REQUIRED,
    DATABASE_NOT_CONFIGURED,
    TEST_PASSWORD_REQUIRED,
    SeedError,
)
from app.scripts.seed.helpers import SeedCounter
from app.scripts.seed.report import (
    RunOutcome,
    SeedOutcome,
    collect_counts,
    summarise_counter,
    verify,
)
from app.scripts.seed.system_seed import collect_endpoints, collect_route_guards, seed_system
from app.scripts.seed.test_seed import seed_test_data
from app.shared.database.engine import build_engine
from app.shared.database.session import build_session_factory

ADMIN_PASSWORD_ENV: str = "VCTN_SEED_ADMIN_PASSWORD"
TEST_PASSWORD_ENV: str = "VCTN_SEED_TEST_PASSWORD"
DEFAULT_ADMIN_USERNAME: str = "admin"

MODE_SYSTEM: str = "system"
MODE_TEST: str = "test"


def resolve_admin_password() -> str:
    """Read the initial administrator password from the environment.

    The password is never defaulted, never hard coded and never written to the
    database in clear text.
    """
    value = os.environ.get(ADMIN_PASSWORD_ENV, "").strip()
    if not value:
        raise SeedError(
            f"the environment variable {ADMIN_PASSWORD_ENV} must be set",
            code=ADMIN_PASSWORD_REQUIRED,
        )
    return value


def resolve_test_password() -> str:
    """Read the optional test account password from the environment."""
    value = os.environ.get(TEST_PASSWORD_ENV, "").strip()
    if not value:
        raise SeedError(
            f"the environment variable {TEST_PASSWORD_ENV} must be set for --mode=test",
            code=TEST_PASSWORD_REQUIRED,
        )
    return value


async def _run_once(
    factory: async_sessionmaker[AsyncSession],
    settings: Settings,
    *,
    mode: str,
    admin_username: str,
    admin_password: str,
    test_password: str,
    index: int,
) -> RunOutcome:
    counter = SeedCounter()
    async with factory() as session:
        try:
            result = await seed_system(
                session,
                settings,
                counter,
                admin_username=admin_username,
                admin_password=admin_password,
            )
            if mode == MODE_TEST:
                await seed_test_data(
                    session,
                    settings,
                    counter,
                    department=result.department,
                    roles=result.roles,
                    password=test_password,
                )
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    return RunOutcome(
        index=index,
        created_total=counter.total_created(),
        skipped_total=counter.total_skipped(),
        created=summarise_counter(counter),
    )


async def execute(
    settings: Settings | None = None,
    *,
    mode: str = MODE_SYSTEM,
    admin_username: str = DEFAULT_ADMIN_USERNAME,
    runs: int = 1,
    progress: Callable[[str], None] | None = None,
) -> SeedOutcome:
    """Run the seed ``runs`` times and verify the result."""
    if mode not in (MODE_SYSTEM, MODE_TEST):
        raise SeedError(f"unknown mode '{mode}'", code="SEED_UNKNOWN_MODE")
    if runs < 1:
        raise SeedError("runs must be at least 1", code="SEED_INVALID_RUNS")

    resolved = settings or get_settings()
    if not resolved.is_database_configured:
        raise SeedError(
            "PostgreSQL is not configured (set DB_HOST/DB_NAME/DB_USER or DATABASE_URL)",
            code=DATABASE_NOT_CONFIGURED,
        )

    admin_password = resolve_admin_password()
    test_password = resolve_test_password() if mode == MODE_TEST else ""

    engine = build_engine(resolved)
    factory = build_session_factory(engine)
    outcome = SeedOutcome(mode=mode)
    try:
        for index in range(1, runs + 1):
            run = await _run_once(
                factory,
                resolved,
                mode=mode,
                admin_username=admin_username,
                admin_password=admin_password,
                test_password=test_password,
                index=index,
            )
            outcome.runs.append(run)
            if progress is not None:
                created_admin = run.created.get("admin", 0)
                if created_admin:
                    progress(f"Admin created: {admin_username}")
                progress(
                    f"run {index}: created={run.created_total} skipped={run.skipped_total}"
                )
        async with factory() as session:
            outcome.counts = await collect_counts(session)
            outcome.checks = await verify(
                session,
                admin_username=admin_username,
                endpoints=collect_endpoints(resolved.API_PREFIX),
                guards=collect_route_guards(resolved.API_PREFIX),
            )
    finally:
        await engine.dispose()
    return outcome


__all__ = [
    "ADMIN_PASSWORD_ENV",
    "DEFAULT_ADMIN_USERNAME",
    "MODE_SYSTEM",
    "MODE_TEST",
    "TEST_PASSWORD_ENV",
    "execute",
    "resolve_admin_password",
    "resolve_test_password",
]
