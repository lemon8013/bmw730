"""app.admin.notifications — HTTP endpoints."""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query

from app.admin.notifications.schema import (
    CreateNotificationRequest,
    NotificationResponse,
    NotificationTypeStat,
)
from app.admin.notifications.service import AdminNotificationService
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _parse(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError as exc:
        from app.core.exceptions import ValidationError

        raise ValidationError("date filters must be ISO 8601 timestamps") from exc


@router.get("/notifications", response_model=ApiResponse[Page[NotificationResponse]])
async def list_notifications(
    session: DbSessionDep,
    user_type: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    notification_type: str | None = Query(default=None),
    unread_only: bool = Query(default=False),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("NOTIFICATION_VIEW")),
) -> ApiResponse[Page[NotificationResponse]]:
    return success(
        await AdminNotificationService(session).list_notifications(
            user_type=user_type,
            user_id=int(user_id) if user_id else None,
            notification_type=notification_type,
            unread_only=unread_only,
            start=_parse(start),
            end=_parse(end),
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.post("/notifications", response_model=ApiResponse[NotificationResponse])
async def send_notification(
    payload: CreateNotificationRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("NOTIFICATION_MANAGE")),
) -> ApiResponse[NotificationResponse]:
    return success(
        await AdminNotificationService(session).send_system_notification(
            actor_id=principal.subject_id,
            actor_username=principal.username,
            payload=payload,
        )
    )


@router.post(
    "/notifications/{notification_id}/read",
    response_model=ApiResponse[NotificationResponse],
)
async def mark_notification_read(
    notification_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("NOTIFICATION_MANAGE")),
) -> ApiResponse[NotificationResponse]:
    return success(
        await AdminNotificationService(session).mark_read(
            notification_id=int(notification_id),
            actor_id=principal.subject_id,
            actor_username=principal.username,
        )
    )


@router.get("/notifications/stats", response_model=ApiResponse[list[NotificationTypeStat]])
async def notification_stats(
    session: DbSessionDep,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    principal: Principal = Depends(require_permission("NOTIFICATION_VIEW")),
) -> ApiResponse[list[NotificationTypeStat]]:
    return success(
        await AdminNotificationService(session).stats(start=_parse(start), end=_parse(end))
    )
