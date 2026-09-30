"""Database schema tests.

These pin the ORM models to the frozen DDL baseline and, when a live PostgreSQL
is configured, pin the database to both. Nothing here touches business logic.

Run the standalone comparison with::

    python scripts/schema_audit.py
"""

from __future__ import annotations

import pytest
import schema_audit
from schema_audit import ModelTable

import app.shared.database.models  # noqa: F401  (registers every table)
from app.shared.database.base import Base

EXPECTED_TABLE_COUNT = 79
EXPECTED_COLUMN_COUNT = 761
EXPECTED_PRIMARY_KEYS = 79
EXPECTED_FOREIGN_KEYS = 82
EXPECTED_UNIQUE_CONSTRAINTS = 28
EXPECTED_CHECK_CONSTRAINTS = 4
# Only the indexes the DDL declares with CREATE [UNIQUE] INDEX live on
# `Table.indexes`; PostgreSQL additionally creates one index per primary key
# and per unique constraint: 79 + 28 + 30 = 137.
EXPECTED_DECLARED_INDEXES = 30
EXPECTED_DATABASE_INDEXES = 137
EXPECTED_JSONB_COLUMNS = 30
EXPECTED_INET_COLUMNS = 7

MULTI_TENANT_MARKERS = ("tenant_id", "tenant_key", "tenant_code", "tenant_scope")


@pytest.fixture(scope="module")
def ddl_tables() -> dict[str, list[str]]:
    return schema_audit.parse_ddl_tables()


@pytest.fixture(scope="module")
def models() -> dict[str, ModelTable]:
    return schema_audit.model_summary()["tables"]


def test_ddl_declares_every_expected_table(ddl_tables: dict[str, list[str]]) -> None:
    assert len(ddl_tables) == EXPECTED_TABLE_COUNT


def test_base_metadata_contains_every_table(models: dict[str, ModelTable]) -> None:
    assert len(models) == EXPECTED_TABLE_COUNT
    assert len(Base.metadata.tables) == EXPECTED_TABLE_COUNT


def test_model_tables_match_ddl_tables(
    ddl_tables: dict[str, list[str]], models: dict[str, ModelTable]
) -> None:
    assert set(models) == set(ddl_tables)
    for table, columns in ddl_tables.items():
        assert models[table]["columns"] == columns, f"column list differs: {table}"


def test_model_declares_every_column(models: dict[str, ModelTable]) -> None:
    total = sum(len(entry["columns"]) for entry in models.values())
    assert total == EXPECTED_COLUMN_COUNT


def test_model_counts_of_every_constraint_kind(models: dict[str, ModelTable]) -> None:
    assert sum(1 for e in models.values() if e["pk"]) == EXPECTED_PRIMARY_KEYS
    assert sum(len(e["fks"]) for e in models.values()) == EXPECTED_FOREIGN_KEYS
    assert sum(len(e["uniques"]) for e in models.values()) == EXPECTED_UNIQUE_CONSTRAINTS
    assert sum(len(e["checks"]) for e in models.values()) == EXPECTED_CHECK_CONSTRAINTS
    assert sum(len(e["indexes"]) for e in models.values()) == EXPECTED_DECLARED_INDEXES


def test_unique_and_check_constraints_are_named(models: dict[str, ModelTable]) -> None:
    for table, entry in models.items():
        for name, _columns in entry["uniques"]:
            assert name, f"unnamed unique constraint on {table}"
        for name, _sqltext in entry["checks"]:
            assert name, f"unnamed check constraint on {table}"


def test_no_primary_key_is_autoincrement() -> None:
    """IDs are Snowflake values from the application, never database sequences."""
    for table in Base.metadata.tables.values():
        keys = list(table.primary_key.columns)
        # A composite key never autoincrements in SQLAlchemy, so only the
        # single-column case can silently turn into BIGSERIAL.
        if len(keys) != 1:
            continue
        column = keys[0]
        if column.type.python_type is int:
            assert column.autoincrement is False, f"{table.name}.{column.name}"


def test_every_primary_key_is_bigint() -> None:
    for table in Base.metadata.tables.values():
        for column in table.primary_key.columns:
            assert type(column.type).__name__ == "BigInteger", f"{table.name}.{column.name}"


def test_timestamps_are_timezone_aware() -> None:
    from sqlalchemy import DateTime

    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, DateTime):
                assert column.type.timezone is True, f"{table.name}.{column.name}"


def test_jsonb_and_inet_use_postgresql_types() -> None:
    """JSONB and INET must stay PostgreSQL native, never Text/String."""
    from sqlalchemy.dialects.postgresql import INET, JSONB

    jsonb = inet = 0
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, JSONB):
                jsonb += 1
            elif isinstance(column.type, INET):
                inet += 1
    assert jsonb == EXPECTED_JSONB_COLUMNS
    assert inet == EXPECTED_INET_COLUMNS


def test_no_multi_tenant_columns() -> None:
    for table in Base.metadata.tables.values():
        for column in table.columns:
            assert column.name not in MULTI_TENANT_MARKERS, f"{table.name}.{column.name}"


def test_foreign_keys_never_declare_cascade() -> None:
    """The DDL declares no ON DELETE rule, so the models must not invent one."""
    for table in Base.metadata.tables.values():
        for fk in table.foreign_keys:
            assert fk.ondelete is None, f"{table.name}.{fk.parent.name}"


def test_every_table_and_column_has_a_chinese_description() -> None:
    for table in Base.metadata.tables.values():
        assert table.comment, f"missing table comment: {table.name}"
        for column in table.columns:
            assert column.comment, f"missing column comment: {table.name}.{column.name}"


def test_deleted_at_is_kept_as_soft_delete_marker() -> None:
    """Soft deletion uses `deleted_at`; no `is_deleted` substitution."""
    for table in Base.metadata.tables.values():
        assert "is_deleted" not in table.columns
        if "deleted_at" in table.columns:
            assert table.columns["deleted_at"].nullable is True


# --------------------------------------------------------------------------
# live database
# --------------------------------------------------------------------------
@pytest.mark.usefixtures("live_infrastructure")
async def test_database_matches_the_frozen_ddl(live_settings: object) -> None:
    """Execute the DDL in a rolled-back transaction and diff it against the DB."""
    settings = live_settings
    dsn = settings.database_url.replace(  # type: ignore[attr-defined]
        "postgresql+asyncpg://", "postgresql://", 1
    )
    reference = await schema_audit.load_ddl_reference(dsn)
    live = await schema_audit.load_live(dsn)

    assert len(reference["columns"]) == EXPECTED_TABLE_COUNT
    assert len(live["columns"]) == EXPECTED_TABLE_COUNT
    assert schema_audit.diff_snapshots(reference, live) == []


@pytest.mark.usefixtures("live_infrastructure")
async def test_database_has_no_autoincrement_sequences(live_settings: object) -> None:
    import asyncpg

    dsn = live_settings.database_url.replace(  # type: ignore[attr-defined]
        "postgresql+asyncpg://", "postgresql://", 1
    )
    conn = await asyncpg.connect(dsn)
    try:
        count = await conn.fetchval(
            "SELECT count(*) FROM pg_sequences WHERE schemaname = current_schema()"
        )
    finally:
        await conn.close()
    assert count == 0, "IDs must come from Snowflake, not database sequences"
