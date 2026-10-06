"""Database package facade.

The booking services keep using `Database.execute(...)` style calls through this
facade while the concrete adapter can be PostgreSQL or the legacy SQLite test
adapter.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .errors import DatabaseIntegrityError
from .guard import DatabaseSchemaError, QueryGuard
from .postgres import PostgresDatabase
from .sqlite import SQLiteDatabase


class Database:
    def __init__(self, url_or_path: str | Path, *, validate_schema: bool = True) -> None:
        self._path_input = isinstance(url_or_path, Path)
        self.raw_url = str(url_or_path)
        self.guard = QueryGuard(enabled=validate_schema)
        self._adapter = self._build_adapter(self.raw_url)
        self._dialect = "postgres" if not self._path_input and urlparse(self.raw_url).scheme in {"postgres", "postgresql"} else "sqlite"

    @property
    def dialect(self) -> str:
        return self._dialect

    def connect(self):
        return self._adapter.connect()

    def initialize(self) -> None:
        self._adapter.initialize()

    @contextmanager
    def transaction(self, *, immediate: bool = False) -> Iterator[Any]:
        connection = self.connect()
        try:
            if connection.dialect == "sqlite":
                connection.execute("BEGIN IMMEDIATE" if immediate else "BEGIN")
            else:
                connection.execute("BEGIN")
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _build_adapter(self, value: str):
        if self._path_input:
            return SQLiteDatabase(value, guard=self.guard)
        parsed = urlparse(value)
        if parsed.scheme in {"postgres", "postgresql"}:
            return PostgresDatabase(value, guard=self.guard)
        if parsed.scheme == "sqlite":
            return SQLiteDatabase(value.removeprefix("sqlite:///"), guard=self.guard)
        if parsed.scheme == "":
            return SQLiteDatabase(value, guard=self.guard)
        raise RuntimeError(f"Unsupported DATABASE_URL scheme: {parsed.scheme}. Use postgresql:// or sqlite:/// for tests.")


__all__ = ["Database", "DatabaseIntegrityError", "DatabaseSchemaError"]
