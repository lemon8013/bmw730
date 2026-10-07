"""app.ops.database — read-only PostgreSQL introspection.

The module owns every statement it executes: they are fixed literals declared at
the top of this file and none of them ever writes. Nothing interpolated comes
from a request — only ``LIMIT`` bound parameters are sent along, and even those
are clamped by the caller.

The repository never commits and never interprets a value: it returns raw rows
and lets the service derive ratios and decide how to degrade.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_PING = text("SELECT 1")

_SERVER_VERSION = text("SHOW server_version")

_MAX_CONNECTIONS = text("SHOW max_connections")

_IDENTITY = text("SELECT current_database() AS database_name")

_UPTIME = text(
    "SELECT EXTRACT(EPOCH FROM (now() - pg_postmaster_start_time())) AS uptime_seconds"
)

_CONNECTION_TOTAL = text(
    "SELECT count(*) AS connection_count "
    "FROM pg_stat_activity WHERE datname = current_database()"
)

_CONNECTION_STATES = text(
    "SELECT coalesce(state, 'unknown') AS state, count(*) AS connection_count "
    "FROM pg_stat_activity WHERE datname = current_database() "
    "GROUP BY 1 ORDER BY connection_count DESC, state ASC"
)

_TRANSACTIONS = text(
    "SELECT coalesce(sum(xact_commit), 0)::bigint AS commits, "
    "       coalesce(sum(xact_rollback), 0)::bigint AS rollbacks, "
    "       coalesce(sum(deadlocks), 0)::bigint AS deadlocks "
    "FROM pg_stat_database WHERE datname = current_database()"
)

_LOCK_TOTALS = text(
    "SELECT count(*) AS total_locks, "
    "       count(*) FILTER (WHERE granted) AS granted_locks, "
    "       count(*) FILTER (WHERE NOT granted) AS waiting_locks "
    "FROM pg_locks "
    "WHERE database = (SELECT oid FROM pg_database WHERE datname = current_database())"
)

_WAITING_SESSIONS = text(
    "SELECT a.pid AS pid, a.datname AS database_name, "
    "       coalesce(a.state, 'unknown') AS state, "
    "       a.wait_event_type AS wait_event_type, a.wait_event AS wait_event, "
    "       EXTRACT(EPOCH FROM (now() - a.xact_start)) AS wait_seconds "
    "FROM pg_stat_activity a "
    "WHERE a.datname = current_database() "
    "  AND a.wait_event_type IS NOT NULL "
    "  AND a.pid <> pg_backend_pid() "
    "ORDER BY wait_seconds DESC NULLS LAST "
    "LIMIT :limit"
)

_STATEMENTS_AVAILABLE = text(
    "SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements') "
    "AS available"
)

_STATEMENTS_TOTALS = text(
    "SELECT coalesce(sum(calls), 0)::bigint AS calls, "
    "       coalesce(sum(rows), 0)::bigint AS rows, "
    "       coalesce(sum(total_exec_time), 0)::numeric AS total_ms, "
    "       coalesce(max(max_exec_time), 0)::numeric AS max_ms "
    "FROM pg_stat_statements "
    "WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database()) "
    "  AND calls > 0"
)

_STATEMENTS_SLOWEST = text(
    "SELECT queryid::text AS query_id, calls, rows, "
    "       total_exec_time::numeric AS total_ms, "
    "       mean_exec_time::numeric AS mean_ms, "
    "       max_exec_time::numeric AS max_ms, "
    "       left(query, 500) AS statement "
    "FROM pg_stat_statements "
    "WHERE dbid = (SELECT oid FROM pg_database WHERE datname = current_database()) "
    "  AND calls > 0 "
    "ORDER BY mean_exec_time DESC "
    "LIMIT :limit"
)

_LONG_RUNNING_QUERIES = text(
    "SELECT a.pid AS pid, a.datname AS database_name, "
    "       a.wait_event_type AS wait_event_type, a.wait_event AS wait_event, "
    "       EXTRACT(EPOCH FROM (now() - a.query_start)) AS duration_seconds "
    "FROM pg_stat_activity a "
    "WHERE a.datname = current_database() "
    "  AND a.state = 'active' "
    "  AND a.query_start IS NOT NULL "
    "  AND a.pid <> pg_backend_pid() "
    "ORDER BY duration_seconds DESC "
    "LIMIT :limit"
)

_DATABASE_SIZE = text(
    "SELECT pg_database_size(current_database())::bigint AS database_size_bytes"
)

_TABLE_STORAGE = text(
    "SELECT schemaname AS schema_name, relname AS table_name, "
    "       pg_total_relation_size(relid)::bigint AS total_bytes, "
    "       pg_relation_size(relid)::bigint AS heap_bytes, "
    "       pg_indexes_size(relid)::bigint AS index_bytes, "
    "       coalesce(n_live_tup, 0)::bigint AS live_rows "
    "FROM pg_stat_user_tables "
    "ORDER BY pg_total_relation_size(relid) DESC "
    "LIMIT :limit"
)

_CACHE_BLOCKS = text(
    "SELECT coalesce(sum(blks_hit), 0)::bigint AS blocks_hit, "
    "       coalesce(sum(blks_read), 0)::bigint AS blocks_read "
    "FROM pg_stat_database WHERE datname = current_database()"
)


def _rows(result: Any) -> list[dict[str, Any]]:
    return [dict(row) for row in result.mappings().all()]


def _row(result: Any) -> dict[str, Any] | None:
    mapping = result.mappings().first()
    return None if mapping is None else dict(mapping)


class DatabaseMonitorRepository:
    """Executes the fixed read-only introspection statements."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ping(self) -> None:
        """Fail when PostgreSQL is unreachable."""
        await self._session.execute(_PING)

    async def server_version(self) -> str | None:
        result = await self._session.execute(_SERVER_VERSION)
        return _scalar_text(result)

    async def database_name(self) -> str | None:
        result = await self._session.execute(_IDENTITY)
        return _scalar_text(result)

    async def uptime_seconds(self) -> float | None:
        row = _row(await self._session.execute(_UPTIME))
        return None if row is None else _optional_float(row.get("uptime_seconds"))

    async def connection_total(self) -> int | None:
        row = _row(await self._session.execute(_CONNECTION_TOTAL))
        return None if row is None else _optional_int(row.get("connection_count"))

    async def max_connections(self) -> int | None:
        result = await self._session.execute(_MAX_CONNECTIONS)
        value = _scalar_text(result)
        return None if value is None else _optional_int(value)

    async def connection_states(self) -> list[dict[str, Any]]:
        return _rows(await self._session.execute(_CONNECTION_STATES))

    async def transactions(self) -> dict[str, Any] | None:
        return _row(await self._session.execute(_TRANSACTIONS))

    async def lock_totals(self) -> dict[str, Any] | None:
        return _row(await self._session.execute(_LOCK_TOTALS))

    async def waiting_sessions(self, *, limit: int) -> list[dict[str, Any]]:
        return _rows(await self._session.execute(_WAITING_SESSIONS, {"limit": limit}))

    async def statements_extension_available(self) -> bool:
        result = await self._session.execute(_STATEMENTS_AVAILABLE)
        first = result.first()
        return bool(first is not None and first[0])

    async def statement_totals(self) -> dict[str, Any] | None:
        return _row(await self._session.execute(_STATEMENTS_TOTALS))

    async def slowest_statements(self, *, limit: int) -> list[dict[str, Any]]:
        return _rows(await self._session.execute(_STATEMENTS_SLOWEST, {"limit": limit}))

    async def long_running_queries(self, *, limit: int) -> list[dict[str, Any]]:
        return _rows(await self._session.execute(_LONG_RUNNING_QUERIES, {"limit": limit}))

    async def database_size_bytes(self) -> int | None:
        row = _row(await self._session.execute(_DATABASE_SIZE))
        return None if row is None else _optional_int(row.get("database_size_bytes"))

    async def largest_tables(self, *, limit: int) -> list[dict[str, Any]]:
        return _rows(await self._session.execute(_TABLE_STORAGE, {"limit": limit}))

    async def cache_blocks(self) -> dict[str, Any] | None:
        return _row(await self._session.execute(_CACHE_BLOCKS))


def _scalar_text(result: Any) -> str | None:
    first = result.first()
    return None if first is None else str(first[0])


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)
