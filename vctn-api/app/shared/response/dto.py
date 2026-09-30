"""Shared DTO primitives.

Every identifier is a BIGINT in PostgreSQL and **must** be serialized as a
string in the API contract, so every DTO that exposes an id uses :data:`StringId`
instead of ``int``.
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, BeforeValidator, ConfigDict


def _coerce_identifier(value: object) -> object:
    """Render a BIGINT identifier as a string."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return str(value)
    return value


StringId = Annotated[str, BeforeValidator(_coerce_identifier)]
OptionalStringId = Annotated[str | None, BeforeValidator(_coerce_identifier)]


class ApiModel(BaseModel):
    """Base class of every request/response DTO."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
