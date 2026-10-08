"""Shared object storage abstractions.

Every binary asset - images, avatars, attachments, generated exports - must go
through this layer so that the rest of the code never touches a filesystem path
or a vendor SDK. Two implementations ship with the project:

``local``
    Files live below :data:`Settings.FILE_STORAGE_ROOT`. Correct for a single
    node, an NFS mount or a development machine. It deliberately does **not**
    implement pre-signed URLs: with local storage the API streams the bytes
    itself, so callers receive ``None`` and fall back to a server side upload.

``s3``
    An S3 compatible object store (RustFS, MinIO, Ceph RGW, AWS S3), implemented
    with ``httpx`` and an explicit AWS Signature Version 4 implementation, because
    the dependency index forbids adding another S3 client library. Storage owned
    and operated by the deployment, no vendor lock-in beyond the S3 API.

Neither backend changes the database contract: ``sys_file`` keeps recording the
provider, the bucket and the object key.
"""

from __future__ import annotations

import datetime
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class StoredObject:
    """An object that exists in a storage backend."""

    provider: str
    bucket: str
    object_key: str
    size_bytes: int = 0
    content_type: str | None = None
    etag: str | None = None
    last_modified: datetime.datetime | None = None


@dataclass(frozen=True, slots=True)
class ObjectContent:
    """Bytes read back from a storage backend."""

    data: bytes
    content_type: str | None = None
    size_bytes: int = 0
    etag: str | None = None


@dataclass(frozen=True, slots=True)
class PresignedUpload:
    """A short lived URL a client may upload an object to directly.

    ``headers`` must be sent verbatim: every header listed here is covered by
    the signature, so dropping one makes the object store reject the request
    and adding one breaks it just as reliably.
    """

    url: str
    expires_at: datetime.datetime
    object_key: str
    method: str = "PUT"
    headers: dict[str, str] = field(default_factory=dict)


@runtime_checkable
class ObjectStorage(Protocol):
    """The contract every storage backend implements.

    Methods never raise ValueError for a missing object: absent objects are
    reported as ``None`` / ``False``. Transport failures surface as
    :class:`app.core.exceptions.ServiceUnavailableError`.
    """

    provider: str

    async def put_object(
        self, *, object_key: str, data: bytes, content_type: str | None = None
    ) -> StoredObject:
        """Write an object and return what was stored."""
        ...

    async def get_object(self, *, object_key: str) -> ObjectContent | None:
        """Read an object, or ``None`` when it does not exist."""
        ...

    async def delete_object(self, *, object_key: str) -> bool:
        """Delete an object; ``False`` when it was already absent."""
        ...

    async def stat_object(self, *, object_key: str) -> StoredObject | None:
        """Describe an object without downloading it."""
        ...

    async def list_objects(self, *, prefix: str) -> AsyncIterator[StoredObject]:
        """Yield every object whose key starts with ``prefix``."""
        ...

    async def presign_upload(
        self,
        *,
        object_key: str,
        content_type: str | None = None,
        expires_seconds: int = 900,
        max_size_bytes: int | None = None,
    ) -> PresignedUpload | None:
        """Return a direct upload target, or ``None`` when unsupported.

        Local storage returns ``None``: the caller then uploads through the API,
        which streams the bytes into the backend itself.
        """
        ...

    async def presign_download(
        self,
        *,
        object_key: str,
        filename: str | None = None,
        content_type: str | None = None,
        expires_seconds: int = 3600,
        inline: bool = False,
    ) -> str | None:
        """Return a download URL, or ``None`` when the caller must proxy."""
        ...

    async def ensure_bucket(self) -> None:
        """Create the bucket/root directory when it does not exist."""
        ...

    async def ping(self) -> None:
        """Raise :class:`ServiceUnavailableError` when the backend is unusable."""
        ...

    async def aclose(self) -> None:
        """Release connections held by the backend."""
        ...


__all__ = [
    "ObjectContent",
    "ObjectStorage",
    "PresignedUpload",
    "StoredObject",
]
