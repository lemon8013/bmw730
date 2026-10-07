"""app.ops.availability — probe execution.

Until this module existed, an availability check was only a row: nothing ever
 dialled the target, so the console showed an empty result list no matter how
many checks were configured. The runner here turns one check row into one
``ops_availability_result`` row.

Two rules keep it safe to run inside the API process:

* **Never raise.** A probe failing is the normal case — that is what it is for.
  A transport error becomes a failed result row, not an exception that kills the
  scheduler tick.
* **Never follow the target blindly.** Redirects are not followed and the
  response body is never read, so an accidentally misconfigured target cannot
  be turned into a request forgery against an internal host.
"""

from __future__ import annotations

import asyncio
import datetime
import socket
import ssl as ssl_module
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from app.ops.availability.model import OpsAvailabilityCheck


@dataclass(frozen=True, slots=True)
class ProbeOutcome:
    """What one execution of one probe observed."""

    success: bool
    latency_ms: float | None = None
    status_code: int | None = None
    error_message: str | None = None
    detail: dict[str, object] | None = None


def split_host_port(target: str, default_port: int) -> tuple[str, int]:
    """Split ``host:port``; a bare host falls back to the protocol default."""
    candidate = target.strip()
    if candidate.startswith("["):  # [::1]:443
        host, _, remainder = candidate[1:].partition("]")
        port_text = remainder.lstrip(":")
        return host, int(port_text) if port_text else default_port
    if ":" in candidate:
        host, _, port_text = candidate.rpartition(":")
        if port_text.isdigit():
            return host, int(port_text)
    return candidate, default_port


def _elapsed_ms(started: float) -> float:
    return round((asyncio.get_running_loop().time() - started) * 1000, 3)


async def probe_http(
    target: str, *, timeout_ms: int, expected_status: int | None
) -> ProbeOutcome:
    """Issue one GET and judge it by the configured status expectation."""
    started = asyncio.get_running_loop().time()
    timeout = httpx.Timeout(max(timeout_ms, 1) / 1000)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.get(target)
    except Exception as failure:  # noqa: BLE001 - a probe records failures
        return ProbeOutcome(
            success=False,
            latency_ms=_elapsed_ms(started),
            error_message=f"{type(failure).__name__}: {failure}",
        )
    expected = expected_status if expected_status is not None else 200
    success = response.status_code == expected
    return ProbeOutcome(
        success=success,
        latency_ms=_elapsed_ms(started),
        status_code=response.status_code,
        error_message=None if success else f"unexpected status {response.status_code}",
    )


async def probe_tcp(target: str, *, timeout_ms: int) -> ProbeOutcome:
    """Open a TCP connection and close it again."""
    started = asyncio.get_running_loop().time()
    host, port = split_host_port(target, 0)
    if not port:
        return ProbeOutcome(success=False, error_message="target must be host:port")
    try:
        await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM),
            timeout=max(timeout_ms, 1) / 1000,
        )
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=max(timeout_ms, 1) / 1000
        )
    except Exception as failure:  # noqa: BLE001 - a probe records failures
        return ProbeOutcome(
            success=False,
            latency_ms=_elapsed_ms(started),
            error_message=f"{type(failure).__name__}: {failure}",
        )
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:  # noqa: BLE001 - closing is best effort, the probe already succeeded
        pass
    return ProbeOutcome(success=True, latency_ms=_elapsed_ms(started))


async def probe_dns(target: str, *, timeout_ms: int) -> ProbeOutcome:
    """Resolve a name; a name that no longer resolves is an outage."""
    started = asyncio.get_running_loop().time()
    host = urlsplit(target if "://" in target else f"//{target}").hostname or target.strip()
    try:
        records = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(host, None),
            timeout=max(timeout_ms, 1) / 1000,
        )
    except Exception as failure:  # noqa: BLE001 - a probe records failures
        return ProbeOutcome(
            success=False,
            latency_ms=_elapsed_ms(started),
            error_message=f"{type(failure).__name__}: {failure}",
        )
    addresses = sorted({record[4][0] for record in records})
    return ProbeOutcome(
        success=bool(addresses),
        latency_ms=_elapsed_ms(started),
        detail={"resolved": addresses[:10], "resolved_count": len(addresses)},
    )


async def probe_ssl(target: str, *, timeout_ms: int) -> ProbeOutcome:
    """Read the peer certificate and report how long it is still valid."""
    started = asyncio.get_running_loop().time()
    host, port = split_host_port(target, 443)
    context = ssl_module.create_default_context()
    context.check_hostname = True
    context.verify_mode = ssl_module.CERT_REQUIRED
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=context, server_hostname=host),
            timeout=max(timeout_ms, 1) / 1000,
        )
    except Exception as failure:  # noqa: BLE001 - a probe records failures
        return ProbeOutcome(
            success=False,
            latency_ms=_elapsed_ms(started),
            error_message=f"{type(failure).__name__}: {failure}",
        )
    certificate = writer.get_extra_info("peercert") or {}
    writer.close()
    try:
        await writer.wait_closed()
    except Exception:  # noqa: BLE001 - closing is best effort
        pass
    not_after = certificate.get("notAfter")
    expires_at = parse_certificate_time(not_after) if isinstance(not_after, str) else None
    detail: dict[str, object] = {"subject": certificate.get("subject"), "not_after": not_after}
    if expires_at is None:
        return ProbeOutcome(
            success=True,
            latency_ms=_elapsed_ms(started),
            error_message="certificate exposes no expiry",
            detail=detail,
        )
    remaining = expires_at - datetime.datetime.now(datetime.UTC)
    days_remaining = remaining.days
    detail["days_remaining"] = days_remaining
    return ProbeOutcome(
        success=remaining.total_seconds() > 0,
        latency_ms=_elapsed_ms(started),
        error_message=None if remaining.total_seconds() > 0 else "certificate has expired",
        detail=detail,
    )


def parse_certificate_time(value: str) -> datetime.datetime | None:
    # OpenSSL renders certificate times as "Jun  1 12:00:00 2026 GMT".
    try:
        return datetime.datetime.strptime(value, "%b %d %H:%M:%S %Y %Z").replace(
            tzinfo=datetime.UTC
        )
    except ValueError:
        return None


#: One runner per check type; adding a probe means adding a function, not a branch.
PROBE_RUNNERS: dict[str, Callable[..., Awaitable[ProbeOutcome]]] = {
    "HTTP": probe_http,
    "TCP": probe_tcp,
    "DNS": probe_dns,
    "SSL": probe_ssl,
}


async def run_probe(check: OpsAvailabilityCheck) -> ProbeOutcome:
    """Execute one check and return what was observed.

    An unknown ``check_type`` is a configuration error rather than an outage: it
    is reported as a failed result so it shows up in the console next to the
    check that produced it.
    """
    runner = PROBE_RUNNERS.get(str(check.check_type))
    if runner is None:
        return ProbeOutcome(
            success=False, error_message=f"unsupported check_type: {check.check_type}"
        )
    try:
        if check.check_type == "HTTP":
            return await runner(
                str(check.target),
                timeout_ms=int(check.timeout_ms),
                expected_status=check.expected_status,
            )
        return await runner(str(check.target), timeout_ms=int(check.timeout_ms))
    except Exception as failure:  # noqa: BLE001 - the tick must survive one bad probe
        return ProbeOutcome(success=False, error_message=f"{type(failure).__name__}: {failure}")
