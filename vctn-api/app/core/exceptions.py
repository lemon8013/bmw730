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


class PermissionDeniedError(AuthorizationError):
    """The caller lacks the permission required by the endpoint."""

    code = 403001
    message = "permission denied"


class DataScopeDeniedError(AuthorizationError):
    """The addressed resource lies outside the caller's data scope."""

    code = 403002
    message = "resource is outside the data scope"


class BusinessRuleError(BusinessError):
    """A frozen business rule refused the operation."""

    code = 400001
    message = "business rule violated"


class RateLimitError(AppException):
    """Too many requests in the current window."""

    http_status = 429
    code = 429001
    message = "too many requests"


class QuotaExceededError(AppException):
    """The caller consumed its daily quota."""

    http_status = 429
    code = 429002
    message = "quota exceeded"


class IdempotencyError(AppException):
    """The idempotency key was reused with a different payload."""

    http_status = 409
    code = 409002
    message = "idempotency key conflict"


class ConcurrencyError(AppException):
    """A concurrent modification lost the race or a lock could not be taken."""

    http_status = 409
    code = 409003
    message = "concurrent modification detected"


class SystemError(AppException):
    """An unexpected internal failure."""

    http_status = 500
    code = 500000
    message = "internal server error"
