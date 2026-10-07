"""Unit tests for the availability probe runner.

A probe's job is to be wrong about the target and still produce a result row,
so the cases here are mostly failures: unreachable ports, unresolvable names and
targets that do not parse.
"""

from __future__ import annotations

import asyncio

from app.ops.availability.model import OpsAvailabilityCheck
from app.ops.availability.probe import (
    parse_certificate_time,
    probe_dns,
    probe_ssl,
    probe_tcp,
    run_probe,
    split_host_port,
)


def _check(**overrides: object) -> OpsAvailabilityCheck:
    fields: dict[str, object] = {
        "check_code": "unit_check",
        "name": "unit",
        "check_type": "TCP",
        "target": "127.0.0.1:1",
        "timeout_ms": 500,
        "interval_seconds": 60,
        "enabled": True,
    }
    fields.update(overrides)
    return OpsAvailabilityCheck(**fields)  # type: ignore[arg-type]


def testsplit_host_port_handles_bare_host_ipv6_and_port() -> None:
    assert split_host_port("localhost", 443) == ("localhost", 443)
    assert split_host_port("db.internal:5432", 443) == ("db.internal", 5432)
    assert split_host_port("[::1]:8443", 443) == ("::1", 8443)
    assert split_host_port("[::1]", 443) == ("::1", 443)


def test_certificate_time_parses_the_openssl_format() -> None:
    assert parse_certificate_time("Jun  1 12:00:00 2026 GMT") is not None
    assert parse_certificate_time("not a date") is None


def test_tcp_probe_fails_against_a_closed_port() -> None:
    outcome = asyncio.run(probe_tcp("127.0.0.1:1", timeout_ms=200))
    assert outcome.success is False
    assert outcome.error_message


def test_tcp_probe_rejects_a_target_without_a_port() -> None:
    outcome = asyncio.run(probe_tcp("127.0.0.1", timeout_ms=200))
    assert outcome.success is False
    assert outcome.error_message == "target must be host:port"


def test_dns_probe_resolves_localhost() -> None:
    outcome = asyncio.run(probe_dns("localhost", timeout_ms=1000))
    assert outcome.success is True
    assert outcome.detail is not None
    assert outcome.detail["resolved_count"] >= 1


def test_dns_probe_fails_on_a_name_that_cannot_resolve() -> None:
    outcome = asyncio.run(probe_dns("none.invalid", timeout_ms=1000))
    assert outcome.success is False
    assert outcome.error_message


def test_ssl_probe_fails_against_a_closed_port() -> None:
    outcome = asyncio.run(probe_ssl("127.0.0.1:1", timeout_ms=300))
    assert outcome.success is False
    assert outcome.error_message


def test_run_probe_reports_an_unknown_check_type_as_a_failure() -> None:
    """A misconfigured check must show up as a failed probe, not as silence."""
    outcome = asyncio.run(run_probe(_check(check_type="PING")))
    assert outcome.success is False
    assert "unsupported check_type" in (outcome.error_message or "")
