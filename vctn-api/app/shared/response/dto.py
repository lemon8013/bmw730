"""Shared DTO primitives.

Every identifier is a BIGINT in PostgreSQL and **must** be serialized as a
string in the API contract, so every DTO that exposes an id uses :data:`StringId`
instead of ``int``.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import AliasChoices, BaseModel, BeforeValidator, ConfigDict


def _coerce_identifier(value: object) -> object:
    """Render a BIGINT identifier as a string."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return str(value)
    return value


def _coerce_text(value: object) -> object:
    """Render a non-string scalar as text.

    asyncpg returns a PostgreSQL ``INET`` column as an ``ipaddress`` object,
    while every address in the API contract is declared as a string. Converting
    here keeps the rule in one place instead of repeating it in every DTO that
    exposes an address.
    """
    if value is None or isinstance(value, str | bool | int | float):
        return value
    return str(value)


StringId = Annotated[str, BeforeValidator(_coerce_identifier)]
OptionalStringId = Annotated[str | None, BeforeValidator(_coerce_identifier)]

#: An IP address (a PostgreSQL ``INET`` column) serialized as a string.
IpAddress = Annotated[str, BeforeValidator(_coerce_text)]
OptionalIpAddress = Annotated[str | None, BeforeValidator(_coerce_text)]

#: Validation alias for the DDL ``metadata`` column.
#:
#: ``metadata`` is reserved by SQLAlchemy's declarative base, so the mapped
#: attribute is named ``metadata_payload``. Declaring the alias lets a response
#: DTO be validated straight from an ORM row while still accepting (and
#: serializing as) ``metadata``.
METADATA_COLUMN_ALIAS = AliasChoices("metadata_payload", "metadata")


class ApiModel(BaseModel):
    """Base class of every request/response DTO."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
