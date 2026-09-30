"""app.admin.departments — request and response DTOs."""

from __future__ import annotations

import datetime

from pydantic import Field

from app.shared.response.dto import ApiModel, OptionalStringId, StringId


class CreateDepartmentRequest(ApiModel):
    """Create a department."""

    department_code: str = Field(min_length=1, max_length=64)
    department_name: str = Field(min_length=1, max_length=128)
    parent_id: OptionalStringId = None
    sort_order: int = 0
    description: str | None = None


class UpdateDepartmentRequest(ApiModel):
    """Update a department."""

    department_name: str | None = Field(default=None, max_length=128)
    parent_id: OptionalStringId = None
    sort_order: int | None = None
    description: str | None = None
    status: str | None = None


class DepartmentResponse(ApiModel):
    """Department detail."""

    id: StringId
    parent_id: OptionalStringId = None
    department_code: str
    department_name: str
    status: str
    sort_order: int
    description: str | None = None
    user_count: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime


class DepartmentTreeNode(ApiModel):
    """One node of the department tree."""

    id: StringId
    parent_id: OptionalStringId = None
    department_code: str
    department_name: str
    status: str
    sort_order: int
    user_count: int = 0
    children: list[DepartmentTreeNode] = Field(default_factory=list)


DepartmentTreeNode.model_rebuild()
