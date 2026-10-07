"""app.ops.database — business logic.

Monitoring must never take the monitoring page down with it: every collector
read runs inside a guard that converts an unreachable or mis-configured
PostgreSQL into a structured degraded response (``status='UNKNOWN'`` plus an
``error`` description) instead of an HTTP 500.

The service also owns the derived numbers (ratios, utilisation) — the
repository returns raw rows only. Nothing here writes, so no read endpoint
produces an audit record.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.ops.database.repository import DatabaseMonitorRepository
from app.ops.database.schema import (
    STATUS_UNKNOWN,
    STATUS_UP,
    ConnectionStateCount,
    DatabaseCacheResponse,
    DatabaseConnectionsResponse,
    DatabaseLocksResponse,
    DatabaseOverviewResponse,
    DatabaseSlowQueriesResponse,
    DatabaseStorageResponse,
    DatabaseTransactionsResponse,
    LongRunningQueryItem,
    SlowStatementItem,
    TableStorageItem,
    WaitingSessionItem,
)

_LOGGER: logging.Logger = logging.getLogger("vctn.ops.database")

#: A collector failure is reported to the UI in full detail; only its length is
#: bounded so that a pathological driver message cannot flood the response.
_MAX_ERROR_LENGTH = 500

_REDACTED = "<redacted>"


class DatabaseMonitorService:
    """Reads PostgreSQL health and performance counters."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = DatabaseMonitorRepository(session)
        self._settings = settings or get_settings()

    async def overview(self) -> DatabaseOverviewResponse:
        """Identity, uptime and headline counters of the monitored instance."""
        try:
            await self._repository.ping()
            cache_blocks = await self._repository.cache_blocks()
            return DatabaseOverviewResponse(
                status=STATUS_UP,
                collected_at=datetime.datetime.now(datetime.UTC),
                version=await self._repository.server_version(),
                database_name=await self._repository.database_name(),
                uptime_seconds=await self._repository.uptime_seconds(),
                connection_count=await self._repository.connection_total(),
                cache_hit_ratio=_hit_ratio(
                    cache_blocks.get("blocks_hit") if cache_blocks else None,
                    cache_blocks.get("blocks_read") if cache_blocks else None,
                ),
                database_size_bytes=await self._repository.database_size_bytes(),
            )
        except Exception as exc:  # noqa: BLE001 - monitoring must fail soft
            return await self._degraded(DatabaseOverviewResponse, exc)

    async def connections(self) -> DatabaseConnectionsResponse:
        """Connection usage grouped by ``pg_stat_activity`` state."""
        try:
            total = await self._repository.connection_total()
            max_connections = await self._repository.max_connections()
            states = [
                ConnectionStateCount(
                    state=str(row.get("state")),
                    count=int(row.get("connection_count") or 0),
                )
                for row in await self._repository.connection_states()
            ]
            return DatabaseConnectionsResponse(
                status=STATUS_UP,
                collected_at=datetime.datetime.now(datetime.UTC),
                total=total,
                max_connections=max_connections,
                utilization_ratio=_ratio(total, max_connections),
                states=states,
            )
        except Exception as exc:  # noqa: BLE001 - monitoring must fail soft
            return await self._degraded(DatabaseConnectionsResponse, exc)

    async def transactions(self) -> DatabaseTransactionsResponse:
        """Committed, rolled back and deadlocked transactions."""
        try:
            row = await self._repository.transactions()
            commits = _optional_int(row.get("commits")) if row else None
            rollbacks = _optional_int(row.get("rollbacks")) if row else None
            return DatabaseTransactionsResponse(
                status=STATUS_UP,
                collected_at=datetime.datetime.now(datetime.UTC),
                commits=commits,
                rollbacks=rollbacks,
                deadlocks=_optional_int(row.get("deadlocks")) if row else None,
                rollback_ratio=_ratio(rollbacks, _total(commits, rollbacks)),
            )
        except Exception as exc:  # noqa: BLE001 - monitoring must fail soft
            return await self._degraded(DatabaseTransactionsResponse, exc)

    async def locks(self, *, limit: int) -> DatabaseLocksResponse:
        """Lock counts plus the sessions currently waiting on a lock."""
        try:
            totals = await self._repository.lock_totals()
            waiting_sessions = [
                WaitingSessionItem(
                    pid=int(row.get("pid") or 0),
                    database_name=_optional_text(row.get("database_name")),
                    state=_optional_text(row.get("state")),
                    wait_event_type=_optional_text(row.get("wait_event_type")),
                    wait_event=_optional_text(row.get("wait_event")),
                    wait_seconds=_optional_float(row.get("wait_seconds")),
                )
                for row in await self._repository.waiting_sessions(limit=limit)
            ]
            return DatabaseLocksResponse(
                status=STATUS_UP,
                collected_at=datetime.datetime.now(datetime.UTC),
                total_locks=_optional_int(totals.get("total_locks")) if totals else None,
                granted_locks=_optional_int(totals.get("granted_locks")) if totals else None,
                waiting_locks=_optional_int(totals.get("waiting_locks")) if totals else None,
                waiting_sessions=waiting_sessions,
            )
        except Exception as exc:  # noqa: BLE001 - monitoring must fail soft
            return await self._degraded(DatabaseLocksResponse, exc)

    async def slow_queries(self, *, limit: int) -> DatabaseSlowQueriesResponse:
        """Aggregated slow-query statistics and the longest running sessions.

        When ``pg_stat_statements`` is not installed the aggregate columns stay
        ``None`` while the ``pg_stat_activity`` reading is still returned, so the
        page can explain that history collection is not enabled.
        """
        try:
            long_running = [
                LongRunningQueryItem(
                    pid=int(row.get("pid") or 0),
                    database_name=_optional_text(row.get("database_name")),
                    wait_event_type=_optional_text(row.get("wait_event_type")),
                    wait_event=_optional_text(row.get("wait_event")),
                    duration_seconds=_optional_float(row.get("duration_seconds")),
                )
                for row in await self._repository.long_running_queries(limit=limit)
            ]
            if not await self._repository.statements_extension_available():
                return DatabaseSlowQueriesResponse(
                    status=STATUS_UP,
                    collected_at=datetime.datetime.now(datetime.UTC),
                    long_running_queries=long_running,
                )
            totals = await self._repository.statement_totals()
            slowest = [
                SlowStatementItem(
                    query_id=_optional_text(row.get("query_id")),
                    calls=_optional_int(row.get("calls")),
                    rows=_optional_int(row.get("rows")),
                    total_ms=_optional_float(row.get("total_ms")),
                    mean_ms=_optional_float(row.get("mean_ms")),
                    max_ms=_optional_float(row.get("max_ms")),
                    statement=_optional_text(row.get("statement")),
                )
                for row in await self._repository.slowest_statements(limit=limit)
            ]
            calls = _optional_int(totals.get("calls")) if totals else None
            total_ms = _optional_float(totals.get("total_ms")) if totals else None
            return DatabaseSlowQueriesResponse(
                status=STATUS_UP,
                collected_at=datetime.datetime.now(datetime.UTC),
                statements_extension_available=True,
                calls=calls,
                rows=_optional_int(totals.get("rows")) if totals else None,
                total_ms=total_ms,
                mean_ms=_ratio(total_ms, calls),
                max_ms=_optional_float(totals.get("max_ms")) if totals else None,
                slowest_statements=slowest,
                long_running_queries=long_running,
            )
        except Exception as exc:  # noqa: BLE001 - monitoring must fail soft
            return await self._degraded(DatabaseSlowQueriesResponse, exc)

    async def storage(self, *, limit: int) -> DatabaseStorageResponse:
        """Database size and the largest user tables."""
        try:
            tables = [
                TableStorageItem(
                    schema_name=str(row.get("schema_name")),
                    table_name=str(row.get("table_name")),
                    total_bytes=_optional_int(row.get("total_bytes")),
                    heap_bytes=_optional_int(row.get("heap_bytes")),
                    index_bytes=_optional_int(row.get("index_bytes")),
                    live_rows=_optional_int(row.get("live_rows")),
                )
                for row in await self._repository.largest_tables(limit=limit)
            ]
            return DatabaseStorageResponse(
                status=STATUS_UP,
                collected_at=datetime.datetime.now(datetime.UTC),
                database_name=await self._repository.database_name(),
                database_size_bytes=await self._repository.database_size_bytes(),
                tables=tables,
            )
        except Exception as exc:  # noqa: BLE001 - monitoring must fail soft
            return await self._degraded(DatabaseStorageResponse, exc)

    async def cache(self) -> DatabaseCacheResponse:
        """Buffer-cache efficiency."""
        try:
            row = await self._repository.cache_blocks()
            blocks_hit = _optional_int(row.get("blocks_hit")) if row else None
            blocks_read = _optional_int(row.get("blocks_read")) if row else None
            return DatabaseCacheResponse(
                status=STATUS_UP,
                collected_at=datetime.datetime.now(datetime.UTC),
                blocks_hit=blocks_hit,
                blocks_read=blocks_read,
                hit_ratio=_hit_ratio(blocks_hit, blocks_read),
            )
        except Exception as exc:  # noqa: BLE001 - monitoring must fail soft
            return await self._degraded(DatabaseCacheResponse, exc)

    async def _degraded(self, response_type: Any, exc: Exception) -> Any:
        """Build the ``UNKNOWN`` response for a failed collector read."""
        message = self._describe(exc)
        _LOGGER.warning("postgresql collector failed: %s", message)
        # The failed statement left the session transaction aborted; rolling
        # back keeps it usable for everything that follows the request.
        await self._session.rollback()
        return response_type(
            status=STATUS_UNKNOWN,
            collected_at=datetime.datetime.now(datetime.UTC),
            error=message,
        )

    def _describe(self, exc: Exception) -> str:
        """Describe a failure without ever echoing a connection secret."""
        rendered = f"{type(exc).__name__}: {exc}"
        url = self._settings.database_url
        if url:
            rendered = rendered.replace(url, _REDACTED)
        return rendered[:_MAX_ERROR_LENGTH]


def _hit_ratio(blocks_hit: int | None, blocks_read: int | None) -> float | None:
    """``blks_hit / (blks_hit + blks_read)``, or ``None`` without any block."""
    return _ratio(blocks_hit, _total(blocks_hit, blocks_read))


def _ratio(numerator: int | float | None, denominator: int | float | None) -> float | None:
    if numerator is None or not denominator:
        return None
    return float(numerator) / float(denominator)


def _total(*values: int | float | None) -> int | float | None:
    total: int | float = 0
    for value in values:
        if value is None:
            return None
        total += value
    return total


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _optional_text(value: Any) -> str | None:
    return None if value is None else str(value)
