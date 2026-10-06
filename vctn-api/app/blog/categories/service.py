"""app.blog.categories — business logic.

Categories are an admin managed reference table. The service is the only place
that decides policy and owns the transaction: every mutation commits at the end
and writes an audit record plus an operation log.
"""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.blog.categories.model import BlogCategory
from app.blog.categories.repository import CategoryRepository
from app.blog.categories.schema import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.logging.writers import RESULT_SUCCESS, write_operation_log
from app.shared.pagination.params import Page, PageParams


class CategoryService:
    """Category management."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = CategoryRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def list_categories(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: PageParams,
    ) -> Page[CategoryResponse]:
        rows, total = await self._repository.list(
            keyword=keyword, status=status, limit=page.limit, offset=page.offset
        )
        return Page.build(
            items=[self._to_response(row) for row in rows], total=total, params=page
        )

    async def get_category(self, category_id: int) -> CategoryResponse:
        row = await self._repository.get(category_id)
        if row is None:
            raise NotFoundError("category not found")
        return self._to_response(row)

    async def create_category(
        self, actor: Principal, payload: CategoryCreateRequest
    ) -> CategoryResponse:
        if await self._repository.get_by_code(payload.category_code):
            raise ConflictError("category code is already taken")
        now = datetime.datetime.now(datetime.UTC)
        row = await self._repository.create(
            id=new_id(),
            category_code=payload.category_code,
            category_name=payload.category_name,
            description=payload.description,
            sort_order=payload.sort_order,
            status="ACTIVE",
            created_at=now,
            updated_at=now,
        )
        await self._audit.record(
            self._session,
            action="BLOG_CATEGORY_CREATE",
            actor=actor,
            operator_username=actor.username,
            resource_type="blog_category",
            resource_id=int(row.id),
            after_data={
                "category_code": row.category_code,
                "category_name": row.category_name,
            },
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await write_operation_log(
            self._session,
            operation="BLOG_CATEGORY_CREATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_category",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    async def update_category(
        self, actor: Principal, category_id: int, payload: CategoryUpdateRequest
    ) -> CategoryResponse:
        row = await self._repository.get(category_id)
        if row is None:
            raise NotFoundError("category not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if not changes:
            raise BusinessRuleError("no field to update")
        await self._repository.update(row, **changes)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="BLOG_CATEGORY_UPDATE",
            actor=actor,
            operator_username=actor.username,
            resource_type="blog_category",
            resource_id=int(row.id),
            after_data=changes,
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await write_operation_log(
            self._session,
            operation="BLOG_CATEGORY_UPDATE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_category",
            resource_id=int(row.id),
        )
        await self._session.commit()
        return self._to_response(row)

    async def delete_category(self, actor: Principal, category_id: int) -> None:
        row = await self._repository.get(category_id)
        if row is None:
            raise NotFoundError("category not found")
        await self._repository.soft_delete(row)
        await self._audit.record(
            self._session,
            action="BLOG_CATEGORY_DELETE",
            actor=actor,
            operator_username=actor.username,
            resource_type="blog_category",
            resource_id=int(row.id),
            after_data={"deleted_at": row.deleted_at.isoformat()},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await write_operation_log(
            self._session,
            operation="BLOG_CATEGORY_DELETE",
            result=RESULT_SUCCESS,
            actor=actor,
            resource_type="blog_category",
            resource_id=int(row.id),
        )
        await self._session.commit()

    def _to_response(self, row: BlogCategory) -> CategoryResponse:
        return CategoryResponse(
            id=str(int(row.id)),
            category_code=str(row.category_code),
            category_name=str(row.category_name),
            description=row.description,
            sort_order=int(row.sort_order or 0),
            status=str(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
