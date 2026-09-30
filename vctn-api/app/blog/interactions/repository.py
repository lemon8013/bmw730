"""app.blog.interactions — data access.

The like / favorite / follow tables use a composite primary key (no surrogate
id), so existence is checked by the natural key and removal is a targeted
delete. Counting lives on the article row and is adjusted through the article
repository.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.blog.interactions.model import (
    BlogArticleFavorite,
    BlogArticleLike,
    BlogUserFollow,
)


class InteractionRepository:
    """Data access for likes, favorites and follows."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ------------------------------------------------------------------
    # Likes
    # ------------------------------------------------------------------
    async def like_exists(self, user_id: int, article_id: int) -> bool:
        result = await self._session.execute(
            select(BlogArticleLike).where(
                BlogArticleLike.user_id == user_id,
                BlogArticleLike.article_id == article_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def add_like(self, user_id: int, article_id: int) -> None:
        self._session.add(BlogArticleLike(user_id=user_id, article_id=article_id))
        await self._session.flush()

    async def remove_like(self, user_id: int, article_id: int) -> bool:
        result = await self._session.execute(
            delete(BlogArticleLike).where(
                BlogArticleLike.user_id == user_id,
                BlogArticleLike.article_id == article_id,
            )
        )
        await self._session.flush()
        return int(result.rowcount or 0) > 0

    # ------------------------------------------------------------------
    # Favorites
    # ------------------------------------------------------------------
    async def favorite_exists(self, user_id: int, article_id: int) -> bool:
        result = await self._session.execute(
            select(BlogArticleFavorite).where(
                BlogArticleFavorite.user_id == user_id,
                BlogArticleFavorite.article_id == article_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def add_favorite(self, user_id: int, article_id: int) -> None:
        self._session.add(BlogArticleFavorite(user_id=user_id, article_id=article_id))
        await self._session.flush()

    async def remove_favorite(self, user_id: int, article_id: int) -> bool:
        result = await self._session.execute(
            delete(BlogArticleFavorite).where(
                BlogArticleFavorite.user_id == user_id,
                BlogArticleFavorite.article_id == article_id,
            )
        )
        await self._session.flush()
        return int(result.rowcount or 0) > 0

    # ------------------------------------------------------------------
    # Follows
    # ------------------------------------------------------------------
    async def follow_exists(self, follower_id: int, followed_id: int) -> bool:
        result = await self._session.execute(
            select(BlogUserFollow).where(
                BlogUserFollow.follower_user_id == follower_id,
                BlogUserFollow.followed_user_id == followed_id,
            )
        )
        return result.scalar_one_or_none() is not None

    async def add_follow(self, follower_id: int, followed_id: int) -> None:
        self._session.add(
            BlogUserFollow(follower_user_id=follower_id, followed_user_id=followed_id)
        )
        await self._session.flush()

    async def remove_follow(self, follower_id: int, followed_id: int) -> bool:
        result = await self._session.execute(
            delete(BlogUserFollow).where(
                BlogUserFollow.follower_user_id == follower_id,
                BlogUserFollow.followed_user_id == followed_id,
            )
        )
        await self._session.flush()
        return int(result.rowcount or 0) > 0
