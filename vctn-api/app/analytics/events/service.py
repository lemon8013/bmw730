"""app.analytics.events — business logic."""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.events.model import BehaviorEvent, BehaviorIdentityMerge
from app.analytics.events.repository import BehaviorEventRepository
from app.analytics.events.schema import (
    BehaviorEventResponse,
    BehaviorEventWriteRequest,
    IdentityMergeRequest,
    IdentityMergeResponse,
)
from app.core.config import Settings, get_settings
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams


def _coerce_int_id(value: str | None) -> int | None:
    if value is None:
        return None
    return int(value)


class BehaviorEventService:
    """Ingest and query raw tracking events."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = BehaviorEventRepository(session)
        self._settings = settings or get_settings()

    async def write_event(self, req: BehaviorEventWriteRequest) -> BehaviorEventResponse:
        """Persist one tracking event, deduplicating on ``event_id``."""
        event_id = req.event_id or str(new_id())
        existing = await self._repository.event_by_event_id(event_id)
        if existing is not None:
            await self._session.commit()
            return self._to_event(existing)

        now = datetime.datetime.now(datetime.UTC)
        row = await self._repository.add_event(
            event_id=event_id,
            event_code=req.event_code,
            event_name=req.event_name,
            anonymous_id_hash=req.anonymous_id_hash,
            user_id=_coerce_int_id(req.user_id),
            session_id=_coerce_int_id(req.session_id),
            platform=req.platform,
            device_type=req.device_type,
            os=req.os,
            browser=req.browser,
            app_code=req.app_code,
            app_version=req.app_version,
            page_code=req.page_code,
            page_url=req.page_url,
            referrer=req.referrer,
            module=req.module,
            resource_type=req.resource_type,
            resource_id=req.resource_id,
            properties=req.properties,
            trace_id=req.trace_id,
            request_id=req.request_id,
            occurred_at=req.occurred_at or now,
        )
        await self._session.commit()
        return self._to_event(row)

    async def write_identity_merge(
        self, req: IdentityMergeRequest, *, operator_id: int | None = None
    ) -> IdentityMergeResponse:
        """Merge an anonymous identity into a user, idempotently."""
        user_id = _coerce_int_id(req.user_id)
        existing = await self._repository.merge_by_key(
            anonymous_id_hash=req.anonymous_id_hash, user_id=user_id
        )
        if existing is not None:
            await self._session.commit()
            return self._to_merge(existing)

        row = await self._repository.add_merge(
            anonymous_id_hash=req.anonymous_id_hash,
            user_id=user_id,
            first_seen_at=req.first_seen_at,
        )
        await write_operation_log(
            self._session,
            operation="ANALYTICS_IDENTITY_MERGE",
            result=RESULT_SUCCESS,
            operator_id=operator_id,
            resource_type="behavior_identity_merge",
            resource_id=str(int(row.id)),
            metadata={
                "anonymous_id_hash": req.anonymous_id_hash,
                "user_id": req.user_id,
            },
        )
        await self._session.commit()
        return self._to_merge(row)

    async def list_events(
        self,
        *,
        event_code: str | None = None,
        start: datetime.datetime | None = None,
        end: datetime.datetime | None = None,
        page: PageParams,
    ) -> Page[BehaviorEventResponse]:
        total = await self._repository.count_events(
            event_code=event_code, start=start, end=end
        )
        rows = await self._repository.list_events(
            event_code=event_code,
            start=start,
            end=end,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_event(row) for row in rows], total=total, params=page
        )

    async def list_identity_merges(
        self,
        *,
        anonymous_id_hash: str | None = None,
        user_id: int | None = None,
        page: PageParams,
    ) -> Page[IdentityMergeResponse]:
        total = await self._repository.count_merges(
            anonymous_id_hash=anonymous_id_hash, user_id=user_id
        )
        rows = await self._repository.list_merges(
            anonymous_id_hash=anonymous_id_hash,
            user_id=user_id,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_merge(row) for row in rows], total=total, params=page
        )

    def _to_event(self, row: BehaviorEvent) -> BehaviorEventResponse:
        return BehaviorEventResponse(
            id=str(int(row.id)),
            event_id=row.event_id,
            event_code=row.event_code,
            event_name=row.event_name,
            anonymous_id_hash=row.anonymous_id_hash,
            user_id=None if row.user_id is None else str(int(row.user_id)),
            session_id=None if row.session_id is None else str(int(row.session_id)),
            platform=row.platform,
            device_type=row.device_type,
            os=row.os,
            browser=row.browser,
            app_code=row.app_code,
            app_version=row.app_version,
            page_code=row.page_code,
            page_url=row.page_url,
            referrer=row.referrer,
            module=row.module,
            resource_type=row.resource_type,
            resource_id=row.resource_id,
            properties=row.properties,
            trace_id=row.trace_id,
            request_id=row.request_id,
            occurred_at=row.occurred_at,
            received_at=row.received_at,
        )

    def _to_merge(self, row: BehaviorIdentityMerge) -> IdentityMergeResponse:
        return IdentityMergeResponse(
            id=str(int(row.id)),
            anonymous_id_hash=row.anonymous_id_hash,
            user_id=None if row.user_id is None else str(int(row.user_id)),
            first_seen_at=row.first_seen_at,
            merged_at=row.merged_at,
        )
