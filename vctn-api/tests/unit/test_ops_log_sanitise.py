"""Unit tests for ops log redaction.

The ops log screen is read by a much wider audience than the log tables
themselves, so a nested metadata payload must be redacted before it leaves the
process: ``password``, ``token``, ``Authorization``, ``api_key``, ``secret`` and
``mfa`` (and their camel/upper/prefixed variants) are replaced by a mask, and
the clear text must never appear in the response.

The repository is stubbed, so no database is touched.
"""

from __future__ import annotations

import datetime
import json
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.exceptions import NotFoundError
from app.ops.logs.schema import APPLICATION, OPERATION, SECURITY
from app.ops.logs.service import OpsLogService, _sanitise

_NOW = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)

#: The clear text that must never survive redaction.
_SECRET = "s3cr3t-plain-text"

#: Key names that must be masked, exactly as they appear in real payloads.
_SENSITIVE_KEYS: tuple[str, ...] = (
    "password",
    "Password",
    "old_password",
    "token",
    "access_token",
    "refreshToken",
    "authorization",
    "Authorization",
    "api_key",
    "secret",
    "client_secret",
    "mfa",
    "mfa_secret",
)


class _NothingSession:
    """Guards the tests: log retrieval must never touch a real session."""

    async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        raise AssertionError("the log sanitise tests must not reach the database")


class _StubLogRepository:
    """Returns one prepared row, whatever stream is addressed."""

    def __init__(self, row: SimpleNamespace | None) -> None:
        self._row = row
        self.requested: list[tuple[str, int]] = []

    async def get(self, log_type: str, log_id: int) -> SimpleNamespace | None:
        self.requested.append((log_type, log_id))
        return self._row

    def supports(self, log_type: str, dimension: str) -> bool:
        return True


def _service(row: SimpleNamespace | None) -> tuple[OpsLogService, _StubLogRepository]:
    service = OpsLogService(_NothingSession())  # type: ignore[arg-type]
    repository = _StubLogRepository(row)
    service._repository = repository  # type: ignore[attr-defined]
    return service, repository


def _security_row(metadata: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        id=91,
        trace_id="trace-1",
        created_at=_NOW,
        event_type="LOGIN_FAILURE",
        result="FAILURE",
        user_id=3,
        ip=None,
        user_agent="pytest",
        error_code="401001",
        metadata_payload=metadata,
    )


def _application_row(metadata: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        id=92,
        trace_id="trace-1",
        created_at=_NOW,
        message="upstream call failed",
        level="ERROR",
        logger_name="app.http",
        exception_type="TimeoutError",
        metadata_payload=metadata,
    )


def _operation_row(metadata: dict[str, Any]) -> SimpleNamespace:
    return SimpleNamespace(
        id=93,
        trace_id="trace-1",
        request_id="req-1",
        created_at=_NOW,
        operation="OPS_AGENT_REGISTER",
        result="SUCCESS",
        operator_id=7,
        resource_type="ops_agent",
        resource_id="7001",
        metadata_payload=metadata,
    )


@pytest.mark.parametrize("key", _SENSITIVE_KEYS)
def test_sensitive_keys_are_masked(key: str) -> None:
    cleaned = _sanitise({key: _SECRET})
    assert cleaned is not None
    assert cleaned[key] != _SECRET
    assert _SECRET not in json.dumps(cleaned)


def test_the_mask_is_used_for_every_sensitive_key() -> None:
    payload = {key: _SECRET for key in _SENSITIVE_KEYS}
    cleaned = _sanitise(payload)
    assert cleaned is not None
    assert set(cleaned.values()) == {"***"}


def test_an_http_header_style_api_key_is_masked_too() -> None:
    """``X-Api-Key`` 与 ``x-api-key`` 必须同样被脱敏。"""
    cleaned = _sanitise({"X-Api-Key": _SECRET, "x-api-key": _SECRET})
    assert cleaned is not None
    assert cleaned["X-Api-Key"] == "***"
    assert cleaned["x-api-key"] == "***"


def test_non_sensitive_keys_survive_redaction() -> None:
    cleaned = _sanitise({"username": "ops-admin", "attempt": 2, "ok": True})
    assert cleaned == {"username": "ops-admin", "attempt": 2, "ok": True}


def test_nested_payloads_are_masked_recursively() -> None:
    payload = {
        "request": {"headers": {"Authorization": _SECRET}, "user": "ops-admin"},
        "attempts": [{"mfa_code": "123456"}, {"password": _SECRET}],
    }
    cleaned = _sanitise(payload)
    assert cleaned is not None
    assert cleaned["request"]["headers"]["Authorization"] == "***"
    assert cleaned["request"]["user"] == "ops-admin"
    assert cleaned["attempts"][0]["mfa_code"] == "***"
    assert cleaned["attempts"][1]["password"] == "***"
    assert _SECRET not in json.dumps(cleaned)
    assert "123456" not in json.dumps(cleaned)


def test_a_payload_without_metadata_stays_none() -> None:
    assert _sanitise(None) is None


@pytest.mark.asyncio()
async def test_security_log_metadata_is_masked_in_the_response() -> None:
    row = _security_row(
        {
            "password": _SECRET,
            "token": _SECRET,
            "authorization": _SECRET,
            "api_key": _SECRET,
            "secret": _SECRET,
            "mfa_code": "123456",
            "username": "ops-admin",
        }
    )
    service, repository = _service(row)

    entry = await service.get(SECURITY, 91)

    assert repository.requested == [(SECURITY, 91)]
    assert entry.metadata is not None
    assert entry.metadata["username"] == "ops-admin"
    for key in ("password", "token", "authorization", "api_key", "secret", "mfa_code"):
        assert entry.metadata[key] == "***"
    assert _SECRET not in json.dumps(entry.metadata)
    assert "123456" not in json.dumps(entry.metadata)


@pytest.mark.asyncio()
async def test_application_log_metadata_is_masked_in_the_response() -> None:
    service, _repository = _service(_application_row({"access_token": _SECRET, "path": "/ops"}))

    entry = await service.get(APPLICATION, 92)

    assert entry.metadata is not None
    assert entry.metadata["access_token"] == "***"
    assert entry.metadata["path"] == "/ops"
    assert _SECRET not in json.dumps(entry.metadata)


@pytest.mark.asyncio()
async def test_operation_log_metadata_is_masked_in_the_response() -> None:
    service, _repository = _service(
        _operation_row({"api_key": _SECRET, "agent_code": "AGENT_1"})
    )

    entry = await service.get(OPERATION, 93)

    assert entry.metadata is not None
    assert entry.metadata["api_key"] == "***"
    assert entry.metadata["agent_code"] == "AGENT_1"
    assert _SECRET not in json.dumps(entry.metadata)


@pytest.mark.asyncio()
async def test_a_missing_record_still_raises_not_found() -> None:
    service, _repository = _service(None)

    with pytest.raises(NotFoundError):
        await service.get(SECURITY, 404)
