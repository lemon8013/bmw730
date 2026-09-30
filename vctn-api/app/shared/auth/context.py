"""Authenticated caller identity.

:class:`Principal` carries only identity facts - it never carries permissions.
Permissions are resolved per request by
:class:`app.shared.authorization.service.AuthorizationService` so that a
permission change takes effect immediately instead of at the next login.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

SUBJECT_TYPE_ADMIN: Final[str] = "admin"
SUBJECT_TYPE_PLATFORM: Final[str] = "platform"


@dataclass(frozen=True, slots=True)
class Principal:
    """The authenticated caller of the current request."""

    subject_id: int
    subject_type: str
    session_id: int
    username: str
    display_name: str
    department_id: int | None = None
    is_super_admin: bool = False
    ip: str | None = None
    user_agent: str | None = None
    must_change_password: bool = False

    @property
    def is_admin(self) -> bool:
        return self.subject_type == SUBJECT_TYPE_ADMIN

    @property
    def is_platform_user(self) -> bool:
        return self.subject_type == SUBJECT_TYPE_PLATFORM
