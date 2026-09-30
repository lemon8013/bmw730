"""Declarative base shared by every ORM model.

No business model is declared in Phase 0. Table structure comes solely from the
frozen PostgreSQL DDL baseline and is introduced in a later phase.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Deterministic constraint names keep Alembic migrations stable.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for the VCTN database."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
