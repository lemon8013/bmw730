"""app.ops.events — business logic."""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.ops.events.model import OpsEvent
from app.ops.events.repository import EventRepository
from app.ops.events.schema import EventResponse
from app.shared.pagination.params import Page, PageParams


class EventService:
    """Operations event queries."""

    def __init__(self, session: AsyncSession) -> None:
        self._repository = EventRepository(session)

    async def list_events(
        self,
        *,
        event_type: str | None = None,
        severity: str | None = None,
        source: str | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        trace_id: str | None = None,
        page: PageParams,
    ) -> Page[EventResponse]:
        start_utc = self._as_utc(start, field="start") if start is not None else None
        end_utc = self._as_utc(end, field="end") if end is not None else None
        if start_utc is not None and end_utc is not None and start_utc > end_utc:
            raise ValidationError("start must not be later than end")
        rows, total = await self._repository.list(
            event_type=event_type,
            severity=severity,
            source=source,
            start=start_utc,
            end=end_utc,
            trace_id=trace_id,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get_event(self, event_id: int) -> EventResponse:
        row = await self._repository.get(event_id)
        if row is None:
            raise NotFoundError("event not found")
        return self._to_response(row)

    @staticmethod
    def _as_utc(value: datetime.datetime, *, field: str) -> datetime.datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValidationError(f"{field} must include a UTC offset")
        return value.astimezone(datetime.UTC)

    @staticmethod
    def _to_response(row: OpsEvent) -> EventResponse:
        return EventResponse(
            id=str(int(row.id)),
            event_id=str(row.event_id),
            event_type=str(row.event_type),
            source=str(row.source),
            resource_type=row.resource_type,
            resource_id=str(int(row.resource_id)) if row.resource_id is not None else None,
            severity=str(row.severity),
            message=row.message,
            trace_id=row.trace_id,
            request_id=row.request_id,
            occurred_at=row.occurred_at,
            metadata=row.metadata_payload,
            created_at=row.created_at,
        )
