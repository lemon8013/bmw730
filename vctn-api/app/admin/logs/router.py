"""app.admin.logs — HTTP endpoints.

Read-only inspection of the five separated log streams. Every response is
redacted by the service layer before it is returned — no password, MFA secret,
API key, token, JWT or raw input can ever leave these endpoints, and phone /
email values are masked.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query

from app.admin.audit.schema import (
    AccessLogResponse,
    AuditLogResponse,
    OperationLogResponse,
    SecurityLogResponse,
    TraceResponse,
)
from app.admin.export.schema import ExportTaskResponse
from app.admin.logs.schema import (
    ApplicationLogResponse,
    LogsSummaryResponse,
)
from app.admin.logs.service import LogsQueryService, _recursive_mask
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()

_LOG_UNION = (
    AuditLogResponse
    | SecurityLogResponse
    | OperationLogResponse
    | AccessLogResponse
    | ApplicationLogResponse
)


def _parse(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError as exc:
        from app.core.exceptions import ValidationError

        raise ValidationError("date filters must be ISO 8601 timestamps") from exc


@router.get("/logs", response_model=ApiResponse[LogsSummaryResponse])
async def logs_summary(
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("LOG_VIEW")),
) -> ApiResponse[LogsSummaryResponse]:
    return success(await LogsQueryService(session).summary())


@router.get("/logs/{log_type}", response_model=ApiResponse[Page[_LOG_UNION]])
async def query_logs(
    log_type: str,
    session: DbSessionDep,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    level: str | None = Query(default=None),
    result: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("LOG_VIEW")),
) -> ApiResponse[Page[_LOG_UNION]]:
    return success(
        await LogsQueryService(session).query(
            log_type,
            start=_parse(start),
            end=_parse(end),
            level=level,
            result=result,
            keyword=keyword,
            user_id=int(user_id) if user_id else None,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get("/logs/audit/traces/{trace_id}", response_model=ApiResponse[TraceResponse])
async def logs_trace(
    trace_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("LOG_VIEW")),
) -> ApiResponse[TraceResponse]:
    return success(await LogsQueryService(session).trace(trace_id))


@router.post("/logs/{log_type}/export", response_model=ApiResponse[ExportTaskResponse])
async def export_logs(
    log_type: str,
    session: DbSessionDep,
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    level: str | None = Query(default=None),
    result: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    principal: Principal = Depends(require_permission("LOG_VIEW")),
) -> ApiResponse[ExportTaskResponse]:
    params = {
        "log_type": log_type,
        "start": start,
        "end": end,
        "level": level,
        "result": result,
        "keyword": keyword,
        "user_id": user_id,
    }
    task = await LogsQueryService(session).trigger_export(
        log_type=log_type,
        actor_id=principal.subject_id,
        actor_username=principal.username,
        params=_recursive_mask(params),
    )
    return success(task)
