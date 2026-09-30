"""app.tools.usage — business logic.

Tool usage is its own stream: ``tool_usage_event`` records what the runtime did,
``tool_usage_daily`` rolls it up per day and ``tool_recent_usage`` remembers what
a signed in user touched last. Behaviour analytics reads the same facts through
``behavior_event``, never through this table.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.shared.events.codes import OutboxEventType
from app.shared.ids import new_id
from app.shared.outbox.service import OutboxService
from app.shared.tracing.context import get_request_id, get_trace_id
from app.tools.usage.repository import ToolUsageRepository

SECONDS_IN_DAY: int = 24 * 3600


class ToolUsageService:
    """Records tool usage and maintains the usage rollups."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = ToolUsageRepository(session)
        self._settings = settings or get_settings()
        self._outbox = OutboxService(self._settings)

    async def record(
        self,
        *,
        tool_id: int,
        tool_version_id: int | None,
        user_id: int | None,
        anonymous_id_hash: str | None,
        execution_mode: str,
        success: bool,
        duration_ms: int,
        source: str = "API",
    ) -> int:
        """Write one usage event, refresh the rollups and publish the fact."""
        now = datetime.datetime.now(datetime.UTC)
        event = await self._repository.add_event(
            id=new_id(),
            tool_id=tool_id,
            tool_version_id=tool_version_id,
            subject_type="GUEST" if user_id is None else "USER",
            user_id=user_id,
            anonymous_id_hash=anonymous_id_hash,
            execution_mode=execution_mode,
            success=success,
            duration_ms=duration_ms,
            source=source,
            trace_id=get_trace_id(),
            request_id=get_request_id(),
        )
        await self._refresh_daily(
            tool_id=tool_id,
            stat_date=now.date(),
            is_guest=user_id is None,
            success=success,
            duration_ms=duration_ms,
        )
        if user_id is not None:
            await self._refresh_recent(user_id=user_id, tool_id=tool_id, now=now)
        await self._outbox.publish(
            self._session,
            event_type=OutboxEventType.TOOL_EXECUTED,
            aggregate_type="tool",
            aggregate_id=tool_id,
            payload={
                "tool_id": tool_id,
                "usage_event_id": int(event.id),
                "user_id": user_id or 0,
                "success": success,
                "duration_ms": duration_ms,
                "occurred_at": now.isoformat(),
            },
        )
        await self._session.flush()
        return int(event.id)

    async def _refresh_daily(
        self,
        *,
        tool_id: int,
        stat_date: datetime.date,
        is_guest: bool,
        success: bool,
        duration_ms: int,
    ) -> None:
        row = await self._repository.rollup_row_for_update(tool_id=tool_id, stat_date=stat_date)
        if row is None:
            row = await self._repository.create_rollup(
                tool_id=tool_id,
                stat_date=stat_date,
                total_count=0,
                success_count=0,
                failure_count=0,
                guest_count=0,
                user_count=0,
                unique_user_count=0,
                unique_guest_count=0,
            )
        row.total_count = int(row.total_count or 0) + 1
        if success:
            row.success_count = int(row.success_count or 0) + 1
        else:
            row.failure_count = int(row.failure_count or 0) + 1
        if is_guest:
            row.guest_count = int(row.guest_count or 0) + 1
        else:
            row.user_count = int(row.user_count or 0) + 1
        previous_average = float(row.avg_duration_ms or 0)
        total = int(row.total_count or 1)
        row.avg_duration_ms = round(
            previous_average + (duration_ms - previous_average) / total, 2
        )
        await self._session.flush()

    async def _refresh_recent(
        self, *, user_id: int, tool_id: int, now: datetime.datetime
    ) -> None:
        row = await self._repository.recent_row(user_id=user_id, tool_id=tool_id)
        if row is None:
            await self._repository.add_recent(
                user_id=user_id, tool_id=tool_id, last_used_at=now, use_count=1
            )
            return
        row.last_used_at = now
        row.use_count = int(row.use_count or 0) + 1
        await self._session.flush()

    async def refresh_popularity(
        self, *, stat_date: datetime.date, window_days: int
    ) -> int:
        """Rebuild the popularity ranking for one window.

        Executions and distinct users are counted separately: the ranking is
        driven by executions, never by a mixed number.
        """
        from app.tools.catalog.repository import ToolCatalogRepository

        catalog = ToolCatalogRepository(self._session)
        tools = await catalog.active_tools()
        start = stat_date - datetime.timedelta(days=window_days - 1)
        window_start = datetime.datetime.combine(start, datetime.time.min, tzinfo=datetime.UTC)
        window_end = window_start + datetime.timedelta(days=window_days)
        scored: list[tuple[int, int, int]] = []
        for tool in tools:
            (
                total,
                _success,
                _failure,
                unique_users,
            ) = await self._repository.counts_for_tool(
                int(tool.id), start=window_start, end=window_end
            )
            scored.append((int(tool.id), total, unique_users))
        scored.sort(key=lambda item: (-item[1], item[0]))

        for rank, (tool_id, usage_count, unique_users) in enumerate(scored, start=1):
            row = await self._repository.popularity_row(
                tool_id=tool_id, stat_date=stat_date, window_days=window_days
            )
            if row is None:
                await self._repository.create_popularity(
                    stat_date=stat_date,
                    window_days=window_days,
                    tool_id=tool_id,
                    usage_count=usage_count,
                    unique_user_count=unique_users,
                    rank_no=rank,
                    score=float(usage_count),
                )
            else:
                row.usage_count = usage_count
                row.unique_user_count = unique_users
                row.rank_no = rank
                row.score = float(usage_count)
        await self._session.flush()
        return len(scored)
