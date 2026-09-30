"""app.analytics.events — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class BehaviorEventWriteRequest(ApiModel):
    """Inbound tracking event (front end or internal service)."""

    event_id: str | None = None
    event_code: str
    event_name: str | None = None
    anonymous_id_hash: str | None = None
    user_id: OptionalStringId | None = None
    session_id: OptionalStringId | None = None
    platform: str | None = None
    device_type: str | None = None
    os: str | None = None
    browser: str | None = None
    app_code: str | None = None
    app_version: str | None = None
    page_code: str | None = None
    page_url: str | None = None
    referrer: str | None = None
    module: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    properties: dict | None = None
    trace_id: str | None = None
    request_id: str | None = None
    occurred_at: datetime.datetime | None = None


class BehaviorEventResponse(ApiModel):
    """One stored tracking event."""

    id: StringId
    event_id: str
    event_code: str
    event_name: str | None = None
    anonymous_id_hash: str | None = None
    user_id: OptionalStringId | None = None
    session_id: OptionalStringId | None = None
    platform: str | None = None
    device_type: str | None = None
    os: str | None = None
    browser: str | None = None
    app_code: str | None = None
    app_version: str | None = None
    page_code: str | None = None
    page_url: str | None = None
    referrer: str | None = None
    module: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    properties: dict | None = None
    trace_id: str | None = None
    request_id: str | None = None
    occurred_at: datetime.datetime
    received_at: datetime.datetime


class IdentityMergeRequest(ApiModel):
    """Merge an anonymous visitor identity into a logged in user."""

    anonymous_id_hash: str
    user_id: OptionalStringId | None = None
    first_seen_at: datetime.datetime | None = None


class IdentityMergeResponse(ApiModel):
    """Result of an identity merge."""

    id: StringId
    anonymous_id_hash: str
    user_id: OptionalStringId | None = None
    first_seen_at: datetime.datetime | None = None
    merged_at: datetime.datetime
