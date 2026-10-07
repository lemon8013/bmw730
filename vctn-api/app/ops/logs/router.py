"""app.ops.logs — HTTP endpoints.

Every endpoint requires ``OPS_LOG_VIEW``. The module exposes no log writing and
no search across raw bodies: the four existing streams are projected onto one
redacted shape, so the most sensitive thing that can leave the API is a metadata
payload whose secrets have been replaced by ``***``.

``host`` is accepted for symmetry with the other log screens but the four
streams store no host column: using it is a validation error rather than a
silently ignored filter.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.logs.schema import (
    DEFAULT_LOG_TYPE,
    LogContextResponse,
    LogEntryResponse,
)
from app.ops.logs.service import OpsLogService
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import MAX_PAGE_SIZE, Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> OpsLogService:
    return OpsLogService(session)


@router.get(
    "/logs",
    response_model=ApiResponse[Page[LogEntryResponse]],
    dependencies=[Depends(require_permission("OPS_LOG_VIEW"))],
)
async def search_logs(
    session: DbSessionDep,
    log_type: str = Query(default=DEFAULT_LOG_TYPE),
    level: str | None = Query(default=None),
    service: str | None = Query(default=None),
    host: str | None = Query(default=None),
    trace_id: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    keyword: str | None = Query(default=None),
    ip: str | None = Query(default=None),
    start_at: datetime.datetime | None = Query(default=None),
    end_at: datetime.datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=MAX_PAGE_SIZE),
) -> ApiResponse[Page[LogEntryResponse]]:
    return success(
        await _service(session).search(
            log_type=log_type,
            level=level,
            service=service,
            host=host,
            trace_id=trace_id,
            request_id=request_id,
            keyword=keyword,
            ip=ip,
            start_at=start_at,
            end_at=end_at,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get(
    "/logs/context",
    response_model=ApiResponse[LogContextResponse],
    dependencies=[Depends(require_permission("OPS_LOG_VIEW"))],
)
async def get_log_context(
    session: DbSessionDep,
    trace_id: str = Query(min_length=1),
    limit: int = Query(default=100, ge=1, le=MAX_PAGE_SIZE),
) -> ApiResponse[LogContextResponse]:
    return success(await _service(session).context(trace_id, limit=limit))


@router.get(
    "/logs/{log_id}",
    response_model=ApiResponse[LogEntryResponse],
    dependencies=[Depends(require_permission("OPS_LOG_VIEW"))],
)
async def get_log(
    log_id: str,
    session: DbSessionDep,
    log_type: str = Query(default=DEFAULT_LOG_TYPE),
) -> ApiResponse[LogEntryResponse]:
    return success(await _service(session).get(log_type, int(log_id)))
