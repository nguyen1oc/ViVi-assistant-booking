from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from src.database import Database, DatabaseIntegrityError
from src.services.booking.common import iso, new_id, parse_utc, utcnow

from .auth import InternalPrincipal, InternalRole
from .errors import InternalPortalError
from .notifications import InternalNotificationMixin
from .operations import InternalOperationsMixin, time_ranges_overlap
from .resources import InternalResourceManagementMixin

PASSWORD_ITERATIONS = 310_000
BOOKING_STATUSES = {
    "held",
    "confirmed",
    "expired",
    "cancelled",
    "rescheduled",
    "checked_in",
    "completed",
    "no_show",
}
VEHICLE_STATUSES = {"available", "in_use", "charging", "maintenance", "out_of_service"}
CHARGING_STATUSES = {"not_charging", "charging", "fully_charged", "unknown"}
STAFF_BOOKING_ASSIGNMENT_ROLE = "test_drive_consultant"


def _normalize_username(value: str) -> str:
    return value.strip().casefold()


def _password_digest(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PASSWORD_ITERATIONS).hex()


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise InternalPortalError("INVALID_TIME", "Thời gian phải có múi giờ.")
    return parsed


class InternalPortalService(InternalNotificationMixin, InternalOperationsMixin, InternalResourceManagementMixin):
    def __init__(self, database: Database, *, session_ttl_seconds: int = 28_800, now=utcnow):
        self.db = database
        self.session_ttl_seconds = session_ttl_seconds
        self.now = now

    def create_user(
        self,
        *,
        username: str,
        password: str,
        display_name: str,
        role: str,
        staff_id: str | None = None,
        showroom_ids: list[str] | None = None,
    ) -> dict:
        username = _normalize_username(username)
        if len(username) < 3 or len(username) > 80:
            raise InternalPortalError("INVALID_USERNAME", "Tên đăng nhập phải có từ 3 đến 80 ký tự.")
        if len(password) < 8:
            raise InternalPortalError("WEAK_PASSWORD", "Mật khẩu nội bộ phải có ít nhất 8 ký tự.")
        try:
            resolved_role = InternalRole(role)
        except ValueError as exc:
            raise InternalPortalError("INVALID_ROLE", "Role nội bộ không hợp lệ.") from exc
        requested_showrooms = tuple(dict.fromkeys(showroom_ids or []))
        now = iso(self.now())
        user_id = new_id("iuser")
        salt = secrets.token_bytes(16)
        with self.db.transaction(immediate=True) as connection:
            staff_id, requested_showrooms = self._validate_account_binding(
                connection,
                role=resolved_role,
                staff_id=staff_id,
                showroom_ids=requested_showrooms,
            )
            if staff_id and connection.execute(
                "SELECT 1 FROM internal_users WHERE staff_id=?", (staff_id,)
            ).fetchone():
                raise InternalPortalError(
                    "STAFF_ACCOUNT_EXISTS", "Nhân viên này đã có tài khoản nội bộ đang hoạt động.", status_code=409
                )
            try:
                connection.execute(
                    "INSERT INTO internal_users(id,username,display_name,password_salt,password_hash,role,staff_id,is_active,last_login_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        user_id,
                        username,
                        display_name.strip() or username,
                        salt.hex(),
                        _password_digest(password, salt),
                        resolved_role.value,
                        staff_id,
                        1,
                        None,
                        now,
                        now,
                    ),
                )
            except DatabaseIntegrityError as exc:
                raise InternalPortalError("USERNAME_EXISTS", "Tên đăng nhập đã tồn tại.", status_code=409) from exc
            connection.executemany(
                "INSERT INTO internal_user_showrooms(user_id,showroom_id,created_at) VALUES(?,?,?)",
                [(user_id, showroom_id, now) for showroom_id in requested_showrooms],
            )
        return {
            "id": user_id,
            "username": username,
            "display_name": display_name.strip() or username,
            "role": resolved_role.value,
            "staff_id": staff_id,
            "showroom_ids": list(requested_showrooms),
        }

    @staticmethod
    def _active_staff(connection, staff_id: str | None):
        if not staff_id:
            return None
        return connection.execute(
            "SELECT id,showroom_id,status,is_active FROM sales_staff "
            "WHERE id=? AND status='active' AND is_active=1",
            (staff_id,),
        ).fetchone()

    def _validate_account_binding(
        self,
        connection,
        *,
        role: InternalRole,
        staff_id: str | None,
        showroom_ids: tuple[str, ...],
        require_active_staff: bool = True,
    ) -> tuple[str | None, tuple[str, ...]]:
        requested_showrooms = tuple(dict.fromkeys(item for item in showroom_ids if item))
        if role is InternalRole.STAFF:
            staff = (
                self._active_staff(connection, staff_id)
                if require_active_staff
                else connection.execute(
                    "SELECT id,showroom_id,status,is_active FROM sales_staff WHERE id=?", (staff_id,)
                ).fetchone()
            )
            if not staff:
                raise InternalPortalError(
                    "STAFF_REQUIRED", "Tài khoản staff phải liên kết với nhân viên đang hoạt động."
                )
            derived_scope = (staff["showroom_id"],)
            if requested_showrooms and requested_showrooms != derived_scope:
                raise InternalPortalError(
                    "STAFF_SCOPE_DERIVED",
                    "Phạm vi staff được xác định từ showroom hiện tại của nhân viên và không thể cấp thêm.",
                )
            return staff_id, derived_scope

        if staff_id:
            raise InternalPortalError(
                "ROLE_SCOPE_MISMATCH", "Chỉ tài khoản staff mới được liên kết với hồ sơ nhân viên."
            )
        if role is InternalRole.OPERATIONS_ADMIN:
            if requested_showrooms:
                raise InternalPortalError(
                    "ROLE_SCOPE_MISMATCH", "Operations Admin luôn có phạm vi toàn hệ thống."
                )
            return None, ()
        if len(requested_showrooms) != 1:
            raise InternalPortalError(
                "MANAGER_SINGLE_SHOWROOM_REQUIRED", "Tài khoản quản lý phải được cấp đúng một showroom."
            )
        for showroom_id in requested_showrooms:
            if not connection.execute(
                "SELECT 1 FROM showrooms WHERE id=? AND is_active=1", (showroom_id,)
            ).fetchone():
                raise InternalPortalError("SHOWROOM_NOT_FOUND", f"Không tìm thấy showroom hoạt động {showroom_id}.")
        return None, requested_showrooms

    def create_managed_user(
        self,
        principal: InternalPrincipal,
        *,
        username: str,
        password: str,
        display_name: str,
        role: str,
        staff_id: str | None = None,
        showroom_ids: list[str] | None = None,
    ) -> dict:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        user = self.create_user(
            username=username,
            password=password,
            display_name=display_name,
            role=role,
            staff_id=staff_id,
            showroom_ids=showroom_ids,
        )
        with self.db.transaction(immediate=True) as connection:
            self._audit(
                connection,
                principal,
                "internal_user.created",
                "internal_user",
                user["id"],
                user["showroom_ids"][0] if len(user["showroom_ids"]) == 1 else None,
                {
                    "username": user["username"],
                    "role": user["role"],
                    "staff_id": user["staff_id"],
                    "showroom_ids": user["showroom_ids"],
                },
            )
        return user

    def list_internal_users(
        self,
        principal: InternalPrincipal,
        *,
        role: str | None = None,
        showroom_id: str | None = None,
        is_active: bool | None = None,
    ) -> list[dict]:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        if role:
            try:
                InternalRole(role)
            except ValueError as exc:
                raise InternalPortalError("INVALID_ROLE", "Role nội bộ không hợp lệ.") from exc
        with self.db.connect() as connection:
            rows = connection.execute(
                "SELECT u.id,u.username,u.display_name,u.role,u.staff_id,u.is_active,u.last_login_at,"
                "u.created_at,s.full_name staff_name,s.showroom_id staff_showroom_id,"
                "s.status staff_status,s.is_active staff_active FROM internal_users u "
                "LEFT JOIN sales_staff s ON s.id=u.staff_id ORDER BY u.created_at DESC,u.username"
            ).fetchall()
            scope_rows = connection.execute(
                "SELECT user_id,showroom_id FROM internal_user_showrooms ORDER BY showroom_id"
            ).fetchall()
        scopes: dict[str, list[str]] = {}
        for scope in scope_rows:
            scopes.setdefault(scope["user_id"], []).append(scope["showroom_id"])
        result = []
        for row in rows:
            item = dict(row)
            staff_showroom_id = item.pop("staff_showroom_id")
            staff_active = item.pop("staff_active")
            item["is_active"] = bool(item["is_active"])
            item["staff_is_active"] = (
                bool(staff_active) and item["staff_status"] == "active" if item["staff_id"] else None
            )
            item["showroom_ids"] = (
                [staff_showroom_id]
                if item["role"] == InternalRole.STAFF.value and staff_showroom_id
                else scopes.get(item["id"], [])
            )
            if role and item["role"] != role:
                continue
            if is_active is not None and item["is_active"] is not is_active:
                continue
            if showroom_id and showroom_id not in item["showroom_ids"]:
                continue
            result.append(item)
        return result

    def update_managed_user(
        self,
        principal: InternalPrincipal,
        user_id: str,
        *,
        changes: dict[str, Any],
    ) -> dict:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        allowed = {"display_name", "role", "staff_id", "showroom_ids", "is_active"}
        unknown = set(changes) - allowed
        if unknown:
            raise InternalPortalError("INVALID_INPUT", f"Trường cập nhật không hợp lệ: {', '.join(sorted(unknown))}.")
        if not changes:
            raise InternalPortalError("NO_CHANGES", "Không có thay đổi nào được gửi lên.")

        now = iso(self.now())
        with self.db.transaction(immediate=True) as connection:
            lock = " FOR UPDATE" if connection.dialect == "postgres" else ""
            current = connection.execute(
                "SELECT * FROM internal_users WHERE id=?" + lock, (user_id,)
            ).fetchone()
            if not current:
                raise InternalPortalError("USER_NOT_FOUND", "Không tìm thấy tài khoản nội bộ.", status_code=404)
            current_scopes = tuple(
                row["showroom_id"]
                for row in connection.execute(
                    "SELECT showroom_id FROM internal_user_showrooms WHERE user_id=? ORDER BY showroom_id",
                    (user_id,),
                )
            )
            try:
                role = InternalRole(changes.get("role", current["role"]))
            except (TypeError, ValueError) as exc:
                raise InternalPortalError("INVALID_ROLE", "Role nội bộ không hợp lệ.") from exc
            staff_id = changes.get("staff_id", current["staff_id"])
            is_active = bool(changes.get("is_active", current["is_active"]))
            requested_showrooms = tuple(
                changes.get(
                    "showroom_ids",
                    () if role is InternalRole.STAFF else current_scopes,
                )
                or ()
            )
            staff_id, requested_showrooms = self._validate_account_binding(
                connection,
                role=role,
                staff_id=staff_id,
                showroom_ids=requested_showrooms,
                require_active_staff=is_active,
            )
            if staff_id and connection.execute(
                "SELECT 1 FROM internal_users WHERE staff_id=? AND id<>?", (staff_id, user_id)
            ).fetchone():
                raise InternalPortalError(
                    "STAFF_ACCOUNT_EXISTS", "Nhân viên này đã có tài khoản nội bộ.", status_code=409
                )

            display_value = changes.get("display_name", current["display_name"])
            display_name = str(display_value).strip() if display_value is not None else ""
            if not display_name or len(display_name) > 120:
                raise InternalPortalError("INVALID_DISPLAY_NAME", "Tên hiển thị phải có từ 1 đến 120 ký tự.")
            current_role = InternalRole(current["role"])
            removing_active_admin = (
                current_role is InternalRole.OPERATIONS_ADMIN
                and bool(current["is_active"])
                and (role is not InternalRole.OPERATIONS_ADMIN or not is_active)
            )
            if removing_active_admin:
                active_admins = connection.execute(
                    "SELECT id FROM internal_users WHERE role=? AND is_active=1" + lock,
                    (InternalRole.OPERATIONS_ADMIN.value,),
                ).fetchall()
                if not any(row["id"] != user_id for row in active_admins):
                    raise InternalPortalError(
                        "LAST_ADMIN_REQUIRED",
                        "Không thể khóa hoặc hạ quyền Operations Admin đang hoạt động cuối cùng.",
                        status_code=409,
                    )

            security_changed = (
                role.value != current["role"]
                or staff_id != current["staff_id"]
                or requested_showrooms != current_scopes
                or is_active != bool(current["is_active"])
            )
            connection.execute(
                "UPDATE internal_users SET display_name=?,role=?,staff_id=?,is_active=?,updated_at=? WHERE id=?",
                (display_name, role.value, staff_id, int(is_active), now, user_id),
            )
            connection.execute("DELETE FROM internal_user_showrooms WHERE user_id=?", (user_id,))
            connection.executemany(
                "INSERT INTO internal_user_showrooms(user_id,showroom_id,created_at) VALUES(?,?,?)",
                [(user_id, showroom_id, now) for showroom_id in requested_showrooms],
            )
            if security_changed:
                connection.execute(
                    "UPDATE internal_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL",
                    (now, user_id),
                )
            self._audit(
                connection,
                principal,
                "internal_user.updated",
                "internal_user",
                user_id,
                None,
                {
                    "role": role.value,
                    "staff_id": staff_id,
                    "showroom_ids": list(requested_showrooms),
                    "is_active": is_active,
                    "sessions_revoked": security_changed,
                },
            )
        return next(item for item in self.list_internal_users(principal) if item["id"] == user_id)

    def reset_managed_user_password(
        self, principal: InternalPrincipal, user_id: str, *, password: str
    ) -> dict:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        if len(password) < 8:
            raise InternalPortalError("WEAK_PASSWORD", "Mật khẩu nội bộ phải có ít nhất 8 ký tự.")
        now = iso(self.now())
        salt = secrets.token_bytes(16)
        with self.db.transaction(immediate=True) as connection:
            if not connection.execute("SELECT 1 FROM internal_users WHERE id=?", (user_id,)).fetchone():
                raise InternalPortalError("USER_NOT_FOUND", "Không tìm thấy tài khoản nội bộ.", status_code=404)
            connection.execute(
                "UPDATE internal_users SET password_salt=?,password_hash=?,updated_at=? WHERE id=?",
                (salt.hex(), _password_digest(password, salt), now, user_id),
            )
            revoked = connection.execute(
                "UPDATE internal_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL",
                (now, user_id),
            ).rowcount
            self._audit(
                connection,
                principal,
                "internal_user.password_reset",
                "internal_user",
                user_id,
                None,
                {"sessions_revoked": revoked},
            )
        return {"id": user_id, "sessions_revoked": revoked}

    def revoke_managed_user_sessions(self, principal: InternalPrincipal, user_id: str) -> dict:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        now = iso(self.now())
        with self.db.transaction(immediate=True) as connection:
            if not connection.execute("SELECT 1 FROM internal_users WHERE id=?", (user_id,)).fetchone():
                raise InternalPortalError("USER_NOT_FOUND", "Không tìm thấy tài khoản nội bộ.", status_code=404)
            revoked = connection.execute(
                "UPDATE internal_sessions SET revoked_at=? WHERE user_id=? AND revoked_at IS NULL",
                (now, user_id),
            ).rowcount
            self._audit(
                connection,
                principal,
                "internal_user.sessions_revoked",
                "internal_user",
                user_id,
                None,
                {"sessions_revoked": revoked},
            )
        return {"id": user_id, "sessions_revoked": revoked}

    def login(self, username: str, password: str) -> dict:
        normalized = _normalize_username(username)
        with self.db.transaction(immediate=True) as connection:
            row = connection.execute("SELECT * FROM internal_users WHERE username=?", (normalized,)).fetchone()
            if row:
                expected = _password_digest(password, bytes.fromhex(row["password_salt"]))
                valid = bool(row["is_active"]) and hmac.compare_digest(expected, row["password_hash"])
            else:
                _password_digest(password, b"\0" * 16)
                valid = False
            if not valid:
                raise InternalPortalError(
                    "INVALID_CREDENTIALS", "Tên đăng nhập hoặc mật khẩu không đúng.", status_code=401
                )
            self._assert_account_eligible(connection, row)
            now_value = self.now()
            expires_at = now_value + timedelta(seconds=self.session_ttl_seconds)
            token = secrets.token_urlsafe(32)
            connection.execute(
                "INSERT INTO internal_sessions(token_hash,user_id,expires_at,revoked_at,created_at) VALUES(?,?,?,?,?)",
                (_token_digest(token), row["id"], iso(expires_at), None, iso(now_value)),
            )
            connection.execute(
                "UPDATE internal_users SET last_login_at=?,updated_at=? WHERE id=?",
                (iso(now_value), iso(now_value), row["id"]),
            )
        principal = self._principal_for_user(row["id"])
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_at": iso(expires_at),
            "user": principal.as_dict(),
        }

    def authenticate(self, token: str) -> InternalPrincipal:
        if not token or len(token) > 512:
            raise InternalPortalError("AUTH_REQUIRED", "Cần đăng nhập để tiếp tục.", status_code=401)
        with self.db.connect() as connection:
            session = connection.execute(
                "SELECT s.user_id FROM internal_sessions s JOIN internal_users u ON u.id=s.user_id "
                "WHERE s.token_hash=? AND s.revoked_at IS NULL AND s.expires_at>? AND u.is_active=1",
                (_token_digest(token), iso(self.now())),
            ).fetchone()
        if not session:
            raise InternalPortalError("SESSION_INVALID", "Phiên đăng nhập đã hết hạn.", status_code=401)
        return self._principal_for_user(session["user_id"])

    def logout(self, token: str) -> None:
        with self.db.transaction(immediate=True) as connection:
            connection.execute(
                "UPDATE internal_sessions SET revoked_at=? WHERE token_hash=? AND revoked_at IS NULL",
                (iso(self.now()), _token_digest(token)),
            )

    def _principal_for_user(self, user_id: str) -> InternalPrincipal:
        with self.db.connect() as connection:
            row = connection.execute(
                "SELECT id,username,display_name,role,staff_id,is_active FROM internal_users WHERE id=?", (user_id,)
            ).fetchone()
            if not row or not row["is_active"]:
                raise InternalPortalError("SESSION_INVALID", "Tài khoản không còn hoạt động.", status_code=401)
            role = InternalRole(row["role"])
            if role is InternalRole.STAFF:
                staff = self._active_staff(connection, row["staff_id"])
                if not staff:
                    raise InternalPortalError(
                        "SESSION_INVALID", "Hồ sơ nhân viên không còn hoạt động.", status_code=401
                    )
                scopes = {staff["showroom_id"]}
            elif role is InternalRole.SHOWROOM_MANAGER:
                scopes = {
                    item["showroom_id"]
                    for item in connection.execute(
                        "SELECT ius.showroom_id FROM internal_user_showrooms ius "
                        "JOIN showrooms sh ON sh.id=ius.showroom_id AND sh.is_active=1 WHERE ius.user_id=?",
                        (user_id,),
                    )
                }
                if len(scopes) != 1:
                    raise InternalPortalError(
                        "SESSION_INVALID", "Tài khoản quản lý phải có đúng một showroom hoạt động.", status_code=401
                    )
            else:
                scopes = set()
        return InternalPrincipal(
            user_id=row["id"],
            username=row["username"],
            display_name=row["display_name"],
            role=role,
            staff_id=row["staff_id"],
            showroom_ids=tuple(sorted(scopes)),
        )

    def _assert_account_eligible(self, connection, row) -> None:
        role = InternalRole(row["role"])
        if role is InternalRole.STAFF and not self._active_staff(connection, row["staff_id"]):
            raise InternalPortalError(
                "ACCOUNT_INACTIVE", "Hồ sơ nhân viên không còn hoạt động.", status_code=403
            )
        if role is InternalRole.SHOWROOM_MANAGER and connection.execute(
            "SELECT count(*) FROM internal_user_showrooms ius "
            "JOIN showrooms sh ON sh.id=ius.showroom_id AND sh.is_active=1 "
            "WHERE ius.user_id=?",
            (row["id"],),
        ).fetchone()[0] != 1:
            raise InternalPortalError(
                "ACCOUNT_SCOPE_INVALID", "Tài khoản quản lý phải có đúng một showroom hoạt động.", status_code=403
            )

    @staticmethod
    def require_roles(principal: InternalPrincipal, *roles: InternalRole) -> None:
        if principal.role not in roles:
            raise InternalPortalError("ACCESS_DENIED", "Bạn không có quyền thực hiện thao tác này.", status_code=403)

    @staticmethod
    def _scope_clause(principal: InternalPrincipal, *, slot_alias: str = "s") -> tuple[str, list[Any]]:
        if principal.role is InternalRole.OPERATIONS_ADMIN:
            return "1=1", []
        if principal.role is InternalRole.STAFF:
            if not principal.staff_id:
                return "1=0", []
            return (
                f"EXISTS (SELECT 1 FROM slot_sales_assignments ssa "
                "JOIN sales_staff assigned_staff ON assigned_staff.id=ssa.sales_staff_id "
                f"WHERE ssa.slot_id={slot_alias}.id AND ssa.sales_staff_id=? "
                "AND ssa.assignment_role=? AND ssa.status='assigned' "
                "AND assigned_staff.status='active' AND assigned_staff.is_active=1)",
                [principal.staff_id, STAFF_BOOKING_ASSIGNMENT_ROLE],
            )
        if not principal.showroom_ids:
            return "1=0", []
        marks = ",".join("?" for _ in principal.showroom_ids)
        return f"{slot_alias}.showroom_id IN ({marks})", list(principal.showroom_ids)

    def dashboard(self, principal: InternalPrincipal) -> dict:
        scope, params = self._scope_clause(principal)
        scheduled_shift_total = 0
        now_value = self.now()
        local_timezone = ZoneInfo("Asia/Ho_Chi_Minh")
        today = now_value.astimezone(local_timezone).date()
        capacity_dates = [today + timedelta(days=offset) for offset in range(7)]
        with self.db.connect() as connection:
            booking_counts = {
                row["status"]: row["total"]
                for row in connection.execute(
                    f"SELECT b.status,count(*) total FROM bookings b JOIN test_drive_slots s ON s.id=b.slot_id WHERE {scope} GROUP BY b.status",
                    params,
                )
            }
            slot_counts = {
                row["status"]: row["total"]
                for row in connection.execute(
                    f"SELECT s.status,count(*) total FROM test_drive_slots s WHERE {scope} GROUP BY s.status", params
                )
            }
            scoped_showrooms = self._showrooms_for_principal(connection, principal, include_inactive=True)
            showroom_ids = [row["id"] for row in scoped_showrooms]
            active_showroom_total = sum(bool(row["is_active"]) for row in scoped_showrooms)
            scoped_booking_times = connection.execute(
                f"SELECT b.status,s.start_at FROM bookings b "
                f"JOIN test_drive_slots s ON s.id=b.slot_id WHERE {scope}",
                params,
            ).fetchall()
            scoped_slot_times = connection.execute(
                f"SELECT s.status,s.start_at FROM test_drive_slots s WHERE {scope} "
                "AND substr(s.start_at,1,10)>=? AND substr(s.start_at,1,10)<=?",
                (*params, capacity_dates[0].isoformat(), capacity_dates[-1].isoformat()),
            ).fetchall()
            trend_start = today - timedelta(days=6)
            trend_dates = [trend_start + timedelta(days=offset) for offset in range(14)]
            booking_trend = {
                day: {"date": day.isoformat(), "total": 0, "completed": 0, "no_show": 0, "cancelled": 0}
                for day in trend_dates
            }
            for row in scoped_booking_times:
                booking_day = parse_utc(row["start_at"]).astimezone(local_timezone).date()
                point = booking_trend.get(booking_day)
                if point:
                    point["total"] += 1
                    if row["status"] in {"completed", "no_show", "cancelled"}:
                        point[row["status"]] += 1

            slot_utilization = {
                day: {
                    "date": day.isoformat(),
                    "total": 0,
                    "booked": 0,
                    "available": 0,
                    "blocked": 0,
                    "utilization_percent": 0,
                }
                for day in capacity_dates
            }
            for row in scoped_slot_times:
                slot_day = parse_utc(row["start_at"]).astimezone(local_timezone).date()
                point = slot_utilization.get(slot_day)
                if not point:
                    continue
                point["total"] += 1
                if row["status"] in {"booked", "held"}:
                    point["booked"] += 1
                elif row["status"] == "blocked":
                    point["blocked"] += 1
                else:
                    point["available"] += 1
            for point in slot_utilization.values():
                usable_capacity = point["total"] - point["blocked"]
                point["utilization_percent"] = (
                    round(point["booked"] * 100 / usable_capacity) if usable_capacity > 0 else 0
                )
            bookings_today = sum(
                parse_utc(row["start_at"]).astimezone(local_timezone).date() == today
                for row in scoped_booking_times
            )
            upcoming_bookings = sum(
                row["status"] in {"confirmed", "checked_in"}
                and parse_utc(row["start_at"]) >= now_value
                for row in scoped_booking_times
            )
            completed_booking_total = booking_counts.get("completed", 0)
            no_show_booking_total = booking_counts.get("no_show", 0)
            if principal.role is InternalRole.STAFF:
                staff_total = 1 if principal.staff_id else 0
                vehicle_total = 0
                if principal.staff_id:
                    scheduled_shift_total = sum(
                        parse_utc(row["start_at"]).astimezone(local_timezone).date() == today
                        for row in connection.execute(
                            "SELECT start_at FROM staff_shifts "
                            "WHERE sales_staff_id=? AND status='scheduled'",
                            (principal.staff_id,),
                        )
                    )
            elif principal.role is InternalRole.OPERATIONS_ADMIN:
                staff_total = connection.execute("SELECT count(*) FROM sales_staff WHERE is_active=1").fetchone()[0]
                vehicle_total = connection.execute("SELECT count(*) FROM demo_vehicles WHERE is_active=1").fetchone()[0]
            elif showroom_ids:
                marks = ",".join("?" for _ in showroom_ids)
                staff_total = connection.execute(
                    f"SELECT count(*) FROM sales_staff WHERE is_active=1 AND showroom_id IN ({marks})", showroom_ids
                ).fetchone()[0]
                vehicle_total = connection.execute(
                    f"SELECT count(*) FROM demo_vehicles WHERE is_active=1 AND showroom_id IN ({marks})", showroom_ids
                ).fetchone()[0]
            else:
                staff_total = vehicle_total = 0
            if principal.role is InternalRole.STAFF:
                available_vehicle_total = unavailable_vehicle_total = 0
                staff_on_duty_total = scheduled_shift_total
                staff_unavailable_total = sum(
                    parse_utc(row["start_at"]) <= now_value < parse_utc(row["end_at"])
                    for row in connection.execute(
                        "SELECT start_at,end_at FROM staff_unavailability WHERE sales_staff_id=?",
                        (principal.staff_id,),
                    )
                )
            else:
                vehicle_where = ["is_active=1"]
                vehicle_params: list[Any] = []
                staff_params: list[Any] = []
                if principal.role is InternalRole.SHOWROOM_MANAGER:
                    vehicle_where.append("showroom_id=?")
                    vehicle_params.append(principal.showroom_ids[0])
                    staff_params.append(principal.showroom_ids[0])
                available_vehicle_total = connection.execute(
                    f"SELECT count(*) FROM demo_vehicles WHERE {' AND '.join(vehicle_where)} AND operational_status='available'",
                    vehicle_params,
                ).fetchone()[0]
                maintenance_vehicle_total = connection.execute(
                    f"SELECT count(*) FROM demo_vehicles WHERE {' AND '.join(vehicle_where)} AND operational_status='maintenance'",
                    vehicle_params,
                ).fetchone()[0]
                unavailable_vehicle_total = max(0, vehicle_total - available_vehicle_total)
                on_duty_rows = connection.execute(
                    "SELECT sales_staff_id,start_at,end_at FROM staff_shifts WHERE status='scheduled'"
                    + (" AND showroom_id=?" if principal.role is InternalRole.SHOWROOM_MANAGER else ""),
                    staff_params,
                )
                staff_on_duty_total = len(
                    {
                        row["sales_staff_id"]
                        for row in on_duty_rows
                        if parse_utc(row["start_at"]) <= now_value < parse_utc(row["end_at"])
                    }
                )
                unavailable_rows = connection.execute(
                    "SELECT sales_staff_id,start_at,end_at FROM staff_unavailability WHERE 1=1"
                    + (" AND showroom_id=?" if principal.role is InternalRole.SHOWROOM_MANAGER else ""),
                    staff_params,
                )
                staff_unavailable_total = len(
                    {
                        row["sales_staff_id"]
                        for row in unavailable_rows
                        if parse_utc(row["start_at"]) <= now_value < parse_utc(row["end_at"])
                    }
                )
            if principal.role is InternalRole.STAFF:
                maintenance_vehicle_total = 0
            manager_total = (
                connection.execute(
                    "SELECT count(*) FROM internal_users WHERE role='showroom_manager' AND is_active=1"
                ).fetchone()[0]
                if principal.role is InternalRole.OPERATIONS_ADMIN
                else 0
            )
            vehicle_transfer_total = (
                connection.execute("SELECT count(*) FROM vehicle_transfers").fetchone()[0]
                if principal.role is InternalRole.OPERATIONS_ADMIN
                else 0
            )
        return {
            "booking_counts": booking_counts,
            "slot_counts": slot_counts,
            "showroom_total": len(scoped_showrooms),
            "active_showroom_total": active_showroom_total,
            "staff_total": staff_total,
            "vehicle_total": vehicle_total,
            "scheduled_shift_total": scheduled_shift_total,
            "bookings_today": bookings_today,
            "upcoming_bookings": upcoming_bookings,
            "available_vehicle_total": available_vehicle_total,
            "unavailable_vehicle_total": unavailable_vehicle_total,
            "maintenance_vehicle_total": maintenance_vehicle_total,
            "staff_on_duty_total": staff_on_duty_total,
            "staff_unavailable_total": staff_unavailable_total,
            "completed_booking_total": completed_booking_total,
            "no_show_booking_total": no_show_booking_total,
            "manager_total": manager_total,
            "vehicle_transfer_total": vehicle_transfer_total,
            "booking_trend": list(booking_trend.values()),
            "slot_utilization": list(slot_utilization.values()),
            "recent_bookings": self.list_bookings(principal, limit=8)["items"],
            "recent_audit_events": (
                self.list_audit_events(principal, limit=8)
                if principal.role is not InternalRole.STAFF
                else []
            ),
            "generated_at": iso(self.now()),
        }

    def list_bookings(
        self,
        principal: InternalPrincipal,
        *,
        booking_id: str | None = None,
        status: str | None = None,
        showroom_id: str | None = None,
        date: str | None = None,
        staff_id: str | None = None,
        vehicle_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        if status and status not in BOOKING_STATUSES:
            raise InternalPortalError("INVALID_STATUS", "Trạng thái booking không hợp lệ.")
        scope, params = self._scope_clause(principal)
        where = [scope]
        if booking_id:
            where.append("b.id=?")
            params.append(booking_id)
        if showroom_id:
            if not principal.can_access_showroom(showroom_id):
                raise InternalPortalError("ACCESS_DENIED", "Showroom nằm ngoài phạm vi của bạn.", status_code=403)
            where.append("s.showroom_id=?")
            params.append(showroom_id)
        if status:
            where.append("b.status=?")
            params.append(status)
        if date:
            where.append("substr(s.start_at,1,10)=?")
            params.append(date)
        if staff_id:
            if principal.role is InternalRole.STAFF and staff_id != principal.staff_id:
                raise InternalPortalError("ACCESS_DENIED", "Bạn chỉ được xem booking của mình.", status_code=403)
            where.append(
                "EXISTS (SELECT 1 FROM slot_sales_assignments filter_assignment "
                "WHERE filter_assignment.slot_id=s.id AND filter_assignment.sales_staff_id=? "
                "AND filter_assignment.assignment_role=? AND filter_assignment.status='assigned')"
            )
            params.extend([staff_id, STAFF_BOOKING_ASSIGNMENT_ROLE])
        if vehicle_id:
            where.append("s.demo_vehicle_id=?")
            params.append(vehicle_id)
        clause = " AND ".join(where)
        with self.db.connect() as connection:
            total = connection.execute(
                f"SELECT count(*) FROM bookings b JOIN test_drive_slots s ON s.id=b.slot_id WHERE {clause}", params
            ).fetchone()[0]
            rows = connection.execute(
                f"""SELECT b.id,b.booking_code,b.status,b.source_channel,b.version,b.created_at,b.updated_at,
                b.customer_note,b.internal_note,s.id slot_id,s.start_at,s.end_at,s.showroom_id,s.demo_vehicle_id,
                sh.code showroom_code,sh.name showroom_name,d.asset_code,d.plate_number,
                d.operational_status vehicle_operational_status,d.battery_soc vehicle_battery_soc,
                m.code vehicle_model,v.name vehicle_variant,
                bp.full_name booker_name,bp.phone booker_phone,bp.email booker_email,
                dp.full_name driver_name,dp.phone driver_phone,dp.email driver_email,bd.license_check_status,
                (SELECT ssa.sales_staff_id FROM slot_sales_assignments ssa WHERE ssa.slot_id=s.id
                AND ssa.assignment_role='test_drive_consultant' AND ssa.status='assigned' LIMIT 1) assigned_staff_id,
                (SELECT assigned.full_name FROM slot_sales_assignments ssa JOIN sales_staff assigned ON assigned.id=ssa.sales_staff_id
                WHERE ssa.slot_id=s.id AND ssa.assignment_role='test_drive_consultant' AND ssa.status='assigned' LIMIT 1) assigned_staff_name
                FROM bookings b JOIN test_drive_slots s ON s.id=b.slot_id
                JOIN showrooms sh ON sh.id=s.showroom_id JOIN demo_vehicles d ON d.id=s.demo_vehicle_id
                JOIN vehicle_variants v ON v.id=d.variant_id JOIN vehicle_models m ON m.id=v.model_id
                LEFT JOIN people bp ON bp.id=b.booker_person_id LEFT JOIN people dp ON dp.id=b.driver_person_id
                LEFT JOIN booking_driver_details bd ON bd.booking_id=b.id
                WHERE {clause} ORDER BY s.start_at DESC,b.updated_at DESC LIMIT ? OFFSET ?""",
                (*params, min(max(limit, 1), 200), max(offset, 0)),
            ).fetchall()
        return {"items": [dict(row) for row in rows], "total": total, "limit": limit, "offset": offset}

    def get_booking(self, principal: InternalPrincipal, booking_id: str) -> dict:
        result = self.list_bookings(principal, booking_id=booking_id, limit=1)
        if not result["items"]:
            raise InternalPortalError(
                "BOOKING_NOT_FOUND",
                "Không tìm thấy booking trong phạm vi được phép.",
                status_code=404,
            )
        booking = result["items"][0]
        booking["customer_profile"] = self._customer_profile(principal, booking_id)
        return booking

    def _customer_profile(self, principal: InternalPrincipal, booking_id: str) -> dict | None:
        """Return factual customer context visible inside the principal's booking scope.

        A new ``people`` row can be created for each booking, so history is matched by
        the current driver's normalized phone/email as well as by person id. The
        booking scope is applied again to the history query to prevent customer data
        from another showroom or another staff assignment leaking through the
        profile view.
        """
        scope, scope_params = self._scope_clause(principal)
        with self.db.connect() as connection:
            current = connection.execute(
                "SELECT b.booker_person_id,b.driver_person_id,"
                "bp.full_name booker_name,bp.phone booker_phone,bp.email booker_email,"
                "bp.preferred_channel booker_preferred_channel,bp.created_at booker_created_at,"
                "bp.normalized_phone booker_normalized_phone,bp.normalized_email booker_normalized_email,"
                "dp.full_name driver_name,dp.phone driver_phone,dp.email driver_email,"
                "dp.preferred_channel driver_preferred_channel,dp.created_at driver_created_at,"
                "dp.normalized_phone driver_normalized_phone,dp.normalized_email driver_normalized_email,"
                "bd.has_driving_license,bd.declared_license_class,bd.required_license_class,"
                "bd.validity_acknowledged,bd.license_check_status,bd.checked_at,bd.rejection_reason "
                "FROM bookings b LEFT JOIN people bp ON bp.id=b.booker_person_id "
                "LEFT JOIN people dp ON dp.id=b.driver_person_id "
                "LEFT JOIN booking_driver_details bd ON bd.booking_id=b.id WHERE b.id=?",
                (booking_id,),
            ).fetchone()
            if not current:
                return None

            customer_person_id = current["driver_person_id"] or current["booker_person_id"]
            if not customer_person_id:
                return None
            normalized_phone = current["driver_normalized_phone"] or current["booker_normalized_phone"]
            normalized_email = current["driver_normalized_email"] or current["booker_normalized_email"]
            identity_clauses = ["b.driver_person_id=?", "b.booker_person_id=?"]
            identity_params: list[Any] = [customer_person_id, customer_person_id]
            if normalized_phone:
                identity_clauses.append("(dp.normalized_phone=? OR bp.normalized_phone=?)")
                identity_params.extend([normalized_phone, normalized_phone])
            if normalized_email:
                identity_clauses.append("(dp.normalized_email=? OR bp.normalized_email=?)")
                identity_params.extend([normalized_email, normalized_email])

            history_rows = connection.execute(
                f"""SELECT b.id,b.booking_code,b.status,b.customer_note,b.created_at,
                s.start_at,s.end_at,sh.name showroom_name,m.code vehicle_model,v.name vehicle_variant
                FROM bookings b JOIN test_drive_slots s ON s.id=b.slot_id
                JOIN showrooms sh ON sh.id=s.showroom_id JOIN demo_vehicles d ON d.id=s.demo_vehicle_id
                JOIN vehicle_variants v ON v.id=d.variant_id JOIN vehicle_models m ON m.id=v.model_id
                LEFT JOIN people bp ON bp.id=b.booker_person_id LEFT JOIN people dp ON dp.id=b.driver_person_id
                WHERE {scope} AND ({' OR '.join(identity_clauses)})
                AND b.status IN ('confirmed','checked_in','completed','no_show','cancelled','rescheduled')
                ORDER BY s.start_at DESC,b.updated_at DESC""",
                (*scope_params, *identity_params),
            ).fetchall()

        history = [dict(row) for row in history_rows]
        model_counts: dict[str, int] = {}
        for item in history:
            model_counts[item["vehicle_model"]] = model_counts.get(item["vehicle_model"], 0) + 1
        vehicle_interests = [
            {"model": model, "booking_count": count}
            for model, count in sorted(model_counts.items(), key=lambda pair: (-pair[1], pair[0]))
        ]
        booker_is_driver = current["booker_person_id"] == current["driver_person_id"]
        return {
            "person_id": customer_person_id,
            "full_name": current["driver_name"] or current["booker_name"],
            "phone": current["driver_phone"] or current["booker_phone"],
            "email": current["driver_email"] or current["booker_email"],
            "preferred_channel": current["driver_preferred_channel"] or current["booker_preferred_channel"],
            "customer_since": current["driver_created_at"] or current["booker_created_at"],
            "booker_is_driver": booker_is_driver,
            "booker": {
                "person_id": current["booker_person_id"],
                "full_name": current["booker_name"],
                "phone": current["booker_phone"],
                "email": current["booker_email"],
                "preferred_channel": current["booker_preferred_channel"],
            },
            "license": {
                "has_driving_license": (
                    bool(current["has_driving_license"])
                    if current["has_driving_license"] is not None
                    else None
                ),
                "declared_license_class": current["declared_license_class"],
                "required_license_class": current["required_license_class"],
                "validity_acknowledged": bool(current["validity_acknowledged"]),
                "check_status": current["license_check_status"],
                "checked_at": current["checked_at"],
                "rejection_reason": current["rejection_reason"],
            },
            "summary": {
                "total_bookings": len(history),
                "completed_bookings": sum(item["status"] == "completed" for item in history),
                "cancelled_bookings": sum(item["status"] == "cancelled" for item in history),
                "no_show_bookings": sum(item["status"] == "no_show" for item in history),
                "first_booking_at": min((item["start_at"] for item in history), default=None),
                "latest_booking_at": max((item["start_at"] for item in history), default=None),
            },
            "vehicle_interests": vehicle_interests,
            "history": history[:10],
        }

    def assert_staff_booking_access(self, principal: InternalPrincipal, booking_id: str) -> None:
        self.require_roles(principal, InternalRole.STAFF)
        if not principal.staff_id:
            raise InternalPortalError("ACCESS_DENIED", "Tài khoản chưa liên kết nhân viên.", status_code=403)
        with self.db.connect() as connection:
            allowed = connection.execute(
                "SELECT 1 FROM bookings b JOIN test_drive_slots s ON s.id=b.slot_id "
                "WHERE b.id=? AND EXISTS (SELECT 1 FROM slot_sales_assignments ssa "
                "JOIN sales_staff assigned_staff ON assigned_staff.id=ssa.sales_staff_id "
                "WHERE ssa.slot_id=s.id AND ssa.sales_staff_id=? AND ssa.assignment_role=? "
                "AND ssa.status='assigned' AND assigned_staff.status='active' AND assigned_staff.is_active=1)",
                (booking_id, principal.staff_id, STAFF_BOOKING_ASSIGNMENT_ROLE),
            ).fetchone()
        if not allowed:
            raise InternalPortalError(
                "ACCESS_DENIED", "Booking không được phân công cho nhân viên này.", status_code=403
            )

    def _showrooms_for_principal(
        self, connection, principal: InternalPrincipal, *, include_inactive: bool = False
    ) -> list[dict]:
        if principal.role is InternalRole.OPERATIONS_ADMIN:
            rows = connection.execute(
                "SELECT * FROM showrooms " + ("" if include_inactive else "WHERE is_active=1 ") + "ORDER BY name"
            )
        elif principal.showroom_ids:
            marks = ",".join("?" for _ in principal.showroom_ids)
            rows = connection.execute(
                f"SELECT * FROM showrooms WHERE is_active=1 AND id IN ({marks}) ORDER BY name",
                principal.showroom_ids,
            )
        else:
            return []
        return [dict(row) for row in rows]

    def list_showrooms(self, principal: InternalPrincipal) -> list[dict]:
        with self.db.connect() as connection:
            return self._showrooms_for_principal(
                connection, principal, include_inactive=principal.role is InternalRole.OPERATIONS_ADMIN
            )

    def list_staff(self, principal: InternalPrincipal, *, showroom_id: str | None = None) -> list[dict]:
        if principal.role is InternalRole.STAFF:
            if not principal.staff_id:
                return []
            sql, params = "SELECT * FROM sales_staff WHERE id=?", [principal.staff_id]
        else:
            where = ["is_active=1"]
            params = []
            if showroom_id:
                if not principal.can_access_showroom(showroom_id):
                    raise InternalPortalError("ACCESS_DENIED", "Showroom nằm ngoài phạm vi của bạn.", status_code=403)
                where.append("showroom_id=?")
                params.append(showroom_id)
            elif principal.role is InternalRole.SHOWROOM_MANAGER:
                if not principal.showroom_ids:
                    return []
                marks = ",".join("?" for _ in principal.showroom_ids)
                where.append(f"showroom_id IN ({marks})")
                params.extend(principal.showroom_ids)
            sql = f"SELECT * FROM sales_staff WHERE {' AND '.join(where)} ORDER BY full_name"
        with self.db.connect() as connection:
            return [dict(row) for row in connection.execute(sql, params)]

    def list_vehicles(
        self,
        principal: InternalPrincipal,
        *,
        showroom_id: str | None = None,
        model_id: str | None = None,
        variant_id: str | None = None,
        operational_status: str | None = None,
    ) -> list[dict]:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        where = ["d.is_active=1"]
        params: list[Any] = []
        if showroom_id:
            if not principal.can_access_showroom(showroom_id):
                raise InternalPortalError("ACCESS_DENIED", "Showroom nằm ngoài phạm vi của bạn.", status_code=403)
            where.append("d.showroom_id=?")
            params.append(showroom_id)
        elif principal.role is not InternalRole.OPERATIONS_ADMIN:
            if not principal.showroom_ids:
                return []
            marks = ",".join("?" for _ in principal.showroom_ids)
            where.append(f"d.showroom_id IN ({marks})")
            params.extend(principal.showroom_ids)
        if model_id:
            where.append("m.id=?")
            params.append(model_id)
        if variant_id:
            where.append("v.id=?")
            params.append(variant_id)
        if operational_status:
            if operational_status not in VEHICLE_STATUSES:
                raise InternalPortalError("INVALID_VEHICLE_STATUS", "Trạng thái xe không hợp lệ.")
            where.append("d.operational_status=?")
            params.append(operational_status)
        with self.db.connect() as connection:
            rows = connection.execute(
                f"""SELECT d.*,sh.name showroom_name,m.id model_id,m.code vehicle_model,
                v.id variant_id,v.name vehicle_variant
                FROM demo_vehicles d JOIN showrooms sh ON sh.id=d.showroom_id
                JOIN vehicle_variants v ON v.id=d.variant_id JOIN vehicle_models m ON m.id=v.model_id
                WHERE {" AND ".join(where)} ORDER BY sh.name,d.asset_code""",
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def list_catalog(self, principal: InternalPrincipal) -> list[dict]:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        with self.db.connect() as connection:
            rows = connection.execute(
                "SELECT m.id model_id,m.code model_code,m.name model_name,m.required_license_class,m.is_active model_active,"
                "v.id variant_id,v.code variant_code,v.name variant_name,v.battery_capacity_kwh,v.estimated_range_km,"
                "v.motor_power_kw,v.is_active variant_active FROM vehicle_models m "
                "LEFT JOIN vehicle_variants v ON v.model_id=m.id ORDER BY m.code,v.code"
            )
            return [dict(row) for row in rows]

    def list_shifts(
        self, principal: InternalPrincipal, *, showroom_id: str | None = None, staff_id: str | None = None
    ) -> list[dict]:
        params: list[Any] = []
        where = ["1=1"]
        if principal.role is InternalRole.STAFF:
            if not principal.staff_id:
                return []
            where.append("ss.sales_staff_id=?")
            params.append(principal.staff_id)
        else:
            if showroom_id:
                if not principal.can_access_showroom(showroom_id):
                    raise InternalPortalError("ACCESS_DENIED", "Showroom nằm ngoài phạm vi của bạn.", status_code=403)
                where.append("ss.showroom_id=?")
                params.append(showroom_id)
            elif principal.role is InternalRole.SHOWROOM_MANAGER:
                if not principal.showroom_ids:
                    return []
                marks = ",".join("?" for _ in principal.showroom_ids)
                where.append(f"ss.showroom_id IN ({marks})")
                params.extend(principal.showroom_ids)
            if staff_id:
                where.append("ss.sales_staff_id=?")
                params.append(staff_id)
        with self.db.connect() as connection:
            rows = connection.execute(
                f"SELECT ss.*,s.full_name staff_name,sh.name showroom_name FROM staff_shifts ss "
                "JOIN sales_staff s ON s.id=ss.sales_staff_id JOIN showrooms sh ON sh.id=ss.showroom_id "
                f"WHERE {' AND '.join(where)} ORDER BY ss.start_at DESC LIMIT 500",
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def create_shift(
        self,
        principal: InternalPrincipal,
        *,
        staff_id: str,
        showroom_id: str,
        start_at: str,
        end_at: str,
    ) -> dict:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        self._assert_scope(principal, showroom_id)
        start, end = _parse_time(start_at), _parse_time(end_at)
        if end <= start:
            raise InternalPortalError("INVALID_TIME_RANGE", "Giờ kết thúc phải sau giờ bắt đầu.")
        now = iso(self.now())
        shift_id = new_id("shift")
        with self.db.transaction(immediate=True) as connection:
            self._assert_staff_showroom(connection, staff_id, showroom_id)
            conflict = any(
                time_ranges_overlap(row["start_at"], row["end_at"], start_at, end_at)
                for row in connection.execute(
                    "SELECT start_at,end_at FROM staff_shifts WHERE sales_staff_id=? AND status='scheduled'",
                    (staff_id,),
                )
            )
            unavailable = any(
                time_ranges_overlap(row["start_at"], row["end_at"], start_at, end_at)
                for row in connection.execute(
                    "SELECT start_at,end_at FROM staff_unavailability WHERE sales_staff_id=?",
                    (staff_id,),
                )
            )
            if conflict or unavailable:
                raise InternalPortalError(
                    "SCHEDULE_CONFLICT", "Ca làm việc trùng lịch hoặc thời gian không khả dụng.", status_code=409
                )
            connection.execute(
                "INSERT INTO staff_shifts(id,sales_staff_id,showroom_id,start_at,end_at,status,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (shift_id, staff_id, showroom_id, start_at, end_at, "scheduled", principal.user_id, now, now),
            )
            self._audit(connection, principal, "shift.created", "staff_shift", shift_id, showroom_id, {})
        return {
            "id": shift_id,
            "staff_id": staff_id,
            "showroom_id": showroom_id,
            "start_at": start_at,
            "end_at": end_at,
            "status": "scheduled",
        }

    def list_unavailability(
        self, principal: InternalPrincipal, *, showroom_id: str | None = None, staff_id: str | None = None
    ) -> list[dict]:
        params: list[Any] = []
        where = ["1=1"]
        if principal.role is InternalRole.STAFF:
            if not principal.staff_id:
                return []
            where.append("u.sales_staff_id=?")
            params.append(principal.staff_id)
        else:
            if showroom_id:
                self._assert_scope(principal, showroom_id)
                where.append("u.showroom_id=?")
                params.append(showroom_id)
            elif principal.role is InternalRole.SHOWROOM_MANAGER:
                if not principal.showroom_ids:
                    return []
                marks = ",".join("?" for _ in principal.showroom_ids)
                where.append(f"u.showroom_id IN ({marks})")
                params.extend(principal.showroom_ids)
            if staff_id:
                where.append("u.sales_staff_id=?")
                params.append(staff_id)
        with self.db.connect() as connection:
            rows = connection.execute(
                f"SELECT u.*,s.full_name staff_name,sh.name showroom_name FROM staff_unavailability u "
                "JOIN sales_staff s ON s.id=u.sales_staff_id JOIN showrooms sh ON sh.id=u.showroom_id "
                f"WHERE {' AND '.join(where)} ORDER BY u.start_at DESC LIMIT 500",
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    def create_unavailability(
        self,
        principal: InternalPrincipal,
        *,
        staff_id: str,
        showroom_id: str,
        start_at: str,
        end_at: str,
        reason: str,
    ) -> dict:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        self._assert_scope(principal, showroom_id)
        start, end = _parse_time(start_at), _parse_time(end_at)
        if end <= start:
            raise InternalPortalError("INVALID_TIME_RANGE", "Giờ kết thúc phải sau giờ bắt đầu.")
        if not reason.strip():
            raise InternalPortalError("REASON_REQUIRED", "Cần nhập lý do không khả dụng.")
        now = iso(self.now())
        record_id = new_id("unavailable")
        with self.db.transaction(immediate=True) as connection:
            self._assert_staff_showroom(connection, staff_id, showroom_id)
            connection.execute(
                "INSERT INTO staff_unavailability(id,sales_staff_id,showroom_id,start_at,end_at,reason,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (record_id, staff_id, showroom_id, start_at, end_at, reason.strip(), principal.user_id, now, now),
            )
            shift_ids = [
                row["id"]
                for row in connection.execute(
                    "SELECT id,start_at,end_at FROM staff_shifts "
                    "WHERE sales_staff_id=? AND status='scheduled'",
                    (staff_id,),
                )
                if time_ranges_overlap(row["start_at"], row["end_at"], start_at, end_at)
            ]
            connection.executemany(
                "UPDATE staff_shifts SET status='cancelled',updated_at=? WHERE id=?",
                [(now, shift_id) for shift_id in shift_ids],
            )
            self._audit(
                connection,
                principal,
                "staff.unavailability_created",
                "staff_unavailability",
                record_id,
                showroom_id,
                {"staff_id": staff_id, "reason": reason.strip()},
            )
        return {
            "id": record_id,
            "staff_id": staff_id,
            "showroom_id": showroom_id,
            "start_at": start_at,
            "end_at": end_at,
            "reason": reason.strip(),
        }

    def update_vehicle(
        self,
        principal: InternalPrincipal,
        vehicle_id: str,
        *,
        operational_status: str | None = None,
        battery_soc: float | None = None,
        charging_status: str | None = None,
    ) -> dict:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        if operational_status is not None and operational_status not in VEHICLE_STATUSES:
            raise InternalPortalError("INVALID_VEHICLE_STATUS", "Trạng thái xe không hợp lệ.")
        if charging_status is not None and charging_status not in CHARGING_STATUSES:
            raise InternalPortalError("INVALID_CHARGING_STATUS", "Trạng thái sạc không hợp lệ.")
        if battery_soc is not None and not 0 <= battery_soc <= 100:
            raise InternalPortalError("INVALID_BATTERY_SOC", "Mức pin phải nằm trong khoảng 0–100.")
        updates: list[str] = []
        values: list[Any] = []
        for column, value in (
            ("operational_status", operational_status),
            ("battery_soc", battery_soc),
            ("charging_status", charging_status),
        ):
            if value is not None:
                updates.append(f"{column}=?")
                values.append(value)
        if not updates:
            raise InternalPortalError("NO_CHANGES", "Không có thay đổi nào được gửi lên.")
        with self.db.transaction(immediate=True) as connection:
            vehicle = connection.execute("SELECT * FROM demo_vehicles WHERE id=?", (vehicle_id,)).fetchone()
            if not vehicle:
                raise InternalPortalError("VEHICLE_NOT_FOUND", "Không tìm thấy xe demo.", status_code=404)
            self._assert_scope(principal, vehicle["showroom_id"])
            if operational_status is not None:
                self.validate_vehicle_status_transition(vehicle["operational_status"], operational_status)
            now = iso(self.now())
            updates.append("updated_at=?")
            values.extend([now, vehicle_id])
            connection.execute(f"UPDATE demo_vehicles SET {','.join(updates)} WHERE id=?", values)
            self._audit(
                connection,
                principal,
                "vehicle.updated",
                "demo_vehicle",
                vehicle_id,
                vehicle["showroom_id"],
                {
                    "old": {
                        "operational_status": vehicle["operational_status"],
                        "battery_soc": vehicle["battery_soc"],
                        "charging_status": vehicle["charging_status"],
                    },
                    "new": {
                        "operational_status": operational_status,
                        "battery_soc": battery_soc,
                        "charging_status": charging_status,
                    },
                },
            )
            updated = connection.execute("SELECT * FROM demo_vehicles WHERE id=?", (vehicle_id,)).fetchone()
        return dict(updated)

    def transfer_vehicle(
        self, principal: InternalPrincipal, vehicle_id: str, *, to_showroom_id: str, effective_at: str
    ) -> dict:
        self.require_roles(principal, InternalRole.OPERATIONS_ADMIN)
        effective = _parse_time(effective_at)
        if effective < self.now():
            raise InternalPortalError("INVALID_EFFECTIVE_TIME", "Thời điểm điều chuyển không được nằm trong quá khứ.")
        now = iso(self.now())
        transfer_id = new_id("transfer")
        with self.db.transaction(immediate=True) as connection:
            vehicle = connection.execute("SELECT * FROM demo_vehicles WHERE id=?", (vehicle_id,)).fetchone()
            target = connection.execute(
                "SELECT id FROM showrooms WHERE id=? AND is_active=1", (to_showroom_id,)
            ).fetchone()
            if not vehicle or not target:
                raise InternalPortalError(
                    "RESOURCE_NOT_FOUND", "Không tìm thấy xe hoặc showroom đích.", status_code=404
                )
            if vehicle["showroom_id"] == to_showroom_id:
                raise InternalPortalError("SAME_SHOWROOM", "Xe đã thuộc showroom đích.")
            if vehicle["operational_status"] == "in_use":
                raise InternalPortalError(
                    "VEHICLE_IN_USE",
                    "Không thể điều chuyển xe đang được sử dụng.",
                    status_code=409,
                )
            future_slot = any(
                parse_utc(row["start_at"]) >= self.now()
                for row in connection.execute(
                    "SELECT s.start_at FROM test_drive_slots s "
                    "LEFT JOIN bookings b ON b.id=s.current_booking_id WHERE s.demo_vehicle_id=? AND "
                    "(s.status='held' OR (s.status='booked' AND b.status IN ('confirmed','checked_in')))",
                    (vehicle_id,),
                )
            )
            if future_slot:
                raise InternalPortalError(
                    "FUTURE_SCHEDULE_EXISTS",
                    "Không thể điều chuyển vì xe còn booking hoặc hold trong tương lai.",
                    status_code=409,
                )
            future_block = any(
                parse_utc(row["end_at"]) > self.now()
                for row in connection.execute(
                    "SELECT end_at FROM vehicle_unavailability WHERE demo_vehicle_id=?",
                    (vehicle_id,),
                )
            )
            if future_block:
                raise InternalPortalError(
                    "VEHICLE_UNAVAILABLE",
                    "Không thể điều chuyển vì xe đang có khoảng thời gian không khả dụng.",
                    status_code=409,
                )
            connection.execute(
                "UPDATE demo_vehicles SET showroom_id=?,updated_at=? WHERE id=?",
                (to_showroom_id, now, vehicle_id),
            )
            future_slot_ids = [
                row["id"]
                for row in connection.execute(
                    "SELECT id,start_at FROM test_drive_slots "
                    "WHERE demo_vehicle_id=? AND status='available'",
                    (vehicle_id,),
                )
                if parse_utc(row["start_at"]) >= self.now()
            ]
            connection.executemany(
                "UPDATE test_drive_slots SET status='blocked',block_reason=?,updated_at=? WHERE id=?",
                [(f"vehicle_transfer:{transfer_id}", now, slot_id) for slot_id in future_slot_ids],
            )
            connection.execute(
                "INSERT INTO vehicle_transfers(id,demo_vehicle_id,from_showroom_id,to_showroom_id,"
                "requested_by,completed_by,status,requested_at,completed_at,effective_at,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    transfer_id,
                    vehicle_id,
                    vehicle["showroom_id"],
                    to_showroom_id,
                    principal.user_id,
                    principal.user_id,
                    "completed",
                    now,
                    now,
                    iso(effective),
                    now,
                    now,
                ),
            )
            self._audit(
                connection,
                principal,
                "vehicle.transferred",
                "demo_vehicle",
                vehicle_id,
                to_showroom_id,
                {"from_showroom_id": vehicle["showroom_id"], "to_showroom_id": to_showroom_id},
            )
        return {
            "id": transfer_id,
            "vehicle_id": vehicle_id,
            "from_showroom_id": vehicle["showroom_id"],
            "to_showroom_id": to_showroom_id,
            "status": "completed",
            "effective_at": iso(effective),
        }

    def list_audit_events(self, principal: InternalPrincipal, *, limit: int = 100) -> list[dict]:
        self.require_roles(principal, InternalRole.SHOWROOM_MANAGER, InternalRole.OPERATIONS_ADMIN)
        params: list[Any] = []
        where = "1=1"
        if principal.role is InternalRole.SHOWROOM_MANAGER:
            if not principal.showroom_ids:
                return []
            marks = ",".join("?" for _ in principal.showroom_ids)
            where = f"a.showroom_id IN ({marks}) AND a.resource_type<>'internal_user'"
            params.extend(principal.showroom_ids)
        params.append(min(max(limit, 1), 500))
        with self.db.connect() as connection:
            rows = connection.execute(
                "SELECT a.*,u.display_name actor_name FROM internal_audit_events a "
                f"JOIN internal_users u ON u.id=a.actor_user_id WHERE {where} ORDER BY a.created_at DESC LIMIT ?",
                params,
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _assert_staff_showroom(connection, staff_id: str, showroom_id: str) -> None:
        if not connection.execute(
            "SELECT 1 FROM sales_staff WHERE id=? AND showroom_id=? AND is_active=1",
            (staff_id, showroom_id),
        ).fetchone():
            raise InternalPortalError("STAFF_SCOPE_MISMATCH", "Nhân viên không thuộc showroom đã chọn.")

    @staticmethod
    def _assert_scope(principal: InternalPrincipal, showroom_id: str) -> None:
        if not principal.can_access_showroom(showroom_id):
            raise InternalPortalError("ACCESS_DENIED", "Showroom nằm ngoài phạm vi của bạn.", status_code=403)

    def _audit(
        self,
        connection,
        principal: InternalPrincipal,
        action: str,
        resource_type: str,
        resource_id: str | None,
        showroom_id: str | None,
        payload: dict,
    ) -> None:
        connection.execute(
            "INSERT INTO internal_audit_events(id,actor_user_id,action,resource_type,resource_id,showroom_id,payload_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
            (
                new_id("iaudit"),
                principal.user_id,
                action,
                resource_type,
                resource_id,
                showroom_id,
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                iso(self.now()),
            ),
        )
