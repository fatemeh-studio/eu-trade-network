"""DuckDB helpers: store node metrics + edges, run analytical SQL from sql/queries/."""

from pathlib import Path

import duckdb
import pandas as pd

from . import config


def connect(db_path: Path = config.DB_PATH) -> duckdb.DuckDBPyConnection:
    """Open (creating parent dirs) a DuckDB connection."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P2")


def init_schema(
    con: duckdb.DuckDBPyConnection, schema_path: Path = config.SQL_DIR / "schema.sql"
) -> None:
    """Execute ``sql/schema.sql``."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P2")


def write_table(
    con: duckdb.DuckDBPyConnection, name: str, df: pd.DataFrame, replace: bool = True
) -> None:
    """Write a DataFrame into a DuckDB table."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P2")


def read_sql(con: duckdb.DuckDBPyConnection, sql: str | Path) -> pd.DataFrame:
    """Run a SQL string, or the contents of a ``.sql`` file, and return a DataFrame."""
    raise NotImplementedError("TODO: implement in Cursor Prompt P2")
