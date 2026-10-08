"""Content type detection and upload validation.

The ``Content-Type`` header of an upload is attacker controlled, so it is never
trusted on its own: images are recognized from their magic bytes and the sniffed
type wins over whatever the client declared. An object whose declared type says
``image/png`` but whose bytes are HTML cannot then be served back as an image.
"""

from __future__ import annotations

from typing import Final

from app.core.exceptions import ValidationError

IMAGE_MIME_TYPES: Final[frozenset[str]] = frozenset(
    {"image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp"}
)

#: Types the API accepts by default. Binary formats that execute in a browser
#: (``application/xhtml+xml`` and friends) are absent on purpose.
DEFAULT_ALLOWED_MIME_TYPES: Final[frozenset[str]] = frozenset(
    IMAGE_MIME_TYPES
    | {
        "image/x-icon",
        "image/svg+xml",
        "application/pdf",
        "application/json",
        "application/zip",
        "application/gzip",
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.ms-excel",
    }
)

OCTET_STREAM: Final[str] = "application/octet-stream"

# ``None`` prefix matches exactly; every other entry is a leading byte prefix.
_SIGNATURES: Final[tuple[tuple[bytes, str], ...]] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"GIF87a", "image/gif"),
    (b"GIF89a", "image/gif"),
    (b"BM", "image/bmp"),
    (b"%PDF-", "application/pdf"),
    (b"PK\x03\x04", "application/zip"),
    (b"\x1f\x8b", "application/gzip"),
    (b"Rar!\x1a\x07", "application/x-rar-compressed"),
)

_WEBP_HEADER: Final[bytes] = b"WEBP"
_SVG_MARKERS: Final[tuple[bytes, ...]] = (b"<svg", b"<?xml")


def sniff_content_type(data: bytes) -> str | None:
    """Return the type implied by the magic bytes, or ``None``."""
    for signature, mime_type in _SIGNATURES:
        if data.startswith(signature):
            return mime_type
    # RIFF....WEBP - the size field sits between the two markers.
    if data[:4] == b"RIFF" and data[8:12] == _WEBP_HEADER:
        return "image/webp"
    head = data[:1024].lstrip().lower()
    if any(head.startswith(marker) for marker in _SVG_MARKERS) and b"<svg" in head:
        return "image/svg+xml"
    return None


def parse_allowed_mime_types(raw: str) -> frozenset[str]:
    """Parse the comma separated allow list from the configuration.

    An empty value means "accept the default allow list"; a literal ``*`` means
    "accept anything", which exists for operators who proxy uploads to trusted
    internal systems and must be opted into explicitly.
    """
    entries = {item.strip().lower() for item in (raw or "").split(",") if item.strip()}
    if not entries:
        return DEFAULT_ALLOWED_MIME_TYPES
    if entries == {"*"}:
        return frozenset()
    return frozenset(entries)


def validate_upload(
    data: bytes,
    *,
    declared: str | None = None,
    allowed: frozenset[str] | None = None,
    max_bytes: int,
) -> str:
    """Validate payload size and content type, returning the effective type.

    A sniffed image always overrides the declared type; otherwise the declared
    type is used and an unknown payload degrades to
    :data:`OCTET_STREAM`.
    """
    if not data:
        raise ValidationError("file is empty")
    if max_bytes > 0 and len(data) > max_bytes:
        raise ValidationError(f"file exceeds the maximum size of {max_bytes} bytes")

    resolved_allowed = DEFAULT_ALLOWED_MIME_TYPES if allowed is None else allowed
    sniffed = sniff_content_type(data)
    declared_type = (declared or "").split(";", 1)[0].strip().lower() or None

    if sniffed is not None:
        resolved = sniffed
    elif declared_type in IMAGE_MIME_TYPES:
        # A client claiming an image must also deliver image bytes.
        raise ValidationError(f"content is not a valid {declared_type} file")
    else:
        resolved = declared_type or OCTET_STREAM

    if resolved_allowed and resolved not in resolved_allowed:
        raise ValidationError(f"content type is not allowed: {resolved}")
    return resolved


def is_image(content_type: str | None) -> bool:
    """Whether the value denotes an image."""
    return (content_type or "").split(";", 1)[0].strip().lower() in IMAGE_MIME_TYPES


def should_force_download(content_type: str | None) -> bool:
    """Whether the type must never be rendered inline by a browser.

    SVG is an XML document that can carry scripts, so it is always served as an
    attachment even though the (already scanned) file may be harmless.
    """
    return (content_type or "").split(";", 1)[0].strip().lower() == "image/svg+xml"


__all__ = [
    "DEFAULT_ALLOWED_MIME_TYPES",
    "IMAGE_MIME_TYPES",
    "OCTET_STREAM",
    "is_image",
    "parse_allowed_mime_types",
    "should_force_download",
    "sniff_content_type",
    "validate_upload",
]
