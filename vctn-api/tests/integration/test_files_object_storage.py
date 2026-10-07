"""End to end file storage against the real database.

The service owns two things at once - a row in ``sys_file`` and an object in the
storage backend - and the only interesting failures live at that boundary: a row
advertising bytes that were never written, an orphaned direct upload nobody
retired, a delete that forgets the object. Stubs cannot show any of it, so these
tests write real rows and real files.
"""

from __future__ import annotations

import datetime
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.core.exceptions import NotFoundError, ValidationError
from app.shared.database.session import build_session_factory
from app.shared.storage.local import LocalStorage
from app.shared.storage.types import (
    ObjectContent,
    PresignedUpload,
    StoredObject,
)
from app.system.files.service import FileService

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16


class _FakeDirectStorage:
    """A pre-signing backend that never actually receives the bytes."""

    provider = "s3"
    bucket = "vctn"

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    async def put_object(self, *, object_key: str, data: bytes, content_type: str | None = None):
        self.objects[object_key] = data
        return StoredObject(
            provider=self.provider,
            bucket=self.bucket,
            object_key=object_key,
            size_bytes=len(data),
            content_type=content_type,
        )

    async def get_object(self, *, object_key: str):
        data = self.objects.get(object_key)
        if data is None:
            return None
        return ObjectContent(data=data, content_type="image/png", size_bytes=len(data))

    async def delete_object(self, *, object_key: str) -> bool:
        return self.objects.pop(object_key, None) is not None

    async def stat_object(self, *, object_key: str):
        if object_key not in self.objects:
            return None
        return StoredObject(
            provider=self.provider,
            bucket=self.bucket,
            object_key=object_key,
            size_bytes=len(self.objects[object_key]),
        )

    async def list_objects(self, *, prefix: str):  # pragma: no cover - not exercised
        del prefix
        return
        yield  # type: ignore[misc]

    async def presign_upload(
        self, *, object_key: str, content_type=None, expires_seconds=900, max_size_bytes=None
    ):
        return PresignedUpload(
            url=f"https://rustfs.internal:9000/vctn/{object_key}",
            expires_at=datetime.datetime.now(datetime.UTC)
            + datetime.timedelta(seconds=expires_seconds),
            object_key=object_key,
            headers={"Content-Type": content_type or "application/octet-stream"},
        )

    async def presign_download(self, *, object_key: str, **_: object) -> str:
        return f"https://rustfs.internal:9000/vctn/{object_key}?signature=abc"

    async def ensure_bucket(self) -> None: ...

    async def ping(self) -> None: ...

    async def aclose(self) -> None: ...


@pytest.fixture()
async def _cleanup_rows(live_settings: Settings) -> AsyncIterator[list[int]]:
    engine = create_async_engine(live_settings.database_url)
    ids: list[int] = []
    try:
        yield ids
    finally:
        if ids:
            async with build_session_factory(engine)() as session:
                await session.execute(
                    text("delete from sys_file where id = any(:ids)"),
                    {"ids": ids},
                )
                await session.commit()
        await engine.dispose()


@pytest.mark.asyncio
async def test_proxy_upload_writes_the_object_and_the_row(
    live_settings: Settings, live_infrastructure: None, tmp_path, _cleanup_rows: list[int]
) -> None:
    del live_infrastructure
    storage = LocalStorage(root=tmp_path / "objects", bucket="vctn")
    await storage.ensure_bucket()
    engine = create_async_engine(live_settings.database_url)
    try:
        async with build_session_factory(engine)() as session:
            service = FileService(session, storage=storage, settings=live_settings)
            intent = await service.create_upload_intent(
                original_name="avatar.png", content_type="image/png", category="avatar"
            )
            _cleanup_rows.append(int(intent.id))
            assert intent.mode == "proxy"
            assert intent.upload_url == f"{live_settings.API_PREFIX}/files/{intent.id}/content"
            assert intent.object_key.startswith("avatar/")

            stored = await service.store_content(int(intent.id), PNG_BYTES)
            assert stored.size_bytes == len(PNG_BYTES)
            assert stored.content_type == "image/png"
            assert stored.checksum

            content = await service.read_content(int(intent.id))
            assert content.data == PNG_BYTES
            assert (tmp_path / "objects" / stored.object_key).is_file()

            # Local storage cannot pre-sign, so the caller is told to proxy.
            download = await service.download_url(int(intent.id))
            assert download.url is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_declared_content_type_is_validated_before_the_upload(
    live_settings: Settings, live_infrastructure: None, tmp_path, _cleanup_rows: list[int]
) -> None:
    del live_infrastructure
    engine = create_async_engine(live_settings.database_url)
    try:
        async with build_session_factory(engine)() as session:
            service = FileService(
                session,
                storage=LocalStorage(root=tmp_path),
                settings=Settings(FILE_ALLOWED_MIME_TYPES="image/png,image/jpeg"),
            )
            with pytest.raises(ValidationError, match="not allowed"):
                await service.create_upload_intent(
                    original_name="payload.exe", content_type="application/x-msdownload"
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_unconfirmed_direct_upload_is_retired(
    live_settings: Settings, live_infrastructure: None, _cleanup_rows: list[int]
) -> None:
    """A reserved row whose bytes never arrive must stop being advertised."""
    del live_infrastructure
    storage = _FakeDirectStorage()
    engine = create_async_engine(live_settings.database_url)
    try:
        async with build_session_factory(engine)() as session:
            service = FileService(session, storage=storage, settings=live_settings)
            intent = await service.create_upload_intent(
                original_name="shot.png", content_type="image/png"
            )
            _cleanup_rows.append(int(intent.id))
            assert intent.mode == "direct"
            assert intent.upload_url.startswith("https://rustfs.internal:9000/")

            with pytest.raises(NotFoundError, match="uploaded object was not found"):
                await service.confirm_upload(int(intent.id))

            with pytest.raises(NotFoundError):
                await service.get_file(int(intent.id))
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_direct_upload_confirmation_records_the_real_size(
    live_settings: Settings, live_infrastructure: None, _cleanup_rows: list[int]
) -> None:
    del live_infrastructure
    storage = _FakeDirectStorage()
    engine = create_async_engine(live_settings.database_url)
    try:
        async with build_session_factory(engine)() as session:
            service = FileService(session, storage=storage, settings=live_settings)
            intent = await service.create_upload_intent(
                original_name="shot.png", content_type="image/png"
            )
            _cleanup_rows.append(int(intent.id))
            await storage.put_object(object_key=intent.object_key, data=PNG_BYTES)

            record = await service.confirm_upload(int(intent.id))
            assert record.size_bytes == len(PNG_BYTES)

            download = await service.download_url(int(intent.id))
            assert download.url is not None and download.expires_at is not None

            deleted = await service.delete_file(int(intent.id))
            assert deleted.status == "DELETED"
            assert intent.object_key not in storage.objects
    finally:
        await engine.dispose()
