"""app.ops.availability — 请求与响应 DTO。

对外标识符一律 ``StringId``；时间一律 UTC，由调用方按展示时区自行转换。
"""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class AvailabilityCheckCreateRequest(ApiModel):
    """新增一个可用性探测。"""

    check_code: str
    name: str
    check_type: str
    target: str
    service_id: str | None = None
    environment: str = "PRODUCTION"
    timeout_ms: int = 5000
    interval_seconds: int = 60
    expected_status: int | None = None
    enabled: bool = True


class AvailabilityCheckUpdateRequest(ApiModel):
    """更新一个可用性探测。"""

    name: str | None = None
    target: str | None = None
    service_id: str | None = None
    environment: str | None = None
    timeout_ms: int | None = None
    interval_seconds: int | None = None
    expected_status: int | None = None
    enabled: bool | None = None


class AvailabilityCheckResponse(ApiModel):
    """一个可用性探测定义。"""

    id: StringId
    check_code: str
    name: str
    check_type: str
    target: str
    service_id: str | None = None
    environment: str
    timeout_ms: int
    interval_seconds: int
    expected_status: int | None = None
    enabled: bool
    created_at: datetime.datetime
    updated_at: datetime.datetime


class AvailabilityResultResponse(ApiModel):
    """一次探测执行结果。"""

    id: StringId
    check_id: StringId
    success: bool
    latency_ms: float | None = None
    status_code: int | None = None
    error_message: str | None = None
    detail: dict | None = None
    checked_at: datetime.datetime
