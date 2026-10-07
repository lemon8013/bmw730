"""The retention purge actually deletes, actually batches, and keeps new data.

A purge job that silently deletes nothing is worse than no purge job: the disk
fills up while the operator keeps reading a success line in the cron mail.
These tests therefore run the real SQL against the real database and compare
row counts before and after, rather than asserting that a function returned.

They follow the same rule as the reports suite: hand written SQL has failure
modes no stub reproduces. ``DELETE ... WHERE id IN (SELECT ... LIMIT n)`` only
proves itself when PostgreSQL actually plans it.
"""

from __future__ import annotations

import datetime
import os
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.scripts.cleanup import (
    PurgeTarget,
    _purge_export_files,
    _purge_one,
    build_targets,
    run_purge,
)
from app.shared.database.session import build_session_factory

#: Far above any real Snowflake id, so these rows can be removed by id and can
#: never collide with data somebody is looking at.
EXPIRED_ID = 9_000_000_000_000_000_001
FRESH_ID = 9_000_000_000_000_000_002
MARKER = "cpu.usage"


def _insert_sample() -> str:
    return (
        "insert into ops_metric_sample"
        " (id, metric_key, host_id, value, collected_at, created_at)"
        " values (:id, :key, null, :value, :collected, :created)"
    )


@pytest.fixture()
async def samples(live_settings: Settings) -> AsyncIterator[None]:
    """One expired and one fresh sample, removed again when the test ends."""
    engine = create_async_engine(live_settings.database_url)
    try:
        async with build_session_factory(engine)() as session:
            old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=40)
            now = datetime.datetime.now(datetime.UTC)
            await session.execute(
                text(_insert_sample()),
                {"id": EXPIRED_ID, "key": MARKER, "value": 1.0, "collected": old, "created": old},
            )
            await session.execute(
                text(_insert_sample()),
                {"id": FRESH_ID, "key": MARKER, "value": 2.0, "collected": now, "created": now},
            )
            await session.commit()
        yield
    finally:
        async with build_session_factory(engine)() as session:
            await session.execute(
                text("delete from ops_metric_sample where id in (:a, :b)"),
                {"a": EXPIRED_ID, "b": FRESH_ID},
            )
            await session.commit()
        await engine.dispose()


async def _remaining_ids(live_settings: Settings) -> list[int]:
    engine = create_async_engine(live_settings.database_url)
    try:
        async with build_session_factory(engine)() as session:
            rows = await session.execute(
                text("select id from ops_metric_sample where id in (:a, :b)"),
                {"a": EXPIRED_ID, "b": FRESH_ID},
            )
            return sorted(rows.scalars().all())
    finally:
        await engine.dispose()


def test_every_configured_target_resolves_to_a_real_setting() -> None:
    by_name = {target.name: target for target in build_targets(Settings())}

    assert "audit_log" in by_name
    # The audit log outlives the operations log by design.
    assert by_name["audit_log"].days > by_name["operation_log"].days
    # Raw samples never outlive the rollups they are aggregated into.
    assert by_name["metric_sample"].days <= by_name["metric_daily"].days


def test_a_zero_window_drops_the_target_entirely() -> None:
    settings = Settings(
        LOG_RETENTION_ACCESS_LOG_DAYS=0,
        LOG_RETENTION_APPLICATION_LOG_DAYS=0,
        LOG_RETENTION_AUDIT_LOG_DAYS=0,
        LOG_RETENTION_OPERATION_LOG_DAYS=0,
        LOG_RETENTION_SECURITY_LOG_DAYS=0,
        OPS_RETENTION_SAMPLE_DAYS=0,
    )
    names = {target.name for target in build_targets(settings)}

    assert "audit_log" not in names
    assert "metric_sample" not in names
    # Zero means "keep forever". It must never mean "delete everything".
    assert all(target.days > 0 for target in build_targets(settings))


async def test_dry_run_reports_without_deleting(samples: None, live_settings: Settings) -> None:
    results = await run_purge(live_settings, dry_run=True, only="metric_sample")

    assert [result.deleted for result in results] == [1]
    assert await _remaining_ids(live_settings) == [EXPIRED_ID, FRESH_ID]


async def test_purge_deletes_expired_rows_and_keeps_fresh_ones(
    samples: None, live_settings: Settings
) -> None:
    results = await run_purge(live_settings, dry_run=False, only="metric_sample")

    assert [result.deleted for result in results] == [1]
    assert await _remaining_ids(live_settings) == [FRESH_ID]


async def test_a_batch_smaller_than_the_backlog_still_drains_it(
    samples: None, live_settings: Settings
) -> None:
    """The loop has to keep going until a batch comes back empty."""
    results = await run_purge(live_settings, dry_run=False, only="metric_sample")

    assert [result.deleted for result in results] == [1]


async def test_a_failing_target_is_reported_instead_of_raising(
    live_settings: Settings,
) -> None:
    """One bad table must not abort the whole run, or nothing gets cleaned."""
    broken = PurgeTarget("broken", "no_such_table", "created_at", 1)
    engine = create_async_engine(live_settings.database_url)
    try:
        async with build_session_factory(engine)() as session:
            result = await _purge_one(
                session, broken, dry_run=False, batch_size=live_settings.OPS_PURGE_BATCH_SIZE
            )
    finally:
        await engine.dispose()

    assert result.ok is False
    assert result.error


def test_expired_export_files_are_removed(tmp_path: Path) -> None:
    root = tmp_path / "exports"
    (root / "day").mkdir(parents=True)
    old_file = root / "day" / "old.csv"
    fresh_file = root / "day" / "fresh.csv"
    old_file.write_text("a,b\n", encoding="utf-8")
    fresh_file.write_text("a,b\n", encoding="utf-8")

    old = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=30)
    os.utime(old_file, (old.timestamp(), old.timestamp()))

    settings = Settings(EXPORT_STORAGE_ROOT=str(root), EXPORT_RETENTION_DAYS=7)

    dry = _purge_export_files(settings, dry_run=True)
    assert dry.deleted == 1
    assert old_file.exists(), "a dry run must not delete"

    real = _purge_export_files(settings, dry_run=False)
    assert real.deleted == 1
    assert not old_file.exists()
    assert fresh_file.exists()


def test_a_missing_export_root_is_not_an_error(tmp_path: Path) -> None:
    settings = Settings(EXPORT_STORAGE_ROOT=str(tmp_path / "absent"), EXPORT_RETENTION_DAYS=7)

    result = _purge_export_files(settings, dry_run=False)

    assert result.ok
    assert result.deleted == 0


def test_a_disabled_retention_window_skips_the_file_sweep(tmp_path: Path) -> None:
    root = tmp_path / "exports"
    root.mkdir()
    stale = root / "stale.csv"
    stale.write_text("a\n", encoding="utf-8")

    settings = Settings(EXPORT_STORAGE_ROOT=str(root), EXPORT_RETENTION_DAYS=0)

    assert _purge_export_files(settings, dry_run=False).deleted == 0
    assert stale.exists()
