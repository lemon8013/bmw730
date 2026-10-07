"""Purge data that is past its retention window.

Run it from cron - or from a Kubernetes CronJob - once a day:

    0 4 * * * docker compose -f /srv/vctn/docker-compose.yml run --rm api clean

The retention windows come from :class:`app.core.config.Settings`; nothing is
hard coded here except the table and column names, which are frozen by the
schema baseline.

Two properties matter in production:

* **Batched deletes.** An unbounded ``DELETE`` on a table that has grown for a
  year stays in one transaction for minutes, which blocks autovacuum and every
  query behind it. Rows are removed in ``OPS_PURGE_BATCH_SIZE`` chunks.
* **Per table transactions.** One failing table must not roll back the tables
  that were already cleaned.

Always run ``--dry-run`` first and read the numbers before deleting anything.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.exceptions import ServiceUnavailableError
from app.shared.storage import PROVIDER_S3, get_object_storage, resolve_provider

#: Where generated exports land inside the object store.
EXPORT_OBJECT_PREFIX: Final[str] = "exports/"


@dataclass(frozen=True)
class PurgeTarget:
    """One table, the time column that decides its age and the setting name."""

    name: str
    table: str
    column: str
    days: int


#: Application and audit logs, driven by ``LOG_RETENTION_*_DAYS``.
LOG_TARGET_ATTRIBUTES: Final[tuple[tuple[str, str, str], ...]] = (
    ("access_log", "sys_access_log", "LOG_RETENTION_ACCESS_LOG_DAYS"),
    ("application_log", "sys_application_log", "LOG_RETENTION_APPLICATION_LOG_DAYS"),
    ("audit_log", "sys_audit_log", "LOG_RETENTION_AUDIT_LOG_DAYS"),
    ("operation_log", "sys_operation_log", "LOG_RETENTION_OPERATION_LOG_DAYS"),
    ("security_log", "sys_security_log", "LOG_RETENTION_SECURITY_LOG_DAYS"),
)

#: Monitoring tables, driven by ``OPS_RETENTION_*_DAYS``.
OPS_TARGET_ATTRIBUTES: Final[tuple[tuple[str, str, str, str], ...]] = (
    ("metric_sample", "ops_metric_sample", "collected_at", "OPS_RETENTION_SAMPLE_DAYS"),
    ("agent_heartbeat", "ops_agent_heartbeat", "collected_at", "OPS_RETENTION_HEARTBEAT_DAYS"),
    ("metric_hourly", "ops_metric_hourly", "bucket_at", "OPS_RETENTION_HOURLY_DAYS"),
    ("metric_daily", "ops_metric_daily", "bucket_at", "OPS_RETENTION_DAILY_DAYS"),
    ("event", "ops_event", "occurred_at", "OPS_RETENTION_EVENT_DAYS"),
    (
        "availability_result",
        "ops_availability_result",
        "checked_at",
        "OPS_RETENTION_AVAILABILITY_DAYS",
    ),
    (
        "alert_history",
        "ops_alert_history",
        "created_at",
        "OPS_RETENTION_ALERT_HISTORY_DAYS",
    ),
    (
        "alert_notification",
        "ops_alert_notification",
        "created_at",
        "OPS_RETENTION_NOTIFICATION_DAYS",
    ),
    ("operation_record", "ops_operation_record", "created_at", "OPS_RETENTION_OPERATION_DAYS"),
)


def build_targets(settings: Settings) -> tuple[PurgeTarget, ...]:
    """Resolve every purge target from the current configuration."""
    targets: list[PurgeTarget] = []
    for name, table, attribute in LOG_TARGET_ATTRIBUTES:
        targets.append(PurgeTarget(name, table, "created_at", int(getattr(settings, attribute))))
    for name, table, column, attribute in OPS_TARGET_ATTRIBUTES:
        targets.append(PurgeTarget(name, table, column, int(getattr(settings, attribute))))
    return tuple(target for target in targets if target.days > 0)


def _count_statement(target: PurgeTarget) -> str:
    return f"SELECT count(*) FROM {target.table} WHERE {target.column} < :cutoff"


def _delete_statement(target: PurgeTarget) -> str:
    # The sub-select keeps the row set bounded, so each statement is short and
    # the transaction never grows with the size of the backlog.
    return (
        f"DELETE FROM {target.table} WHERE id IN ("
        f"  SELECT id FROM {target.table} WHERE {target.column} < :cutoff"
        f"  ORDER BY id LIMIT :batch_size"
        f")"
    )


@dataclass
class PurgeResult:
    """What one target ended up doing."""

    name: str
    days: int
    deleted: int = 0
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


async def _purge_one(
    session: AsyncSession, target: PurgeTarget, *, dry_run: bool, batch_size: int
) -> PurgeResult:
    """Delete one target's expired rows, in batches, inside its own transaction."""
    result = PurgeResult(name=target.name, days=target.days)
    cutoff = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=target.days)
    try:
        if dry_run:
            expired = (
                await session.execute(text(_count_statement(target)), {"cutoff": cutoff})
            ).scalar_one()
            result.deleted = int(expired)
            return result

        while True:
            removed = (
                await session.execute(
                    text(_delete_statement(target)),
                    {"cutoff": cutoff, "batch_size": batch_size},
                )
            ).rowcount
            await session.commit()
            result.deleted += int(removed or 0)
            if not removed:
                break
    except Exception as failure:  # noqa: BLE001 - one bad table must not stop the rest
        await session.rollback()
        # Only the exception type and message are reported: purge failures are
        # written to the operator's terminal and to cron mail, never to logs
        # that might carry row data.
        result.error = f"{type(failure).__name__}: {failure}"
    return result


