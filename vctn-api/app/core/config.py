"""Application settings.

This module is the **single source of truth for backend configuration**.
Every tunable value is declared here exactly once, and no other backend module
may hard code configuration: infrastructure code reads what it needs from a
:class:`Settings` instance.

Values are supplied through environment variables or a local ``.env`` file
(see ``.env.example``). No password, token, secret or database credential may
be hard coded here.

Database and Redis connections are described by **separate fields**
(host / port / name / user / password) and assembled into a driver URL by the
``database_url`` and ``redis_url`` properties. A full URL may still be supplied
through ``DATABASE_URL`` / ``REDIS_URL``; when present it takes precedence over
the individual fields.

A value that is ``None`` means "use the library default", which keeps the
configuration surface explicit without overriding behaviour we do not intend to
change.
"""

from __future__ import annotations

import os
import secrets
import string
from functools import lru_cache
from typing import Any, Final, Literal
from urllib.parse import quote

from pydantic import AliasChoices, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_WILDCARD: Final[str] = "*"

_ENV_FILE_VARIABLE: Final[str] = "VCTN_ENV_FILE"

_LOG_LEVELS: Final[tuple[str, ...]] = (
    "CRITICAL",
    "ERROR",
    "WARNING",
    "INFO",
    "DEBUG",
    "NOTSET",
)

_POSTGRES_DRIVER: Final[str] = "postgresql+asyncpg"
_REDIS_SCHEME: Final[str] = "redis"


def _quote(value: str) -> str:
    """Percent-encode a URL userinfo component."""
    return quote(value, safe="")


def _env_file_setting() -> str | None:
    """Resolve which dotenv file supplies configuration.

    Defaults to ``.env``. Setting ``VCTN_ENV_FILE`` to a blank value or to
    another path lets a deployment (or the test suite) select a different file
    or opt out of dotenv loading entirely, which keeps tests independent from a
    developer's local ``.env``.
    """
    raw = os.environ.get(_ENV_FILE_VARIABLE)
    if raw is None:
        return ".env"
    return raw.strip() or None


def _format_host(host: str) -> str:
    """Bracket a bare IPv6 literal so it can be embedded in a URL."""
    if ":" in host and not host.startswith("["):
        return f"[{host}]"
    return host


#: Accepted FILE_STORAGE_PROVIDER values. ``s3`` is canonical; ``rustfs`` reads
#: better in a deployment that runs RustFS, and ``minio`` is kept so an older
#: .env keeps booting. All three build the same S3 compatible backend.
_STORAGE_PROVIDERS: Final[frozenset[str]] = frozenset({"local", "s3", "rustfs", "minio"})

#: Credentials shipped in every quick start guide, refused in production.
_SAMPLE_STORAGE_SECRETS: Final[frozenset[str]] = frozenset(
    {"rustfsadmin", "minioadmin", "changeme", "password"}
)


