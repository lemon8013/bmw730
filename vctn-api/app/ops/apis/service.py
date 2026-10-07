"""app.ops.apis — 业务逻辑。

端点注册表由访问日志归一化产出，本模块只提供读能力，因此没有事务与审计：读
路径不产生需要追溯的状态变更。
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.ops.apis.model import OpsEndpoint
from app.ops.apis.repository import EndpointRepository
from app.ops.apis.schema import (
    API_METRIC_ERROR_RATE,
    API_METRIC_KEYS,
    API_METRIC_LATENCY_AVG,
    API_METRIC_LATENCY_P95,
    API_METRIC_REQUEST_COUNT,
    EndpointMetricsResponse,
    EndpointResponse,
)
from app.shared.pagination.params import Page, PageParams


class EndpointService:
    """API 端点监控查询。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repository = EndpointRepository(session)

    async def list_endpoints(
        self,
        *,
        keyword: str | None = None,
        http_method: str | None = None,
        service_id: int | None = None,
        environment: str | None = None,
        is_monitored: bool | None = None,
        page: PageParams,
    ) -> Page[EndpointResponse]:
        rows, total = await self._repository.list(
            keyword=keyword,
            http_method=http_method,
            service_id=service_id,
            environment=environment,
            is_monitored=is_monitored,
            limit=page.limit,
            offset=page.offset,
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get_endpoint(self, endpoint_id: int) -> EndpointResponse:
        row = await self._repository.get(endpoint_id)
        if row is None:
            raise NotFoundError("endpoint not found")
        return self._to_response(row)

    async def get_endpoint_metrics(
        self, endpoint_id: int, *, hours: int
    ) -> EndpointMetricsResponse:
        """聚合一个端点在最近 ``hours`` 小时内的计数、错误率与延迟。

        窗口优先取 ``ops_metric_sample`` 的采样；没有采样时回落到端点上累计的
        计数与延迟字段；两者都没有则给 0 —— 缺少数据不是错误。
        """
        row = await self._repository.get(endpoint_id)
        if row is None:
            raise NotFoundError("endpoint not found")
        window_end = datetime.datetime.now(datetime.UTC)
        window_start = window_end - datetime.timedelta(hours=hours)

        request_total, _, _, _ = await self._repository.aggregate_samples(
            endpoint_id=endpoint_id, metric_key=API_METRIC_REQUEST_COUNT, since=window_start
        )
        _, error_rate_avg, _, _ = await self._repository.aggregate_samples(
            endpoint_id=endpoint_id, metric_key=API_METRIC_ERROR_RATE, since=window_start
        )
        _, latency_avg, _, _ = await self._repository.aggregate_samples(
            endpoint_id=endpoint_id, metric_key=API_METRIC_LATENCY_AVG, since=window_start
        )
        _, _, latency_p95, _ = await self._repository.aggregate_samples(
            endpoint_id=endpoint_id, metric_key=API_METRIC_LATENCY_P95, since=window_start
        )
        sample_count = await self._repository.count_samples(
            endpoint_id=endpoint_id, metric_keys=API_METRIC_KEYS, since=window_start
        )

        # 采样缺失时回落到端点累计值：端点登记后由采集任务维护的统计仍然可信。
        if request_total is not None:
            request_count = int(request_total)
        else:
            request_count = int(row.request_count or 0)
        if error_rate_avg is not None:
            error_rate = float(error_rate_avg)
        elif request_count:
            error_rate = float(row.error_count or 0) / float(request_count)
        else:
            error_rate = 0.0
        if latency_avg is not None:
            avg_latency_ms = float(latency_avg)
        else:
            avg_latency_ms = float(row.avg_latency_ms or 0.0)
        if latency_p95 is not None:
            p95_latency_ms = float(latency_p95)
        else:
            p95_latency_ms = float(row.p95_latency_ms or 0.0)
        return EndpointMetricsResponse(
            endpoint_id=str(int(row.id)),
            hours=hours,
            window_start=window_start,
            window_end=window_end,
            request_count=request_count,
            error_count=int(round(request_count * error_rate)),
            error_rate=error_rate,
            avg_latency_ms=avg_latency_ms,
            p95_latency_ms=p95_latency_ms,
            sample_count=sample_count,
        )

    def _to_response(self, row: OpsEndpoint) -> EndpointResponse:
        return EndpointResponse(
            id=str(int(row.id)),
            endpoint_key=str(row.endpoint_key),
            http_method=str(row.http_method),
            path_pattern=str(row.path_pattern),
            service_id=str(int(row.service_id)) if row.service_id else None,
            environment=str(row.environment),
            is_monitored=bool(row.is_monitored),
            request_count=int(row.request_count or 0),
            error_count=int(row.error_count or 0),
            avg_latency_ms=row.avg_latency_ms,
            p95_latency_ms=row.p95_latency_ms,
            last_seen_at=row.last_seen_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
