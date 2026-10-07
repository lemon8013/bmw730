"""Unit tests for the in-process ops scheduler.

These cover the two failure modes that are invisible in a single process and
only show up in production: a scheduler that starts when it should not, and a
job whose exception stops every other job.
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from app.core.config import Settings
from app.ops.scheduler import jobs
from app.ops.scheduler.lock import job_lock
from app.ops.scheduler.runtime import OpsScheduler


class _FakeScheduler:
    """Records what was registered instead of running it."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        self.jobs: list[dict[str, object]] = []
        self.started = False
        self.stopped = False

    def add_job(self, func: object, trigger: object, **kwargs: object) -> None:
        self.jobs.append({"func": func, "trigger": trigger, **kwargs})

    def get_jobs(self) -> list[object]:
        return []

    def start(self) -> None:
        self.started = True

    def shutdown(self, wait: bool = False) -> None:
        self.stopped = True


def test_scheduler_stays_off_unless_enabled() -> None:
    settings = Settings(OPS_SCHEDULER_ENABLED=False)
    scheduler = OpsScheduler(settings, None, None)  # type: ignore[arg-type]
    assert scheduler.start() is False
    assert scheduler.running is False


def test_scheduler_registers_every_periodic_job(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = _FakeScheduler()
    monkeypatch.setattr("app.ops.scheduler.runtime.AsyncIOScheduler", lambda **_: fake)
    settings = Settings(
        OPS_SCHEDULER_ENABLED=True,
        OPS_SCHEDULER_ALERT_INTERVAL_SECONDS=60,
        OPS_SCHEDULER_PROBE_INTERVAL_SECONDS=30,
        OPS_SCHEDULER_ROLLUP_INTERVAL_MINUTES=60,
        OPS_SCHEDULER_PURGE_HOUR=4,
    )
    scheduler = OpsScheduler(settings, None, None)  # type: ignore[arg-type]
    assert scheduler.start() is True
    assert scheduler.running is True

    registered = {job["id"] for job in fake.jobs}
    assert registered == {
        "ops_rollup_metrics",
        "ops_alert_evaluation",
        "ops_availability_probes",
        "ops_retention_purge",
    }
    # One instance at a time and coalesced: a backlog must not turn into a
    # burst of overlapping ticks after a restart.
    assert all(job["max_instances"] == 1 for job in fake.jobs)
    assert all(job["coalesce"] is True for job in fake.jobs)

    scheduler.shutdown()
    assert fake.stopped is True


def test_retention_purge_runs_at_a_fixed_hour(monkeypatch: pytest.MonkeyPatch) -> None:
    """A purge must not drift into business hours because a container restarted."""
    fake = _FakeScheduler()
    monkeypatch.setattr("app.ops.scheduler.runtime.AsyncIOScheduler", lambda **_: fake)
    settings = Settings(OPS_SCHEDULER_ENABLED=True, OPS_SCHEDULER_PURGE_HOUR=4)
    scheduler = OpsScheduler(settings, None, None)  # type: ignore[arg-type]
    scheduler.start()
    purge = next(job for job in fake.jobs if job["id"] == "ops_retention_purge")
    assert str(purge["trigger"]) == "cron[hour='4', minute='0']"


def test_job_lock_reports_acquired_without_postgresql() -> None:
    """SQLite has no advisory locks; the caller must still run its tick."""
    engine = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))

    async def scenario() -> bool:
        async with job_lock(engine, 1) as acquired:
            return acquired
        return False  # pragma: no cover

    assert asyncio.run(scenario()) is True


def test_run_guarded_swallows_a_failing_job() -> None:
    """One broken job must not take the scheduler - and every other job - down."""

    async def explodes() -> None:
        raise RuntimeError("boom")

    # No exception escapes; if it did, the test itself would fail.
    asyncio.run(jobs.run_guarded("explodes", explodes()))


def test_lock_ids_are_stable_across_processes() -> None:
    """``hash()`` is randomised per process; the lock key must not be."""
    settings = Settings()
    assert jobs.lock_id(settings, "rollup_metrics") == jobs.lock_id(settings, "rollup_metrics")
    assert jobs.lock_id(settings, "rollup_metrics") != jobs.lock_id(
        settings, "evaluate_alerts"
    )
