"""app.ops.audit — HTTP endpoints.

Every endpoint requires ``OPS_AUDIT_VIEW`` and every endpoint is a read: the
trail is append-only, so this router deliberately exposes no write method.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.audit.schema import AuditRecordResponse
from app.ops.audit.service import AuditService
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> AuditService:
    return AuditService(session)


@router.get(
    "/audit",
    response_model=ApiResponse[Page[AuditRecordResponse]],
    dependencies=[Depends(require_permission("OPS_AUDIT_VIEW"))],
)
async def list_audit_records(
    session: DbSessionDep,
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    operator_username: str | None = Query(default=None),
    result: str | None = Query(default=None),
    trace_id: str | None = Query(default=None),
    start_at: datetime.datetime | None = Query(default=None),
    end_at: datetime.datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[AuditRecordResponse]]:
    return success(
        await _service(session).list_records(
            action=action,
            resource_type=resource_type,
            operator_username=operator_username,
            result=result,
            trace_id=trace_id,
            start_at=start_at,
            end_at=end_at,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get(
    "/audit/{record_id}",
    response_model=ApiResponse[AuditRecordResponse],
    dependencies=[Depends(require_permission("OPS_AUDIT_VIEW"))],
)
async def get_audit_record(
    record_id: str, session: DbSessionDep
) -> ApiResponse[AuditRecordResponse]:
    return success(await _service(session).get_record(int(record_id)))
