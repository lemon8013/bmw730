"""app.blog.interactions — request and response DTOs."""

from __future__ import annotations

from app.shared.response.dto import ApiModel, StringId


class LikeResponse(ApiModel):
    """Like status for an article."""

    article_id: StringId
    liked: bool
    like_count: int


class FavoriteResponse(ApiModel):
    """Favorite status for an article."""

    article_id: StringId
    favorited: bool
    favorite_count: int


class FollowResponse(ApiModel):
    """Follow status for a user."""

    followed_user_id: StringId
    following: bool
