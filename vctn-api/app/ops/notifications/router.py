"""app.ops.notifications — HTTP endpoints.

Notification reads require ``OPS_ALERT_VIEW``; channel management requires
``OPS_ALERT_MANAGE``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.alerts.schema import AlertNotificationResponse
from app.ops.notifications.schema import (
    NotificationChannelCreateRequest,
    NotificationChannelResponse,
    NotificationChannelUpdateRequest,
)
from app.ops.notifications.service import NotificationService
from app.shared.authorization.dependencies import AdminPrincipal, require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> NotificationService:
    return NotificationService(session)


@router.get(
    "/notifications",
    response_model=ApiResponse[Page[AlertNotificationResponse]],
    dependencies=[Depends(require_permission("OPS_ALERT_VIEW"))],
)
async def list_notifications(
    session: DbSessionDep,
    status: str | None = Query(default=None),
    alert_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[AlertNotificationResponse]]:
    return success(
        await _service(session).list_notifications(
            status=status,
            alert_id=int(alert_id) if alert_id else None,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get(
    "/notification-channels",
    response_model=ApiResponse[Page[NotificationChannelResponse]],
    dependencies=[Depends(require_permission("OPS_ALERT_VIEW"))],
)
async def list_notification_channels(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    channel_type: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[NotificationChannelResponse]]:
    return success(
        await _service(session).list_channels(
            keyword=keyword,
            channel_type=channel_type,
            enabled=enabled,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.post(
    "/notification-channels",
    response_model=ApiResponse[NotificationChannelResponse],
    dependencies=[Depends(require_permission("OPS_ALERT_MANAGE"))],
)
async def create_notification_channel(
    payload: NotificationChannelCreateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[NotificationChannelResponse]:
    return success(await _service(session).create_channel(principal, payload))


@router.put(
    "/notification-channels/{channel_id}",
    response_model=ApiResponse[NotificationChannelResponse],
    dependencies=[Depends(require_permission("OPS_ALERT_MANAGE"))],
)
async def update_notification_channel(
    channel_id: str,
    payload: NotificationChannelUpdateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[NotificationChannelResponse]:
    return success(
        await _service(session).update_channel(principal, int(channel_id), payload)
    )
