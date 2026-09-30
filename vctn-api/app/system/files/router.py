"""app.system.files — HTTP endpoints.

Mounted by the application at the ``/system/files`` prefix. File management
endpoints require the ``SYSTEM_FILE_MANAGE`` admin permission.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.core.dependencies import DbSessionDep
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.logging.writers import write_operation_log
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse
from app.system.files.schema import FileCreatedResponse, FileCreateRequest, FileResponse
from app.system.files.service import FileService

router = APIRouter(tags=["system:files"])


@router.post(
    "",
    response_model=ApiResponse[FileCreatedResponse],
    summary="Record file metadata",
)
async def create_file(
    payload: FileCreateRequest,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("SYSTEM_FILE_MANAGE")),
) -> ApiResponse[FileCreatedResponse]:
    result = await FileService(session).create_file(
        storage_provider=payload.storage_provider,
        object_key=payload.object_key,
        bucket=payload.bucket,
        original_name=payload.original_name,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        checksum=payload.checksum,
        owner_type=payload.owner_type,
        owner_id=payload.owner_id,
        metadata=payload.metadata,
    )
    await write_operation_log(
        session,
        operation="FILE_CREATE",
        result="SUCCESS",
        operator_id=principal.subject_id,
        resource_type="sys_file",
        resource_id=result.id,
        metadata={"storage_provider": payload.storage_provider},
    )
    await session.commit()
    return success(result)


@router.get(
    "",
    response_model=ApiResponse[Page[FileResponse]],
    summary="List file metadata",
    dependencies=[Depends(require_permission("SYSTEM_FILE_MANAGE"))],
)
async def list_files(
    session: DbSessionDep,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    status: str | None = Query(default=None),
    owner_type: str | None = Query(default=None),
) -> ApiResponse[Page[FileResponse]]:
    return success(
        await FileService(session).list_files(
            page=PageParams(page=page, page_size=page_size),
            status=status,
            owner_type=owner_type,
        )
    )


@router.get(
    "/{file_id}",
    response_model=ApiResponse[FileResponse],
    summary="Get a file record",
    dependencies=[Depends(require_permission("SYSTEM_FILE_MANAGE"))],
)
async def get_file(
    file_id: int,
    session: DbSessionDep,
) -> ApiResponse[FileResponse]:
    return success(await FileService(session).get_file(file_id))


@router.delete(
    "/{file_id}",
    response_model=ApiResponse[FileResponse],
    summary="Delete (logically) a file record",
)
async def delete_file(
    file_id: int,
    session: DbSessionDep,
    principal: Principal = Depends(require_permission("SYSTEM_FILE_MANAGE")),
) -> ApiResponse[FileResponse]:
    result = await FileService(session).delete_file(file_id)
    await write_operation_log(
        session,
        operation="FILE_DELETE",
        result="SUCCESS",
        operator_id=principal.subject_id,
        resource_type="sys_file",
        resource_id=str(file_id),
    )
    await session.commit()
    return success(result)
