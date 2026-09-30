"""VCTN logging shared infrastructure.

The five log streams are separated (access / security / operation / audit /
application). Writers live in :mod:`app.shared.logging.writers`; the retention
periods are configuration.
"""

from app.shared.logging.writers import (
    RESULT_FAILURE,
    RESULT_SUCCESS,
    purge_retired_logs,
    write_access_log,
    write_application_log,
    write_operation_log,
    write_security_log,
)

__all__ = [
    "RESULT_FAILURE",
    "RESULT_SUCCESS",
    "purge_retired_logs",
    "write_access_log",
    "write_application_log",
    "write_operation_log",
    "write_security_log",
]
