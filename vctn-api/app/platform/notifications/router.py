"""app.platform.notifications — HTTP endpoints (system area: /notifications)."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import DbSessionDep
from app.platform.notifications.schema import NotificationPage
from app.platform.notifications.service import NotificationService, user_type_for
from app.shared.authorization.dependencies import CurrentPrincipal
from app.shared.pagination.params import PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> NotificationService:
    return NotificationService(session)


@router.get("/notifications", response_model=ApiResponse[NotificationPage])
async def list_notifications(
    session: DbSessionDep,
    principal: CurrentPrincipal,
    unread_only: bool = Query(default=False),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[NotificationPage]:
    return success(
        await _service(session).list_for(
            user_type=user_type_for(principal.is_admin),
            user_id=principal.subject_id,
            unread_only=unread_only,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.post("/notifications/{notification_id}/read", response_model=ApiResponse[dict])
async def read_notification(
    notification_id: str,
    session: DbSessionDep,
    principal: CurrentPrincipal,
) -> ApiResponse[dict]:
    changed = await _service(session).mark_read(
        user_type=user_type_for(principal.is_admin),
        user_id=principal.subject_id,
        notification_id=int(notification_id),
    )
    return success({"read": True, "changed": changed, "notification_id": notification_id})


@router.post("/notifications/read-all", response_model=ApiResponse[dict])
async def read_all_notifications(
    session: DbSessionDep,
    principal: CurrentPrincipal,
) -> ApiResponse[dict]:
    changed = await _service(session).mark_all_read(
        user_type=user_type_for(principal.is_admin), user_id=principal.subject_id
    )
    return success({"changed": changed})
