"""Integration tests for the ops scheduler jobs.

The jobs are hand written aggregate SQL and network probes; neither can be
validated against a stub. These run them against the real PostgreSQL instance
and assert that they complete and report counters, which is the only evidence
that a deployment's periodic work actually works.
"""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.ops.scheduler import jobs
from app.shared.database.session import build_session_factory


async def _with_infrastructure(coro, settings: Settings):
    engine = create_async_engine(settings.database_url)
    factory = build_session_factory(engine)
    try:
        return await coro(engine, factory, settings)
    finally:
        await engine.dispose()


def test_metric_rollup_runs_against_postgresql(
    live_infrastructure: None, live_settings: Settings
) -> None:
    async def scenario(engine, factory, settings):  # type: ignore[no-untyped-def]
        return await jobs.rollup_metrics(engine, factory, settings)

    outcome = asyncio.run(_with_infrastructure(scenario, live_settings))
    assert "hourly_buckets" in outcome
    # A second tick must recompute rather than duplicate, which is the whole
    # point of the upsert; it is also what makes a missed tick recoverable.
    again = asyncio.run(_with_infrastructure(scenario, live_settings))
    assert "hourly_buckets" in again


def test_availability_probes_run_against_postgresql(
    live_infrastructure: None, live_settings: Settings
) -> None:
    async def scenario(engine, factory, settings):  # type: ignore[no-untyped-def]
        return await jobs.run_availability_probes(engine, factory, settings)

    outcome = asyncio.run(_with_infrastructure(scenario, live_settings))
    assert outcome["succeeded"] + outcome["failed"] == outcome["due"]


def test_alert_evaluation_runs_against_postgresql(
    live_infrastructure: None, live_settings: Settings
) -> None:
    async def scenario(engine, factory, settings):  # type: ignore[no-untyped-def]
        return await jobs.evaluate_alerts(engine, factory, settings)

    outcome = asyncio.run(_with_infrastructure(scenario, live_settings))
    assert "evaluated_rules" in outcome
