"""app.system.files — request and response DTOs.

Records describe an object in the configured storage backend. Uploads follow a
two step protocol - request an upload target, then either PUT the bytes straight
to the object store (RustFS / MinIO / S3) or POST them to the API when local
storage is used - so the binary
never needs a concurrent downtimes persistence pathway the caller can misuse.
"""

from __future__ import annotations

import datetime
from typing import Any

from pydantic import AliasChoices, Field

from app.shared.response.dto import (
    METADATA_COLUMN_ALIAS,
    ApiModel,
    OptionalStringId,
    StringId,
)


class FileCreateRequest(ApiModel):
    """Record file metadata; storage is abstract (no real binary I/O)."""

    storage_provider: str = "ABSTRACT"
    bucket: str | None = None
    object_key: str
    original_name: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    owner_type: str | None = None
    owner_id: int | None = None
    metadata: dict[str, Any] | None = None


class FileResponse(ApiModel):
    """A file metadata record."""

    id: StringId
    owner_type: str | None = None
    owner_id: OptionalStringId = None
    storage_provider: str
    bucket: str | None = None
    object_key: str
    storage_key: str
    original_name: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    checksum: str | None = None
    status: str
    metadata: dict[str, Any] | None = Field(
        default=None, validation_alias=METADATA_COLUMN_ALIAS
    )
    created_at: datetime.datetime
    deleted_at: datetime.datetime | None = None


class FileCreatedResponse(ApiModel):
    """Result of recording a file."""

    id: StringId
    storage_key: str
    status: str


class UploadIntentRequest(ApiModel):
    """Ask the server for a place to put the bytes.

    The client declares what it intends to upload; the server decides the key,
    the content type and - with an S3 backend - issues the pre-signed URL.
    """

    original_name: str | None = None
    content_type: str | None = None
    category: str = "general"
    size_bytes: int | None = None
    owner_type: str | None = None
    owner_id: OptionalStringId = Field(
        default=None, validation_alias=AliasChoices("owner_id")
    )
    metadata: dict[str, Any] | None = Field(
        default=None, validation_alias=METADATA_COLUMN_ALIAS
    )


class UploadIntentResponse(ApiModel):
    """Where to send the bytes.

    ``mode`` tells the client everything it needs: ``direct`` means the URL is
    absolute and must be PUT verbatim with the listed headers, ``proxy`` means
    the bytes go to our own endpoint (local storage, no pre-signature exists).
    """

    id: StringId
    mode: str
    upload_url: str
    method: str
    headers: dict[str, str] = Field(default_factory=dict)
    expires_at: datetime.datetime | None = None
    object_key: str
    storage_key: str
    content_type: str
    max_size_bytes: int


class DownloadUrlRequest(ApiModel):
    """Ask for a rendered download instead of an attachment."""

    inline: bool = False


class DownloadUrlResponse(ApiModel):
    """A short lived download URL, or ``None`` when the API must proxy."""

    id: StringId
    url: str | None = None
    inline: bool = False
    expires_at: datetime.datetime | None = None
    content_type: str | None = None
    original_name: str | None = None
