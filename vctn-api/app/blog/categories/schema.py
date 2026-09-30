"""app.blog.categories — request and response DTOs."""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class CategoryCreateRequest(ApiModel):
    """Create a blog category."""

    category_code: str
    category_name: str
    description: str | None = None
    sort_order: int = 0


class CategoryUpdateRequest(ApiModel):
    """Update a blog category."""

    category_name: str | None = None
    description: str | None = None
    sort_order: int | None = None
    status: str | None = None


class CategoryResponse(ApiModel):
    """A blog category."""

    id: StringId
    category_code: str
    category_name: str
    description: str | None = None
    sort_order: int
    status: str
    created_at: datetime.datetime
    updated_at: datetime.datetime
