"""app.admin.dictionaries — HTTP endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.admin.dictionaries.schema import (
    CreateDictItemRequest,
    CreateDictTypeRequest,
    DictItemResponse,
    DictTypeResponse,
    UpdateDictItemRequest,
    UpdateDictTypeRequest,
)
from app.admin.dictionaries.service import DictionaryService
from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse

router = APIRouter()


def _service(session: DbSessionDep) -> DictionaryService:
    return DictionaryService(session)


@router.get("/dictionaries/types", response_model=ApiResponse[Page[DictTypeResponse]])
async def list_types(
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    principal: Principal = Depends(require_permission("DICT_VIEW")),
) -> ApiResponse[Page[DictTypeResponse]]:
    return success(
        await _service(session).list_types(page=PageParams(page=page, page_size=page_size))
    )


@router.post("/dictionaries/types", response_model=ApiResponse[DictTypeResponse])
async def create_type(
    payload: CreateDictTypeRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("DICT_EDIT")),
) -> ApiResponse[DictTypeResponse]:
    return success(await _service(session).create_type(principal, payload))


@router.put("/dictionaries/types/{type_id}", response_model=ApiResponse[DictTypeResponse])
async def update_type(
    type_id: str,
    payload: UpdateDictTypeRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("DICT_EDIT")),
) -> ApiResponse[DictTypeResponse]:
    return success(await _service(session).update_type(principal, int(type_id), payload))


@router.delete("/dictionaries/types/{type_id}", response_model=ApiResponse[dict])
async def delete_type(
    type_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("DICT_EDIT")),
) -> ApiResponse[dict]:
    await _service(session).delete_type(principal, int(type_id))
    return success({"deleted": True, "type_id": type_id})


@router.get(
    "/dictionaries/types/{type_id}/items",
    response_model=ApiResponse[list[DictItemResponse]],
)
async def list_items(
    type_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("DICT_VIEW")),
) -> ApiResponse[list[DictItemResponse]]:
    return success(await _service(session).list_items(int(type_id)))


@router.post(
    "/dictionaries/types/{type_id}/items",
    response_model=ApiResponse[DictItemResponse],
)
async def create_item(
    type_id: str,
    payload: CreateDictItemRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("DICT_EDIT")),
) -> ApiResponse[DictItemResponse]:
    return success(await _service(session).create_item(principal, int(type_id), payload))


@router.put("/dictionaries/items/{item_id}", response_model=ApiResponse[DictItemResponse])
async def update_item(
    item_id: str,
    payload: UpdateDictItemRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("DICT_EDIT")),
) -> ApiResponse[DictItemResponse]:
    return success(await _service(session).update_item(principal, int(item_id), payload))


@router.delete("/dictionaries/items/{item_id}", response_model=ApiResponse[dict])
async def delete_item(
    item_id: str,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("DICT_EDIT")),
) -> ApiResponse[dict]:
    await _service(session).delete_item(principal, int(item_id))
    return success({"deleted": True, "item_id": item_id})
