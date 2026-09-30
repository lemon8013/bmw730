"""Transactional outbox.

A module that changes its own state never reaches into another module's tables:
it writes an event into ``sys_outbox_event`` **inside the same transaction** and
the receiving module reacts when the event is dispatched. This keeps the two
modules consistent even if the process dies right after the commit.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.shared.ids import new_id
from app.shared.tracing.context import get_trace_id
from app.system.jobs.model import SysOutboxEvent

STATUS_PENDING: str = "PENDING"
STATUS_PROCESSING: str = "PROCESSING"
STATUS_PROCESSED: str = "PROCESSED"
STATUS_FAILED: str = "FAILED"


class OutboxService:
    """Writes and drains outbox events."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    async def publish(
        self,
        session: AsyncSession,
        *,
        event_type: str,
        aggregate_type: str,
        aggregate_id: str | int,
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
        available_at: datetime | None = None,
    ) -> SysOutboxEvent:
        """Append an event to the caller's transaction."""
        event = SysOutboxEvent(
            id=new_id(),
            event_id=event_id or uuid.uuid4().hex,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=str(aggregate_id),
            payload=payload or {},
            status=STATUS_PENDING,
            attempt_count=0,
            available_at=available_at or datetime.now(tz=UTC),
            trace_id=get_trace_id(),
        )
        session.add(event)
        await session.flush()
        return event

    async def claim_batch(
        self,
        session: AsyncSession,
        *,
        batch_size: int | None = None,
        now: datetime | None = None,
    ) -> list[SysOutboxEvent]:
        """Claim the next events for processing.

        ``FOR UPDATE SKIP LOCKED`` lets several workers drain the same table
        without blocking or double processing each other.
        """
        reference = now or datetime.now(tz=UTC)
        subquery = (
            select(SysOutboxEvent.id)
            .where(
                SysOutboxEvent.status == STATUS_PENDING,
                SysOutboxEvent.available_at <= reference,
            )
            .order_by(SysOutboxEvent.available_at, SysOutboxEvent.id)
            .limit(batch_size or self._settings.OUTBOX_BATCH_SIZE)
            .with_for_update(skip_locked=True)
        )
        identifiers = list((await session.execute(subquery)).scalars())
        if not identifiers:
            return []
        await session.execute(
            update(SysOutboxEvent)
            .where(SysOutboxEvent.id.in_(identifiers))
            .values(status=STATUS_PROCESSING, attempt_count=SysOutboxEvent.attempt_count + 1)
        )
        rows = list(
            (
                await session.execute(
                    select(SysOutboxEvent).where(SysOutboxEvent.id.in_(identifiers))
                )
            ).scalars()
        )
        return rows

    async def mark_processed(
        self, session: AsyncSession, *, event_id: int, now: datetime | None = None
    ) -> None:
        """Mark an event as delivered."""
        reference = now or datetime.now(tz=UTC)
        await session.execute(
            update(SysOutboxEvent)
            .where(SysOutboxEvent.id == event_id)
            .values(status=STATUS_PROCESSED, processed_at=reference, last_error=None)
        )

    async def mark_failure(
        self,
        session: AsyncSession,
        *,
        event_id: int,
        error: str,
        now: datetime | None = None,
    ) -> None:
        """Record a delivery failure and schedule a retry."""
        reference = now or datetime.now(tz=UTC)
        await session.execute(
            update(SysOutboxEvent)
            .where(SysOutboxEvent.id == event_id)
            .values(
                status=STATUS_FAILED,
                last_error=error[:4000],
                available_at=reference
                + timedelta(seconds=self._settings.OUTBOX_RETRY_DELAY_SECONDS),
            )
        )

    async def requeue_failed(self, session: AsyncSession) -> int:
        """Put failed events that still have attempts left back into the queue."""
        result = await session.execute(
            update(SysOutboxEvent)
            .where(
                SysOutboxEvent.status == STATUS_FAILED,
                SysOutboxEvent.attempt_count < self._settings.OUTBOX_MAX_ATTEMPTS,
            )
            .values(status=STATUS_PENDING)
        )
        return int(result.rowcount or 0)

    @property
    def enabled(self) -> bool:
        return self._settings.OUTBOX_ENABLED
