"""Read-only SQLite execution with SQL AST validation."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

import sqlglot
from sqlglot import exp


@dataclass(frozen=True)
class ExecutionResult:
    ok: bool
    rows: list[tuple] | None = None
    error: str | None = None


def validate_read_only(sql: str) -> str:
    statements = sqlglot.parse(sql, read="sqlite")
    if len(statements) != 1 or not isinstance(statements[0], exp.Query):
        raise ValueError("Only one read-only SELECT or WITH query is allowed")
    return statements[0].sql(dialect="sqlite")


def execute_read_only(db_path: str | Path, sql: str, max_steps: int = 100_000) -> ExecutionResult:
    try:
        normalized = validate_read_only(sql)
        uri = f"file:{Path(db_path).resolve()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        try:
            remaining = max_steps
            def guard():
                nonlocal remaining
                remaining -= 1
                return 1 if remaining <= 0 else 0
            connection.set_progress_handler(guard, 1_000)
            rows = connection.execute(normalized).fetchall()
            return ExecutionResult(True, rows=rows)
        finally:
            connection.close()
    except Exception as error:
        return ExecutionResult(False, error=str(error))
