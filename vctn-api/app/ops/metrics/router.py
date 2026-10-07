"""app.ops.metrics — HTTP endpoints.

Metric reads require ``OPS_MONITOR_VIEW`` and collector writes require
``OPS_MONITOR_MANAGE``.
"""

from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.ops.metrics.schema import (
    MetricDefinitionResponse,
    MetricSamplesCreateRequest,
    MetricSamplesCreateResponse,
    MetricSeriesPoint,
)
from app.ops.metrics.service import MetricService
from app.shared.authorization.dependencies import AdminPrincipal, require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> MetricService:
    return MetricService(session)


@router.get(
    "/metrics",
    response_model=ApiResponse[Page[MetricDefinitionResponse]],
    dependencies=[Depends(require_permission("OPS_MONITOR_VIEW"))],
)
async def list_metrics(
    session: DbSessionDep,
    keyword: str | None = Query(default=None),
    metric_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
) -> ApiResponse[Page[MetricDefinitionResponse]]:
    return success(
        await _service(session).list_definitions(
            keyword=keyword,
            metric_type=metric_type,
            page=PageParams(page=page, page_size=page_size),
        )
    )


@router.get(
    "/metrics/series",
    response_model=ApiResponse[list[MetricSeriesPoint]],
    dependencies=[Depends(require_permission("OPS_MONITOR_VIEW"))],
)
async def get_metric_series(
    session: DbSessionDep,
    metric_key: str = Query(min_length=1),
    start: datetime.datetime = Query(),
    end: datetime.datetime = Query(),
    step: str = Query(min_length=1),
    host_id: str | None = Query(default=None),
    service_id: str | None = Query(default=None),
    endpoint_id: str | None = Query(default=None),
) -> ApiResponse[list[MetricSeriesPoint]]:
    return success(
        await _service(session).get_series(
            metric_key=metric_key,
            start=start,
            end=end,
            step=step,
            host_id=int(host_id) if host_id else None,
            service_id=int(service_id) if service_id else None,
            endpoint_id=int(endpoint_id) if endpoint_id else None,
        )
    )


@router.post(
    "/metrics/samples",
    response_model=ApiResponse[MetricSamplesCreateResponse],
    dependencies=[Depends(require_permission("OPS_MONITOR_MANAGE"))],
)
async def create_metric_samples(
    payload: MetricSamplesCreateRequest,
    session: DbSessionDep,
    principal: AdminPrincipal,
) -> ApiResponse[MetricSamplesCreateResponse]:
    return success(await _service(session).create_samples(principal, payload))
