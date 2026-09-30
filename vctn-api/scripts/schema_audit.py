"""Compare the frozen DDL, the SQLAlchemy models and the live PostgreSQL schema.

The frozen DDL is the single source of truth. Rather than trusting the parser,
this module executes the DDL inside a transaction that is always rolled back and
snapshots what PostgreSQL actually built. That snapshot is then compared with
the live database created by Alembic, so both sides come from PostgreSQL itself
and the comparison is apples to apples.

Usage::

    python scripts/schema_audit.py
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path
from typing import Any, TypedDict

REPO_ROOT = Path(__file__).resolve().parents[1]
API_ROOT = REPO_ROOT
DDL_PATH = REPO_ROOT.parent / "aicoding" / "sql" / "vctn-enterprise-ddl-v2.0.sql"

COLUMN_SQL = """
SELECT c.relname AS table_name,
       a.attname AS column_name,
       a.attnum  AS ordinal,
       format_type(a.atttypid, a.atttypmod) AS data_type,
       a.attnotnull AS not_null,
       pg_get_expr(d.adbin, d.adrelid) AS column_default
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid
LEFT JOIN pg_attrdef d ON d.adrelid = c.oid AND d.adnum = a.attnum
WHERE c.relkind = 'r' AND n.nspname = current_schema()
  AND a.attnum > 0 AND NOT a.attisdropped
ORDER BY c.relname, a.attnum
"""

CONSTRAINT_SQL = """
SELECT con.conname   AS name,
       con.contype::text AS type,
       rel.relname   AS table_name,
       pg_get_constraintdef(con.oid) AS definition,
       (SELECT array_agg(att.attname ORDER BY u.ord)
          FROM unnest(con.conkey) WITH ORDINALITY AS u(attnum, ord)
          JOIN pg_attribute att
            ON att.attrelid = con.conrelid AND att.attnum = u.attnum) AS columns,
       frel.relname  AS ref_table,
       (SELECT array_agg(att.attname ORDER BY u.ord)
          FROM unnest(con.confkey) WITH ORDINALITY AS u(attnum, ord)
          JOIN pg_attribute att
            ON att.attrelid = con.confrelid AND att.attnum = u.attnum) AS ref_columns
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
JOIN pg_namespace n ON n.oid = rel.relnamespace
LEFT JOIN pg_class frel ON frel.oid = con.confrelid
WHERE n.nspname = current_schema() AND rel.relkind = 'r'
ORDER BY rel.relname, con.conname
"""

INDEX_SQL = """
SELECT i.relname AS index_name,
       t.relname AS table_name,
       ix.indisunique AS is_unique,
       ix.indisprimary AS is_primary,
       pg_get_indexdef(ix.indexrelid) AS definition,
       pg_get_expr(ix.indpred, ix.indrelid) AS where_clause
