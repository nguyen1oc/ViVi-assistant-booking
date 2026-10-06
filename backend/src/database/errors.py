from __future__ import annotations


class DatabaseIntegrityError(RuntimeError):
    """Portable integrity error raised by database adapters."""

