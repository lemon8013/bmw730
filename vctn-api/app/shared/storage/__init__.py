"""Object storage entry points.

Every file, image and generated export reaches durable storage through this
package. See :mod:`app.shared.storage.types` for the contract and
:mod:`app.shared.storage.factory` for backend selection.
"""

from __future__ import annotations

from app.shared.storage.factory import (
    LOCAL_BUCKET,
    PROVIDER_LOCAL,
    PROVIDER_MINIO,
    PROVIDER_RUSTFS,
    PROVIDER_S3,
    PROVIDERS,
    get_object_storage,
    normalize_provider,
    reset_object_storage_cache,
    resolve_provider,
)
from app.shared.storage.keys import (
    InvalidObjectKey,
    build_object_key,
    sanitize_category,
    sanitize_extension,
    validate_object_key,
)
from app.shared.storage.types import (
    ObjectContent,
    ObjectStorage,
    PresignedUpload,
    StoredObject,
)

__all__ = [
    "LOCAL_BUCKET",
    "PROVIDERS",
    "PROVIDER_LOCAL",
    "PROVIDER_MINIO",
    "PROVIDER_RUSTFS",
    "PROVIDER_S3",
    "InvalidObjectKey",
    "ObjectContent",
    "ObjectStorage",
    "PresignedUpload",
    "StoredObject",
    "build_object_key",
    "get_object_storage",
    "normalize_provider",
    "reset_object_storage_cache",
    "resolve_provider",
    "sanitize_category",
    "sanitize_extension",
    "validate_object_key",
]
