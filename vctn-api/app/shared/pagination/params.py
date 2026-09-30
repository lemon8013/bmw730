"""Pagination primitives.

DD-13 (pagination semantics) is not frozen. The minimal runnable contract used
throughout the backend is therefore fixed here, in one place: a one based
``page``, a ``page_size`` bounded by configuration, and a ``total`` count so a
client can render a pager.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

DEFAULT_PAGE_SIZE: int = 20
MAX_PAGE_SIZE: int = 200


class PageParams(BaseModel):
    """Query parameters accepted by every list endpoint."""

    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


class Page(BaseModel, Generic[T]):
    """Envelope returned by every list endpoint."""

    items: list[T] = Field(default_factory=list)
    total: int = 0
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    @classmethod
    def build(cls, *, items: list[Any], total: int, params: PageParams) -> Page[Any]:
        return cls(items=list(items), total=total, page=params.page, page_size=params.page_size)


class SortOrder:
    """Sort directions understood by the list endpoints."""

    ASC = "asc"
    DESC = "desc"
