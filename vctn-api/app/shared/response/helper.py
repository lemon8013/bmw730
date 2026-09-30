"""Unified response helpers.

Only the envelope construction lives here. Concrete business error handling is
implemented in the phase that freezes the error-code catalogue.
"""

from __future__ import annotations

from typing import Any, Final, TypeVar

from app.shared.response.schema import ApiError, ApiResponse

T = TypeVar("T")

SUCCESS_CODE: Final[int] = 0
SUCCESS_MESSAGE: Final[str] = "success"


def success(
    data: T | None = None,
    *,
    message: str = SUCCESS_MESSAGE,
    code: int = SUCCESS_CODE,
) -> ApiResponse[T]:
    """Build a success envelope."""
    return ApiResponse[T](code=code, message=message, data=data)


def error(*, code: int, message: str, data: Any = None) -> ApiError:
    """Build an error envelope."""
    return ApiError(code=code, message=message, data=data)
