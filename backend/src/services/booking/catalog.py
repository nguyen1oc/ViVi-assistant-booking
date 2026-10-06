from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta
from difflib import SequenceMatcher
from typing import Any
from zoneinfo import ZoneInfo

from src.services.booking.base import BookingBase
from src.services.booking.common import iso, parse_utc
from src.services.booking.errors import BookingError
from src.services.booking.location import Coordinates, HaversineMapProvider, resolve_address_coordinates
from src.services.booking.location_normalizer import (
    broad_region_clarification,
    normalize_location_text,
    normalize_location_tokens,
)

VIETNAM_TZ = ZoneInfo("Asia/Ho_Chi_Minh")
_SHOWROOM_TOKEN_CACHE: dict[str, tuple[tuple[str, str, str], frozenset[str]]] = {}
_GENERIC_SHOWROOM_TOKENS = frozenset({"vinfast", "showroom", "dai", "ly", "co", "so"})
_ADMINISTRATIVE_LOCATION_TOKENS = frozenset({
    "phuong",
    "quan",
    "huyen",
    "tinh",
    "thanh",
    "pho",
    "xa",
})


# Điểm khớp tên tối thiểu để coi truy vấn là chỉ đích danh một showroom.
# Cùng thang điểm với _showroom_query_score: 100 = trùng mã, 90 = trùng tên/định danh.
_SHOWROOM_QUERY_CONFIDENT_SCORE = 90


def _showroom_identity_text(value: object) -> str:
    normalized = normalize_location_text(str(value or ""))
    return " ".join(token for token in normalized.split() if token not in _GENERIC_SHOWROOM_TOKENS)


def _looks_like_showroom_reference(value: str) -> bool:
    normalized = normalize_location_text(value)
    tokens = set(normalized.split())
    explicit = bool(tokens & _GENERIC_SHOWROOM_TOKENS)
    distinctive_name = len(tokens) >= 2 and not bool(tokens & _ADMINISTRATIVE_LOCATION_TOKENS)
    return explicit or distinctive_name


def _showroom_location_tokens(showroom: dict) -> frozenset[str]:
    """Return cached tokens; an updated showroom naturally gets a new cache key."""
    showroom_id = str(showroom.get("id", ""))
    version = (
        str(showroom.get("updated_at", "")),
        str(showroom.get("name", "")),
        str(showroom.get("address", "")),
    )
    cached = _SHOWROOM_TOKEN_CACHE.get(showroom_id)
    if cached is None or cached[0] != version:
        tokens = frozenset(normalize_location_tokens(f"{version[1]} {version[2]}"))
        _SHOWROOM_TOKEN_CACHE[showroom_id] = (version, tokens)
        return tokens
    return cached[1]


def _to_vietnam_time(iso_str: str) -> datetime:
    dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(VIETNAM_TZ)


def _normalize_preferred_date(date_str: str, now_dt: datetime) -> str:
    """Normalize shorthand date inputs ('20', 'ngày 20', '20/8', '20-8') to 'YYYY-MM-DD'."""
    if not date_str or not isinstance(date_str, str):
        return date_str

    cleaned = date_str.strip().lower()
    cleaned = re.sub(r"^(?:ngày|ngay)\s+", "", cleaned)

    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", cleaned):
        return cleaned

    match_dm = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})", cleaned)
    if match_dm:
        day, month = int(match_dm.group(1)), int(match_dm.group(2))
        year = now_dt.year
        if month < now_dt.month or (month == now_dt.month and day < now_dt.day):
            year += 1
        return f"{year:04d}-{month:02d}-{day:02d}"

    match_d = re.fullmatch(r"(\d{1,2})", cleaned)
    if match_d:
        day = int(match_d.group(1))
        if 1 <= day <= 31:
            month = now_dt.month
            year = now_dt.year
            if day < now_dt.day:
                month += 1
                if month > 12:
                    month = 1
                    year += 1
            return f"{year:04d}-{month:02d}-{day:02d}"

    return date_str


