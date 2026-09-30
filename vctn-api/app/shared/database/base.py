"""Declarative base shared by every ORM model.

Every VCTN model derives from this single ``Base``, so ``Base.metadata`` is the
one and only registry of the schema.

Deliberately no ``naming_convention``
-------------------------------------
A ``MetaData`` naming convention makes SQLAlchemy invent names such as
``fk_sys_user_department_id_sys_department`` for constraints the DDL leaves
unnamed. The frozen DDL declares no such names; executing it lets PostgreSQL
apply its own defaults (``<table>_<column>_fkey``, ``<table>_pkey``,
``<table>_<columns>_key``, ``<table>_check``). Dropping the convention keeps the
ORM faithful to the DDL. Every constraint that does need a stable name --
uniques, checks, and the deferred ``tool.current_version_id`` foreign key -- is
named explicitly in its model using the name PostgreSQL itself generated, which
also makes Alembic downgrades possible.
"""

from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for the VCTN database."""

    metadata = MetaData()
