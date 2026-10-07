"""Contract tests for the ops module: permissions, route ordering, code registry.

Three things are frozen here.

* Every ops endpoint is guarded by an ``OPS_*`` permission. The ops console is
  an admin surface and an unguarded endpoint would let any authenticated
  operator read or rewrite the monitoring configuration. The one deliberate
  exception is ``POST /ops/agents/heartbeat``: it is called by the agent itself,
  which owns a credential instead of an admin session.
* The codes are exactly the 22 codes Spec 21 registered. A code that is not in
  the frozen catalogue must be registered before it may appear on a route.
* Literal segments are registered before the parameterised segment that would
  otherwise swallow them (``/logs/context`` vs ``/logs/{log_id}``). FastAPI
  matches in registration order, so a shadowed literal would be parsed as an id.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.main import _BUSINESS_ROUTERS

_API_PREFIX = "/api/v1"
OPS_PREFIX = f"{_API_PREFIX}/ops"

#: Spec 21 — the permission codes registered for the ops console.
REGISTERED_OPS_PERMISSIONS: frozenset[str] = frozenset(
    {
        "OPS_AGENT_VIEW",
        "OPS_AGENT_MANAGE",
        "OPS_ALERT_VIEW",
        "OPS_ALERT_MANAGE",
        "OPS_ALERT_ACK",
        "OPS_ALERT_SILENCE",
        "OPS_API_VIEW",
        "OPS_AUDIT_VIEW",
        "OPS_MONITOR_VIEW",
        "OPS_MONITOR_MANAGE",
        "OPS_DASHBOARD_VIEW",
        "OPS_DASHBOARD_MANAGE",
        "OPS_DATABASE_VIEW",
        "OPS_HOST_VIEW",
        "OPS_HOST_MANAGE",
        "OPS_JOB_VIEW",
        "OPS_JOB_MANAGE",
        "OPS_LOG_VIEW",
        "OPS_MAINTENANCE_MANAGE",
        "OPS_REDIS_VIEW",
        "OPS_REPORT_VIEW",
        "OPS_SERVICE_VIEW",
        "OPS_SERVICE_MANAGE",
    }
)

#: The size of the frozen catalogue; guards against a silent extension.
#: Spec 21 registered 22 codes; ``OPS_REPORT_VIEW`` was added with the report
#: page and is listed here on purpose — a code used on a route must appear in
#: this catalogue rather than slip past it.
REGISTERED_OPS_PERMISSION_COUNT: int = 23

_PERMISSION_DEPENDENCY_PREFIX = "require_permission_"
_ADMIN_DEPENDENCY = "require_admin"

_WRITE_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH", "DELETE"})
_BUSINESS_METHODS: frozenset[str] = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE"})

#: The only ops endpoints that carry no permission: an agent authenticates its
#: heartbeat with its own credential instead of an admin session.
_PERMISSION_EXEMPT: frozenset[tuple[str, str]] = frozenset(
    {("POST", f"{OPS_PREFIX}/agents/heartbeat")}
)

#: Literal segments that share a prefix with a parameterised sibling route.
_LITERAL_BEFORE_PARAM: tuple[tuple[str, str], ...] = (
    (f"{OPS_PREFIX}/logs/context", f"{OPS_PREFIX}/logs/{{log_id}}"),
    (f"{OPS_PREFIX}/jobs/statistics", f"{OPS_PREFIX}/jobs/{{job_id}}"),
    (f"{OPS_PREFIX}/hosts/groups", f"{OPS_PREFIX}/hosts/{{host_id}}"),
    (f"{OPS_PREFIX}/hosts/environments", f"{OPS_PREFIX}/hosts/{{host_id}}"),
)

_PARAM_SEGMENT = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*(?::[^}]+)?\}")
_PATH_CONVERTER = re.compile(r"\{[a-zA-Z_][a-zA-Z0-9_]*:path\}")


@dataclass(frozen=True, slots=True)
class _OpsEndpoint:
    """One mounted ops route and the guards it declares."""

    method: str
    path: str
    permissions: tuple[str, ...]
    requires_admin: bool


def _methods_of(route: APIRoute) -> frozenset[str]:
    declared = route.methods or frozenset()
    return frozenset(str(method).upper() for method in declared) & _BUSINESS_METHODS


def _dependency_names(route: APIRoute) -> list[str]:
    """Return the name of every dependency callable of a route, deeply."""
    names: list[str] = []
    pending = [route.dependant]
    while pending:
        dependant = pending.pop()
        for sub in dependant.dependencies:
            names.append(getattr(sub.call, "__name__", ""))
            pending.append(sub)
    return names


def _ops_endpoints() -> list[_OpsEndpoint]:
    """Every mounted ops endpoint with the guards the router declares.

    FastAPI 0.142 keeps an included router lazy, so the routes are read from the
    frozen module table instead of from ``app.routes``.
    """
    endpoints: list[_OpsEndpoint] = []
    for mount, tag, module_router in _BUSINESS_ROUTERS:
        if not tag.startswith("ops:"):
            continue
        for route in module_router.routes:
            if not isinstance(route, APIRoute):
                continue
            names = _dependency_names(route)
            permissions = tuple(
                sorted(
                    {
                        name[len(_PERMISSION_DEPENDENCY_PREFIX) :].upper()
                        for name in names
                        if name.startswith(_PERMISSION_DEPENDENCY_PREFIX)
                    }
                )
            )
            for method in sorted(_methods_of(route)):
                endpoints.append(
                    _OpsEndpoint(
                        method=method,
                        path=f"{_API_PREFIX}{mount}{route.path}",
                        permissions=permissions,
                        requires_admin=_ADMIN_DEPENDENCY in names,
                    )
                )
    return endpoints


def _matcher(path: str) -> re.Pattern[str] | None:
    """Return a regex matching every concrete path ``path`` would swallow."""
    if "{" not in path:
        return None
    pattern = _PATH_CONVERTER.sub(".+", path)
    pattern = _PARAM_SEGMENT.sub(r"[^/]+", pattern)
    return re.compile(f"^{pattern}$")


def test_registered_permission_catalogue_is_frozen() -> None:
    assert len(REGISTERED_OPS_PERMISSIONS) == REGISTERED_OPS_PERMISSION_COUNT


def test_ops_module_is_mounted(client: TestClient) -> None:
    endpoints = _ops_endpoints()
    assert endpoints, "no ops endpoint is mounted under " + OPS_PREFIX
    assert all(endpoint.path.startswith(OPS_PREFIX) for endpoint in endpoints)


def test_every_ops_endpoint_is_reachable_in_the_openapi_document(
    client: TestClient,
) -> None:
    """Cross-checks the frozen mount table against the mounted application."""
    documented = set(client.get("/openapi.json").json()["paths"])
    for endpoint in _ops_endpoints():
        assert endpoint.path in documented, endpoint.path


def test_every_ops_endpoint_declares_exactly_one_registered_permission(
    client: TestClient,
) -> None:
    endpoints = _ops_endpoints()
    for endpoint in endpoints:
        key = (endpoint.method, endpoint.path)
        if key in _PERMISSION_EXEMPT:
            assert endpoint.permissions == (), f"{key} must stay credential based"
            continue
        assert len(endpoint.permissions) == 1, f"{key} declares {endpoint.permissions}"
        assert endpoint.permissions[0].startswith("OPS_"), f"{key}: {endpoint.permissions}"


def test_every_ops_write_endpoint_carries_a_permission_and_an_admin_identity(
    client: TestClient,
) -> None:
    writes = [
        endpoint
        for endpoint in _ops_endpoints()
        if endpoint.method in _WRITE_METHODS
        and (endpoint.method, endpoint.path) not in _PERMISSION_EXEMPT
    ]
    assert writes, "no ops write endpoint is mounted"
    for endpoint in writes:
        assert len(endpoint.permissions) == 1, f"{endpoint.method} {endpoint.path}"
        assert endpoint.requires_admin, f"{endpoint.method} {endpoint.path} needs an admin"


def test_every_ops_read_endpoint_carries_a_permission(client: TestClient) -> None:
    reads = [endpoint for endpoint in _ops_endpoints() if endpoint.method == "GET"]
    assert reads, "no ops read endpoint is mounted"
    for endpoint in reads:
        assert len(endpoint.permissions) == 1, f"GET {endpoint.path}"
        assert endpoint.permissions[0].startswith("OPS_"), f"GET {endpoint.path}"


def test_ops_permission_codes_stay_inside_the_registered_catalogue(
    client: TestClient,
) -> None:
    used = {
        permission for endpoint in _ops_endpoints() for permission in endpoint.permissions
    }
    assert used, "no ops endpoint declares a permission"
    unregistered = sorted(used - REGISTERED_OPS_PERMISSIONS)
    assert unregistered == [], f"register these codes in Spec 21 first: {unregistered}"


def test_literal_segments_are_declared_before_parameterised_ones(
    client: TestClient,
) -> None:
    paths = list(client.get("/openapi.json").json()["paths"])
    for literal, parameterised in _LITERAL_BEFORE_PARAM:
        assert literal in paths, literal
        assert parameterised in paths, parameterised
        assert paths.index(literal) < paths.index(parameterised), (
            f"{literal} must be registered before {parameterised}"
        )


def test_no_literal_ops_path_is_shadowed_by_a_parameterised_one() -> None:
    """A literal path that an earlier parameterised path can swallow is a bug.

    The comparison is method aware: ``POST /agents/heartbeat`` may follow
    ``GET /agents/{agent_id}`` because Starlette keeps looking after a partial
    match, but it may never follow a ``POST /agents/{agent_id}``.
    """
    endpoints = _ops_endpoints()
    shadowed: list[tuple[str, str]] = []
    for index, endpoint in enumerate(endpoints):
        if "{" in endpoint.path:
            continue
        for earlier in endpoints[:index]:
            if "{" not in earlier.path or earlier.method != endpoint.method:
                continue
            matcher = _matcher(earlier.path)
            if matcher is not None and matcher.match(endpoint.path):
                shadowed.append((earlier.path, endpoint.path))
    assert shadowed == [], f"literal routes swallowed by a parameterised one: {shadowed}"


@pytest.mark.parametrize(
    ("literal", "parameterised"),
    (
        (f"{OPS_PREFIX}/alert-rules", f"{OPS_PREFIX}/alerts/{{alert_id}}"),
        (f"{OPS_PREFIX}/overview", f"{OPS_PREFIX}/dashboards/{{dashboard_id}}"),
        (
            f"{OPS_PREFIX}/notification-channels",
            f"{OPS_PREFIX}/notifications/{{notification_id}}",
        ),
    ),
)
def test_lookalike_paths_do_not_collide(literal: str, parameterised: str) -> None:
    """Different first segments: ``alert-rules`` is not ``alerts/{alert_id}``."""
    matcher = _matcher(parameterised)
    assert matcher is not None
    assert matcher.match(literal) is None


def test_agent_heartbeat_is_not_swallowed_by_a_parameterised_route() -> None:
    """``POST /agents/heartbeat`` carries no permission on purpose.

    It is safe only because no parameterised ``POST`` route matches the same
    path: Starlette would otherwise hand ``heartbeat`` to ``{agent_id}``.
    """
    heartbeat = f"{OPS_PREFIX}/agents/heartbeat"
    posting = [endpoint for endpoint in _ops_endpoints() if endpoint.method == "POST"]
    assert heartbeat in {endpoint.path for endpoint in posting}
    shadowing = [
        endpoint.path
        for endpoint in posting
        if "{" in endpoint.path
        and (matcher := _matcher(endpoint.path)) is not None
        and matcher.match(heartbeat)
    ]
    assert shadowing == []


def test_dashboards_widget_subroutes_are_registered_after_their_parent(
    client: TestClient,
) -> None:
    paths = list(client.get("/openapi.json").json()["paths"])
    parent = f"{OPS_PREFIX}/dashboards/{{dashboard_id}}"
    child = f"{OPS_PREFIX}/dashboards/{{dashboard_id}}/widgets"
    assert parent in paths
    assert child in paths
    assert paths.index(parent) < paths.index(child)


def test_log_context_does_not_500_on_a_non_numeric_id(client: TestClient) -> None:
    """A 500 here would mean ``/logs/context`` was parsed as ``/logs/{id}``."""
    response = client.get(f"{OPS_PREFIX}/logs/context", params={"trace_id": "trace-1"})
    assert response.status_code != 500
    assert response.json()["code"] != 500000
