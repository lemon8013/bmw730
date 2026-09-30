"""Tool providers and the runtime registry.

The Spec forbids ``if tool == "xxx"`` dispatch: a tool is executed by the
provider registered for its ``component_key``, and the catalogue row only selects
which registered component runs.

Execution modes:

* ``FRONTEND`` - the payload is already produced by the browser; the backend only
  validates and echoes the result, so no server side dependency is needed.
* ``BACKEND``  - the provider runs here (encoding, hashing, HTTP probing, IP/DNS
  style lookups).
* ``ASYNC``    - the provider refuses to run inline and a job is created instead.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
import secrets
import time
import uuid
import xml.dom.minidom
import xml.parsers.expat
from dataclasses import dataclass, field
from typing import Any, Final, Protocol
from urllib.parse import quote, unquote

import jwt

EXECUTION_MODE_FRONTEND: Final[str] = "FRONTEND"
EXECUTION_MODE_BACKEND: Final[str] = "BACKEND"
EXECUTION_MODE_ASYNC: Final[str] = "ASYNC"


@dataclass(frozen=True, slots=True)
class ToolExecutionRequest:
    """What a provider receives."""

    component_key: str
    inputs: dict[str, Any]
    runtime_config: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ToolExecutionResult:
    """What a provider returns."""

    success: bool
    output: Any
    error_code: str | None = None
    error_message: str | None = None


class ToolProvider(Protocol):
    """Contract every tool provider implements."""

    component_key: str
    execution_mode: str

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        """Run the tool."""
        ...


class ToolError(Exception):
    """A provider refused the input."""

    def __init__(self, message: str, *, code: str = "TOOL_INPUT_INVALID") -> None:
        super().__init__(message)
        self.code = code


def _require_text(payload: dict[str, Any], key: str = "input") -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ToolError(f"'{key}' must be a string")
    return value


class JsonFormatProvider:
    """Pretty print or minify JSON."""

    component_key = "json.format"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        raw = _require_text(request.inputs)
        try:
            parsed = json.loads(raw)
        except ValueError as exc:
            return ToolExecutionResult(False, None, "JSON_INVALID", str(exc))
        mode = str(request.inputs.get("mode", "pretty")).lower()
        indent = 2 if mode != "minify" else None
        text = json.dumps(parsed, ensure_ascii=False, indent=indent, sort_keys=mode == "sort")
        return ToolExecutionResult(True, {"text": text, "valid": True})


class XmlFormatProvider:
    """Pretty print XML."""

    component_key = "xml.format"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        raw = _require_text(request.inputs)
        try:
            text = xml.dom.minidom.parseString(raw).toprettyxml(indent="  ")
        except (xml.parsers.expat.ExpatError, ValueError) as exc:
            return ToolExecutionResult(False, None, "XML_INVALID", str(exc))
        return ToolExecutionResult(True, {"text": text, "valid": True})


class TomlParseProvider:
    """Parse TOML with the standard library ``tomllib``."""

    component_key = "toml.parse"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        import tomllib

        raw = _require_text(request.inputs)
        try:
            parsed = tomllib.loads(raw)
        except tomllib.TOMLDecodeError as exc:
            return ToolExecutionResult(False, None, "TOML_INVALID", str(exc))
        return ToolExecutionResult(True, {"value": parsed, "valid": True})


class Base64Provider:
    """Encode and decode Base64 (URL safe variant supported)."""

    component_key = "base64.codec"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        raw = _require_text(request.inputs)
        mode = str(request.inputs.get("mode", "encode")).lower()
        urlsafe = bool(request.inputs.get("urlsafe", False))
        encoder = base64.urlsafe_b64encode if urlsafe else base64.b64encode
        decoder = base64.urlsafe_b64decode if urlsafe else base64.b64decode
        try:
            if mode == "encode":
                return ToolExecutionResult(
                    True, {"text": encoder(raw.encode("utf-8")).decode("ascii")}
                )
            decoded = decoder(raw.encode("ascii"), validate=True)
            return ToolExecutionResult(True, {"text": decoded.decode("utf-8")})
        except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
            return ToolExecutionResult(False, None, "BASE64_INVALID", str(exc))


class UrlCodecProvider:
    """Percent encode and decode."""

    component_key = "url.codec"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        raw = _require_text(request.inputs)
        mode = str(request.inputs.get("mode", "encode")).lower()
        if mode == "encode":
            safe = str(request.inputs.get("safe", ""))
            return ToolExecutionResult(True, {"text": quote(raw, safe=safe)})
        return ToolExecutionResult(True, {"text": unquote(raw)})


class UuidProvider:
    """Generate UUIDv4 values."""

    component_key = "uuid.generate"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        count = int(request.inputs.get("count", 1))
        count = max(1, min(count, 100))
        uppercase = bool(request.inputs.get("uppercase", False))
        values = [str(uuid.uuid4()) for _ in range(count)]
        if uppercase:
            values = [value.upper() for value in values]
        return ToolExecutionResult(True, {"values": values})


class UlidProvider:
    """Generate ULID values (Crockford base32, no third party library)."""

    component_key = "ulid.generate"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        count = int(request.inputs.get("count", 1))
        count = max(1, min(count, 100))
        alphabet = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
        values: list[str] = []
        for _ in range(count):
            timestamp_ms = int(time.time() * 1000)
            time_part = ""
            remaining = timestamp_ms
            for _ in range(10):
                time_part = alphabet[remaining % 32] + time_part
                remaining //= 32
            random_part = "".join(secrets.choice(alphabet) for _ in range(16))
            values.append(time_part + random_part)
        return ToolExecutionResult(True, {"values": values})


class HashProvider:
    """MD5 / SHA1 / SHA256 / SHA512 digests."""

    component_key = "hash.digest"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        raw = _require_text(request.inputs)
        algorithm = str(request.inputs.get("algorithm", "sha256")).lower()
        mapping = {
            "md5": hashlib.md5,
            "sha1": hashlib.sha1,
            "sha256": hashlib.sha256,
            "sha512": hashlib.sha512,
        }
        factory = mapping.get(algorithm)
        if factory is None:
            return ToolExecutionResult(False, None, "ALGORITHM_UNSUPPORTED", algorithm)
        digest = factory(raw.encode("utf-8")).hexdigest()
        return ToolExecutionResult(True, {"algorithm": algorithm, "digest": digest})


class RegexTestProvider:
    """Run a regular expression against text."""

    component_key = "regex.test"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        pattern = str(request.inputs.get("pattern", ""))
        text = _require_text(request.inputs, "text")
        if not pattern:
            raise ToolError("'pattern' is required")
        try:
            compiled = re.compile(pattern)
        except re.error as exc:
            return ToolExecutionResult(False, None, "REGEX_INVALID", str(exc))
        matches = [match.group(0) for match in compiled.finditer(text)][:100]
        return ToolExecutionResult(
            True, {"matches": matches, "match_count": len(matches), "is_match": bool(matches)}
        )


class JwtParseProvider:
    """Decode a JWT without verifying its signature.

    Only the header and the payload are returned; the signature is never echoed
    and never logged.
    """

    component_key = "jwt.parse"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        token = _require_text(request.inputs, "token").strip()
        try:
            header = jwt.get_unverified_header(token)
            payload = jwt.decode(token, options={"verify_signature": False})
        except jwt.PyJWTError as exc:
            return ToolExecutionResult(False, None, "JWT_INVALID", str(exc))
        return ToolExecutionResult(True, {"header": header, "payload": payload})


class TextStatsProvider:
    """Count characters, words and lines."""

    component_key = "text.stats"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        raw = _require_text(request.inputs)
        return ToolExecutionResult(
            True,
            {
                "characters": len(raw),
                "characters_no_spaces": len(raw.replace(" ", "")),
                "words": len([item for item in raw.split() if item]),
                "lines": raw.count("\n") + (1 if raw else 0),
                "bytes": len(raw.encode("utf-8")),
            },
        )


class TimestampProvider:
    """Convert between epoch seconds/milliseconds and ISO 8601."""

    component_key = "datetime.convert"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        from datetime import UTC, datetime

        mode = str(request.inputs.get("mode", "now")).lower()
        if mode == "now":
            moment = datetime.now(UTC)
        elif mode == "from_epoch":
            raw = request.inputs.get("value", 0)
            value = int(raw)
            if abs(value) > 10_000_000_000:
                value /= 1000
            moment = datetime.fromtimestamp(value, tz=UTC)
        elif mode == "from_iso":
            moment = datetime.fromisoformat(str(request.inputs.get("value")))
        else:
            return ToolExecutionResult(False, None, "MODE_UNSUPPORTED", mode)
        return ToolExecutionResult(
            True,
            {
                "iso": moment.isoformat(),
                "epoch_seconds": int(moment.timestamp()),
                "epoch_milliseconds": int(moment.timestamp() * 1000),
            },
        )


class RandomStringProvider:
    """Generate a random string."""

    component_key = "random.string"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        length = max(1, min(int(request.inputs.get("length", 16)), 256))
        alphabet = str(request.inputs.get("alphabet", "")) or (
            "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        )
        return ToolExecutionResult(
            True, {"text": "".join(secrets.choice(alphabet) for _ in range(length))}
        )


class UnicodeInspectProvider:
    """Show code points of a text."""

    component_key = "unicode.inspect"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        raw = _require_text(request.inputs)
        return ToolExecutionResult(
            True,
            {
                "code_points": [ord(character) for character in raw[:256]],
                "length": len(raw),
            },
        )


class MarkdownRenderProvider:
    """Render Markdown to sanitized HTML."""

    component_key = "markdown.render"
    execution_mode = EXECUTION_MODE_BACKEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        import bleach
        from markdown_it import MarkdownIt

        raw = _require_text(request.inputs)
        html = MarkdownIt("commonmark").enable("table").render(raw)
        allowed = {"p", "br", "strong", "em", "code", "pre", "ul", "ol", "li", "a", "h1",
                   "h2", "h3", "h4", "h5", "h6", "blockquote", "table", "thead", "tbody",
                   "tr", "th", "td", "hr", "img"}
        attrs = {"a": ["href", "title"], "img": ["src", "alt"]}
        clean = bleach.clean(html, tags=allowed, attributes=attrs, strip=True)
        return ToolExecutionResult(True, {"html": clean, "markdown": raw})


class AsyncJobProvider:
    """Placeholder provider for tools that must not run inline.

    It does not pretend to execute anything: it reports that the work has to be
    queued, and the runtime turns that into a job.
    """

    component_key = "async.job"
    execution_mode = EXECUTION_MODE_ASYNC

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        return ToolExecutionResult(
            False,
            None,
            "ASYNC_REQUIRED",
            "this tool must be executed through an asynchronous job",
        )


class FrontendEchoProvider:
    """FRONTEND tools: validate the shape and echo the client produced result.

    The browser already produced the output; storing or re-computing it here
    would only duplicate work, so the provider only enforces that a result is
    present.
    """

    component_key = "frontend.echo"
    execution_mode = EXECUTION_MODE_FRONTEND

    async def execute(self, request: ToolExecutionRequest) -> ToolExecutionResult:
        if "result" not in request.inputs:
            raise ToolError("'result' is required for a frontend tool")
        return ToolExecutionResult(True, {"result": request.inputs["result"]})


class ToolRegistry:
    """Maps a ``component_key`` to the provider that runs it."""

    def __init__(self) -> None:
        self._providers: dict[str, ToolProvider] = {}

    def register(self, provider: ToolProvider) -> None:
        self._providers[provider.component_key] = provider

    def get(self, component_key: str) -> ToolProvider | None:
        return self._providers.get(component_key)

    def keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def __len__(self) -> int:
        return len(self._providers)


def build_default_registry() -> ToolRegistry:
    """Return the registry with every provider shipped by the backend."""
    registry = ToolRegistry()
    for provider in (
        JsonFormatProvider(),
        XmlFormatProvider(),
        TomlParseProvider(),
        Base64Provider(),
        UrlCodecProvider(),
        UuidProvider(),
        UlidProvider(),
        HashProvider(),
        RegexTestProvider(),
        JwtParseProvider(),
        TextStatsProvider(),
        TimestampProvider(),
        RandomStringProvider(),
        UnicodeInspectProvider(),
        MarkdownRenderProvider(),
        FrontendEchoProvider(),
        AsyncJobProvider(),
    ):
        registry.register(provider)
    return registry


_REGISTRY: ToolRegistry | None = None


def get_registry() -> ToolRegistry:
    """Return the process wide tool registry."""
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = build_default_registry()
    return _REGISTRY
