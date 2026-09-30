"""app.platform.levels — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import DbSessionDep
from app.platform.levels.schema import LevelHistoryResponse, LevelResponse, MyLevelResponse
from app.platform.levels.service import LevelService
from app.shared.authorization.dependencies import PlatformPrincipal
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> LevelService:
    return LevelService(session)


@router.get("/levels", response_model=ApiResponse[list[LevelResponse]])
async def list_levels(session: DbSessionDep) -> ApiResponse[list[LevelResponse]]:
    return success(await _service(session).list_levels())


@router.get("/levels/me", response_model=ApiResponse[MyLevelResponse])
async def my_level(
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[MyLevelResponse]:
    return success(await _service(session).my_level(principal.subject_id))


@router.get("/levels/me/history", response_model=ApiResponse[Page[LevelHistoryResponse]])
async def my_level_history(
    session: DbSessionDep,
    principal: PlatformPrincipal,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[LevelHistoryResponse]]:
    return success(
        await _service(session).history(
            principal.subject_id, page=PageParams(page=page, page_size=page_size)
        )
    )
