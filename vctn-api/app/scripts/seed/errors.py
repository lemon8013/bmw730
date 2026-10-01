"""Seed specific failures.

Every failure carries a stable machine readable ``code`` so an operator (or a
test) can react without parsing a message.
"""

from __future__ import annotations


class SeedError(Exception):
    """A seed precondition is not satisfied."""

    def __init__(self, message: str, *, code: str) -> None:
        super().__init__(message)
        self.code = code


ADMIN_PASSWORD_REQUIRED: str = "SEED_ADMIN_PASSWORD_REQUIRED"
TEST_PASSWORD_REQUIRED: str = "SEED_TEST_PASSWORD_REQUIRED"
DATABASE_NOT_CONFIGURED: str = "SEED_DATABASE_NOT_CONFIGURED"
SCHEMA_MISSING: str = "SEED_SCHEMA_MISSING"

__all__ = [
    "ADMIN_PASSWORD_REQUIRED",
    "DATABASE_NOT_CONFIGURED",
    "SCHEMA_MISSING",
    "TEST_PASSWORD_REQUIRED",
    "SeedError",
]
