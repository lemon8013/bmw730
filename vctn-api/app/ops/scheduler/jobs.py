"""app.ops.scheduler — the periodic work itself.

Each function here is a plain coroutine that takes what it needs and returns a
counter dict. None of them know about APScheduler, so a tick can also be run
from a CLI, from a cron job or from a test without starting a scheduler.

Two properties matter in production:

* **No exception escapes.** A tick that raises takes the scheduler down with it,
  and then nothing is collected for the rest of the process lifetime.
* **No shared transaction.** Every job opens its own session so that one failing
  job cannot roll back the work of another.
"""

from __future__ import annotations

import datetime
from typing import Any
from zlib import crc32

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.ops.alerts.evaluator import AlertEvaluator
from app.ops.availability.service import AvailabilityService
from app.ops.metrics.service import MetricService
from app.ops.scheduler.lock import job_lock


def lock_id(settings: Settings, job: str) -> int:
    """Derive a stable advisory lock key for one job name.

    The configured base keeps the namespace away from any other advisory lock in
    the deployment; the offset keeps two jobs of this scheduler apart, because a
    shared key would silently merge two unrelated critical sections.
    """
    # crc32, not hash(): str hashing is randomised per process, which would
    # give every replica a different key and make the lock useless.
    return settings.OPS_SCHEDULER_LOCK_ID + (crc32(job.encode("utf-8")) % 1000)


async def rollup_metrics(
    engine: AsyncEngine,
    factory: async_sessionmaker[Any],
    settings: Settings | None = None,
    *,
    now: datetime.datetime | None = None,
) -> dict[str, int]:
    """Recompute the hourly rollup, and the daily one when the hour says so."""
    resolved = settings or get_settings()
    moment = now or datetime.datetime.now(datetime.UTC)
    daily = moment.hour == resolved.OPS_SCHEDULER_DAILY_ROLLUP_HOUR
    async with job_lock(engine, lock_id(resolved, "rollup_metrics")) as acquired:
        if not acquired:
            return {"skipped": 1}
        async with factory() as session:
            outcome = await MetricService(session, resolved).rollup(
                now=moment, hourly=True, daily=daily
            )
    get_logger().info("ops scheduler hourly rollup done buckets=%s", outcome)
    return outcome


async def evaluate_alerts(
    engine: AsyncEngine,
    factory: async_sessionmaker[Any],
    settings: Settings | None = None,
    *,
    now: datetime.datetime | None = None,
) -> dict[str, int]:
    """Run one alert evaluation pass, including notification dispatch."""
    resolved = settings or get_settings()
    moment = now or datetime.datetime.now(datetime.UTC)
    async with job_lock(engine, lock_id(resolved, "evaluate_alerts")) as acquired:
        if not acquired:
            return {"skipped": 1}
        async with factory() as session:
            # The evaluator is used directly rather than through AlertService:
            # a service evaluation requires an operator principal to audit, and
            # a scheduler tick has no operator.
            outcome = await AlertEvaluator(session).evaluate(moment)
            await session.commit()
    get_logger().info("ops scheduler alert evaluation done outcome=%s", outcome)
    return outcome


async def run_availability_probes(
    engine: AsyncEngine,
    factory: async_sessionmaker[Any],
    settings: Settings | None = None,
    *,
    now: datetime.datetime | None = None,
) -> dict[str, int]:
    """Probe every availability check whose interval has elapsed."""
    resolved = settings or get_settings()
    moment = now or datetime.datetime.now(datetime.UTC)
    async with job_lock(engine, lock_id(resolved, "run_availability_probes")) as acquired:
        if not acquired:
            return {"skipped": 1}
        async with factory() as session:
            outcome = await AvailabilityService(session, resolved).run_due_checks(moment)
    get_logger().info("ops scheduler availability probes done outcome=%s", outcome)
    return outcome


async def purge_expired_data(
    engine: AsyncEngine,
    factory: async_sessionmaker[Any],
    settings: Settings | None = None,
) -> dict[str, int]:
    """Delete monitoring data and export files past their retention window."""
    resolved = settings or get_settings()
    # Imported here rather than at module scope: the purge builds its own engine
    # from the configuration, and importing it eagerly would make every
    # scheduler start touch the database URL validation path.
    from app.scripts.cleanup import run_purge

    async with job_lock(engine, lock_id(resolved, "purge_expired_data")) as acquired:
        if not acquired:
            return {"skipped": 1}
        results = await run_purge(resolved, dry_run=False)
    deleted = sum(result.deleted for result in results)
    failed = sum(1 for result in results if result.error)
    get_logger().info(
        "ops scheduler retention purge done deleted=%s failed_tables=%s", deleted, failed
    )
    return {"deleted": deleted, "failed_tables": failed}


async def run_guarded(name: str, coroutine: Any) -> None:
    """Run one job and swallow whatever it raises.

    A periodic job failing is information, not a crash: the next tick is minutes
    away, whereas an exception escaping into APScheduler kills the scheduler and
    with it every other job in this process.
    """
    try:
        await coroutine
    except Exception as failure:  # noqa: BLE001 - deliberately broad
        get_logger().error(
            "ops scheduler job failed job=%s type=%s", name, type(failure).__name__
        )
