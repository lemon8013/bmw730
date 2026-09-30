"""Application exception hierarchy.

Error codes follow the structural scheme ``http_status * 1000 + sequence``.
The full error-code catalogue is NOT frozen yet, therefore only structural
defaults are defined here. Business error codes are added once the catalogue is
frozen; they must not be invented by the implementation.
"""

from __future__ import annotations

from typing import Any


class AppException(Exception):
    """Base class of every application exception."""

    http_status: int = 500
    code: int = 500000
    message: str = "internal server error"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: int | None = None,
        http_status: int | None = None,
        data: Any = None,
    ) -> None:
        self.message = type(self).message if message is None else message
        if code is not None:
            self.code = code
        if http_status is not None:
            self.http_status = http_status
        self.data = data
        super().__init__(self.message)


class ValidationError(AppException):
    """Request payload or parameter validation failed."""

    http_status = 422
    code = 422001
    message = "validation error"


class AuthenticationError(AppException):
    """The caller is not authenticated."""

    http_status = 401
    code = 401001
    message = "authentication required"


class AuthorizationError(AppException):
    """The caller is authenticated but not permitted."""

    http_status = 403
    code = 403001
    message = "permission denied"


class NotFoundError(AppException):
    """The addressed resource does not exist."""

    http_status = 404
    code = 404001
    message = "resource not found"


class ConflictError(AppException):
    """The operation conflicts with the current resource state."""

    http_status = 409
    code = 409001
    message = "resource conflict"


class BusinessError(AppException):
    """A frozen business rule was violated."""

    http_status = 400
    code = 400001
    message = "business rule violated"


class ServiceUnavailableError(AppException):
    """A required infrastructure dependency is not configured or not reachable."""

    http_status = 503
    code = 503001
    message = "service unavailable"
