from typing import Any


class InternalPortalMixin:
    """Type bridge for dependencies supplied by the composed portal service."""

    def __getattr__(self, name: str) -> Any:
        raise AttributeError(name)
