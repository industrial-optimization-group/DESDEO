"""Idempotent column additions for tables that already exist.

`SQLModel.metadata.create_all` creates missing *tables* but never alters existing ones, and this
project carries no migration tool. So when a column is added to a state model whose table already
has rows in a deployed database, that column has to be added separately or every read of the table
fails.

Each entry is safe to apply repeatedly, and safe against a fresh database where `create_all`
already produced the column. Adding a column here is only correct when it is nullable or has a
default: existing rows get NULL, and the reading code must already treat NULL as "written before
this column existed".

Delete an entry once every database that matters has been through it.
"""

from __future__ import annotations

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

# (table, column, SQL type). JSON and INTEGER are spelled the same in SQLite and PostgreSQL.
_ADDED_COLUMNS: list[tuple[str, str, str]] = [
    # The JINA multi-scenario (combined) method gained scalarizer variants, so a round can now
    # produce several designs instead of one. Rows written before that read back as NULL, which
    # the router falls back to the single-design columns for.
    # Precomputed per-cell payoff ranges for the combined multi-scenario method.
    ("jinamultiscenariometadata", "combined_cell_ranges", "JSON"),
    # Per-scenario information hours for the combined multi-scenario method's normal-operation
    # (non-anticipativity) constraints. NULL means no constraints, i.e. the behaviour before it.
    ("jinamultiscenariometadata", "information_hours", "JSON"),
    ("districtheatingcombinediterationstate", "solutions", "JSON"),
    ("districtheatingcombinediterationstate", "max_solutions", "INTEGER"),
]


def add_missing_columns(engine: Engine) -> list[str]:
    """Add any column in `_ADDED_COLUMNS` that its table does not already have.

    Returns the `table.column` names actually added, so a caller can report them. Tables that do
    not exist yet are skipped — `create_all` will build them complete.
    """
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    added: list[str] = []

    with engine.begin() as connection:
        for table, column, sql_type in _ADDED_COLUMNS:
            if table not in existing_tables:
                continue
            if column in {c["name"] for c in inspector.get_columns(table)}:
                continue
            # Identifiers here are module-level constants, not input.
            connection.execute(text(f'ALTER TABLE "{table}" ADD COLUMN "{column}" {sql_type}'))
            added.append(f"{table}.{column}")

    return added


if __name__ == "__main__":
    from desdeo.api.db import engine as _engine

    for name in add_missing_columns(_engine):
        print(f"[db-migrate] added {name}")  # noqa: T201  # command-line entry point
    print("[db-migrate] Done.")  # noqa: T201
