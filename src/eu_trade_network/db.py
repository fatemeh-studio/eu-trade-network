"""DuckDB helpers: store node metrics + edges, run analytical SQL from sql/queries/."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from . import config


def connect(db_path: Path = config.DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (creating parent dirs) a DuckDB connection.

    Args:
        db_path: Path to the ``.duckdb`` file (created if absent).

    Returns:
        Open DuckDB connection.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(db_path))


def init_schema(
    con: duckdb.DuckDBPyConnection, schema_path: Path = config.SQL_DIR / "schema.sql"
) -> None:
    """Execute ``sql/schema.sql``.

    Args:
        con: Open DuckDB connection.
        schema_path: Path to the DDL script.
    """
    sql = Path(schema_path).read_text(encoding="utf-8")
    con.execute(sql)


def write_table(
    con: duckdb.DuckDBPyConnection, name: str, df: pd.DataFrame, replace: bool = True
) -> None:
    """Write a DataFrame into a DuckDB table.

    Inserts only the columns present in ``df``. When ``replace`` is True, existing
    rows are deleted first (table must already exist via ``init_schema``).

    Args:
        con: Open DuckDB connection.
        name: Destination table name.
        df: Data to write.
        replace: If True, clear the table before inserting.
    """
    tmp = f"_write_{name}"
    con.register(tmp, df)
    cols = ", ".join(df.columns)
    if replace:
        con.execute(f"DELETE FROM {name}")
    con.execute(f"INSERT INTO {name} ({cols}) SELECT {cols} FROM {tmp}")
    con.unregister(tmp)


def read_sql(con: duckdb.DuckDBPyConnection, sql: str | Path) -> pd.DataFrame:
    """Run a SQL string, or the contents of a ``.sql`` file, and return a DataFrame.

    Args:
        con: Open DuckDB connection.
        sql: SQL text, or a path to a ``.sql`` file.

    Returns:
        Query result as a pandas DataFrame.
    """
    if isinstance(sql, Path):
        query = sql.read_text(encoding="utf-8")
    else:
        path = Path(sql)
        query = path.read_text(encoding="utf-8") if path.is_file() else sql
    return con.execute(query).df()
