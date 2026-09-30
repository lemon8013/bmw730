"""Structural tests for the single modular-monolith application."""

from __future__ import annotations

from fastapi import APIRouter

from app.main import _BUSINESS_ROUTERS, create_app

EXPECTED_BUSINESS_PREFIXES = {
    "/admin/auth",
    "/admin/users",
    "/admin/departments",
    "/admin/roles",
    "/admin/permissions",
    "/admin/audit",
    "/admin/dictionaries",
    "/admin/config",
    "/platform/auth",
    "/platform/users",
    "/platform/growth",
    "/platform/points",
    "/platform/levels",
    "/platform/cosmetics",
    "/platform/notifications",
    "/tools/catalog",
    "/tools/runtime",
    "/tools/access",
    "/tools/usage",
    "/tools/statistics",
    "/tools/jobs",
    "/blog/articles",
    "/blog/comments",
    "/blog/categories",
    "/blog/authors",
    "/blog/interactions",
    "/analytics/events",
    "/analytics/statistics",
    "/analytics/reports",
    "/system/files",
    "/system/jobs",
    "/system/search",
}


def test_business_router_table_covers_every_frozen_module() -> None:
    mounted = {path for path, _tag, _router in _BUSINESS_ROUTERS}
    assert mounted == EXPECTED_BUSINESS_PREFIXES


def test_every_business_module_exposes_an_api_router() -> None:
    for path, tag, module_router in _BUSINESS_ROUTERS:
        assert isinstance(module_router, APIRouter), path
        assert tag


def test_application_is_created_once_and_has_no_duplicate_prefixes() -> None:
    application = create_app()
    assert application.title == "vctn-api"
    prefixes = [path for path, _tag, _router in _BUSINESS_ROUTERS]
    assert len(prefixes) == len(set(prefixes))
