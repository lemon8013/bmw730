"""app.platform.growth — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import DbSessionDep
from app.platform.growth.schema import (
    GrowthAccountResponse,
    GrowthTransactionResponse,
)
from app.platform.growth.service import GrowthService
from app.shared.authorization.dependencies import PlatformPrincipal
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> GrowthService:
    return GrowthService(session)


@router.get("/growth/me", response_model=ApiResponse[GrowthAccountResponse])
async def my_growth(
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[GrowthAccountResponse]:
    return success(await _service(session).account(principal.subject_id))


@router.get(
    "/growth/me/transactions",
    response_model=ApiResponse[Page[GrowthTransactionResponse]],
)
async def my_growth_transactions(
    session: DbSessionDep,
    principal: PlatformPrincipal,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[GrowthTransactionResponse]]:
    return success(
        await _service(session).transactions(
            principal.subject_id, page=PageParams(page=page, page_size=page_size)
        )
    )
