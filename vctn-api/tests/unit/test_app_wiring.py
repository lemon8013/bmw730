"""Structural tests for the single modular-monolith application."""

from __future__ import annotations

import re
from collections import defaultdict

import pytest
from fastapi import APIRouter

from app.main import _BUSINESS_ROUTERS, create_app

# Mount prefixes, not module identities: the Admin API base is ``/api/v1/admin``
# and every admin router declares its own business segment, so several routers
# legitimately share ``/admin``. Module identity is asserted through the tags.
EXPECTED_BUSINESS_PREFIXES = {
    "",
    "/admin",
    "/admin/auth",
    "/analytics",
    "/blog",
    "/files",
    "/jobs",
    "/search",
    "/tools",
}

EXPECTED_BUSINESS_TAGS = {
    "admin:analytics",
    "admin:audit",
    "admin:auth",
    "admin:config",
    "admin:departments",
    "admin:dictionaries",
    "admin:export",
    "admin:growth",
    "admin:logs",
    "admin:notifications",
    "admin:permissions",
    "admin:roles",
    "admin:tools",
    "admin:users",
    "analytics:events",
    "analytics:reports",
    "analytics:statistics",
    "blog:articles",
    "blog:authors",
    "blog:categories",
    "blog:comments",
    "blog:interactions",
    "platform:achievements",
    "platform:auth",
    "platform:cosmetics",
    "platform:growth",
    "platform:levels",
    "platform:notifications",
    "platform:points",
    "platform:tasks",
    "platform:users",
    "system:files",
    "system:jobs",
    "system:search",
    "tools:access",
    "tools:catalog",
    "tools:jobs",
    "tools:runtime",
    "tools:statistics",
    "tools:usage",
}

_ALL_METHODS = frozenset({"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"})
# A module segment repeated back to back (``/users/users``) means the mount
# prefix and the router-internal path both carry it.
_REPEATED_SEGMENT = re.compile(r"/([a-z0-9-]+)/\1(?:/|$)")


def _methods_of(route: object) -> set[str]:
    declared = getattr(route, "methods", None) or ()
    return {str(method).upper() for method in declared} & _ALL_METHODS


def test_business_router_table_covers_every_frozen_module() -> None:
    prefixes = {path for path, _tag, _router in _BUSINESS_ROUTERS}
    tags = {tag for _path, tag, _router in _BUSINESS_ROUTERS}
    assert prefixes == EXPECTED_BUSINESS_PREFIXES
    assert tags == EXPECTED_BUSINESS_TAGS


def test_every_business_module_exposes_an_api_router() -> None:
    for path, tag, module_router in _BUSINESS_ROUTERS:
        assert isinstance(module_router, APIRouter), path
        assert tag


def test_no_two_routers_claim_the_same_method_and_path() -> None:
    claimed: dict[tuple[str, str], str] = {}
    for prefix, tag, module_router in _BUSINESS_ROUTERS:
        for route in module_router.routes:
            for method in _methods_of(route):
                key = (method, f"{prefix}{route.path}")
                owner = claimed.get(key)
                assert owner is None, f"{key} claimed by both {owner} and {tag}"
                claimed[key] = tag


def test_application_is_created_once_and_mounts_canonical_paths() -> None:
    application = create_app()
    assert application.title == "vctn-api"

    paths = set(application.openapi()["paths"])
    duplicated = sorted(path for path in paths if _REPEATED_SEGMENT.search(path))
    assert duplicated == []


def test_every_mounted_module_contributes_at_least_one_endpoint() -> None:
    contributing: defaultdict[str, int] = defaultdict(int)
    for _prefix, tag, module_router in _BUSINESS_ROUTERS:
        for route in module_router.routes:
            if _methods_of(route):
                contributing[tag] += 1
    assert sorted(EXPECTED_BUSINESS_TAGS - set(contributing)) == []


@pytest.mark.parametrize("module", sorted(EXPECTED_BUSINESS_TAGS))
def test_module_is_mounted_exactly_once(module: str) -> None:
    assert sum(1 for _path, tag, _router in _BUSINESS_ROUTERS if tag == module) == 1