class Settings(BaseSettings):
    """Runtime configuration for the single VCTN FastAPI application."""

    model_config = SettingsConfigDict(
        env_file=_env_file_setting(),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        # Fields carrying an AliasChoices (the S3_* block) must still be
        # constructible by their field name, which is what tests and code do.
        populate_by_name=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _blank_value_means_unset(cls, data: Any) -> Any:
        """Treat a blank value as "not provided" so the field default applies.

        A blank line in ``.env`` (``DB_ECHO_SQL=``) must behave like an absent
        key. Without this, every typed optional field would fail to parse the
        empty string instead of falling back to its default.
        """
        if not isinstance(data, dict):
            return data
        return {
            key: value
            for key, value in data.items()
            if not (isinstance(value, str) and not value.strip())
        }

    # ------------------------------------------------------------------
    # Application
    # ------------------------------------------------------------------
    APP_NAME: str = "vctn-api"
    APP_VERSION: str = "0.1.0"
    APP_ENV: Literal["development", "testing", "staging", "production"] = "development"
    APP_DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # ------------------------------------------------------------------
    # PostgreSQL - fill in these fields
    # ------------------------------------------------------------------
    DB_HOST: str = ""
    DB_PORT: int = 5432
    DB_NAME: str = ""
    DB_USER: str = ""
    DB_PASSWORD: str = ""
    # Optional escape hatch: a complete URL that overrides the fields above.
    DATABASE_URL: str = ""

    # ------------------------------------------------------------------
    # SQLAlchemy engine
    # ------------------------------------------------------------------
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT_SECONDS: float = 30.0
    # -1 disables connection recycling, which is the SQLAlchemy default.
    DB_POOL_RECYCLE_SECONDS: int = -1
    DB_POOL_PRE_PING: bool = True
    # None means "follow APP_DEBUG".
    DB_ECHO_SQL: bool | None = None

    # ------------------------------------------------------------------
    # Redis - fill in these fields
    # ------------------------------------------------------------------
    REDIS_HOST: str = ""
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_USERNAME: str = ""
    REDIS_PASSWORD: str = ""
    # Optional escape hatch: a complete URL that overrides the fields above.
    REDIS_URL: str = ""

    # ------------------------------------------------------------------
    # Redis client
    # ------------------------------------------------------------------
    REDIS_ENCODING: str = "utf-8"
    REDIS_DECODE_RESPONSES: bool = True
    # None means "use the redis library default".
    REDIS_MAX_CONNECTIONS: int | None = None
    REDIS_SOCKET_TIMEOUT_SECONDS: float | None = None

    # ------------------------------------------------------------------
    # Snowflake ID (DD-14: the bit layout is not frozen - these fields expose
    # the minimal runnable default layout instead of hiding it in code)
    # ------------------------------------------------------------------
    SNOWFLAKE_EPOCH_MS: int = 1735689600000
    SNOWFLAKE_NODE_ID: int = 1
    SNOWFLAKE_NODE_BITS: int = 10
    SNOWFLAKE_SEQUENCE_BITS: int = 12

    # ------------------------------------------------------------------
    # Authentication (token lifetime is not frozen - exposed as configuration)
    # ------------------------------------------------------------------
    AUTH_JWT_SECRET: str = ""
    AUTH_JWT_ALGORITHM: str = "HS256"
    AUTH_ISSUER: str = "vctn-api"
    AUTH_ACCESS_TOKEN_TTL_SECONDS: int = 900
    AUTH_REFRESH_TOKEN_TTL_SECONDS: int = 604800
    AUTH_REFRESH_TOKEN_BYTES: int = 32
    AUTH_MAX_ACTIVE_SESSIONS_PER_USER: int = 5

    # ------------------------------------------------------------------
    # Password policy
    # ------------------------------------------------------------------
    PASSWORD_MIN_LENGTH: int = 12
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_DIGIT: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    PASSWORD_SPECIAL_CHARACTERS: str = "!@#$%^&*()-_=+[]{};:,.<>?/~"
    PASSWORD_HISTORY_COUNT: int = 5
    PASSWORD_EXPIRE_DAYS: int = 90
    PASSWORD_MAX_FAILED_ATTEMPTS: int = 5
    PASSWORD_LOCK_MINUTES: int = 30

    # ------------------------------------------------------------------
    # Rate limit (exact values are not frozen - exposed as configuration)
    # ------------------------------------------------------------------
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    RATE_LIMIT_LOGIN_PER_WINDOW: int = 10
    RATE_LIMIT_API_PER_WINDOW: int = 300
    RATE_LIMIT_TOOL_GUEST_PER_WINDOW: int = 30
    RATE_LIMIT_TOOL_USER_PER_WINDOW: int = 120
    RATE_LIMIT_SENSITIVE_PER_WINDOW: int = 20

    # ------------------------------------------------------------------
    # Redis key space and locking
    # ------------------------------------------------------------------
    REDIS_KEY_PREFIX: str = "vctn"
    REDIS_LOCK_TTL_SECONDS: int = 30
    REDIS_LOCK_RETRY_INTERVAL_SECONDS: float = 0.05
    REDIS_LOCK_RETRY_TIMES: int = 100

    # ------------------------------------------------------------------
    # Tool quota
    # ------------------------------------------------------------------
    TOOL_GUEST_DAILY_QUOTA: int = 50
    TOOL_USER_DAILY_QUOTA: int = 500

    # Default visibility of a tool that has no explicit access policy row.
    # PUBLIC opens the tool to everyone, REGISTERED keeps it to signed in users
    # until an operator relaxes it.
    TOOL_DEFAULT_VISIBILITY: str = "PUBLIC"

    # ------------------------------------------------------------------
    # Idempotency
    # ------------------------------------------------------------------
    IDEMPOTENCY_TTL_SECONDS: int = 86400

    # ------------------------------------------------------------------
    # Outbox
    # ------------------------------------------------------------------
    OUTBOX_BATCH_SIZE: int = 100
    OUTBOX_MAX_ATTEMPTS: int = 5
    OUTBOX_RETRY_DELAY_SECONDS: int = 60
    OUTBOX_ENABLED: bool = True

    # ------------------------------------------------------------------
    # Verification codes
    # ------------------------------------------------------------------
    VERIFICATION_CODE_TTL_SECONDS: int = 300
    VERIFICATION_CODE_MAX_ATTEMPTS: int = 5
    VERIFICATION_CODE_LENGTH: int = 6

    # ------------------------------------------------------------------
    # Files / object storage
    #
    # ``local`` keeps objects below FILE_STORAGE_ROOT; it is correct only for a
    # single node or a shared mount. ``s3`` targets any S3 compatible endpoint
    # - RustFS, MinIO, Ceph RGW, AWS S3 - and is the supported choice for a
    # multi replica deployment, because every replica must see the same bytes.
    # ``rustfs`` is accepted as a self documenting alias of ``s3``.
    # ------------------------------------------------------------------
    FILE_STORAGE_PROVIDER: str = "local"
    FILE_STORAGE_ROOT: str = "storage"
    FILE_MAX_SIZE_BYTES: int = 10485760
    FILE_PRESIGN_TTL_SECONDS: int = 900
    FILE_DOWNLOAD_URL_TTL_SECONDS: int = 3600
    #: Comma separated allow list. Empty means "use the built in allow list";
    #: the single value ``*`` disables content type checking entirely.
    FILE_ALLOWED_MIME_TYPES: str = ""

    # -- Any S3 compatible object store (RustFS / MinIO / Ceph RGW / AWS) ---
    #
    # The keys were named ``MINIO_*`` while MinIO was the only backend. They are
    # ``S3_*`` now that the fleet runs on RustFS; the old names are still
    # accepted through the validation alias so an existing .env keeps working.
    S3_ENDPOINT: str = Field(
        default="", validation_alias=AliasChoices("S3_ENDPOINT", "MINIO_ENDPOINT")
    )
    S3_ACCESS_KEY: str = Field(
        default="", validation_alias=AliasChoices("S3_ACCESS_KEY", "MINIO_ACCESS_KEY")
    )
    S3_SECRET_KEY: str = Field(
        default="", validation_alias=AliasChoices("S3_SECRET_KEY", "MINIO_SECRET_KEY")
    )
    S3_BUCKET: str = Field(
        default="", validation_alias=AliasChoices("S3_BUCKET", "MINIO_BUCKET")
    )
    S3_SECURE: bool = Field(
        default=True, validation_alias=AliasChoices("S3_SECURE", "MINIO_SECURE")
    )
    S3_REGION: str = Field(
        default="us-east-1", validation_alias=AliasChoices("S3_REGION", "MINIO_REGION")
    )
    #: Optional key prefix, e.g. ``vctn`` - useful when the bucket is shared.
    S3_PREFIX: str = Field(
        default="", validation_alias=AliasChoices("S3_PREFIX", "MINIO_PREFIX")
    )
    #: ``path`` works everywhere; ``virtual`` needs the DNS wildcard.
    S3_ADDRESSING_STYLE: str = Field(
        default="path",
        validation_alias=AliasChoices("S3_ADDRESSING_STYLE", "MINIO_ADDRESSING_STYLE"),
    )
    S3_AUTO_CREATE_BUCKET: bool = Field(
        default=True,
        validation_alias=AliasChoices("S3_AUTO_CREATE_BUCKET", "MINIO_AUTO_CREATE_BUCKET"),
    )
    S3_CONNECT_TIMEOUT_SECONDS: int = Field(
        default=5,
        validation_alias=AliasChoices(
            "S3_CONNECT_TIMEOUT_SECONDS", "MINIO_CONNECT_TIMEOUT_SECONDS"
        ),
    )
    S3_READ_TIMEOUT_SECONDS: int = Field(
        default=30,
        validation_alias=AliasChoices(
            "S3_READ_TIMEOUT_SECONDS", "MINIO_READ_TIMEOUT_SECONDS"
        ),
    )
    S3_VERIFY_TLS: bool = Field(
        default=True, validation_alias=AliasChoices("S3_VERIFY_TLS", "MINIO_VERIFY_TLS")
    )

    # ------------------------------------------------------------------
    # Exports
    # ------------------------------------------------------------------
    EXPORT_STORAGE_ROOT: str = "exports"
    EXPORT_MAX_ROWS: int = 100000
    EXPORT_URL_TTL_SECONDS: int = 3600
    EXPORT_RETENTION_DAYS: int = 7

    # ------------------------------------------------------------------
    # Log retention (days) - the Spec freezes these periods
    # ------------------------------------------------------------------
    LOG_RETENTION_ACCESS_LOG_DAYS: int = 30
    LOG_RETENTION_SECURITY_LOG_DAYS: int = 180
    LOG_RETENTION_OPERATION_LOG_DAYS: int = 180
    LOG_RETENTION_AUDIT_LOG_DAYS: int = 730
    LOG_RETENTION_APPLICATION_LOG_DAYS: int = 30

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------
    AUDIT_ENABLED: bool = True

    # ------------------------------------------------------------------
    # Monitoring data retention (purged by ``python -m app.scripts.cleanup``)
    # ------------------------------------------------------------------
    # Raw samples are cheap to lose and expensive to keep: they are rolled up
    # into the hourly and daily tables, so seven days is plenty.
    OPS_RETENTION_SAMPLE_DAYS: int = 7
    OPS_RETENTION_HEARTBEAT_DAYS: int = 7
    OPS_RETENTION_HOURLY_DAYS: int = 30
    OPS_RETENTION_DAILY_DAYS: int = 180
    OPS_RETENTION_EVENT_DAYS: int = 30
    OPS_RETENTION_AVAILABILITY_DAYS: int = 30
    # Alert history and notification records are the audit trail of what the
    # platform told whom, so they live as long as the audit log.
    OPS_RETENTION_ALERT_HISTORY_DAYS: int = 180
    OPS_RETENTION_NOTIFICATION_DAYS: int = 180
    OPS_RETENTION_OPERATION_DAYS: int = 180
    # Rows removed per statement. A single unbounded DELETE on a table that
    # has grown for a year holds one transaction open for a long time, which
    # blocks autovacuum and everything else behind it.
    OPS_PURGE_BATCH_SIZE: int = 5000

    # ------------------------------------------------------------------
    # Ops scheduler (in-process periodic jobs)
    # ------------------------------------------------------------------
    # Off by default: every replica must not run the same periodic work twice.
    # When it is on, each job still takes a PostgreSQL advisory lock first, so
    # a second replica silently skips the tick instead of duplicating it.
    OPS_SCHEDULER_ENABLED: bool = False
    OPS_SCHEDULER_ALERT_INTERVAL_SECONDS: int = 60
    OPS_SCHEDULER_PROBE_INTERVAL_SECONDS: int = 60
    OPS_SCHEDULER_ROLLUP_INTERVAL_MINUTES: int = 60
    OPS_SCHEDULER_DAILY_ROLLUP_HOUR: int = 0
    OPS_SCHEDULER_PURGE_HOUR: int = 4
    # One fixed key per job namespace. Do not reuse it for anything else: a
    # colliding key silently merges two unrelated critical sections.
    OPS_SCHEDULER_LOCK_ID: int = 8_172_543_011

    # ------------------------------------------------------------------
    # Ops self monitoring
    # ------------------------------------------------------------------
    # The platform watches everything except itself until this is on: seeding
    # creates one availability check against this URL, so an outage of the API
    # itself is detected by the same pipeline as any other outage.
    OPS_SELF_MONITOR_ENABLED: bool = True
    OPS_SELF_MONITOR_URL: str = "http://127.0.0.1:8000/health"

    # ------------------------------------------------------------------
    # HTTP / CORS
    # ------------------------------------------------------------------
    # Comma separated list of allowed browser origins, for example:
    # CORS_ORIGINS=http://localhost:5173,http://localhost:5174
    CORS_ORIGINS: str = Field(default="")
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: str = "*"
    CORS_ALLOW_HEADERS: str = "*"
    CORS_EXPOSE_HEADERS: str = "X-Trace-ID,X-Request-ID"

    # ------------------------------------------------------------------
    # HTTP security headers
    # ------------------------------------------------------------------
    # HSTS is opt in: sending it over plain HTTP is useless and, worse, it
    # makes a browser refuse the downgraded origin for the whole max-age.
    # Turn it on only once TLS terminates in front of the application.
    SECURITY_HSTS_ENABLED: bool = False
    SECURITY_HSTS_MAX_AGE_SECONDS: int = 31_536_000
    SECURITY_HSTS_INCLUDE_SUBDOMAINS: bool = True
    # ``DENY`` for the consoles; a portal that must be framed uses
    # ``SAMEORIGIN`` instead. An empty value omits the header.
    SECURITY_FRAME_OPTIONS: str = "DENY"
    SECURITY_REFERRER_POLICY: str = "strict-origin-when-cross-origin"
    # Empty means "do not send CSP". The four frontends load Element Plus
    # styles compiled at build time, so a strict CSP is viable, but it has to
    # be written per application - a wrong default would break a working site.
    SECURITY_CSP: str = ""
    # Report only mode lets a new policy be observed before it is enforced.
    SECURITY_CSP_REPORT_ONLY: bool = False
    # Turns off the device APIs none of the four frontends use. Empty omits it.
    SECURITY_PERMISSIONS_POLICY: str = "geolocation=(), microphone=(), camera=()"
    # Comma separated Host allow-list checked on every request. Empty means
    # "accept any Host", which is fine behind a reverse proxy that already
    # pins the server name but is a Host header injection risk when exposed.
    ALLOWED_HOSTS: str = ""
    # ``None`` means "derive from APP_ENV": documentation is served outside
    # production only. Set it explicitly to override.
    DOCS_ENABLED: bool | None = None

    # ------------------------------------------------------------------
    # Tracing
    # ------------------------------------------------------------------
    TRACE_ID_HEADER: str = "X-Trace-ID"
    REQUEST_ID_HEADER: str = "X-Request-ID"
    TRACE_ID_MAX_LENGTH: int = 128

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    # Empty string means "derive from APP_DEBUG".
    LOG_LEVEL: str = ""
    LOG_FORMAT: str = "%(asctime)s %(levelname)-8s %(name)s [trace_id=%(trace_id)s] %(message)s"
    # Empty string means "use the logging module default".
    LOG_DATE_FORMAT: str = ""
    LOG_STREAM: Literal["stdout", "stderr"] = "stdout"

    # ------------------------------------------------------------------
    # Connection URLs (assembled from the fields above)
    # ------------------------------------------------------------------
    @property
    def database_url(self) -> str:
        """Return the PostgreSQL driver URL.

        An explicitly configured ``DATABASE_URL`` wins. Otherwise the URL is
        assembled from ``DB_HOST`` / ``DB_PORT`` / ``DB_NAME`` / ``DB_USER`` /
        ``DB_PASSWORD``. Returns ``""`` when the connection is not configured.
        """
        explicit = self.DATABASE_URL.strip()
        if explicit:
            return explicit

        host = self.DB_HOST.strip()
        name = self.DB_NAME.strip()
        user = self.DB_USER.strip()
        if not (host and name and user):
            return ""

        return (
            f"{_POSTGRES_DRIVER}://{_quote(user)}:{_quote(self.DB_PASSWORD)}"
            f"@{_format_host(host)}:{self.DB_PORT}/{name}"
        )

    @property
    def redis_url(self) -> str:
        """Return the Redis driver URL.

        An explicitly configured ``REDIS_URL`` wins. Otherwise the URL is
        assembled from ``REDIS_HOST`` / ``REDIS_PORT`` / ``REDIS_DB`` /
        ``REDIS_USERNAME`` / ``REDIS_PASSWORD``. Returns ``""`` when the
        connection is not configured.
        """
        explicit = self.REDIS_URL.strip()
        if explicit:
            return explicit

        host = self.REDIS_HOST.strip()
        if not host:
            return ""

        username = self.REDIS_USERNAME.strip()
        if username and self.REDIS_PASSWORD:
            auth = f"{_quote(username)}:{_quote(self.REDIS_PASSWORD)}@"
        elif self.REDIS_PASSWORD:
            auth = f":{_quote(self.REDIS_PASSWORD)}@"
        else:
            auth = ""

        return f"{_REDIS_SCHEME}://{auth}{_format_host(host)}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @property
    def is_database_configured(self) -> bool:
        return bool(self.database_url)

    @property
    def is_redis_configured(self) -> bool:
        return bool(self.redis_url)

    # ------------------------------------------------------------------
    # Derived helpers
    # ------------------------------------------------------------------
    @property
    def cors_origins(self) -> tuple[str, ...]:
        """Return the parsed CORS allow-list.

        The wildcard origin is rejected: the frozen Spec forbids
        ``allow_origins=["*"]``.
        """
        items = tuple(item.strip() for item in self.CORS_ORIGINS.split(",") if item.strip())
        if _WILDCARD in items:
            raise ValueError("CORS_ORIGINS must not contain the wildcard origin '*'")
        return items

    @property
    def cors_methods(self) -> list[str]:
        """Return the parsed CORS allow-methods list."""
        return [item.strip() for item in self.CORS_ALLOW_METHODS.split(",") if item.strip()]

    @property
    def cors_headers(self) -> list[str]:
        """Return the parsed CORS allow-headers list."""
        return [item.strip() for item in self.CORS_ALLOW_HEADERS.split(",") if item.strip()]

    @property
    def cors_exposed_headers(self) -> list[str]:
        """Return the parsed CORS expose-headers list."""
        return [item.strip() for item in self.CORS_EXPOSE_HEADERS.split(",") if item.strip()]

    @property
    def allowed_hosts(self) -> tuple[str, ...]:
        """Return the Host allow-list, lower-cased and without ports.

        A bare host name also accepts any port on that host, because the
        application sits behind a proxy that is reached on 443 while the
        container itself listens on 8000.
        """
        items = tuple(
            item.strip().lower() for item in self.ALLOWED_HOSTS.split(",") if item.strip()
        )
        return tuple(item.split(":", 1)[0] if ":" in item else item for item in items)

    @property
    def resolved_docs_enabled(self) -> bool:
        """Return whether the interactive API documentation is served.

        Shipping ``/docs`` and ``/openapi.json`` to production publishes the
        entire endpoint catalogue - every path, parameter and schema - to
        anyone who finds the URL. It is therefore off in production unless
        somebody deliberately turns it back on.
        """
        if self.DOCS_ENABLED is not None:
            return self.DOCS_ENABLED
        return self.APP_ENV != "production"

    @property
    def resolved_log_level(self) -> str:
        """Return the effective log level name."""
        if self.LOG_LEVEL.strip():
            return self.LOG_LEVEL.strip().upper()
        return "DEBUG" if self.APP_DEBUG else "INFO"

    @property
    def resolved_jwt_secret(self) -> str:
        """Return the secret used to sign tokens.

        The Secret Manager integration is not frozen. Until it is, the secret
        comes from configuration, and a process-local ephemeral secret is used
        when none is configured so that development can start without a secret
        store. ``production`` refuses to start without a configured secret.
        """
        configured = self.AUTH_JWT_SECRET.strip()
        if configured:
            return configured
        if self.APP_ENV == "production":
            raise ValueError("AUTH_JWT_SECRET must be configured in production")
        ephemeral = getattr(self, "_ephemeral_jwt_secret", None)
        if ephemeral is None:
            ephemeral = secrets.token_urlsafe(48)
            object.__setattr__(self, "_ephemeral_jwt_secret", ephemeral)
        return str(ephemeral)

    @property
    def resolved_db_echo(self) -> bool:
        """Return whether the SQLAlchemy engine should echo statements."""
        if self.DB_ECHO_SQL is None:
            return self.APP_DEBUG
        return self.DB_ECHO_SQL

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    def validate_startup(self) -> None:
        """Fail fast on invalid configuration before the app starts serving.

        Note: because a blank value is treated as "unset" (see
        ``_blank_value_means_unset``), string fields that carry a non-empty
        default can never be blank here - a blank entry silently falls back to
        the default instead.
        """
        if not self.API_PREFIX.startswith("/"):
            raise ValueError("API_PREFIX must start with '/'")
        if self.API_PREFIX.endswith("/"):
            raise ValueError("API_PREFIX must not end with '/'")
        if self.TRACE_ID_MAX_LENGTH <= 0:
            raise ValueError("TRACE_ID_MAX_LENGTH must be a positive integer")
        if self.resolved_log_level not in _LOG_LEVELS:
            raise ValueError(f"LOG_LEVEL must be one of {_LOG_LEVELS}")

        self._validate_database()
        self._validate_redis()
        self._validate_identity_and_auth()
        self._validate_ops_scheduler()
        self._validate_storage()
        self._validate_production_hardening()

        # Touching the property triggers the wildcard-origin validation eagerly.
        _ = self.cors_origins

    def _validate_production_hardening(self) -> None:
        """Refuse to boot in production with a development grade posture.

        These are not nice-to-haves. An empty ``ALLOWED_HOSTS`` means any Host
        header is accepted, which turns password reset links and absolute URLs
        into an injection surface; a blank ``CORS_ORIGINS`` silently locks the
        four frontends out because the browser sends an Origin that is not on
        the allow-list.
        """
        if self.APP_ENV != "production":
            return
        if self.APP_DEBUG:
            raise ValueError("APP_DEBUG must be false in production")
        if not self.allowed_hosts:
            raise ValueError("ALLOWED_HOSTS must list every public host in production")
        if not self.cors_origins:
            raise ValueError("CORS_ORIGINS must list every frontend origin in production")
        if self.CORS_ALLOW_METHODS.strip() == "*" or self.CORS_ALLOW_HEADERS.strip() == "*":
            raise ValueError("CORS methods and headers must be enumerated in production")
        _ = self.resolved_jwt_secret

    def _validate_positive(self, name: str, value: int) -> None:
        if value <= 0:
            raise ValueError(f"{name} must be a positive integer")

    def _validate_identity_and_auth(self) -> None:
        self._validate_positive("AUTH_ACCESS_TOKEN_TTL_SECONDS", self.AUTH_ACCESS_TOKEN_TTL_SECONDS)
        self._validate_positive(
            "AUTH_REFRESH_TOKEN_TTL_SECONDS", self.AUTH_REFRESH_TOKEN_TTL_SECONDS
        )
        self._validate_positive("AUTH_REFRESH_TOKEN_BYTES", self.AUTH_REFRESH_TOKEN_BYTES)
        self._validate_positive(
            "AUTH_MAX_ACTIVE_SESSIONS_PER_USER", self.AUTH_MAX_ACTIVE_SESSIONS_PER_USER
        )
        self._validate_positive("PASSWORD_MIN_LENGTH", self.PASSWORD_MIN_LENGTH)
        self._validate_positive("PASSWORD_HISTORY_COUNT", self.PASSWORD_HISTORY_COUNT)
        self._validate_positive("PASSWORD_EXPIRE_DAYS", self.PASSWORD_EXPIRE_DAYS)
        self._validate_positive("PASSWORD_MAX_FAILED_ATTEMPTS", self.PASSWORD_MAX_FAILED_ATTEMPTS)
        self._validate_positive("PASSWORD_LOCK_MINUTES", self.PASSWORD_LOCK_MINUTES)
        if self.SNOWFLAKE_NODE_BITS < 0 or self.SNOWFLAKE_SEQUENCE_BITS < 0:
            raise ValueError("Snowflake bit widths must not be negative")
        if self.SNOWFLAKE_NODE_BITS + self.SNOWFLAKE_SEQUENCE_BITS > 22:
            raise ValueError("SNOWFLAKE_NODE_BITS + SNOWFLAKE_SEQUENCE_BITS must not exceed 22")
        max_node = (1 << self.SNOWFLAKE_NODE_BITS) - 1
        if not 0 <= self.SNOWFLAKE_NODE_ID <= max_node:
            raise ValueError(f"SNOWFLAKE_NODE_ID must be between 0 and {max_node}")
        if self.SNOWFLAKE_EPOCH_MS <= 0:
            raise ValueError("SNOWFLAKE_EPOCH_MS must be a positive epoch in milliseconds")
        if not self.AUTH_JWT_ALGORITHM.strip():
            raise ValueError("AUTH_JWT_ALGORITHM must not be blank")
        self._validate_positive("VERIFICATION_CODE_LENGTH", self.VERIFICATION_CODE_LENGTH)
        self._validate_positive("VERIFICATION_CODE_TTL_SECONDS", self.VERIFICATION_CODE_TTL_SECONDS)

    def _validate_storage(self) -> None:
        """Validate object storage before a request can fail on it.

        A misconfigured endpoint used to surface as a 500 on the first upload.
        Failing at startup is cheaper: the container never becomes ready and
        the operator sees the reason immediately.
        """
        provider = self.FILE_STORAGE_PROVIDER.strip().lower()
        if provider not in _STORAGE_PROVIDERS:
            raise ValueError(
                "FILE_STORAGE_PROVIDER must be 'local', 's3' or 'rustfs' "
                "('minio' is accepted as a legacy alias of 's3')"
            )
        # `s3` is the canonical value: `rustfs` and the legacy `minio` are
        # aliases, so the recorded provider never depends on the vendor.
        self.FILE_STORAGE_PROVIDER = provider if provider == "local" else "s3"
        self._validate_positive("FILE_MAX_SIZE_BYTES", self.FILE_MAX_SIZE_BYTES)
        self._validate_positive("FILE_PRESIGN_TTL_SECONDS", self.FILE_PRESIGN_TTL_SECONDS)
        self._validate_positive(
            "FILE_DOWNLOAD_URL_TTL_SECONDS", self.FILE_DOWNLOAD_URL_TTL_SECONDS
        )
        if self.FILE_STORAGE_PROVIDER == "local":
            return

        missing = [
            name
            for name, value in (
                ("S3_ENDPOINT", self.S3_ENDPOINT),
                ("S3_BUCKET", self.S3_BUCKET),
                ("S3_ACCESS_KEY", self.S3_ACCESS_KEY),
                ("S3_SECRET_KEY", self.S3_SECRET_KEY),
            )
            if not value.strip()
        ]
        if missing:
            raise ValueError(
                f"{', '.join(missing)} is required when storage is "
                f"'{self.FILE_STORAGE_PROVIDER}'"
            )
        self._validate_bucket_name(self.S3_BUCKET)
        if self.S3_ADDRESSING_STYLE.strip().lower() not in {"path", "virtual"}:
            raise ValueError("S3_ADDRESSING_STYLE must be 'path' or 'virtual'")
        self.S3_ADDRESSING_STYLE = self.S3_ADDRESSING_STYLE.strip().lower()
        self._validate_positive("S3_CONNECT_TIMEOUT_SECONDS", self.S3_CONNECT_TIMEOUT_SECONDS)
        self._validate_positive("S3_READ_TIMEOUT_SECONDS", self.S3_READ_TIMEOUT_SECONDS)
        if not self.S3_REGION.strip():
            raise ValueError("S3_REGION must not be empty")
        if self.APP_ENV == "production":
            # The RustFS and MinIO sample credentials are public knowledge.
            if self.S3_SECRET_KEY.strip() in _SAMPLE_STORAGE_SECRETS:
                raise ValueError("S3_SECRET_KEY must not be a sample credential in production")
            if len(self.S3_SECRET_KEY.strip()) < 12:
                raise ValueError("S3_SECRET_KEY must be at least 12 characters in production")

    @staticmethod
    def _validate_bucket_name(bucket: str) -> None:
        """Check the S3 bucket naming rules every compatible server enforces."""
        name = bucket.strip()
        if not 3 <= len(name) <= 63:
            raise ValueError("S3_BUCKET must be between 3 and 63 characters long")
        if not name[0].isalnum() or not name[-1].isalnum():
            raise ValueError("S3_BUCKET must start and end with an alphanumeric character")
        allowed = set(string.ascii_lowercase + string.digits + ".-")
        lowered = name.lower()
        if any(character not in allowed for character in lowered):
            raise ValueError(
                "S3_BUCKET may contain only lower case letters, digits, dots and '-'"
            )
        if ".." in lowered:
            raise ValueError("S3_BUCKET must not contain consecutive dots")

    def _validate_ops_scheduler(self) -> None:
        if not self.OPS_SCHEDULER_ENABLED:
            return
        self._validate_positive(
            "OPS_SCHEDULER_ALERT_INTERVAL_SECONDS", self.OPS_SCHEDULER_ALERT_INTERVAL_SECONDS
        )
        self._validate_positive(
            "OPS_SCHEDULER_PROBE_INTERVAL_SECONDS", self.OPS_SCHEDULER_PROBE_INTERVAL_SECONDS
        )
        self._validate_positive(
            "OPS_SCHEDULER_ROLLUP_INTERVAL_MINUTES", self.OPS_SCHEDULER_ROLLUP_INTERVAL_MINUTES
        )
        if not 0 <= self.OPS_SCHEDULER_DAILY_ROLLUP_HOUR <= 23:
            raise ValueError("OPS_SCHEDULER_DAILY_ROLLUP_HOUR must be between 0 and 23")
        if not 0 <= self.OPS_SCHEDULER_PURGE_HOUR <= 23:
            raise ValueError("OPS_SCHEDULER_PURGE_HOUR must be between 0 and 23")
        if self.OPS_SELF_MONITOR_ENABLED and not self.OPS_SELF_MONITOR_URL.strip():
            raise ValueError("OPS_SELF_MONITOR_URL must not be blank when self monitoring is on")

    def _validate_database(self) -> None:
        if not 1 <= self.DB_PORT <= 65535:
            raise ValueError("DB_PORT must be between 1 and 65535")
        if self.DB_POOL_SIZE <= 0:
            raise ValueError("DB_POOL_SIZE must be a positive integer")
        if self.DB_MAX_OVERFLOW < 0:
            raise ValueError("DB_MAX_OVERFLOW must not be negative")
        if self.DB_POOL_TIMEOUT_SECONDS <= 0:
            raise ValueError("DB_POOL_TIMEOUT_SECONDS must be positive")

    @property
    def missing_database_fields(self) -> tuple[str, ...]:
        """Return the PostgreSQL fields still missing while ``DB_HOST`` is set.

        A partially filled connection is reported, not raised: the application
        still starts (database access simply stays disabled) so that a ``.env``
        being filled in step by step does not break startup.
        """
        if self.DATABASE_URL.strip() or not self.DB_HOST.strip():
            return ()
        return tuple(
            label
            for label, value in (("DB_NAME", self.DB_NAME), ("DB_USER", self.DB_USER))
            if not value.strip()
        )

    def _validate_redis(self) -> None:
        if not 1 <= self.REDIS_PORT <= 65535:
            raise ValueError("REDIS_PORT must be between 1 and 65535")
        if self.REDIS_DB < 0:
            raise ValueError("REDIS_DB must not be negative")
        if self.REDIS_MAX_CONNECTIONS is not None and self.REDIS_MAX_CONNECTIONS <= 0:
            raise ValueError("REDIS_MAX_CONNECTIONS must be a positive integer")
        if self.REDIS_SOCKET_TIMEOUT_SECONDS is not None and self.REDIS_SOCKET_TIMEOUT_SECONDS <= 0:
            raise ValueError("REDIS_SOCKET_TIMEOUT_SECONDS must be positive")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process wide settings singleton."""
    return Settings()
