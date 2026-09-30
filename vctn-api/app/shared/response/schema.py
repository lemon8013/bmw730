"""Unified API response envelope.

Success::

    {"code": 0, "message": "success", "data": {...}}

Error::

    {"code": 403001, "message": "permission denied", "data": null}
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Envelope returned by every endpoint."""

    code: int = Field(default=0, description="0 means success, non-zero is an error code")
    message: str = Field(default="success")
    data: T | None = Field(default=None)


class ApiError(BaseModel):
    """Envelope returned when an error occurs."""

    code: int
    message: str
    data: Any = None
