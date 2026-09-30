"""app.analytics.events — HTTP endpoints."""

from __future__ import annotations

import datetime
import os
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from app.analytics.events.schema import (
    BehaviorEventResponse,
    BehaviorEventWriteRequest,
    IdentityMergeRequest,
    IdentityMergeResponse,
)
from app.analytics.events.service import BehaviorEventService
from app.core.dependencies import DbSessionDep
from app.core.exceptions import AuthenticationError
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import (
    require_permission,
    resolve_optional_principal,
)
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()

_INTERNAL_TOKEN_HEADER = "x-internal-token"


async def _require_event_writer(
    request: Request,
    session: DbSessionDep,
    principal: Annotated[Principal | None, Depends(resolve_optional_principal)],
) -> Principal | None:
    """Allow an admin principal or a trusted internal token.

    Returns the :class:`Principal` for an authenticated admin, or ``None`` when
    the request was authorised through the shared internal token (an anonymous
    but trusted writer such as the tool runtime outbox consumer).
    """
    if principal is not None and principal.is_admin:
        return principal
    expected = os.environ.get("VCTN_INTERNAL_TOKEN")
    if expected:
        provided = request.headers.get(_INTERNAL_TOKEN_HEADER)
        if provided and provided == expected:
            return None
    raise AuthenticationError("event writer authentication required")


def _range(
    date_from: datetime.date | None, date_to: datetime.date | None
) -> tuple[datetime.datetime | None, datetime.datetime | None]:
    start = None
    end = None
    if date_from is not None:
        start = datetime.datetime.combine(date_from, datetime.time.min, tzinfo=datetime.UTC)
    if date_to is not None:
        end = datetime.datetime.combine(date_to, datetime.time.max, tzinfo=datetime.UTC)
    return start, end


@router.post("/events", response_model=ApiResponse[BehaviorEventResponse])
async def ingest_event(
    payload: BehaviorEventWriteRequest,
    session: DbSessionDep,
    _writer: Annotated[Principal | None, Depends(_require_event_writer)],
) -> ApiResponse[BehaviorEventResponse]:
    return success(await BehaviorEventService(session).write_event(payload))


@router.post("/identity-merge", response_model=ApiResponse[IdentityMergeResponse])
async def merge_identity(
    payload: IdentityMergeRequest,
    session: DbSessionDep,
    _writer: Annotated[Principal | None, Depends(_require_event_writer)],
) -> ApiResponse[IdentityMergeResponse]:
    operator_id = None if _writer is None else _writer.subject_id
    return success(
        await BehaviorEventService(session).write_identity_merge(
            payload, operator_id=operator_id
        )
    )


@router.get("/events", response_model=ApiResponse[Page[BehaviorEventResponse]])
async def query_events(
    session: DbSessionDep,
    _principal: Annotated[Principal, Depends(require_permission("ANALYTICS_VIEW"))],
    event_code: str | None = Query(default=None),
    date_from: datetime.date | None = Query(default=None),
    date_to: datetime.date | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[BehaviorEventResponse]]:
    start, end = _range(date_from, date_to)
    return success(
        await BehaviorEventService(session).list_events(
            event_code=event_code,
            start=start,
            end=end,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get(
    "/identity-merges", response_model=ApiResponse[Page[IdentityMergeResponse]]
)
async def query_identity_merges(
    session: DbSessionDep,
    _principal: Annotated[Principal, Depends(require_permission("ANALYTICS_VIEW"))],
    anonymous_id_hash: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[IdentityMergeResponse]]:
    return success(
        await BehaviorEventService(session).list_identity_merges(
            anonymous_id_hash=anonymous_id_hash,
            user_id=user_id,
            page=PageParams(page=page, page_size=page_size),
        )
    )
