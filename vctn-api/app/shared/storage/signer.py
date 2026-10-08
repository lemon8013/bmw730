"""AWS Signature Version 4, computed with the standard library.

The dependency index allows ``httpx`` and nothing else for outbound HTTP, yet
every S3 compatible server - RustFS, MinIO, Ceph RGW, AWS - requires SigV4.
This module implements the two variants actually needed:

``sign_request``
    An ``Authorization`` header, used for requests the API performs itself
    (upload, download, delete, list, bucket creation).

``presign``
    A signed query string, used to hand a client a URL it may upload to or
    download from without ever seeing our credentials.

Reference: the canonical-request construction described by the AWS SigV4
specification. Only ``hmac``/``hashlib`` from the standard library are used.
"""

from __future__ import annotations

import datetime
import hashlib
import hmac
from urllib.parse import quote

ALGORITHM: str = "AWS4-HMAC-SHA256"
_UNRESERVED = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"
)
_SERVICE = "s3"
_MAX_EXPIRES = 604800  # seven days, the maximum S3 accepts for a presigned URL


def sha256_hex(data: bytes) -> str:
    """Hex encoded SHA-256 of ``data``."""
    return hashlib.sha256(data).hexdigest()


def canonical_uri(path: str) -> str:
    """Percent-encode a path, preserving the ``/`` separators."""
    segments = [quote(segment, safe="") for segment in path.split("/")]
    joined = "/".join(segments)
    return joined if joined.startswith("/") else f"/{joined}"


def canonical_query(params: dict[str, str]) -> str:
    """Build the canonical query string: sorted, RFC 3986 encoded."""
    return "&".join(
        f"{uri_encode(name)}={uri_encode(value)}"
        for name, value in sorted(params.items(), key=lambda item: item[0])
    )


def uri_encode(value: str) -> str:
    """Encode every character outside the unreserved set, space becomes ``%20``."""
    return quote(value, safe="")


def canonical_headers(headers: dict[str, str]) -> tuple[str, str]:
    """Return the canonical header block and the ``SignedHeaders`` value.

    Header names are lower cased, values are trimmed of surrounding whitespace
    and consecutive inner spaces are collapsed, exactly as the specification
    requires.
    """
    normalized = {
        name.strip().lower(): " ".join(str(value).split())
        for name, value in headers.items()
    }
    ordered = sorted(normalized.items())
    block = "".join(f"{name}:{value}\n" for name, value in ordered)
    return block, ";".join(name for name, _ in ordered)


def _signing_key(secret_key: str, datestamp: str, region: str) -> bytes:
    date_key = hmac.new(f"AWS4{secret_key}".encode(), datestamp.encode(), hashlib.sha256).digest()
    region_key = hmac.new(date_key, region.encode(), hashlib.sha256).digest()
    service_key = hmac.new(region_key, _SERVICE.encode(), hashlib.sha256).digest()
    return hmac.new(service_key, b"aws4_request", hashlib.sha256).digest()


def build_canonical_request(
    *,
    method: str,
    uri: str,
    query: dict[str, str],
    headers: dict[str, str],
    payload_hash: str,
) -> tuple[str, str, str]:
    """Assemble the canonical request and return it with its signature inputs."""
    header_block, signed_headers = canonical_headers(headers)
    canonical = "\n".join(
        [
            method.upper(),
            canonical_uri(uri),
            canonical_query(query),
            header_block,
            signed_headers,
            payload_hash,
        ]
    )
    return canonical, signed_headers, sha256_hex(canonical.encode())


def string_to_sign(*, amzdate: str, region: str, canonical_hash: str) -> str:
    """Build the string that gets HMAC-ed."""
    scope = f"{amzdate[:8]}/{region}/{_SERVICE}/aws4_request"
    return "\n".join([ALGORITHM, amzdate, scope, canonical_hash])


def signature(*, secret_key: str, datestamp: str, region: str, to_sign: str) -> str:
    """Compute the hex HMAC signature of a string-to-sign."""
    key = _signing_key(secret_key, datestamp, region)
    return hmac.new(key, to_sign.encode(), hashlib.sha256).hexdigest()


