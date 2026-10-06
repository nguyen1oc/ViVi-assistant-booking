from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any


class DbRow(Mapping[str, Any]):
    """Mapping row that also supports sqlite-style numeric indexing."""

    def __init__(self, values: Mapping[str, Any]) -> None:
        self._values = dict(values)
        self._ordered = list(self._values.values())

    def __getitem__(self, key: str | int) -> Any:
        if isinstance(key, int):
            return self._ordered[key]
        return self._values[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def keys(self):  # noqa: ANN201 - match sqlite row ergonomics.
        return self._values.keys()


def to_db_row(row: Any) -> DbRow | None:
    if row is None:
        return None
    if isinstance(row, DbRow):
        return row
    if isinstance(row, Mapping):
        return DbRow(row)
    if hasattr(row, "keys"):
        return DbRow({key: row[key] for key in row.keys()})
    raise TypeError(f"Cannot convert row type {type(row)!r}.")

