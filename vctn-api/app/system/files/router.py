"""app.system.files — HTTP endpoints.

Mounted by the application at the ``/files`` prefix. File management endpoints
require the ``SYSTEM_FILE_MANAGE`` admin permission.

Uploads deliberately avoid ``multipart/form-data`` (which would add another
dependency): the raw body is read from the stream with a hard byte limit, so the
endpoint stays a pure binary sink and works identically whether the bytes end up
in the object store (RustFS / MinIO / S3) or on a local disk.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response

from app.core.dependencies import DbSessionDep, SettingsDep
from app.core.exceptions import ValidationError
from app.shared.auth.context import Principal
from app.shared.authorization.dependencies import require_permission
from app.shared.logging.writers import write_operation_log
from app.shared.pagination.params import Page, PageParams
from app.shared.response.helper import success
from app.shared.response.schema import ApiResponse
from app.shared.storage.content import OCTET_STREAM, should_force_download
from app.system.files.schema import (
    DownloadUrlResponse,
    FileCreatedResponse,
    FileCreateRequest,
    FileResponse,
    UploadIntentRequest,
    UploadIntentResponse,
)
from app.system.files.service import FileService

router = APIRouter(tags=["system:files"])


async def _read_body(request: Request, *, limit: int) -> bytes:
    """Collect the request body, refusing anything past ``limit``.

    Reading the stream (instead of awaiting ``request.body()``) keeps a rogue
    client from pushing hundreds of megabytes into memory before the size check
    can run.
    """
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        total += len(chunk)
        if limit > 0 and total > limit:
            raise ValidationError("request body exceeds the maximum upload size")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post(
    "/upload-intent",
    response_model=ApiResponse[UploadIntentResponse],
    summary="Reserve an object key and return where to send the bytes",
)
async def create_upload_intent(
    payload: UploadIntentRequest,
    session: DbSessionDep,
    settings: SettingsDep,
    principal: Principal = Depends(require_permission("SYSTEM_FILE_MANAGE")),
) -> ApiResponse[UploadIntentResponse]:
    result = await FileService(session, settings=settings).create_upload_intent(
        original_name=payload.original_name,
        content_type=payload.content_type,
        category=payload.category,
        size_bytes=payload.size_bytes,
        owner_type=payload.owner_type,
        owner_id=payload.owner_id,
        metadata=payload.metadata,
    )
    await write_operation_log(
        session,
        operation="FILE_UPLOAD_INTENT",
        result="SUCCESS",
        operator_id=principal.subject_id,
        resource_type="sys_file",
        resource_id=result.id,
        metadata={"mode": result.mode, "content_type": result.content_type},
    )
    await session.commit()
    return success(result)


@router.post(
    "/{file_id}/content",
    response_model=ApiResponse[FileResponse],
    summary="Upload the bytes through the API",
)
async def upload_content(
    file_id: int,
    request: Request,
    session: DbSessionDep,
    settings: SettingsDep,
    principal: Principal = Depends(require_permission("SYSTEM_FILE_MANAGE")),
) -> ApiResponse[FileResponse]:
    body = await _read_body(request, limit=settings.FILE_MAX_SIZE_BYTES)
    declared = request.headers.get("content-type")
    result = await FileService(session, settings=settings).store_content(
        file_id, body, content_type=declared
    )
    await write_operation_log(
        session,
        operation="FILE_UPLOAD",
        result="SUCCESS",
        operator_id=principal.subject_id,
        resource_type="sys_file",
        resource_id=result.id,
        metadata={"size_bytes": result.size_bytes},
    )
    await session.commit()
    return success(result)


@router.post(
    "/{file_id}/confirm",
    response_model=ApiResponse[FileResponse],
    summary="Confirm a direct upload landed",
)
async def confirm_upload(
    file_id: int,
    session: DbSessionDep,
    settings: SettingsDep,
    principal: Principal = Depends(require_permission("SYSTEM_FILE_MANAGE")),
) -> ApiResponse[FileResponse]:
    result = await FileService(session, settings=settings).confirm_upload(file_id)
    await write_operation_log(
        session,
        operation="FILE_UPLOAD_CONFIRM",
        result="SUCCESS",
        operator_id=principal.subject_id,
        resource_type="sys_file",
        resource_id=result.id,
    )
    await session.commit()
    return success(result)


@router.get(
    "/{file_id}/download-url",
    response_model=ApiResponse[DownloadUrlResponse],
    summary="Return a short lived download URL",
    dependencies=[Depends(require_permission("SYSTEM_FILE_MANAGE"))],
)
async def download_url(
    file_id: int,
    session: DbSessionDep,
    settings: SettingsDep,
    inline: bool = Query(default=False),
) -> ApiResponse[DownloadUrlResponse]:
    return success(
        await FileService(session, settings=settings).download_url(file_id, inline=inline)
    )


@router.get(
    "/{file_id}/content",
    summary="Stream the object through the API",
    dependencies=[Depends(require_permission("SYSTEM_FILE_MANAGE"))],
)
async def download_content(
    file_id: int,
    session: DbSessionDep,
    settings: SettingsDep,
    inline: bool = Query(default=False),
) -> Response:
    service = FileService(session, settings=settings)
    record = await service.get_file(file_id)
    content = await service.read_content(file_id)
    content_type = content.content_type or OCTET_STREAM
    disposition = (
        "inline" if inline and not should_force_download(content_type) else "attachment"
    )
    headers = {
        "Content-Length": str(content.size_bytes or len(content.data)),
        "Content-Disposition": disposition,
    }
    if record.original_name:
        encoded = quote(record.original_name, safe="")
        headers["Content-Disposition"] = (
            f'{disposition}; filename="{record.original_name}"; '
            f"filename*=UTF-8''{encoded}"
        )
    return Response(content=content.data, media_type=content_type, headers=headers)


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
    summary="Delete (logically) a file record and its stored object",
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
