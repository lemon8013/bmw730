"""app.ops.hosts — HTTP endpoints.

Read endpoints require ``OPS_HOST_VIEW``; every write requires
``OPS_HOST_MANAGE``. The permission is enforced by the backend
``AuthorizationService`` — the frontend hides the buttons, the backend decides.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.hosts.schema import (
    EnvironmentResponse,
    HostCreateRequest,
    HostGroupResponse,
    HostResponse,
    HostUpdateRequest,
)
from app.ops.hosts.service import HostService
from app.shared.authorization.dependencies import AdminPrincipal, require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> HostService:
    return HostService(session)


@router.get(
    "/hosts",
    response_model=ApiResponse[Page[HostResponse]],
    dependencies=[Depends(require_permission("OPS_HOST_VIEW"))],
)
async def list_hosts(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    host_group_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[HostResponse]]:
    return success(
        await _service(session).list_hosts(
            keyword=keyword,
            status=status,
            environment=environment,
            host_group_id=int(host_group_id) if host_group_id else None,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get(
    "/hosts/groups",
    response_model=ApiResponse[list[HostGroupResponse]],
    dependencies=[Depends(require_permission("OPS_HOST_VIEW"))],
)
async def list_host_groups(session: DbSessionDep) -> ApiResponse[list[HostGroupResponse]]:
    return success(await _service(session).list_host_groups())


@router.get(
    "/hosts/environments",
    response_model=ApiResponse[list[EnvironmentResponse]],
    dependencies=[Depends(require_permission("OPS_HOST_VIEW"))],
)
async def list_environments(session: DbSessionDep) -> ApiResponse[list[EnvironmentResponse]]:
    return success(await _service(session).list_environments())


@router.get(
    "/hosts/{host_id}",
    response_model=ApiResponse[HostResponse],
    dependencies=[Depends(require_permission("OPS_HOST_VIEW"))],
)
async def get_host(host_id: str, session: DbSessionDep) -> ApiResponse[HostResponse]:
    return success(await _service(session).get_host(int(host_id)))


@router.post(
    "/hosts",
    response_model=ApiResponse[HostResponse],
    dependencies=[Depends(require_permission("OPS_HOST_MANAGE"))],
)
async def create_host(
    payload: HostCreateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[HostResponse]:
    return success(await _service(session).create_host(principal, payload))


@router.put(
    "/hosts/{host_id}",
    response_model=ApiResponse[HostResponse],
    dependencies=[Depends(require_permission("OPS_HOST_MANAGE"))],
)
async def update_host(
    host_id: str,
    payload: HostUpdateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[HostResponse]:
    return success(await _service(session).update_host(principal, int(host_id), payload))


@router.delete(
    "/hosts/{host_id}",
    response_model=ApiResponse[dict],
    dependencies=[Depends(require_permission("OPS_HOST_MANAGE"))],
)
async def delete_host(
    host_id: str, session: DbSessionDep, principal: AdminPrincipal
) -> ApiResponse[dict]:
    await _service(session).delete_host(principal, int(host_id))
    return success({"deleted": True, "host_id": host_id})