def _normalize_date_filters(
    *,
    preferred_date: str | None,
    preferred_dates: list[str] | None,
    preferred_date_from: str | None,
    preferred_date_to: str | None,
    now_dt: datetime,
) -> dict[str, Any]:
    """Normalize exactly one supported date-selection mode."""
    has_single = preferred_date is not None
    has_list = preferred_dates is not None
    has_range = preferred_date_from is not None or preferred_date_to is not None
    if sum((has_single, has_list, has_range)) > 1:
        raise BookingError(
            "INVALID_INPUT",
            "Chỉ dùng một trong preferred_date, preferred_dates hoặc khoảng preferred_date_from/preferred_date_to.",
        )
    if has_range and not (preferred_date_from and preferred_date_to):
        raise BookingError("INVALID_INPUT", "Khoảng ngày phải có cả ngày bắt đầu và ngày kết thúc.")

    def normalize_one(raw: str) -> str:
        normalized = _normalize_preferred_date(raw, now_dt)
        try:
            date.fromisoformat(normalized)
        except (TypeError, ValueError):
            raise BookingError("INVALID_INPUT", f"Ngày không hợp lệ: {raw}.") from None
        return normalized

    if has_single:
        if not preferred_date:
            raise BookingError("INVALID_INPUT", "preferred_date không được để trống.")
        normalized = normalize_one(preferred_date)
        return {"mode": "single", "dates": [normalized], "from": None, "to": None}

    if has_list:
        if not preferred_dates:
            raise BookingError("INVALID_INPUT", "preferred_dates phải có ít nhất một ngày.")
        if len(preferred_dates) > 31:
            raise BookingError("INVALID_INPUT", "Chỉ được yêu cầu tối đa 31 ngày trong một lần tìm.")
        normalized_dates = list(dict.fromkeys(normalize_one(item) for item in preferred_dates))
        return {"mode": "list", "dates": normalized_dates, "from": None, "to": None}

    if has_range and preferred_date_from and preferred_date_to:
        normalized_from = normalize_one(preferred_date_from)
        normalized_to = normalize_one(preferred_date_to)
        start = date.fromisoformat(normalized_from)
        end = date.fromisoformat(normalized_to)
        if end < start:
            raise BookingError("INVALID_INPUT", "Ngày kết thúc phải bằng hoặc sau ngày bắt đầu.")
        if (end - start).days > 30:
            raise BookingError("INVALID_INPUT", "Khoảng ngày không được dài quá 31 ngày.")
        return {"mode": "range", "dates": [], "from": normalized_from, "to": normalized_to}

    return {"mode": "none", "dates": [], "from": None, "to": None}


def _date_filter_sql(filters: dict[str, Any], *, dialect: str) -> tuple[str, list[str]]:
    # SQL expressions cannot be bound as query parameters. Select them from a
    # closed internal allowlist so callers can never inject an arbitrary SQL
    # fragment into this helper.
    if dialect == "postgres":
        slot_date_sql = "to_char(s.start_at::timestamptz AT TIME ZONE 'Asia/Ho_Chi_Minh', 'YYYY-MM-DD')"
    elif dialect == "sqlite":
        slot_date_sql = "strftime('%Y-%m-%d', datetime(s.start_at, '+7 hours'))"
    else:
        raise ValueError(f"Unsupported database dialect: {dialect}")

    if filters["mode"] == "range":
        return f" AND {slot_date_sql} BETWEEN ? AND ?", [filters["from"], filters["to"]]
    dates = filters["dates"]
    if dates:
        marks = ",".join("?" * len(dates))
        return f" AND {slot_date_sql} IN ({marks})", dates
    return "", []


