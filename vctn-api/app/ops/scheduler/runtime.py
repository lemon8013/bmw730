"""app.ops.scheduler — APScheduler wiring.

The scheduler lives inside the API process: a separate worker process would be
one more thing to deploy, supervise and keep in lockstep with the code that
owns the tables. That choice has one consequence worth stating out loud — **if
you scale the API to N replicas, N schedulers start**. Every job therefore takes
an advisory lock first (see :mod:`app.ops.scheduler.lock`), so the extra
replicas skip instead of duplicating work.

It is off unless ``OPS_SCHEDULER_ENABLED`` is set, because a deployment that
silently starts writing on its own is worse than one that does nothing.
"""

from __future__ import annotations

import datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.ops.scheduler import jobs


class OpsScheduler:
    """Registers and owns the periodic ops jobs."""

    def __init__(
        self,
        settings: Settings,
        engine: AsyncEngine,
        factory: async_sessionmaker[Any],
    ) -> None:
        self._settings = settings
        self._engine = engine
        self._factory = factory
        self._scheduler: AsyncIOScheduler | None = None

    @property
    def running(self) -> bool:
        return self._scheduler is not None

    def start(self) -> bool:
        """Register every job and start the scheduler.

        Returns ``False`` when it stays stopped, which is the normal case in
        development: no configuration, no surprise writes.
        """
        if not self._settings.OPS_SCHEDULER_ENABLED:
            return False
        if self._scheduler is not None:
            return True

        scheduler = AsyncIOScheduler(timezone=datetime.UTC)
        common = {"max_instances": 1, "coalesce": True, "misfire_grace_time": 300}
        scheduler.add_job(
            self._run(jobs.rollup_metrics),
            IntervalTrigger(minutes=self._settings.OPS_SCHEDULER_ROLLUP_INTERVAL_MINUTES),
            id="ops_rollup_metrics",
            name="Hourly and daily metric rollup",
            replace_existing=True,
            **common,
        )
        scheduler.add_job(
            self._run(jobs.evaluate_alerts),
            IntervalTrigger(seconds=self._settings.OPS_SCHEDULER_ALERT_INTERVAL_SECONDS),
            id="ops_alert_evaluation",
            name="Alert rule evaluation and notification dispatch",
            replace_existing=True,
            **common,
        )
        scheduler.add_job(
            self._run(jobs.run_availability_probes),
            IntervalTrigger(seconds=self._settings.OPS_SCHEDULER_PROBE_INTERVAL_SECONDS),
            id="ops_availability_probes",
            name="Availability probes",
            replace_existing=True,
            **common,
        )
        # A fixed hour, not "every 24 hours from boot": a retention purge that
        # drifts into business hours because the container restarted at 15:47 is
        # a self-inflicted incident.
        scheduler.add_job(
            self._run(jobs.purge_expired_data),
            CronTrigger(
                hour=self._settings.OPS_SCHEDULER_PURGE_HOUR, minute=0, timezone=datetime.UTC
            ),
            id="ops_retention_purge",
            name="Retention purge",
            replace_existing=True,
            **common,
        )
        scheduler.start()
        self._scheduler = scheduler
        get_logger().info(
            "ops scheduler started jobs=%s",
            ",".join(sorted(job.id for job in scheduler.get_jobs())),
        )
        return True

    def _run(self, job: Any) -> Any:
        """Bind the infrastructure arguments and make failures non fatal."""
        settings = self._settings

        async def _wrapped() -> None:
            await jobs.run_guarded(job.__name__, job(self._engine, self._factory, settings))

        _wrapped.__name__ = job.__name__
        return _wrapped

    def shutdown(self) -> None:
        """Stop the scheduler without waiting for a running job."""
        if self._scheduler is None:
            return
        self._scheduler.shutdown(wait=False)
        self._scheduler = None
        get_logger().info("ops scheduler stopped")


def build_scheduler(
    settings: Settings | None, engine: AsyncEngine, factory: async_sessionmaker[Any]
) -> OpsScheduler:
    """Build the scheduler for the current process."""
    return OpsScheduler(settings or get_settings(), engine, factory)
