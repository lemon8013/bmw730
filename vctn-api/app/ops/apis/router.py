"""app.ops.apis — HTTP 端点。

API 监控是只读域：端点由访问日志归一化产出，人工改不动，因此所有端点只需要
``OPS_API_VIEW``。聚合窗口由调用方通过 ``hours`` 给出，后端不预设观察区间。
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.apis.schema import EndpointMetricsResponse, EndpointResponse
from app.ops.apis.service import EndpointService
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> EndpointService:
    return EndpointService(session)


@router.get(
    "/apis",
    response_model=ApiResponse[Page[EndpointResponse]],
    dependencies=[Depends(require_permission("OPS_API_VIEW"))],
)
async def list_endpoints(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    http_method: str | None = Query(default=None),
    service_id: str | None = Query(default=None),
    environment: str | None = Query(default=None),
    is_monitored: bool | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[EndpointResponse]]:
    return success(
        await _service(session).list_endpoints(
            keyword=keyword,
            http_method=http_method,
            service_id=int(service_id) if service_id else None,
            environment=environment,
            is_monitored=is_monitored,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get(
    "/apis/{endpoint_id}",
    response_model=ApiResponse[EndpointResponse],
    dependencies=[Depends(require_permission("OPS_API_VIEW"))],
)
async def get_endpoint(
    endpoint_id: str, session: DbSessionDep
) -> ApiResponse[EndpointResponse]:
    return success(await _service(session).get_endpoint(int(endpoint_id)))


@router.get(
    "/apis/{endpoint_id}/metrics",
    response_model=ApiResponse[EndpointMetricsResponse],
    dependencies=[Depends(require_permission("OPS_API_VIEW"))],
)
async def get_endpoint_metrics(
    endpoint_id: str,
    session: DbSessionDep,
    hours: int = Query(default=24, ge=1, le=720),
) -> ApiResponse[EndpointMetricsResponse]:
    return success(
        await _service(session).get_endpoint_metrics(int(endpoint_id), hours=hours)
    )
