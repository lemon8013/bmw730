"""app.admin.dictionaries — business logic."""

from __future__ import annotations

import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.admin.dictionaries.model import SysDictItem, SysDictType
from app.admin.dictionaries.repository import DictionaryRepository
from app.admin.dictionaries.schema import (
    CreateDictItemRequest,
    CreateDictTypeRequest,
    DictItemResponse,
    DictTypeResponse,
    UpdateDictItemRequest,
    UpdateDictTypeRequest,
)
from app.core.config import Settings, get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.shared.audit.service import AuditService
from app.shared.auth.context import Principal
from app.shared.ids import new_id
from app.shared.pagination.params import Page, PageParams

ACTIVE_STATUS: str = "ACTIVE"


class DictionaryService:
    """Dictionary types and items."""

    def __init__(self, session: AsyncSession, settings: Settings | None = None) -> None:
        self._session = session
        self._repository = DictionaryRepository(session)
        self._settings = settings or get_settings()
        self._audit = AuditService(self._settings)

    async def list_types(self, *, page: PageParams) -> Page[DictTypeResponse]:
        rows = await self._repository.list_types()
        counts = await self._repository.item_counts()
        items = [
            DictTypeResponse(
                id=str(int(row.id)),
                dict_code=str(row.dict_code),
                dict_name=str(row.dict_name),
                description=row.description,
                status=str(row.status),
                item_count=counts.get(int(row.id), 0),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
        total = len(items)
        return Page.build(
            items=items[page.offset : page.offset + page.limit], total=total, params=page
        )

    async def create_type(
        self, actor: Principal, payload: CreateDictTypeRequest
    ) -> DictTypeResponse:
        if await self._repository.exists_type_code(payload.dict_code):
            raise ConflictError("dictionary code is already taken")
        row = SysDictType(
            id=new_id(),
            dict_code=payload.dict_code,
            dict_name=payload.dict_name,
            description=payload.description,
            status=ACTIVE_STATUS,
        )
        self._repository.add_type(row)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="DICT_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_dict_type",
            resource_id=int(row.id),
            after_data={"dict_code": row.dict_code},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return DictTypeResponse(
            id=str(int(row.id)),
            dict_code=str(row.dict_code),
            dict_name=str(row.dict_name),
            description=row.description,
            status=str(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def update_type(
        self, actor: Principal, type_id: int, payload: UpdateDictTypeRequest
    ) -> DictTypeResponse:
        row = await self._repository.get_type(type_id)
        if row is None:
            raise NotFoundError("dictionary type not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        before = {"dict_name": row.dict_name, "status": row.status}
        for field_name, value in changes.items():
            setattr(row, field_name, value)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="DICT_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_dict_type",
            resource_id=type_id,
            before_data=before,
            after_data={"dict_name": row.dict_name, "status": row.status},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return DictTypeResponse(
            id=str(int(row.id)),
            dict_code=str(row.dict_code),
            dict_name=str(row.dict_name),
            description=row.description,
            status=str(row.status),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )

    async def delete_type(self, actor: Principal, type_id: int) -> None:
        row = await self._repository.get_type(type_id)
        if row is None:
            raise NotFoundError("dictionary type not found")
        await self._repository.soft_delete_type(type_id, now=datetime.datetime.now(datetime.UTC))
        await self._audit.record(
            self._session,
            action="DICT_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_dict_type",
            resource_id=type_id,
            after_data={"deleted_at": datetime.datetime.now(datetime.UTC).isoformat()},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()

    async def list_items(self, type_id: int) -> list[DictItemResponse]:
        row = await self._repository.get_type(type_id)
        if row is None:
            raise NotFoundError("dictionary type not found")
        return [
            DictItemResponse.model_validate(item)
            for item in await self._repository.list_items(type_id)
        ]

    async def create_item(
        self, actor: Principal, type_id: int, payload: CreateDictItemRequest
    ) -> DictItemResponse:
        if await self._repository.get_type(type_id) is None:
            raise NotFoundError("dictionary type not found")
        if await self._repository.exists_item_value(type_id, payload.item_value):
            raise ConflictError("dictionary item value already exists")
        if payload.is_default:
            await self._repository.clear_default_flag(type_id)
        row = SysDictItem(
            id=new_id(),
            dict_type_id=type_id,
            item_label=payload.item_label,
            item_value=payload.item_value,
            item_code=payload.item_code,
            sort_order=payload.sort_order,
            status=ACTIVE_STATUS,
            is_default=payload.is_default,
            description=payload.description,
        )
        self._repository.add_item(row)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="DICT_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_dict_item",
            resource_id=int(row.id),
            after_data={"item_value": row.item_value},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return DictItemResponse.model_validate(row)

    async def update_item(
        self, actor: Principal, item_id: int, payload: UpdateDictItemRequest
    ) -> DictItemResponse:
        row = await self._repository.get_item(item_id)
        if row is None:
            raise NotFoundError("dictionary item not found")
        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        before = {"item_value": row.item_value, "item_label": row.item_label}
        if "item_value" in changes and changes["item_value"] != row.item_value:
            if await self._repository.exists_item_value(
                int(row.dict_type_id), str(changes["item_value"]), exclude_id=item_id
            ):
                raise ConflictError("dictionary item value already exists")
        for field_name, value in changes.items():
            setattr(row, field_name, value)
        if row.is_default:
            await self._repository.clear_default_flag(int(row.dict_type_id), exclude_id=item_id)
        row.updated_at = datetime.datetime.now(datetime.UTC)
        await self._session.flush()
        await self._audit.record(
            self._session,
            action="DICT_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_dict_item",
            resource_id=item_id,
            before_data=before,
            after_data={"item_value": row.item_value, "item_label": row.item_label},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
        return DictItemResponse.model_validate(row)

    async def delete_item(self, actor: Principal, item_id: int) -> None:
        row = await self._repository.get_item(item_id)
        if row is None:
            raise NotFoundError("dictionary item not found")
        await self._repository.soft_delete_item(item_id, now=datetime.datetime.now(datetime.UTC))
        await self._audit.record(
            self._session,
            action="DICT_EDIT",
            operator_id=actor.subject_id,
            operator_username=actor.username,
            resource_type="sys_dict_item",
            resource_id=item_id,
            after_data={"deleted_at": datetime.datetime.now(datetime.UTC).isoformat()},
            ip=actor.ip,
            user_agent=actor.user_agent,
        )
        await self._session.commit()
