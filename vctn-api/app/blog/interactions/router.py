"""app.blog.interactions — HTTP endpoints.

Every interaction endpoint is a platform user action. The operations are
idempotent: repeating a like / favorite / follow returns the current state
rather than failing.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.blog.interactions.schema import (
    FavoriteResponse,
    FollowResponse,
    LikeResponse,
)
from app.blog.interactions.service import InteractionService
from app.core.dependencies import DbSessionDep
from app.shared.authorization.dependencies import PlatformPrincipal
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> InteractionService:
    return InteractionService(session)


@router.post(
    "/articles/{article_id}/like",
    response_model=ApiResponse[LikeResponse],
)
async def like_article(
    article_id: str,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[LikeResponse]:
    return success(await _service(session).like_article(principal, int(article_id)))


@router.delete(
    "/articles/{article_id}/like",
    response_model=ApiResponse[LikeResponse],
)
async def unlike_article(
    article_id: str,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[LikeResponse]:
    return success(await _service(session).unlike_article(principal, int(article_id)))


@router.post(
    "/articles/{article_id}/favorite",
    response_model=ApiResponse[FavoriteResponse],
)
async def favorite_article(
    article_id: str,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[FavoriteResponse]:
    return success(await _service(session).favorite_article(principal, int(article_id)))


@router.delete(
    "/articles/{article_id}/favorite",
    response_model=ApiResponse[FavoriteResponse],
)
async def unfavorite_article(
    article_id: str,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[FavoriteResponse]:
    return success(
        await _service(session).unfavorite_article(principal, int(article_id))
    )


@router.post(
    "/users/{user_id}/follow",
    response_model=ApiResponse[FollowResponse],
)
async def follow_user(
    user_id: str,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[FollowResponse]:
    return success(await _service(session).follow_user(principal, int(user_id)))


@router.delete(
    "/users/{user_id}/follow",
    response_model=ApiResponse[FollowResponse],
)
async def unfollow_user(
    user_id: str,
    session: DbSessionDep,
    principal: PlatformPrincipal,
) -> ApiResponse[FollowResponse]:
    return success(await _service(session).unfollow_user(principal, int(user_id)))
