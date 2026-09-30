"""app.platform.points — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import DbSessionDep
from app.platform.points.repository import PointRepository
from app.platform.points.schema import (
    PointAccountResponse,
    PointRuleResponse,
    PointTransactionResponse,
)
from app.platform.points.service import PointService
from app.shared.authorization.dependencies import PlatformPrincipal
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> PointService:
    return PointService(session)


@router.get("/points/me", response_model=ApiResponse[PointAccountResponse])
async def my_points(
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[PointAccountResponse]:
    return success(await _service(session).account(principal.subject_id))


@router.get(
    "/points/me/transactions",
    response_model=ApiResponse[Page[PointTransactionResponse]],
)
async def my_point_transactions(
    session: DbSessionDep,
    principal: PlatformPrincipal,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[PointTransactionResponse]]:
    return success(
        await _service(session).transactions(
            principal.subject_id, page=PageParams(page=page, page_size=page_size)
        )
    )


@router.get("/point-rules/public", response_model=ApiResponse[list[PointRuleResponse]])
async def public_point_rules(session: DbSessionDep) -> ApiResponse[list[PointRuleResponse]]:
    rows = await PointRepository(session).list_rules()
    return success(
        [
            PointRuleResponse(
                id=str(int(row.id)),
                rule_code=str(row.rule_code),
                rule_name=str(row.rule_name),
                event_code=str(row.event_code),
                points=int(row.points),
                daily_limit=None if row.daily_limit is None else int(row.daily_limit),
                cooldown_seconds=row.cooldown_seconds,
                enabled=bool(row.enabled),
                conditions=row.conditions,
                description=row.description,
            )
            for row in rows
            if bool(row.enabled)
        ]
    )