FROM pg_index ix
JOIN pg_class i ON i.oid = ix.indexrelid
JOIN pg_class t ON t.oid = ix.indrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname = current_schema() AND t.relkind = 'r'
ORDER BY t.relname, i.relname
"""

# pgcrypto is declared by the DDL but is not installed on the server, and no
# column references any pgcrypto function (verified by scanning the DDL).
UNSUPPORTED_STATEMENT_PREFIXES = ("CREATE EXTENSION",)


def ddl_without_unavailable_statements(ddl: str) -> str:
    """Drop statements the server cannot execute, keeping the rest verbatim."""
    return "\n".join(
        line
        for line in ddl.splitlines()
        if not line.strip().upper().startswith(UNSUPPORTED_STATEMENT_PREFIXES)
    )


Snapshot = dict[str, Any]


class ModelTable(TypedDict):
    """The structural facts one ORM model declares."""

    columns: list[str]
    pk: list[str]
    fks: list[tuple[str, str, str | None]]
    uniques: list[tuple[str | None, tuple[str, ...]]]
    checks: list[tuple[str | None, str]]
    indexes: list[tuple[str | None, tuple[str, ...]]]


class ModelSummary(TypedDict):
    """Result of :func:`model_summary`."""

    tables: dict[str, ModelTable]
    count: int


def _snapshot_from_rows(
    columns: list[Any], constraints: list[Any], indexes: list[Any], exclude: set[str]
) -> Snapshot:
    cols: dict[str, list[dict[str, Any]]] = {}
    for table, name, ordinal, data_type, not_null, default in columns:
        if table in exclude:
            continue
        cols.setdefault(table, []).append(
            {
                "name": name,
                "ordinal": ordinal,
                "type": data_type,
                "not_null": not_null,
                "default": default,
            }
        )
    cons: dict[tuple[str, str], dict[str, Any]] = {}
    for name, ctype, table, definition, ccolumns, ref_table, ref_columns in constraints:
        if table in exclude:
            continue
        # PostgreSQL 17+ also records NOT NULL as contype 'n'; nullability is
        # already covered by the column snapshot.
        if ctype == "n":
            continue
        cons[(table, name)] = {
            "type": ctype,
            "definition": definition,
            "columns": list(ccolumns) if ccolumns else None,
            "ref_table": ref_table,
            "ref_columns": list(ref_columns) if ref_columns else None,
        }
    idxs: dict[tuple[str, str], dict[str, Any]] = {}
    for name, table, unique, primary, definition, where in indexes:
        if table in exclude:
            continue
        idxs[(table, name)] = {
            "unique": unique,
            "primary": primary,
            "definition": definition,
            "where": where,
        }
    return {"columns": cols, "constraints": cons, "indexes": idxs}


async def _fetch_snapshot(conn: Any, exclude: set[str]) -> Snapshot:
    columns = [tuple(r) for r in await conn.fetch(COLUMN_SQL)]
    constraints = [tuple(r) for r in await conn.fetch(CONSTRAINT_SQL)]
    indexes = [tuple(r) for r in await conn.fetch(INDEX_SQL)]
    return _snapshot_from_rows(columns, constraints, indexes, exclude)


REFERENCE_SCHEMA = "vctn_ddl_reference"


async def load_ddl_reference(dsn: str) -> Snapshot:
    """Execute the frozen DDL in a transaction, snapshot it, then roll back.

    The DDL uses plain ``CREATE TABLE``, so it is applied inside a throwaway
    schema. Both the schema and everything it contains disappear on rollback.
    """
    import asyncpg  # noqa: PLC0415

    ddl = ddl_without_unavailable_statements(DDL_PATH.read_text(encoding="utf-8"))
    conn = await asyncpg.connect(dsn)
    try:
        txn = conn.transaction()
        await txn.start()
        try:
            await conn.execute(f'CREATE SCHEMA "{REFERENCE_SCHEMA}"')
            await conn.execute(f'SET LOCAL search_path TO "{REFERENCE_SCHEMA}"')
            await conn.execute(ddl)
            return await _fetch_snapshot(conn, exclude=set())
        finally:
            await txn.rollback()
    finally:
        await conn.close()


async def load_live(dsn: str) -> Snapshot:
    """Snapshot the database as Alembic has built it."""
    import asyncpg  # noqa: PLC0415

    conn = await asyncpg.connect(dsn)
    try:
        return await _fetch_snapshot(conn, exclude={"alembic_version"})
    finally:
        await conn.close()


def diff_snapshots(expected: Snapshot, actual: Snapshot) -> list[str]:
    """Return a human-readable list of every difference between two snapshots."""
    problems: list[str] = []

    exp_tables = set(expected["columns"])
    act_tables = set(actual["columns"])
    for table in sorted(exp_tables - act_tables):
        problems.append(f"missing table: {table}")
    for table in sorted(act_tables - exp_tables):
        problems.append(f"unexpected table: {table}")

    for table in sorted(exp_tables & act_tables):
        exp_cols = expected["columns"][table]
        act_cols = actual["columns"][table]
        if len(exp_cols) != len(act_cols):
            problems.append(f"{table}: column count {len(exp_cols)} != {len(act_cols)}")
            continue
        for exp, act in zip(exp_cols, act_cols, strict=True):
            for field in ("name", "ordinal", "type", "not_null", "default"):
                if exp[field] != act[field]:
                    problems.append(
                        f"{table}.{exp['name']}: {field} {exp[field]!r} != {act[field]!r}"
                    )

    exp_cons = set(expected["constraints"])
    act_cons = set(actual["constraints"])
    for key in sorted(exp_cons - act_cons):
        problems.append(f"missing constraint: {key[0]}.{key[1]}")
    for key in sorted(act_cons - exp_cons):
        problems.append(f"unexpected constraint: {key[0]}.{key[1]}")
    for key in sorted(exp_cons & act_cons):
        exp_c = expected["constraints"][key]
        act_c = actual["constraints"][key]
        for field in ("type", "definition", "columns", "ref_table", "ref_columns"):
            if exp_c[field] != act_c[field]:
                problems.append(f"{key[0]}.{key[1]}: {field} {exp_c[field]!r} != {act_c[field]!r}")

    exp_idx = set(expected["indexes"])
    act_idx = set(actual["indexes"])
    for key in sorted(exp_idx - act_idx):
        problems.append(f"missing index: {key[0]}.{key[1]}")
    for key in sorted(act_idx - exp_idx):
        problems.append(f"unexpected index: {key[0]}.{key[1]}")
    for key in sorted(exp_idx & act_idx):
        exp_i = expected["indexes"][key]
        act_i = actual["indexes"][key]
        for field in ("unique", "primary", "where"):
            if exp_i[field] != act_i[field]:
                problems.append(f"{key[0]}.{key[1]}: {field} {exp_i[field]!r} != {act_i[field]!r}")
    return problems


def model_summary() -> ModelSummary:
    """Collect the structural facts that the ORM models declare."""
    from sqlalchemy import CheckConstraint, UniqueConstraint  # noqa: PLC0415

    sys.path.insert(0, str(API_ROOT))
    import app.shared.database.models  # noqa: F401,PLC0415
    from app.shared.database.base import Base  # noqa: PLC0415

    def constraint_name(constraint: Any) -> str | None:
        name = constraint.name
        return name if isinstance(name, str) else None

    metadata = Base.metadata
    tables: dict[str, ModelTable] = {}
    for name, table in sorted(metadata.tables.items()):
        fks = sorted(
            (
                str(fk.parent.name),
                str(fk.target_fullname),
                fk.name if isinstance(fk.name, str) else None,
            )
            for fk in table.foreign_keys
        )
        tables[name] = {
            "columns": [str(c.name) for c in table.columns],
            "pk": sorted(str(c.name) for c in table.primary_key.columns),
            "fks": fks,
            "uniques": sorted(
                (constraint_name(u), tuple(str(c.name) for c in u.columns))
                for u in table.constraints
                if isinstance(u, UniqueConstraint)
            ),
            "checks": sorted(
                (constraint_name(c), str(c.sqltext))
                for c in table.constraints
                if isinstance(c, CheckConstraint)
            ),
            "indexes": sorted(
                (constraint_name(i), tuple(_expr_text(e) for e in i.expressions))
                for i in table.indexes
            ),
        }
    return {"tables": tables, "count": len(metadata.tables)}


def _expr_text(expression: Any) -> str:
    return str(getattr(expression, "text", expression))


def parse_ddl_tables() -> dict[str, list[str]]:
    """Return {table: [column, ...]} straight from the DDL text."""
    sql = DDL_PATH.read_text(encoding="utf-8")
    tables: dict[str, list[str]] = {}
    for match in re.finditer(r"CREATE\s+TABLE\s+(\w+)\s*\(", sql, flags=re.IGNORECASE):
        table = match.group(1)
        start = match.end()
        depth = 1
        i = start
        while i < len(sql) and depth:
            if sql[i] == "(":
                depth += 1
            elif sql[i] == ")":
                depth -= 1
            i += 1
        body = sql[start : i - 1]
        columns = [
            segment.split()[0]
            for segment in _split_top_level(body)
            if not re.match(
                r"(PRIMARY\s+KEY|UNIQUE|CHECK|CONSTRAINT)\s*\(",
                segment,
                flags=re.IGNORECASE,
            )
        ]
        tables[table] = columns
    return tables


def _split_top_level(text: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    quote = False
    current: list[str] = []
    for ch in text:
        if quote:
            current.append(ch)
            if ch == "'":
                quote = False
            continue
        if ch == "'":
            quote = True
            current.append(ch)
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    tail = "".join(current).strip()
    if tail:
        parts.append(tail)
    return parts


async def _run() -> int:
    sys.path.insert(0, str(API_ROOT))
    from app.core.config import Settings  # noqa: PLC0415

    settings = Settings(_env_file=str(API_ROOT / ".env"))
    if not settings.is_database_configured:
        print("DATABASE-CONNECTION-BLOCKER: PostgreSQL is not configured")
        return 2
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    model = model_summary()
    ddl = parse_ddl_tables()
    reference = await load_ddl_reference(dsn)
    live = await load_live(dsn)

    print("DDL tables            :", len(ddl))
    print("Model tables          :", model["count"])
    print("Base.metadata tables  :", len(model["tables"]))
    print("Reference (DDL run)   :", len(reference["columns"]))
    print("Live (Alembic)        :", len(live["columns"]))
    print()

    problems: list[str] = []
    if len(ddl) != model["count"]:
        problems.append(f"model count {model['count']} != DDL count {len(ddl)}")
    if set(ddl) - set(model["tables"]):
        problems.append(f"tables missing from models: {sorted(set(ddl) - set(model['tables']))}")
    if set(model["tables"]) - set(ddl):
        problems.append(f"tables not in DDL: {sorted(set(model['tables']) - set(ddl))}")
    for table in sorted(set(ddl) & set(model["tables"])):
        if ddl[table] != model["tables"][table]["columns"]:
            problems.append(
                f"{table}: column list differs\n"
                f"      ddl  : {ddl[table]}\n"
                f"      model: {model['tables'][table]['columns']}"
            )
    problems.extend(diff_snapshots(reference, live))

    if problems:
        print(f"DIFFERENCES ({len(problems)}):")
        for problem in problems:
            print("  -", problem)
        return 1
    print("RESULT: DDL == Model == PostgreSQL (no differences)")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_run()))