def amzdate_of(moment: datetime.datetime) -> str:
    """Render a UTC instant as a SigV4 timestamp."""
    aware = moment if moment.tzinfo else moment.replace(tzinfo=datetime.UTC)
    return aware.astimezone(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def sign_request(
    *,
    method: str,
    uri: str,
    query: dict[str, str] | None,
    headers: dict[str, str],
    payload_hash: str,
    access_key: str,
    secret_key: str,
    region: str,
    moment: datetime.datetime,
) -> tuple[str, str]:
    """Return the ``Authorization`` header value and the timestamp it signs.

    The timestamp belongs to the signature, so the caller must send exactly the
    returned value in ``x-amz-date`` rather than recomputing it: signing next to
    a second boundary would otherwise produce a request that no longer matches.
    """
    amzdate = amzdate_of(moment)
    signed = dict(headers)
    signed["x-amz-date"] = amzdate
    canonical, signed_headers, canonical_hash = build_canonical_request(
        method=method,
        uri=uri,
        query=query or {},
        headers=signed,
        payload_hash=payload_hash,
    )
    del canonical
    to_sign = string_to_sign(
        amzdate=amzdate, region=region, canonical_hash=canonical_hash
    )
    amz_signature = signature(
        secret_key=secret_key,
        datestamp=amzdate[:8],
        region=region,
        to_sign=to_sign,
    )
    return (
        (
            f"{ALGORITHM} "
            f"Credential={access_key}/{amzdate[:8]}/{region}/{_SERVICE}/aws4_request, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={amz_signature}"
        ),
        amzdate,
    )


def presign(
    *,
    method: str,
    base_url: str,
    uri: str,
    access_key: str,
    secret_key: str,
    region: str,
    expires_seconds: int,
    moment: datetime.datetime,
    query: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    payload_hash: str = "UNSIGNED-PAYLOAD",
) -> str:
    """Return a pre-signed absolute URL.

    The signed headers list is part of the URL, therefore any header recorded in
    ``headers`` must be sent verbatim by whoever uses the URL.
    """
    resolved_expires = max(1, min(int(expires_seconds), _MAX_EXPIRES))
    amzdate = amzdate_of(moment)
    scope = f"{amzdate[:8]}/{region}/{_SERVICE}/aws4_request"
    params = dict(query or {})
    params.update(
        {
            "X-Amz-Algorithm": ALGORITHM,
            "X-Amz-Credential": f"{access_key}/{scope}",
            "X-Amz-Date": amzdate,
            "X-Amz-Expires": str(resolved_expires),
        }
    )
    signed_lower = {name.lower(): value for name, value in (headers or {}).items()}
    signed_lower["host"] = _host_header(base_url)
    params["X-Amz-SignedHeaders"] = ";".join(sorted(signed_lower))

    canonical, _, canonical_hash = build_canonical_request(
        method=method,
        uri=uri,
        query=params,
        headers=signed_lower,
        payload_hash=payload_hash,
    )
    del canonical
    to_sign = string_to_sign(
        amzdate=params["X-Amz-Date"], region=region, canonical_hash=canonical_hash
    )
    amz_signature = signature(
        secret_key=secret_key,
        datestamp=params["X-Amz-Date"][:8],
        region=region,
        to_sign=to_sign,
    )
    params["X-Amz-Signature"] = amz_signature
    return f"{base_url.rstrip('/')}{canonical_uri(uri)}?{canonical_query(params)}"


def _host_header(base_url: str) -> str:
    """Derive the ``Host`` header value from a request URL."""
    stripped = base_url
    for scheme in ("https://", "http://"):
        if stripped.startswith(scheme):
            stripped = stripped[len(scheme) :]
            break
    return stripped.rstrip("/")


__all__ = [
    "ALGORITHM",
    "amzdate_of",
    "build_canonical_request",
    "canonical_headers",
    "canonical_query",
    "canonical_uri",
    "presign",
    "sha256_hex",
    "sign_request",
    "string_to_sign",
    "uri_encode",
]
