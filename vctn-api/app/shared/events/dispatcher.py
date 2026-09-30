"""Outbox event dispatcher.

Handlers are registered per event type. A module registers its own handler for
the events it consumes, which keeps cross-module coupling declarative: the
publisher only knows the event type, never the consumer.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Final

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import Settings, get_settings
from app.shared.outbox.service import OutboxService

_LOGGER: Final = logging.getLogger("vctn.outbox")


@dataclass(frozen=True, slots=True)
class OutboxEventRef:
    """Detached view of an outbox event handed to a handler."""

    id: int
    event_id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: dict[str, Any]


OutboxHandler = Callable[[AsyncSession, OutboxEventRef], Awaitable[None]]


class OutboxDispatcher:
    """Routes outbox events to the handler registered for their type."""

    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()
        self._outbox = OutboxService(self._settings)
        self._handlers: dict[str, OutboxHandler] = {}

    def register(self, event_type: str, handler: OutboxHandler) -> None:
        """Register the handler that consumes ``event_type``."""
        self._handlers[event_type] = handler

    def registered_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))

    async def dispatch_batch(
        self,
        factory: async_sessionmaker[AsyncSession],
        *,
        batch_size: int | None = None,
    ) -> int:
        """Claim and deliver one batch of pending events.

        Each event gets its own transaction so one failing handler cannot undo
        the delivery of the events before it. Returns the number of processed
        events.
        """
        processed = 0
        for _ in range(max(1, batch_size or self._settings.OUTBOX_BATCH_SIZE)):
            event = await self._claim_one(factory)
            if event is None:
                break
            await self._deliver(factory, event)
            processed += 1
        return processed

    async def _claim_one(self, factory: async_sessionmaker[AsyncSession]) -> OutboxEventRef | None:
        async with factory() as session:
            events = await self._outbox.claim_batch(session, batch_size=1)
            if not events:
                await session.rollback()
                return None
            event = events[0]
            reference = OutboxEventRef(
                id=int(event.id),
                event_id=str(event.event_id),
                event_type=str(event.event_type),
                aggregate_type=str(event.aggregate_type),
                aggregate_id=str(event.aggregate_id),
                payload=dict(event.payload or {}),
            )
            await session.commit()
            return reference

    async def _deliver(
        self, factory: async_sessionmaker[AsyncSession], event: OutboxEventRef
    ) -> None:
        handler = self._handlers.get(str(event.event_type))
        async with factory() as session:
            if handler is None:
                _LOGGER.warning("no outbox handler registered for %s", event.event_type)
                await self._outbox.mark_processed(session, event_id=event.id)
                await session.commit()
                return
            try:
                await handler(session, event)
            except Exception as exc:  # noqa: BLE001 - one bad event must not stop the drain
                await self._outbox.mark_failure(session, event_id=event.id, error=str(exc))
                await session.commit()
                _LOGGER.warning("outbox event %s failed: %s", event.event_type, type(exc).__name__)
                return
            await self._outbox.mark_processed(session, event_id=event.id)
            await session.commit()


_DISPATCHER: OutboxDispatcher | None = None


def get_dispatcher(settings: Settings | None = None) -> OutboxDispatcher:
    """Return the process wide dispatcher."""
    global _DISPATCHER
    if _DISPATCHER is None:
        _DISPATCHER = OutboxDispatcher(settings)
    return _DISPATCHER


def reset_dispatcher() -> None:
    """Drop the process wide dispatcher (used by the test suite)."""
    global _DISPATCHER
    _DISPATCHER = None
