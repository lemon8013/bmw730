"""app.ops.events — HTTP endpoints."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.events.schema import EventResponse
from app.ops.events.service import EventService
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> EventService:
    return EventService(session)


@router.get(
    "/events",
    response_model=ApiResponse[Page[EventResponse]],
    dependencies=[Depends(require_permission("OPS_MONITOR_VIEW"))],
)
async def list_events(
    session: DbSessionDep,
    event_type: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    source: str | None = Query(default=None),
    start: datetime.datetime | None = Query(default=None),
    end: datetime.datetime | None = Query(default=None),
    trace_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[EventResponse]]:
    return success(
        await _service(session).list_events(
            event_type=event_type,
            severity=severity,
            source=source,
            start=start,
            end=end,
            trace_id=trace_id,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get(
    "/events/{event_id}",
    response_model=ApiResponse[EventResponse],
    dependencies=[Depends(require_permission("OPS_MONITOR_VIEW"))],
)
async def get_event(event_id: str, session: DbSessionDep) -> ApiResponse[EventResponse]:
    return success(await _service(session).get_event(int(event_id)))
