"""VCTN authorization shared infrastructure."""

from app.shared.authorization.service import (
    AuthorizationService,
    DataScope,
)

__all__ = ["AuthorizationService", "DataScope"]
