"""app.blog.comments — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class CommentCreateRequest(ApiModel):
    """Post a comment."""

    content: str
    parent_id: OptionalStringId = None


class CommentReviewRequest(ApiModel):
    """Admin review decision for a comment."""

    decision: str  # APPROVED | REJECTED
    review_comment: str | None = None


class CommentResponse(ApiModel):
    """A blog comment."""

    id: StringId
    article_id: OptionalStringId = None
    user_id: OptionalStringId = None
    parent_id: OptionalStringId = None
    content: str
    status: str
    reviewer_id: OptionalStringId = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
