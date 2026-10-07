"""app.ops.apis — 请求与响应 DTO。

对外标识符一律 ``StringId``。指标键是采集侧与查询侧共用的约定，集中定义在这里，
避免服务里散落字符串字面量。
"""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId

#: 端点维度指标的键约定（endpoint_id 维度写入 ops_metric_sample）。
API_METRIC_REQUEST_COUNT: str = "api.request_count"
API_METRIC_ERROR_RATE: str = "api.error_rate"
API_METRIC_LATENCY_AVG: str = "api.latency_avg"
API_METRIC_LATENCY_P95: str = "api.latency_p95"

API_METRIC_KEYS: tuple[str, ...] = (
    API_METRIC_REQUEST_COUNT,
    API_METRIC_ERROR_RATE,
    API_METRIC_LATENCY_AVG,
    API_METRIC_LATENCY_P95,
)


class EndpointResponse(ApiModel):
    """一个被监控的 API 端点。"""

    id: StringId
    endpoint_key: str
    http_method: str
    path_pattern: str
    service_id: str | None = None
    environment: str
    is_monitored: bool
    request_count: int
    error_count: int
    avg_latency_ms: float | None = None
    p95_latency_ms: float | None = None
    last_seen_at: datetime.datetime | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class EndpointMetricsResponse(ApiModel):
    """一个端点在时间窗口内的指标聚合。

    窗口内没有采样点时字段回落为 0 而不是报错：端点刚登记或采集器尚未上报都属
    于正常状态，运维看板不应因此变红。
    """

    endpoint_id: StringId
    hours: int
    window_start: datetime.datetime
    window_end: datetime.datetime
    request_count: int
    error_count: int
    error_rate: float
    avg_latency_ms: float
    p95_latency_ms: float
    sample_count: int
