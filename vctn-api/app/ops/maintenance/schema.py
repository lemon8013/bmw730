"""app.ops.maintenance — 请求与响应 DTO。

对外标识符一律 ``StringId``；窗口起止时间一律 UTC，由调用方按展示时区转换。
"""

from __future__ import annotations

import datetime

from app.shared.response.dto import ApiModel, StringId


class MaintenanceWindowCreateRequest(ApiModel):
    """新增一个维护窗口。"""

    window_code: str
    title: str
    reason: str | None = None
    scope_type: str = "GLOBAL"
    scope_id: str | None = None
    starts_at: datetime.datetime
    ends_at: datetime.datetime
    suppress_alerts: bool = True
    enabled: bool = True


class MaintenanceWindowUpdateRequest(ApiModel):
    """更新一个维护窗口。"""

    title: str | None = None
    reason: str | None = None
    scope_type: str | None = None
    scope_id: str | None = None
    starts_at: datetime.datetime | None = None
    ends_at: datetime.datetime | None = None
    suppress_alerts: bool | None = None
    enabled: bool | None = None


class MaintenanceWindowResponse(ApiModel):
    """一个维护窗口。"""

    id: StringId
    window_code: str
    title: str
    reason: str | None = None
    scope_type: str
    scope_id: str | None = None
    starts_at: datetime.datetime
    ends_at: datetime.datetime
    suppress_alerts: bool
    enabled: bool
    created_by: str | None = None
    created_by_username: str | None = None
    created_at: datetime.datetime
    updated_at: datetime.datetime
