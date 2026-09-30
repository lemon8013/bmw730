"""app.admin.config — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.admin.config.schema import (
    ConfigResponse,
    CreateFeatureFlagRequest,
    FeatureFlagResponse,
    UpdateConfigRequest,
    UpdateFeatureFlagRequest,
)
from app.admin.config.service import ConfigService
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> ConfigService:
    return ConfigService(session)


@router.get("/config", response_model=ApiResponse[Page[ConfigResponse]])
async def list_configs(
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("CONFIG_VIEW")),
) -> ApiResponse[Page[ConfigResponse]]:
    return success(
        await _service(session).list_configs(page=PageParams(page=page, page_size=page_size))
    )


@router.put("/config/{config_key}", response_model=ApiResponse[ConfigResponse])
async def update_config(
    config_key: str,
    payload: UpdateConfigRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("CONFIG_EDIT")),
) -> ApiResponse[ConfigResponse]:
    return success(await _service(session).update_config(principal, config_key, payload))


@router.get("/feature-flags", response_model=ApiResponse[Page[FeatureFlagResponse]])
async def list_flags(
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("FEATURE_FLAG_VIEW")),
) -> ApiResponse[Page[FeatureFlagResponse]]:
    return success(
        await _service(session).list_flags(page=PageParams(page=page, page_size=page_size))
    )


@router.post("/feature-flags", response_model=ApiResponse[FeatureFlagResponse])
async def create_flag(
    payload: CreateFeatureFlagRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("FEATURE_FLAG_EDIT")),
) -> ApiResponse[FeatureFlagResponse]:
    return success(await _service(session).create_flag(principal, payload))


@router.put("/feature-flags/{flag_id}", response_model=ApiResponse[FeatureFlagResponse])
async def update_flag(
    flag_id: str,
    payload: UpdateFeatureFlagRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("FEATURE_FLAG_EDIT")),
) -> ApiResponse[FeatureFlagResponse]:
    return success(await _service(session).update_flag(principal, int(flag_id), payload))


@router.post("/feature-flags/{flag_id}/enable", response_model=ApiResponse[FeatureFlagResponse])
async def enable_flag(
    flag_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("FEATURE_FLAG_EDIT")),
) -> ApiResponse[FeatureFlagResponse]:
    return success(await _service(session).set_flag_enabled(principal, int(flag_id), enabled=True))


@router.post("/feature-flags/{flag_id}/disable", response_model=ApiResponse[FeatureFlagResponse])
async def disable_flag(
    flag_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("FEATURE_FLAG_EDIT")),
) -> ApiResponse[FeatureFlagResponse]:
    return success(await _service(session).set_flag_enabled(principal, int(flag_id), enabled=False))
