from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class InternalRole(StrEnum):
    STAFF = "staff"
    SHOWROOM_MANAGER = "showroom_manager"
    OPERATIONS_ADMIN = "operations_admin"


@dataclass(frozen=True)
class InternalPrincipal:
    user_id: str
    username: str
    display_name: str
    role: InternalRole
    staff_id: str | None
    showroom_ids: tuple[str, ...]

    def as_dict(self) -> dict:
        return {
            "id": self.user_id,
            "username": self.username,
            "display_name": self.display_name,
            "role": self.role.value,
            "staff_id": self.staff_id,
            "showroom_ids": list(self.showroom_ids),
        }

    def has_role(self, *roles: InternalRole) -> bool:
        return self.role in roles

    def can_access_showroom(self, showroom_id: str) -> bool:
        return self.role is InternalRole.OPERATIONS_ADMIN or showroom_id in self.showroom_ids
