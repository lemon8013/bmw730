"""app.system.search — request and response DTOs.

A unified, read-only site search across articles, tools and users. Results are
aggregated into a flat list of :class:`SearchResultItem`.
"""

from __future__ import annotations

from app.shared.response.dto import ApiModel, StringId


class SearchResultItem(ApiModel):
    """One aggregated search hit."""

    resource_type: str
    id: StringId
    title: str
    snippet: str | None = None
    status: str | None = None
    url: str | None = None
