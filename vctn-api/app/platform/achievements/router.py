"""app.platform.achievements — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.dependencies import DbSessionDep
from app.platform.achievements.schema import AchievementResponse, UserAchievementResponse
from app.platform.achievements.service import AchievementService
from app.shared.authorization.dependencies import PlatformPrincipal
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> AchievementService:
    return AchievementService(session)


@router.get("/achievements", response_model=ApiResponse[list[AchievementResponse]])
async def list_achievements(session: DbSessionDep) -> ApiResponse[list[AchievementResponse]]:
    return success(await _service(session).list_achievements())


@router.get("/achievements/me", response_model=ApiResponse[list[UserAchievementResponse]])
async def my_achievements(
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[list[UserAchievementResponse]]:
    return success(await _service(session).my_achievements(principal.subject_id))
