"""app.ops.alerts — HTTP endpoints.

Read endpoints require ``OPS_ALERT_VIEW``; rule management and evaluation
require ``OPS_ALERT_MANAGE``; acknowledging and silencing have their own
permissions (``OPS_ALERT_ACK`` / ``OPS_ALERT_SILENCE``).
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.alerts.schema import (
    AlertAckRequest,
    AlertEvaluationResponse,
    AlertResolveRequest,
    AlertResponse,
    AlertRuleCreateRequest,
    AlertRuleResponse,
    AlertRuleUpdateRequest,
    AlertSilenceRequest,
)
from app.ops.alerts.service import AlertService
from app.shared.authorization.dependencies import AdminPrincipal, require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> AlertService:
    return AlertService(session)


@router.get(
    "/alerts",
    response_model=ApiResponse[Page[AlertResponse]],
    dependencies=[Depends(require_permission("OPS_ALERT_VIEW"))],
)
async def list_alerts(
    session: DbSessionDep,
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    alert_type: str | None = Query(default=None),
    start: datetime.datetime | None = Query(default=None),
    end: datetime.datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[AlertResponse]]:
    return success(
        await _service(session).list_alerts(
            status=status,
            severity=severity,
            alert_type=alert_type,
            start=start,
            end=end,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get(
    "/alerts/{alert_id}",
    response_model=ApiResponse[AlertResponse],
    dependencies=[Depends(require_permission("OPS_ALERT_VIEW"))],
)
async def get_alert(alert_id: str, session: DbSessionDep) -> ApiResponse[AlertResponse]:
    return success(await _service(session).get_alert(int(alert_id)))


@router.post(
    "/alerts/{alert_id}/ack",
    response_model=ApiResponse[AlertResponse],
    dependencies=[Depends(require_permission("OPS_ALERT_ACK"))],
)
async def acknowledge_alert(
    alert_id: str,
    payload: AlertAckRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[AlertResponse]:
    return success(
        await _service(session).acknowledge_alert(principal, int(alert_id), payload)
    )


@router.post(
    "/alerts/{alert_id}/silence",
    response_model=ApiResponse[AlertResponse],
    dependencies=[Depends(require_permission("OPS_ALERT_SILENCE"))],
)
async def silence_alert(
    alert_id: str,
    payload: AlertSilenceRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[AlertResponse]:
    return success(await _service(session).silence_alert(principal, int(alert_id), payload))


@router.post(
    "/alerts/{alert_id}/resolve",
    response_model=ApiResponse[AlertResponse],
    dependencies=[Depends(require_permission("OPS_ALERT_MANAGE"))],
)
async def resolve_alert(
    alert_id: str,
    payload: AlertResolveRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[AlertResponse]:
    return success(await _service(session).resolve_alert(principal, int(alert_id), payload))


@router.post(
    "/alerts/evaluate",
    response_model=ApiResponse[AlertEvaluationResponse],
    dependencies=[Depends(require_permission("OPS_ALERT_MANAGE"))],
)
async def evaluate_alerts(
    session: DbSessionDep, principal: AdminPrincipal
) -> ApiResponse[AlertEvaluationResponse]:
    return success(await _service(session).evaluate(principal))


@router.get(
    "/alert-rules",
    response_model=ApiResponse[Page[AlertRuleResponse]],
    dependencies=[Depends(require_permission("OPS_ALERT_VIEW"))],
)
async def list_alert_rules(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    alert_type: str | None = Query(default=None),
    enabled: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[AlertRuleResponse]]:
    return success(
        await _service(session).list_rules(
            keyword=keyword,
            alert_type=alert_type,
            enabled=enabled,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.post(
    "/alert-rules",
    response_model=ApiResponse[AlertRuleResponse],
    dependencies=[Depends(require_permission("OPS_ALERT_MANAGE"))],
)
async def create_alert_rule(
    payload: AlertRuleCreateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[AlertRuleResponse]:
    return success(await _service(session).create_rule(principal, payload))


@router.put(
    "/alert-rules/{rule_id}",
    response_model=ApiResponse[AlertRuleResponse],
    dependencies=[Depends(require_permission("OPS_ALERT_MANAGE"))],
)
async def update_alert_rule(
    rule_id: str,
    payload: AlertRuleUpdateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[AlertRuleResponse]:
    return success(await _service(session).update_rule(principal, int(rule_id), payload))


@router.delete(
    "/alert-rules/{rule_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission("OPS_ALERT_MANAGE"))],
)
async def delete_alert_rule(
    rule_id: str, session: DbSessionDep, principal: AdminPrincipal
) -> ApiResponse[dict]:
    await _service(session).delete_rule(principal, int(rule_id))
    return success({"deleted": True, "rule_id": rule_id})
