"""app.blog.interactions — business logic.

Likes, favorites and follows are idempotent: repeating an action that is already
in effect returns the current state instead of failing. The service owns the
transaction and keeps the article counters in sync.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.blog.articles.repository import ArticleRepository
from app.blog.interactions.repository import InteractionRepository
from app.blog.interactions.schema import (
    FavoriteResponse,
    FollowResponse,
    LikeResponse,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, NotFoundError
from app.shared.auth.context import Principal
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log


class InteractionService:
    """Likes, favorites and follows."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = InteractionRepository(session)
        self._articles = ArticleRepository(session)
        self._settings = settings or get_settings()

    # ------------------------------------------------------------------
    # Likes
    # ------------------------------------------------------------------
    async def like_article(self, actor: Principal, article_id: int) -> LikeResponse:
        article = await self._articles.get_published(article_id)
        if article is None:
            raise NotFoundError("article not found")
        if await self._repository.like_exists(actor.subject_id, article_id):
            return LikeResponse(
                article_id=str(article_id),
                liked=True,
                like_count=int(article.like_count or 0),
            )
        await self._repository.add_like(actor.subject_id, article_id)
        await self._articles.adjust_count(article_id, "like_count", 1)
        await self._session.commit()
        return LikeResponse(
            article_id=str(article_id),
            liked=True,
            like_count=int((await self._articles.get_any(article_id)).like_count or 0),
        )

    async def unlike_article(self, actor: Principal, article_id: int) -> LikeResponse:
        article = await self._articles.get_published(article_id)
        if article is None:
            raise NotFoundError("article not found")
        removed = await self._repository.remove_like(actor.subject_id, article_id)
        if removed:
            await self._articles.adjust_count(article_id, "like_count", -1)
            await self._session.commit()
        current = await self._articles.get_any(article_id)
        return LikeResponse(
            article_id=str(article_id),
            liked=False,
            like_count=int(current.like_count or 0),
        )

    # ------------------------------------------------------------------
    # Favorites
    # ------------------------------------------------------------------
    async def favorite_article(self, actor: Principal, article_id: int) -> FavoriteResponse:
        article = await self._articles.get_published(article_id)
        if article is None:
            raise NotFoundError("article not found")
        if await self._repository.favorite_exists(actor.subject_id, article_id):
            return FavoriteResponse(
                article_id=str(article_id),
                favorited=True,
                favorite_count=int(article.favorite_count or 0),
            )
        await self._repository.add_favorite(actor.subject_id, article_id)
        await self._articles.adjust_count(article_id, "favorite_count", 1)
        await self._session.commit()
        return FavoriteResponse(
            article_id=str(article_id),
            favorited=True,
            favorite_count=int(
                (await self._articles.get_any(article_id)).favorite_count or 0
            ),
        )

    async def unfavorite_article(self, actor: Principal, article_id: int) -> FavoriteResponse:
        article = await self._articles.get_published(article_id)
        if article is None:
            raise NotFoundError("article not found")
        removed = await self._repository.remove_favorite(actor.subject_id, article_id)
        if removed:
            await self._articles.adjust_count(article_id, "favorite_count", -1)
            await self._session.commit()
        current = await self._articles.get_any(article_id)
        return FavoriteResponse(
            article_id=str(article_id),
            favorited=False,
            favorite_count=int(current.favorite_count or 0),
        )

    # ------------------------------------------------------------------
    # Follows
    # ------------------------------------------------------------------
    async def follow_user(self, actor: Principal, followed_user_id: int) -> FollowResponse:
        if actor.subject_id == followed_user_id:
            raise BusinessRuleError("you cannot follow yourself")
        if await self._repository.follow_exists(actor.subject_id, followed_user_id):
            return FollowResponse(followed_user_id=str(followed_user_id), following=True)
        await self._repository.add_follow(actor.subject_id, followed_user_id)
        await write_operation_log(
            self._session,
            operation="BLOG_USER_FOLLOW",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_user_follow",
            resource_id=followed_user_id,
        )
        await self._session.commit()
        return FollowResponse(followed_user_id=str(followed_user_id), following=True)

    async def unfollow_user(self, actor: Principal, followed_user_id: int) -> FollowResponse:
        if actor.subject_id == followed_user_id:
            raise BusinessRuleError("you cannot follow yourself")
        removed = await self._repository.remove_follow(actor.subject_id, followed_user_id)
        if removed:
            await write_operation_log(
                self._session,
                operation="BLOG_USER_UNFOLLOW",
                result=RESULT_SUCCESS,
                actor=actor,
                resource_type="blog_user_follow",
                resource_id=followed_user_id,
            )
            await self._session.commit()
        return FollowResponse(followed_user_id=str(followed_user_id), following=False)
