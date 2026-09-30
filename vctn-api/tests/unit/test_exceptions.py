"""Unit tests for the application exception hierarchy."""

from __future__ import annotations

import pytest

from app.core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    BusinessError,
    ConflictError,
    NotFoundError,
    ValidationError,
)

EXPECTED: list[tuple[type[AppException], int, int]] = [
    (ValidationError, 422, 422001),
    (AuthenticationError, 401, 401001),
    (AuthorizationError, 403, 403001),
    (NotFoundError, 404, 404001),
    (ConflictError, 409, 409001),
    (BusinessError, 400, 400001),
]


@pytest.mark.parametrize(("exception_type", "http_status", "code"), EXPECTED)
def test_structural_status_and_code(
    exception_type: type[AppException], http_status: int, code: int
) -> None:
    failure = exception_type()
    assert failure.http_status == http_status
    assert failure.code == code
    assert failure.data is None


@pytest.mark.parametrize(("exception_type", "_status", "_code"), EXPECTED)
def test_exception_types_are_app_exceptions(
    exception_type: type[AppException], _status: int, _code: int
) -> None:
    assert issubclass(exception_type, AppException)


def test_custom_message_overrides_default() -> None:
    failure = AuthorizationError("role assignment denied")
    assert failure.message == "role assignment denied"


def test_code_and_status_can_be_overridden_per_instance() -> None:
    failure = AppException("database is not configured", code=503001, http_status=503)
    assert failure.http_status == 503
    assert failure.code == 503001
