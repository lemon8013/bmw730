"""app.ops.services — 请求与响应 DTO。

对外标识符一律使用 ``StringId``：库里是 BIGINT，契约里是字符串。
依赖边的两个端点同样用字符串，避免前端处理大整数时丢精度。
"""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class ServiceCreateRequest(ApiModel):
    """注册一个被监控的服务。"""

    service_code: str
    service_name: str
    service_type: str = "APPLICATION"
    environment: str = "PRODUCTION"
    host_id: str | None = None
    tags: dict | None = None


class ServiceUpdateRequest(ApiModel):
    """更新一个被监控的服务。"""

    service_name: str | None = None
    service_type: str | None = None
    environment: str | None = None
    host_id: str | None = None
    status: str | None = None
    last_check_at: datetime.datetime | None = None
    availability_rate: float | None = None
    error_rate: float | None = None
    avg_latency_ms: float | None = None
    tags: dict | None = None


class ServiceResponse(ApiModel):
    """一个被监控的服务。"""

    id: StringId
    service_code: str
    service_name: str
    service_type: str
    environment: str
    host_id: str | None = None
    status: str
    last_check_at: datetime.datetime | None = None
    availability_rate: float | None = None
    error_rate: float | None = None
    avg_latency_ms: float | None = None
    tags: dict | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime


class ServiceDependencyCreateRequest(ApiModel):
    """新增一条服务依赖边。"""

    depends_on_service_id: str
    dependency_type: str = "CALLS"


class ServiceDependencyResponse(ApiModel):
    """一条服务依赖边。"""

    id: StringId
    service_id: StringId
    depends_on_service_id: StringId
    dependency_type: str
    created_at: datetime.datetime