class CatalogService(BookingBase):
    def list_active_vehicle_models(self) -> list[dict]:
        with self.db.connect() as c:
            models = [dict(row) for row in c.execute("SELECT * FROM vehicle_models WHERE is_active=1 ORDER BY code")]
            for model in models:
                model["variants"] = [
                    dict(row)
                    for row in c.execute(
                        "SELECT * FROM vehicle_variants WHERE model_id=? AND is_active=1 ORDER BY code", (model["id"],)
                    )
                ]
            return models

    def list_active_variants(self, model_id: str) -> list[dict]:
        with self.db.connect() as c:
            if not c.execute("SELECT 1 FROM vehicle_models WHERE id=? AND is_active=1", (model_id,)).fetchone():
                raise BookingError("MODEL_NOT_FOUND", "Không tìm thấy mẫu xe.")
            return [
                dict(row)
                for row in c.execute(
                    "SELECT * FROM vehicle_variants WHERE model_id=? AND is_active=1 ORDER BY code", (model_id,)
                )
            ]

    def list_active_showrooms(self) -> list[dict]:
        with self.db.connect() as c:
            return [dict(row) for row in c.execute("SELECT * FROM showrooms WHERE is_active=1 ORDER BY code")]

    def resolve_vehicle_model(self, query: str) -> dict:
        with self.db.connect() as c:
            row = c.execute(
                "SELECT * FROM vehicle_models WHERE is_active=1 AND (lower(code)=lower(?) OR lower(name)=lower(?))",
                (query, query),
            ).fetchone()
            if not row:
                row = c.execute(
                    "SELECT * FROM vehicle_models WHERE is_active=1 AND lower(name) LIKE lower(?) ORDER BY name LIMIT 1",
                    (f"%{query}%",),
                ).fetchone()
        if not row:
            raise BookingError("VEHICLE_NOT_FOUND", "Không tìm thấy mẫu xe.")
        return dict(row)

    def search_options(
        self,
        *,
        vehicle_model: str,
        vehicle_variant: str | None = None,
        showroom_id: str | None = None,
        showroom_query: str | None = None,
        address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        preferred_date: str | None = None,
        preferred_dates: list[str] | None = None,
        preferred_date_from: str | None = None,
        preferred_date_to: str | None = None,
        preferred_time: str | None = None,
        showroom_limit: int = 5,
        slot_limit: int | None = None,
        **_: Any,
    ) -> dict:
        if (latitude is None) != (longitude is None):
            raise BookingError("INVALID_INPUT", "Latitude và longitude phải được cung cấp cùng nhau.")
        model = self.resolve_vehicle_model(vehicle_model)
        clarification = (
            broad_region_clarification(address) if address and not showroom_id and latitude is None else None
        )
        if clarification:
            return {
                "resolved_vehicle": model,
                "license_requirement": model["required_license_class"],
                "showrooms": [],
                "slots": [],
                "search_stage": "location_clarification",
                "location_scope": "broad_region",
                "clarification_message": clarification,
                "missing_fields": ["province_or_city"],
            }
        params: list[Any] = [model["id"]]
        variant_sql = ""
        if vehicle_variant:
            variant_sql = " AND (lower(v.code)=lower(?) OR lower(v.name)=lower(?))"
            params += [vehicle_variant, vehicle_variant]
        with self.db.connect() as c:
            variants = [
                dict(r)
                for r in c.execute(
                    "SELECT v.* FROM vehicle_variants v WHERE v.model_id=? AND v.is_active=1" + variant_sql, params
                )
            ]
            if vehicle_variant and not variants:
                raise BookingError("VEHICLE_NOT_FOUND", "Không tìm thấy phiên bản xe.")
            variant_ids = [v["id"] for v in variants]
            if not variant_ids:
                return {
                    "resolved_vehicle": model,
                    "license_requirement": model["required_license_class"],
                    "showrooms": [],
                    "slots": [],
                    "search_stage": "showroom_selection",
                    "missing_fields": [],
                }
            marks = ",".join("?" * len(variant_ids))
            now = iso(self.now())
            horizon = iso(self.now() + timedelta(days=self.booking_advance_window_days))
            future_slot_sql = (
                "s.start_at::timestamptz > ?::timestamptz"
                if c.dialect == "postgres"
                else "datetime(s.start_at) > datetime(?)"
            )
            horizon_slot_sql = (
                "s.start_at::timestamptz <= ?::timestamptz"
                if c.dialect == "postgres"
                else "datetime(s.start_at) <= datetime(?)"
            )
            date_filters = _normalize_date_filters(
                preferred_date=preferred_date,
                preferred_dates=preferred_dates,
                preferred_date_from=preferred_date_from,
                preferred_date_to=preferred_date_to,
                now_dt=self.now().astimezone(VIETNAM_TZ),
            )
            date_sql, date_values = _date_filter_sql(date_filters, dialect=c.dialect)

            if not showroom_id:
                # A location belongs to the customer, not to a showroom. Do not
                # hard-filter candidates by address tokens: a nearby showroom in
                # another province (for example Da Nang for Que Son) must remain
                # eligible. The aggregate also ensures every returned showroom
                # already has at least one genuinely bookable slot.
                candidate_values: list[Any] = [*variant_ids, now, now, horizon, *date_values]
                rows = c.execute(
                    f"SELECT sr.*, COUNT(s.id) AS available_slot_count, MIN(s.start_at) AS nearest_slot_at "
                    f"FROM showrooms sr "
                    f"JOIN test_drive_slots s ON s.showroom_id=sr.id "
                    f"JOIN demo_vehicles d ON d.id=s.demo_vehicle_id "
                    f"WHERE sr.is_active=1 AND d.variant_id IN ({marks}) "
                    f"AND s.status='available' AND (s.held_until IS NULL OR s.held_until<=?) "
                    f"AND {future_slot_sql} AND {horizon_slot_sql} "
                    f"AND d.is_active=1 AND d.operational_status='available' "
                    f"AND d.battery_soc IS NOT NULL AND d.battery_soc>=d.minimum_booking_soc"
                    f"{date_sql} GROUP BY sr.id",
                    candidate_values,
                ).fetchall()
                showrooms = [dict(row) for row in rows]

                # The model sometimes places a named showroom in ``address``
                # (for example "cơ sở Thanh Hà") instead of
                # ``showroom_query``. Resolve that representation only when it
                # points confidently to one available showroom. Broad
                # locations such as "Quận 7" remain customer addresses.
                if address and not showroom_query and _looks_like_showroom_reference(address):
                    address_scores = [
                        (self._showroom_query_score(address, showroom), showroom)
                        for showroom in showrooms
                    ]
                    confident = [item for item in address_scores if item[0] >= 70]
                    if len(confident) == 1:
                        showroom_query = address
                        address = None

                target_coords: dict[str, float] | None = None
                if latitude is not None and longitude is not None:
                    target_coords = {"latitude": latitude, "longitude": longitude}
                elif address:
                    resolved_coords = resolve_address_coordinates(address)
                    if resolved_coords:
                        target_coords = {"latitude": resolved_coords.latitude, "longitude": resolved_coords.longitude}

                if showroom_query:
                    scored = [
                        (self._showroom_query_score(showroom_query, showroom), showroom) for showroom in showrooms
                    ]
                    showrooms = [showroom for score, showroom in scored if score > 0]
                    if not showrooms:
                        raise BookingError("SHOWROOM_NOT_FOUND", "Không tìm thấy showroom theo tên hoặc mã.")
                    for score, showroom in scored:
                        if score > 0:
                            showroom["text_match_score"] = score

                origin_coords = (
                    Coordinates(target_coords["latitude"], target_coords["longitude"]) if target_coords else None
                )
                if origin_coords:
                    destinations = [Coordinates(s["latitude"], s["longitude"]) for s in showrooms]
                    for s, distance in zip(
                        showrooms, self.map_provider.distances_km(origin_coords, destinations), strict=True
                    ):
                        s["distance_km"] = round(distance, 2)
                for showroom in showrooms:
                    reasons: list[str] = []
                    if showroom.get("distance_km") is not None:
                        reasons.append("Gần vị trí của bạn")
                    if showroom.get("available_slot_count"):
                        reasons.append(f"Còn {showroom['available_slot_count']} lịch trống")
                    if showroom_query and showroom.get("text_match_score"):
                        reasons.append("Khớp tên showroom")
                    showroom["match_reasons"] = reasons

                if showroom_query:
                    showrooms.sort(
                        key=lambda item: (
                            -int(item.get("text_match_score") or 0),
                            item.get("distance_km", float("inf")),
                            -int(item.get("available_slot_count") or 0),
                            item["name"],
                        )
                    )
                elif origin_coords:
                    showrooms.sort(
                        key=lambda item: (
                            item.get("distance_km", float("inf")),
                            -int(item.get("available_slot_count") or 0),
                            item["name"],
                        )
                    )
                else:
                    showrooms.sort(key=lambda item: (-int(item.get("available_slot_count") or 0), item["name"]))

                # Khách gọi thẳng tên showroom thì họ đã chọn rồi, đừng bắt chọn lại.
                # Trả về "showroom_selection" ở đây làm luồng đứng lại một bước thừa và
                # vứt luôn ngày/giờ khách vừa nói, vì nhánh này không đọc lịch trống.
                # Chỉ đi tiếp khi truy vấn chỉ đích danh đúng MỘT nơi; còn mơ hồ thì vẫn
                # trả danh sách cho khách chọn như cũ.
                promoted = self._unique_confident_showroom(showrooms) if showroom_query else None
                if promoted is None:
                    return {
                        "resolved_vehicle": {**model, "variants": variants},
                        "license_requirement": model["required_license_class"],
                        "showrooms": showrooms[: min(max(showroom_limit, 1), 30)],
                        "target_coordinates": target_coords,
                        "slots": [],
                        "search_stage": "showroom_selection",
                        "missing_fields": [],
                    }
                showroom_id = str(promoted["id"])
            selected = self._row(
                c.execute("SELECT * FROM showrooms WHERE id=? AND is_active=1", (showroom_id,)).fetchone()
            )
            if not selected:
                raise BookingError("SHOWROOM_NOT_FOUND", "Showroom not found.")
            # Slot timestamps in the dataset may carry a local UTC offset (for
            # example +07:00) while `now` is stored as UTC. Comparing those ISO
            # strings lexicographically can make an already-past local slot look
            # newer than the UTC value. Normalize both operands in SQL instead.
            values: list[Any] = [showroom_id, *variant_ids, now, now, horizon]
            order_sql = "s.start_at"
            values.extend(date_values)
            if preferred_time:
                if not isinstance(preferred_time, str) or not re.fullmatch(
                    r"(?:[01]\d|2[0-3]):[0-5]\d", preferred_time
                ):
                    raise BookingError("INVALID_INPUT", "Preferred time must be a valid HH:MM value.")
                hour, minute = (int(x) for x in preferred_time.split(":"))
                target = hour * 60 + minute
                slot_minutes_sql = (
                    "(EXTRACT(HOUR FROM s.start_at::timestamptz AT TIME ZONE 'Asia/Ho_Chi_Minh') * 60 "
                    "+ EXTRACT(MINUTE FROM s.start_at::timestamptz AT TIME ZONE 'Asia/Ho_Chi_Minh'))"
                    if c.dialect == "postgres"
                    else "(CAST(strftime('%H', datetime(s.start_at, '+7 hours')) AS INTEGER) * 60 "
                    "+ CAST(strftime('%M', datetime(s.start_at, '+7 hours')) AS INTEGER))"
                )
                order_sql = f"ABS({slot_minutes_sql} - ?), s.start_at"
                values.append(target)
            slot_limit_sql = " LIMIT ?" if slot_limit is not None else ""
            slot_query_values = tuple(values)
            if slot_limit is not None:
                slot_query_values = (*slot_query_values, min(max(slot_limit, 1), 300))
            slots = [
                dict(r)
                for r in c.execute(
                    f"SELECT s.*,d.asset_code,v.name variant_name FROM test_drive_slots s JOIN demo_vehicles d ON d.id=s.demo_vehicle_id JOIN vehicle_variants v ON v.id=d.variant_id WHERE s.showroom_id=? AND d.variant_id IN ({marks}) AND (s.status='available' AND (s.held_until IS NULL OR s.held_until<=?)) AND {future_slot_sql} AND {horizon_slot_sql} AND d.is_active=1 AND d.operational_status='available' AND d.battery_soc IS NOT NULL AND d.battery_soc>=d.minimum_booking_soc {date_sql} ORDER BY {order_sql}{slot_limit_sql}",
                    slot_query_values,
                )
            ]
            raw_slot_count = len(slots)
            staff_rows = [
                dict(row)
                for row in c.execute(
                    "SELECT id FROM sales_staff WHERE showroom_id=? "
                    "AND status='active' AND is_active=1 ORDER BY id",
                    (showroom_id,),
                ).fetchall()
            ]
            capacity_tracked = bool(staff_rows)
            blocked_intervals: dict[str, list[tuple[str, str]]] = {}
            current_instant = parse_utc(now)
            for staff in staff_rows:
                staff_id = str(staff["id"])
                intervals = [
                    (str(row["start_at"]), str(row["end_at"]))
                    for row in c.execute(
                        "SELECT start_at,end_at FROM staff_unavailability WHERE sales_staff_id=?",
                        (staff_id,),
                    ).fetchall()
                ]
                for row in c.execute(
                    "SELECT s.start_at,s.end_at,s.status,s.held_until "
                    "FROM slot_sales_assignments a JOIN test_drive_slots s ON s.id=a.slot_id "
                    "WHERE a.sales_staff_id=? AND a.assignment_role='test_drive_consultant' "
                    "AND a.status='assigned' AND s.status IN ('held','booked')",
                    (staff_id,),
                ).fetchall():
                    active = row["status"] == "booked" or (
                        row["status"] == "held"
                        and (row["held_until"] is None or parse_utc(row["held_until"]) > current_instant)
                    )
                    if active:
                        intervals.append((str(row["start_at"]), str(row["end_at"])))
                blocked_intervals[staff_id] = intervals
            active_staff_count = 0
            allocated: dict[str, list[tuple[str, str]]] = {}
            capacity_filtered_slots: list[dict[str, Any]] = []
            for slot in slots:
                if not capacity_tracked:
                    capacity_filtered_slots.append(slot)
                    continue
                candidates = [
                    staff
                    for staff in staff_rows
                    if not any(
                        self._overlaps(start, end, slot["start_at"], slot["end_at"])
                        for start, end in blocked_intervals[str(staff["id"])]
                    )
                ]
                active_staff_count = max(active_staff_count, len(candidates))
                selected_staff_id = next(
                    (
                        str(staff["id"])
                        for staff in candidates
                        if not any(
                            self._overlaps(start, end, slot["start_at"], slot["end_at"])
                            for start, end in allocated.get(str(staff["id"]), [])
                        )
                    ),
                    None,
                )
                if selected_staff_id is None:
                    continue
                allocated.setdefault(selected_staff_id, []).append((slot["start_at"], slot["end_at"]))
                capacity_filtered_slots.append(slot)
            slots = capacity_filtered_slots
            weekdays_vi = {0: "Thứ 2", 1: "Thứ 3", 2: "Thứ 4", 3: "Thứ 5", 4: "Thứ 6", 5: "Thứ 7", 6: "Chủ nhật"}
            for s in slots:
                dt_start = _to_vietnam_time(s["start_at"])
                dt_end = _to_vietnam_time(s["end_at"])
                s["start_at"] = dt_start.isoformat()
                s["end_at"] = dt_end.isoformat()
                day_label = weekdays_vi[dt_start.weekday()]
                date_str = dt_start.strftime("%d/%m")
                time_str = dt_start.strftime("%H:%M")
                s["formatted_schedule"] = f"{day_label}, {date_str} {time_str}"

        focused_date = date_filters["dates"][0] if date_filters["mode"] == "single" else None
        requested_dates = date_filters["dates"] if date_filters["mode"] == "list" else []
        requested_date_range = (
            {"from": date_filters["from"], "to": date_filters["to"]} if date_filters["mode"] == "range" else None
        )
        available_dates = sorted({slot["start_at"][:10] for slot in slots})
        highlighted_dates = (
            [available_date[5:] for available_date in available_dates] if date_filters["mode"] != "none" else []
        )

        return {
            "resolved_vehicle": {**model, "variants": variants},
            "license_requirement": model["required_license_class"],
            "selected_showroom": selected,
            "showrooms": [],
            "slots": slots,
            "search_stage": "slot_selection",
            "focused_date": focused_date,
            "requested_dates": requested_dates,
            "requested_date_range": requested_date_range,
            "available_dates": available_dates,
            "highlighted_dates": highlighted_dates,
            "staff_capacity": {
                "tracked": capacity_tracked,
                "active_staff_count": active_staff_count if capacity_tracked else None,
                "candidate_slot_count": raw_slot_count,
                "returned_slot_count": len(slots),
                "capacity_filtered_slot_count": raw_slot_count - len(slots),
            },
            "missing_fields": [],
        }

    @staticmethod
    def _distance(a, b, c, d):
        return HaversineMapProvider.distance_km(Coordinates(a, b), Coordinates(c, d))

    @staticmethod
    def _address_match_score(address: str, showroom: dict) -> int:
        """Rank available showrooms by locality tokens without a remote geocoder."""

        requested = normalize_location_tokens(address)
        candidate = _showroom_location_tokens(showroom)
        return len(requested & candidate)

    @staticmethod
    def _unique_confident_showroom(showrooms: list[dict]) -> dict | None:
        """Trả showroom mà một truy vấn theo TÊN chỉ đích danh, hoặc None nếu còn mơ hồ.

        Chỉ nhận điểm >= 90, tức khớp nguyên mã (100) hoặc nguyên tên/định danh (90).
        Điểm 70 là "truy vấn nằm trong tên" và 50 là "nằm trong địa chỉ" — hai mức đó
        có thể trúng nhiều nơi cùng lúc ("Minh Đạo Phát" ra ba showroom), nên tuyệt đối
        không tự chọn. Có từ hai ứng viên đích danh trở lên cũng trả None: lúc đó phải
        để khách tự chọn chứ không đoán hộ.
        """
        confident = [
            showroom
            for showroom in showrooms
            if int(showroom.get("text_match_score") or 0) >= _SHOWROOM_QUERY_CONFIDENT_SCORE
        ]
        return confident[0] if len(confident) == 1 else None

    @staticmethod
    def _showroom_query_score(query: str, showroom: dict) -> int:
        """Score a showroom-name query without selecting a showroom implicitly."""

        normalized_query = normalize_location_text(query)
        normalized_code = normalize_location_text(str(showroom.get("code", "")))
        normalized_name = normalize_location_text(str(showroom.get("name", "")))
        normalized_address = normalize_location_text(str(showroom.get("address", "")))
        if normalized_query and normalized_query == normalized_code:
            return 100
        if normalized_query and normalized_query == normalized_name:
            return 90
        if normalized_query and normalized_query in normalized_name:
            return 70
        if normalized_query and normalized_query in normalized_address:
            return 50

        identity_query = _showroom_identity_text(query)
        identity_name = _showroom_identity_text(showroom.get("name", ""))
        if identity_query and identity_name:
            if identity_query == identity_name:
                return 90
            if identity_query in identity_name or identity_name in identity_query:
                return 70
            similarity = SequenceMatcher(None, identity_query, identity_name).ratio()
            if similarity >= 0.84:
                return 75

        query_tokens = set(normalized_query.split())
        candidate_tokens = set(f"{normalized_code} {normalized_name} {normalized_address}".split())
        return 10 * len(query_tokens & candidate_tokens)
