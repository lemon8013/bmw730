"""Unified application logging.

Phase 0 implements the application log only. The access, security, operation and
audit logs are reserved: their formats are enabled in the phase that freezes
them.

Sensitive values (passwords, MFA secrets, tokens, API keys, cookies,
authorization headers, raw user input, uploaded file content) must never be
logged.
"""

from __future__ import annotations

import logging
import sys
from typing import Final

from app.core.config import Settings
from app.shared.tracing.context import get_trace_id

APPLICATION_LOGGER: Final[str] = "vctn.app"

# Reserved logger names. Phase 0 does not emit records to them yet.
ACCESS_LOGGER: Final[str] = "vctn.access"
SECURITY_LOGGER: Final[str] = "vctn.security"
OPERATION_LOGGER: Final[str] = "vctn.operation"
AUDIT_LOGGER: Final[str] = "vctn.audit"

RESERVED_LOGGERS: Final[tuple[str, ...]] = (
    ACCESS_LOGGER,
    SECURITY_LOGGER,
    OPERATION_LOGGER,
    AUDIT_LOGGER,
)

_LOG_FORMAT: Final[str] = "%(asctime)s %(levelname)-8s %(name)s [trace_id=%(trace_id)s] %(message)s"


class TraceIdFilter(logging.Filter):
    """Attach the current trace id to every log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = get_trace_id() or "-"
        return True


def setup_logging(settings: Settings) -> None:
    """Configure the application logger exactly once per process."""
    level = logging.DEBUG if settings.APP_DEBUG else logging.INFO

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    handler.addFilter(TraceIdFilter())

    application_logger = logging.getLogger(APPLICATION_LOGGER)
    application_logger.handlers.clear()
    application_logger.addHandler(handler)
    application_logger.setLevel(level)
    application_logger.propagate = False

    for name in RESERVED_LOGGERS:
        logging.getLogger(name).setLevel(level)


def get_logger(name: str = APPLICATION_LOGGER) -> logging.Logger:
    """Return an application logger."""
    return logging.getLogger(name)
