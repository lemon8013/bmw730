"""Unit tests for the unified response envelope."""

from __future__ import annotations

from app.shared.response.helper import SUCCESS_CODE, error, success
from app.shared.response.schema import ApiResponse


def test_success_envelope_defaults() -> None:
    envelope = success({"id": "1"})
    assert envelope.code == SUCCESS_CODE
    assert envelope.message == "success"
    assert envelope.data == {"id": "1"}


def test_success_envelope_without_payload() -> None:
    envelope: ApiResponse[object] = success()
    assert envelope.code == 0
    assert envelope.data is None


def test_error_envelope_shape() -> None:
    envelope = error(code=403001, message="permission denied")
    assert envelope.code == 403001
    assert envelope.message == "permission denied"
    assert envelope.data is None


def test_error_envelope_keeps_structured_details() -> None:
    envelope = error(code=503001, message="service unavailable", data={"checks": {}})
    assert envelope.data == {"checks": {}}
