"""app.admin.audit — HTTP endpoints."""

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
from app.admin.audit.service import AuditQueryService
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> AuditQueryService:
    return AuditQueryService(session)


def _parse(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except ValueError as exc:
        from app.core.exceptions import ValidationError

        raise ValidationError("date filters must be ISO 8601 timestamps") from exc


@router.get("/audit/logs", response_model=ApiResponse[Page[AuditLogResponse]])
async def list_audit_logs(
    session: DbSessionDep,
    action: str | None = Query(default=None),
    operator_id: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    resource_id: str | None = Query(default=None),
    result: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("AUDIT_VIEW")),
) -> ApiResponse[Page[AuditLogResponse]]:
    return success(
        await _service(session).audit_logs(
            action=action,
            operator_id=int(operator_id) if operator_id else None,
            resource_type=resource_type,
            resource_id=resource_id,
            result=result,
            start=_parse(start),
            end=_parse(end),
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get("/audit/logs/{log_id}", response_model=ApiResponse[AuditLogResponse])
async def get_audit_log(
    log_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("AUDIT_VIEW")),
) -> ApiResponse[AuditLogResponse]:
    return success(await _service(session).audit_log(int(log_id)))


@router.get("/traces/{trace_id}", response_model=ApiResponse[TraceResponse])
async def get_trace(
    trace_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("TRACE_VIEW")),
) -> ApiResponse[TraceResponse]:
    return success(await _service(session).trace(trace_id))


@router.get("/security/logs", response_model=ApiResponse[Page[SecurityLogResponse]])
async def list_security_logs(
    session: DbSessionDep,
    event_type: str | None = Query(default=None),
    user_id: str | None = Query(default=None),
    result: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("SECURITY_LOG_VIEW")),
) -> ApiResponse[Page[SecurityLogResponse]]:
    return success(
        await _service(session).security_logs(
            event_type=event_type,
            user_id=int(user_id) if user_id else None,
            result=result,
            start=_parse(start),
            end=_parse(end),
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get("/operation/logs", response_model=ApiResponse[Page[OperationLogResponse]])
async def list_operation_logs(
    session: DbSessionDep,
    operation: str | None = Query(default=None),
    operator_id: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    result: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("OPERATION_LOG_VIEW")),
) -> ApiResponse[Page[OperationLogResponse]]:
    return success(
        await _service(session).operation_logs(
            operation=operation,
            operator_id=int(operator_id) if operator_id else None,
            resource_type=resource_type,
            result=result,
            start=_parse(start),
            end=_parse(end),
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get("/access/logs", response_model=ApiResponse[Page[AccessLogResponse]])
async def list_access_logs(
    session: DbSessionDep,
    method: str | None = Query(default=None),
    path: str | None = Query(default=None),
    status_code: int | None = Query(default=None),
    user_id: str | None = Query(default=None),
    start: str | None = Query(default=None),
    end: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("ACCESS_LOG_VIEW")),
) -> ApiResponse[Page[AccessLogResponse]]:
    return success(
        await _service(session).access_logs(
            method=method,
            path=path,
            status_code=status_code,
            user_id=int(user_id) if user_id else None,
            start=_parse(start),
            end=_parse(end),
            page=PageParams(page=page, page_size=page_size),
        )
    )