def _purge_export_files(settings: Settings, *, dry_run: bool) -> PurgeResult:
    """Delete generated export files past their retention window.

    Files are judged by their own modification time rather than by a database
    row, so an orphaned file left behind by a crashed job is still collected.
    """
    result = PurgeResult(name="export_files", days=settings.EXPORT_RETENTION_DAYS)
    root = Path(settings.EXPORT_STORAGE_ROOT)
    if settings.EXPORT_RETENTION_DAYS <= 0 or not root.is_dir():
        return result

    deadline = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
        days=settings.EXPORT_RETENTION_DAYS
    )
    try:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            modified = datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.UTC)
            if modified >= deadline:
                continue
            result.deleted += 1
            if not dry_run:
                path.unlink()
    except OSError as failure:
        result.error = f"OSError: {failure}"
    return result


async def _purge_export_objects(settings: Settings, *, dry_run: bool) -> PurgeResult:
    """Delete expired export objects from the object store.

    Local deployments ignore this target: ``_purge_export_files`` already walks
    the export directory, and an S3 bucket has no directory to walk - objects
    have to be listed and deleted one by one.
    """
    result = PurgeResult(name="export_objects", days=settings.EXPORT_RETENTION_DAYS)
    if resolve_provider(settings) != PROVIDER_S3:
        return result
    if settings.EXPORT_RETENTION_DAYS <= 0:
        return result

    storage = get_object_storage(settings)
    deadline = datetime.datetime.now(datetime.UTC) - datetime.timedelta(
        days=settings.EXPORT_RETENTION_DAYS
    )
    try:
        async for stored in storage.list_objects(prefix=EXPORT_OBJECT_PREFIX):
            if stored.last_modified is None or stored.last_modified >= deadline:
                continue
            result.deleted += 1
            if not dry_run:
                await storage.delete_object(object_key=stored.object_key)
    except ServiceUnavailableError as failure:
        result.error = f"{type(failure).__name__}: {failure}"
    finally:
        await storage.aclose()
    return result


async def run_purge(
    settings: Settings,
    *,
    dry_run: bool,
    only: str | None = None,
    include_files: bool = True,
) -> tuple[PurgeResult, ...]:
    """Purge every configured target and return one result per target."""
    engine = create_async_engine(settings.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    results: list[PurgeResult] = []
    try:
        async with factory() as session:
            for target in build_targets(settings):
                if only and target.name != only:
                    continue
                results.append(
                    await _purge_one(
                        session,
                        target,
                        dry_run=dry_run,
                        batch_size=settings.OPS_PURGE_BATCH_SIZE,
                    )
                )
        if include_files and (only is None or only == "export_files"):
            results.append(_purge_export_files(settings, dry_run=dry_run))
        if include_files and (only is None or only == "export_objects"):
            results.append(await _purge_export_objects(settings, dry_run=dry_run))
    finally:
        await engine.dispose()
    return tuple(results)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.scripts.cleanup",
        description="Delete data that is past its retention window.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report how many rows would go, delete nothing",
    )
    parser.add_argument("--only", help="purge a single target by name")
    parser.add_argument(
        "--no-files",
        action="store_true",
        help="skip the export file sweep",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="print the configured targets and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point. Returns a process exit code."""
    args = _build_parser().parse_args(argv)
    settings = get_settings()

    if args.list:
        for target in build_targets(settings):
            print(f"{target.name:22} {target.table:28} {target.column:14} {target.days}d")
        print(f"{'export_files':22} {settings.EXPORT_STORAGE_ROOT}")
        if resolve_provider(settings) == PROVIDER_S3:
            print(f"{'export_objects':22} {EXPORT_OBJECT_PREFIX}")
        return 0

    verb = "would delete" if args.dry_run else "deleted"
    results = asyncio.run(
        run_purge(
            settings,
            dry_run=args.dry_run,
            only=args.only,
            include_files=not args.no_files,
        )
    )

    failed = 0
    for result in results:
        if result.error:
            failed += 1
            print(f"{result.name:22} FAILED  {result.error}")
            continue
        print(f"{result.name:22} {verb} {result.deleted} row(s), window {result.days}d")

    if failed:
        print(f"{failed} target(s) failed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
