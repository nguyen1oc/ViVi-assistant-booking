from __future__ import annotations

from typing import Any

from src.database import DatabaseIntegrityError
from src.services.booking.common import iso, new_id

from .auth import InternalPrincipal, InternalRole
from .base import InternalPortalMixin
from .errors import InternalPortalError


class InternalResourceManagementMixin(InternalPortalMixin):
    """Explicit admin mutations for showroom and master catalogue resources."""

    def create_showroom(self, principal: InternalPrincipal, *, values: dict[str, Any]) -> dict:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        required = {"code", "name", "address", "latitude", "longitude"}
        if not required.issubset(values) or any(values.get(key) in {None, ""} for key in required):
            raise InternalPortalError("INVALID_INPUT", "Thiếu thông tin showroom bắt buộc.")
        if not -90 <= float(values["latitude"]) <= 90 or not -180 <= float(values["longitude"]) <= 180:
            raise InternalPortalError("INVALID_COORDINATES", "Tọa độ showroom không hợp lệ.")
        now = iso(self.now())
        showroom_id = new_id("showroom")
        try:
            with self.db.transaction(immediate=True) as connection:
                connection.execute(
                    "INSERT INTO showrooms(id,code,name,address,latitude,longitude,phone,email,timezone,region,map_visible,is_active,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        showroom_id,
                        str(values["code"]).strip().upper(),
                        str(values["name"]).strip(),
                        str(values["address"]).strip(),
                        float(values["latitude"]),
                        float(values["longitude"]),
                        values.get("phone"),
                        values.get("email"),
                        values.get("timezone") or "Asia/Ho_Chi_Minh",
                        values.get("region"),
                        int(values.get("map_visible", True)),
                        int(values.get("is_active", True)),
                        now,
                        now,
                    ),
                )
                self._audit(
                    connection,
                    principal,
                    "showroom.created",
                    "showroom",
                    showroom_id,
                    showroom_id,
                    {"code": str(values["code"]).strip().upper(), "name": str(values["name"]).strip()},
                )
        except DatabaseIntegrityError as exc:
            raise InternalPortalError("SHOWROOM_CODE_EXISTS", "Mã showroom đã tồn tại.", status_code=409) from exc
        return self.get_showroom(principal, showroom_id)

    def get_showroom(self, principal: InternalPrincipal, showroom_id: str) -> dict:
        self._assert_scope(principal, showroom_id)
        with self.db.connect() as connection:
            row = connection.execute("SELECT * FROM showrooms WHERE id=?", (showroom_id,)).fetchone()
        if not row:
            raise InternalPortalError("SHOWROOM_NOT_FOUND", "Không tìm thấy showroom.", status_code=404)
        return dict(row)

    def update_showroom(
        self, principal: InternalPrincipal, showroom_id: str, *, changes: dict[str, Any]
    ) -> dict:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        allowed = {"name", "address", "latitude", "longitude", "phone", "email", "timezone", "region", "map_visible", "is_active"}
        unknown = set(changes) - allowed
        if unknown or not changes:
            raise InternalPortalError("INVALID_INPUT", "Không có trường showroom hợp lệ để cập nhật.")
        if "latitude" in changes and not -90 <= float(changes["latitude"]) <= 90:
            raise InternalPortalError("INVALID_COORDINATES", "Vĩ độ showroom không hợp lệ.")
        if "longitude" in changes and not -180 <= float(changes["longitude"]) <= 180:
            raise InternalPortalError("INVALID_COORDINATES", "Kinh độ showroom không hợp lệ.")
        with self.db.transaction(immediate=True) as connection:
            current = connection.execute("SELECT * FROM showrooms WHERE id=?", (showroom_id,)).fetchone()
            if not current:
                raise InternalPortalError("SHOWROOM_NOT_FOUND", "Không tìm thấy showroom.", status_code=404)
            normalized = {
                key: int(value) if key in {"map_visible", "is_active"} else value
                for key, value in changes.items()
            }
            now = iso(self.now())
            connection.execute(
                "UPDATE showrooms SET " + ",".join(f"{key}=?" for key in normalized) + ",updated_at=? WHERE id=?",
                (*normalized.values(), now, showroom_id),
            )
            self._audit(
                connection,
                principal,
                "showroom.updated",
                "showroom",
                showroom_id,
                showroom_id,
                {"old": {key: current[key] for key in normalized}, "new": normalized},
            )
        return self.get_showroom(principal, showroom_id)

    def create_vehicle_model(self, principal: InternalPrincipal, *, values: dict[str, Any]) -> dict:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        for key in ("code", "name", "vehicle_type"):
            if not str(values.get(key) or "").strip():
                raise InternalPortalError("INVALID_INPUT", f"Thiếu trường {key} của model.")
        now = iso(self.now())
        model_id = new_id("model")
        try:
            with self.db.transaction(immediate=True) as connection:
                connection.execute(
                    "INSERT INTO vehicle_models(id,code,name,vehicle_type,required_license_class,license_requirement_note,seat_count,test_drive_eligible,is_active,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        model_id,
                        str(values["code"]).strip().upper(),
                        str(values["name"]).strip(),
                        str(values["vehicle_type"]).strip(),
                        values.get("required_license_class"),
                        values.get("license_requirement_note"),
                        values.get("seat_count"),
                        int(values.get("test_drive_eligible", True)),
                        int(values.get("is_active", True)),
                        now,
                        now,
                    ),
                )
                self._audit(connection, principal, "catalog.model_created", "vehicle_model", model_id, None, {"code": values["code"]})
        except DatabaseIntegrityError as exc:
            raise InternalPortalError("MODEL_CODE_EXISTS", "Mã model đã tồn tại.", status_code=409) from exc
        return self._catalog_model(principal, model_id)

    def update_vehicle_model(
        self, principal: InternalPrincipal, model_id: str, *, changes: dict[str, Any]
    ) -> dict:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        allowed = {"name", "vehicle_type", "required_license_class", "license_requirement_note", "seat_count", "test_drive_eligible", "is_active"}
        if not changes or set(changes) - allowed:
            raise InternalPortalError("INVALID_INPUT", "Không có trường model hợp lệ để cập nhật.")
        normalized = {
            key: int(value) if key in {"test_drive_eligible", "is_active"} else value
            for key, value in changes.items()
        }
        with self.db.transaction(immediate=True) as connection:
            current = connection.execute("SELECT * FROM vehicle_models WHERE id=?", (model_id,)).fetchone()
            if not current:
                raise InternalPortalError("MODEL_NOT_FOUND", "Không tìm thấy model.", status_code=404)
            connection.execute(
                "UPDATE vehicle_models SET " + ",".join(f"{key}=?" for key in normalized) + ",updated_at=? WHERE id=?",
                (*normalized.values(), iso(self.now()), model_id),
            )
            self._audit(connection, principal, "catalog.model_updated", "vehicle_model", model_id, None, {"old": {key: current[key] for key in normalized}, "new": normalized})
        return self._catalog_model(principal, model_id)

    def _catalog_model(self, principal: InternalPrincipal, model_id: str) -> dict:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        with self.db.connect() as connection:
            row = connection.execute("SELECT * FROM vehicle_models WHERE id=?", (model_id,)).fetchone()
        return dict(row)

    def create_vehicle_variant(self, principal: InternalPrincipal, *, values: dict[str, Any]) -> dict:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        for key in ("model_id", "code", "name"):
            if not str(values.get(key) or "").strip():
                raise InternalPortalError("INVALID_INPUT", f"Thiếu trường {key} của variant.")
        now = iso(self.now())
        variant_id = new_id("variant")
        try:
            with self.db.transaction(immediate=True) as connection:
                if not connection.execute("SELECT 1 FROM vehicle_models WHERE id=?", (values["model_id"],)).fetchone():
                    raise InternalPortalError("MODEL_NOT_FOUND", "Không tìm thấy model.", status_code=404)
                connection.execute(
                    "INSERT INTO vehicle_variants(id,model_id,code,name,battery_capacity_kwh,estimated_range_km,motor_power_kw,default_test_drive_minutes,is_active,created_at,updated_at) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        variant_id,
                        values["model_id"],
                        str(values["code"]).strip().upper(),
                        str(values["name"]).strip(),
                        values.get("battery_capacity_kwh"),
                        values.get("estimated_range_km"),
                        values.get("motor_power_kw"),
                        values.get("default_test_drive_minutes"),
                        int(values.get("is_active", True)),
                        now,
                        now,
                    ),
                )
                self._audit(connection, principal, "catalog.variant_created", "vehicle_variant", variant_id, None, {"model_id": values["model_id"], "code": values["code"]})
        except DatabaseIntegrityError as exc:
            raise InternalPortalError("VARIANT_CODE_EXISTS", "Mã variant đã tồn tại trong model.", status_code=409) from exc
        return self._catalog_variant(principal, variant_id)

    def update_vehicle_variant(
        self, principal: InternalPrincipal, variant_id: str, *, changes: dict[str, Any]
    ) -> dict:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        allowed = {"name", "battery_capacity_kwh", "estimated_range_km", "motor_power_kw", "default_test_drive_minutes", "is_active"}
        if not changes or set(changes) - allowed:
            raise InternalPortalError("INVALID_INPUT", "Không có trường variant hợp lệ để cập nhật.")
        normalized = {key: int(value) if key == "is_active" else value for key, value in changes.items()}
        with self.db.transaction(immediate=True) as connection:
            current = connection.execute("SELECT * FROM vehicle_variants WHERE id=?", (variant_id,)).fetchone()
            if not current:
                raise InternalPortalError("VARIANT_NOT_FOUND", "Không tìm thấy variant.", status_code=404)
            connection.execute(
                "UPDATE vehicle_variants SET " + ",".join(f"{key}=?" for key in normalized) + ",updated_at=? WHERE id=?",
                (*normalized.values(), iso(self.now()), variant_id),
            )
            self._audit(connection, principal, "catalog.variant_updated", "vehicle_variant", variant_id, None, {"old": {key: current[key] for key in normalized}, "new": normalized})
        return self._catalog_variant(principal, variant_id)

    def _catalog_variant(self, principal: InternalPrincipal, variant_id: str) -> dict:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        with self.db.connect() as connection:
            row = connection.execute("SELECT * FROM vehicle_variants WHERE id=?", (variant_id,)).fetchone()
        return dict(row)

    def list_vehicle_transfers(self, principal: InternalPrincipal, *, limit: int = 200) -> list[dict]:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        with self.db.connect() as connection:
            rows = connection.execute(
                "SELECT t.*,d.asset_code,source.name from_showroom_name,target.name to_showroom_name "
                "FROM vehicle_transfers t JOIN demo_vehicles d ON d.id=t.demo_vehicle_id "
                "JOIN showrooms source ON source.id=t.from_showroom_id "
                "JOIN showrooms target ON target.id=t.to_showroom_id "
                "ORDER BY COALESCE(t.completed_at,t.requested_at,t.created_at) DESC LIMIT ?",
                (min(max(limit, 1), 500),),
            ).fetchall()
        return [dict(row) for row in rows]
