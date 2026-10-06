"""Lightweight schema checks for SQL calls before they reach the driver."""

from __future__ import annotations

import re
from collections.abc import Sequence

from .schema import TABLES


class DatabaseSchemaError(RuntimeError):
    """Raised before executing SQL that does not match the known schema."""


SYSTEM_TABLES = {"information_schema", "columns"}


_TABLE_PATTERNS = (
    # The atomic identifier prevents backtracking into qualified columns such
    # as ``EXTRACT(HOUR FROM s.start_at ...)``. Those are not table clauses.
    re.compile(r"\bFROM\s+((?>[a-z_][a-z0-9_]*))(?!\s*\.)", re.IGNORECASE),
    re.compile(r"\bJOIN\s+((?>[a-z_][a-z0-9_]*))(?!\s*\.)", re.IGNORECASE),
    re.compile(r"^\s*UPDATE\s+([a-z_][a-z0-9_]*)", re.IGNORECASE),
    re.compile(r"\bINTO\s+([a-z_][a-z0-9_]*)", re.IGNORECASE),
    re.compile(r"\bALTER\s+TABLE\s+([a-z_][a-z0-9_]*)", re.IGNORECASE),
    re.compile(r"\bCREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+([a-z_][a-z0-9_]*)", re.IGNORECASE),
)


def _strip_literals(sql: str) -> str:
    return re.sub(r"'(?:''|[^'])*'", "''", sql)


def _split_csv(text: str) -> list[str]:
    parts: list[str] = []
    current: list[str] = []
    depth = 0
    for char in text:
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(0, depth - 1)
        if char == "," and depth == 0:
            parts.append("".join(current).strip())
            current = []
        else:
            current.append(char)
    if current:
        parts.append("".join(current).strip())
    return parts


def count_qmark_placeholders(sql: str) -> int:
    count = 0
    in_string = False
    index = 0
    while index < len(sql):
        char = sql[index]
        if char == "'":
            in_string = not in_string
            if in_string and index + 1 < len(sql) and sql[index + 1] == "'":
                index += 1
        elif char == "?" and not in_string:
            count += 1
        index += 1
    return count


def translate_qmark_placeholders(sql: str, placeholder: str) -> str:
    if placeholder == "?":
        return sql
    out: list[str] = []
    in_string = False
    index = 0
    while index < len(sql):
        char = sql[index]
        if char == "'":
            in_string = not in_string
            out.append(char)
        elif char == "?" and not in_string:
            out.append(placeholder)
        else:
            out.append(char)
        index += 1
    return "".join(out)


class QueryGuard:
    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    def validate(self, sql: str, params: Sequence[object] | None = None, *, many: bool = False) -> None:
        if not self.enabled:
            return
        compact = sql.strip()
        if not compact:
            raise DatabaseSchemaError("SQL statement is empty.")
        if ";" in compact.rstrip(";"):
            raise DatabaseSchemaError("Use one SQL statement per execute call.")
        expected = count_qmark_placeholders(compact)
        if params is not None and not many and expected != len(params):
            raise DatabaseSchemaError(f"SQL placeholder count mismatch: expected {expected}, got {len(params)}.")
        self._validate_tables(compact)
        self._validate_insert_columns(compact)
        self._validate_update_columns(compact)

    def _validate_tables(self, sql: str) -> None:
        searchable = _strip_literals(sql)
        for pattern in _TABLE_PATTERNS:
            for table in pattern.findall(searchable):
                if table.lower() not in TABLES:
                    if table.lower() not in SYSTEM_TABLES:
                        raise DatabaseSchemaError(f"Unknown table in SQL: {table}.")

    def _validate_insert_columns(self, sql: str) -> None:
        match = re.search(r"\bINSERT\s+INTO\s+([a-z_][a-z0-9_]*)\s*\(([^)]*)\)", sql, re.IGNORECASE | re.DOTALL)
        if not match:
            return
        table = match.group(1).lower()
        columns = [column.strip().lower() for column in match.group(2).split(",")]
        self._assert_columns(table, columns)

    def _validate_update_columns(self, sql: str) -> None:
        match = re.search(
            r"^\s*UPDATE\s+([a-z_][a-z0-9_]*)\s+SET\s+(.+?)(?:\s+WHERE\s+|\s+RETURNING\s+|$)",
            sql,
            re.IGNORECASE | re.DOTALL,
        )
        if not match:
            return
        table = match.group(1).lower()
        columns = [part.split("=", 1)[0].strip().lower() for part in _split_csv(match.group(2))]
        self._assert_columns(table, columns)

    @staticmethod
    def _assert_columns(table: str, columns: Sequence[str]) -> None:
        schema = TABLES.get(table)
        if not schema:
            raise DatabaseSchemaError(f"Unknown table in SQL: {table}.")
        for column in columns:
            if column and column not in schema.columns:
                raise DatabaseSchemaError(f"Unknown column in SQL: {table}.{column}.")
