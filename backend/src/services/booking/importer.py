from __future__ import annotations

import csv
import io
import os
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

from src.database import DatabaseIntegrityError
from src.services.booking.base import BookingBase
from src.services.booking.common import iso, new_id, normalize_phone, normalize_timestamp, parse_utc
from src.services.booking.errors import BookingError

_id = new_id


def _columns(value: str) -> list[str]:
    return value.split(",")


class ImportService(BookingBase):
    IMPORT_BATCH_SIZE = 5_000
    DATASET_BATCH_SIZE = IMPORT_BATCH_SIZE

    @staticmethod
    def _report_import_progress(message: str) -> None:
        """Print opt-in bulk-import progress for long-running seed commands."""
        if os.getenv("IMPORT_PROGRESS", "").lower() in {"1", "true", "yes"}:
            print(f"[seed] {message}", flush=True)

    @staticmethod
    def _validate_coordinates(latitude: object, longitude: object, *, context: str) -> tuple[float, float]:
        try:
            lat, lon = float(str(latitude)), float(str(longitude))
        except (TypeError, ValueError) as exc:
            raise BookingError("INVALID_INPUT", f"Invalid coordinates {context}.") from exc
        if not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise BookingError("INVALID_INPUT", f"Coordinates out of range {context}.")
        return lat, lon

    @staticmethod
    def _normalize_slot_timestamps(rows: list[dict[str, str]], *, filename: str, line_offset: int = 0) -> None:
        """Persist slot times as explicit UTC instants, never local text values."""
        for line, row in enumerate(rows, start=2 + line_offset):
            try:
                start = parse_utc(row["start_at"])
                end = parse_utc(row["end_at"])
            except (TypeError, ValueError) as exc:
                raise BookingError("INVALID_INPUT", f"Invalid slot timestamp at line {line} of {filename}.") from exc
            if end <= start:
                raise BookingError("INVALID_INPUT", f"Slot end_at must be after start_at at line {line} of {filename}.")
            row["start_at"] = iso(start)
            row["end_at"] = iso(end)
            if row.get("held_until"):
                try:
                    row["held_until"] = normalize_timestamp(row["held_until"])
                except (TypeError, ValueError) as exc:
                    raise BookingError("INVALID_INPUT", f"Invalid held_until at line {line} of {filename}.") from exc

    def import_showrooms_csv(self, csv_text: str) -> dict:
        """Upsert showroom rows from a UTF-8 CSV document."""
        required = {"code", "name", "address", "latitude", "longitude"}
        reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise BookingError("INVALID_INPUT", "CSV thiếu cột bắt buộc: code,name,address,latitude,longitude.")
        imported = 0
        with self.db.transaction(immediate=True) as c:
            for line, row in enumerate(reader, start=2):
                lat, lon = self._validate_coordinates(row["latitude"], row["longitude"], context=f"at line {line}")
                now = iso(self.now())
                existing = c.execute("SELECT id FROM showrooms WHERE code=?", (row["code"].strip(),)).fetchone()
                sid = existing["id"] if existing else _id("showroom")
                c.execute(
                    "INSERT INTO showrooms(id,code,name,address,latitude,longitude,phone,email,timezone,is_active,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(code) DO UPDATE SET name=excluded.name,address=excluded.address,latitude=excluded.latitude,longitude=excluded.longitude,phone=excluded.phone,email=excluded.email,timezone=excluded.timezone,is_active=excluded.is_active,updated_at=excluded.updated_at",
                    (
                        sid,
                        row["code"].strip(),
                        row["name"].strip(),
                        row["address"].strip(),
                        lat,
                        lon,
                        row.get("phone") or None,
                        row.get("email") or None,
                        row.get("timezone") or "Asia/Ho_Chi_Minh",
                        0 if str(row.get("is_active", "1")).lower() in ("0", "false", "no") else 1,
                        now,
                        now,
                    ),
                )
                imported += 1
        return {"imported": imported}

    DATASET_FILES = {
        "01_vehicle_models.csv": (
            "vehicle_models",
            [
                "id",
                "code",
                "name",
                "vehicle_type",
                "required_license_class",
                "license_requirement_note",
                "is_active",
                "created_at",
                "updated_at",
            ],
        ),
        "02_vehicle_variants.csv": (
            "vehicle_variants",
            [
                "id",
                "model_id",
                "code",
                "name",
                "battery_capacity_kwh",
                "estimated_range_km",
                "motor_power_kw",
                "is_active",
                "created_at",
                "updated_at",
            ],
        ),
        "03_showrooms.csv": (
            "showrooms",
            [
                "id",
                "code",
                "name",
                "address",
                "latitude",
                "longitude",
                "phone",
                "email",
                "timezone",
                "is_active",
                "created_at",
                "updated_at",
            ],
        ),
        "04_sales_staff.csv": (
            "sales_staff",
            ["id", "showroom_id", "employee_code", "full_name", "phone", "email", "status", "created_at", "updated_at"],
        ),
        "05_demo_vehicles.csv": (
            "demo_vehicles",
            [
                "id",
                "showroom_id",
                "variant_id",
                "asset_code",
                "vin",
                "plate_number",
                "operational_status",
                "battery_soc",
                "minimum_booking_soc",
                "charging_status",
                "is_active",
                "created_at",
                "updated_at",
            ],
        ),
        # normalized_phone/email are database-only nullable derivatives, not mock CSV fields.
        "08_people.csv": (
            "people",
            ["id", "full_name", "phone", "email", "preferred_channel", "created_at", "updated_at"],
        ),
        "06_test_drive_slots.csv": (
            "test_drive_slots",
            [
                "id",
                "showroom_id",
                "demo_vehicle_id",
                "start_at",
                "end_at",
                "status",
                "held_until",
                "current_booking_id",
                "block_reason",
                "created_at",
                "updated_at",
            ],
        ),
        "09_bookings.csv": (
            "bookings",
            [
                "id",
                "booking_code",
                "slot_id",
                "booker_person_id",
                "driver_person_id",
                "status",
                "held_at",
                "hold_expires_at",
                "confirmed_at",
                "checked_in_at",
                "completed_at",
                "cancelled_at",
                "cancellation_reason",
                "rescheduled_from_booking_id",
                "replaced_by_booking_id",
                "source_channel",
                "version",
                "created_at",
                "updated_at",
            ],
        ),
        "07_slot_sales_assignments.csv": (
            "slot_sales_assignments",
            ["id", "slot_id", "sales_staff_id", "assignment_role", "status", "created_at", "updated_at"],
        ),
        "10_booking_driver_details.csv": (
            "booking_driver_details",
            [
                "booking_id",
                "license_number",
                "declared_license_class",
                "required_license_class",
                "validity_acknowledged",
                "license_check_status",
                "checked_at",
                "checked_by",
                "rejection_reason",
                "created_at",
                "updated_at",
            ],
        ),
        "11_notification_plans.csv": (
            "notification_plans",
            [
                "booking_id",
                "primary_recipient_role",
                "copy_booker",
                "sms_enabled",
                "email_enabled",
                "reminder_24h_enabled",
                "reminder_2h_enabled",
                "custom_plan_json",
                "created_at",
                "updated_at",
            ],
        ),
        "12_notification_jobs.csv": (
            "notification_jobs",
            [
                "id",
                "booking_id",
                "recipient_person_id",
                "notification_type",
                "channel",
                "scheduled_at",
                "status",
                "sent_at",
                "provider_message_id",
                "attempt_count",
                "error_message",
                "created_at",
                "updated_at",
            ],
        ),
        "13_otp_challenges.csv": (
            "otp_challenges",
            [
                "id",
                "booking_id",
                "purpose",
                "channel",
                "destination_masked",
                "destination_hash",
                "code_hash",
                "expires_at",
                "attempt_count",
                "max_attempts",
                "resend_count",
                "status",
                "verified_at",
                "created_at",
            ],
        ),
        # token_hash is generated during import because mock sessions contain no usable raw token.
        "14_booking_access_sessions.csv": (
            "booking_access_sessions",
            ["id", "booking_id", "otp_challenge_id", "permissions_json", "expires_at", "revoked_at", "created_at"],
        ),
        "15_booking_events.csv": (
            "booking_events",
            ["id", "booking_id", "event_type", "actor_type", "actor_id", "payload_json", "created_at"],
        ),
    }

    V5_DATASET_FILES = {
        "01_provinces.csv": (
            "provinces",
            _columns(
                "id,code,name,normalized_name,unit_type,effective_from,effective_to,is_active,created_at,updated_at"
            ),
        ),
        "02_districts.csv": (
            "districts",
            _columns(
                "id,province_id,code,name,normalized_name,unit_type,effective_from,effective_to,is_active,created_at,updated_at"
            ),
        ),
        "03_wards.csv": (
            "wards",
            _columns(
                "id,district_id,province_id,code,name,normalized_name,unit_type,effective_from,effective_to,is_active,created_at,updated_at"
            ),
        ),
        "04_showrooms.csv": (
            "showrooms",
            _columns(
                "id,code,name,province_id,district_id,ward_id,address,normalized_address,latitude,longitude,phone,email,timezone,region,map_visible,is_active,created_at,updated_at"
            ),
        ),
        "05_showroom_source_metadata.csv": (
            "showroom_source_metadata",
            _columns(
                "showroom_id,public_source_id,source_system,source_url,verification_status,quality_status,source_checked_at,notes,created_at,updated_at"
            ),
        ),
        "06_showroom_services.csv": (
            "showroom_services",
            _columns(
                "showroom_id,test_drive_enabled,service_enabled,delivery_enabled,charging_enabled,created_at,updated_at"
            ),
        ),
        "07_showroom_operating_hours.csv": (
            "showroom_operating_hours",
            _columns("id,showroom_id,day_of_week,open_time,close_time,is_closed,created_at,updated_at"),
        ),
        "08_vehicle_models.csv": (
            "vehicle_models",
            _columns(
                "id,code,name,vehicle_type,required_license_class,license_requirement_note,seat_count,test_drive_eligible,is_active,created_at,updated_at"
            ),
        ),
        "09_vehicle_variants.csv": (
            "vehicle_variants",
            _columns(
                "id,model_id,code,name,battery_capacity_kwh,estimated_range_km,motor_power_kw,default_test_drive_minutes,is_active,created_at,updated_at"
            ),
        ),
        "10_demo_vehicles.csv": (
            "demo_vehicles",
            _columns(
                "id,showroom_id,variant_id,asset_code,vin,plate_number,operational_status,battery_soc,minimum_booking_soc,charging_status,is_active,created_at,updated_at"
            ),
        ),
        "11_sales_staff.csv": (
            "sales_staff",
            _columns("id,showroom_id,employee_code,full_name,phone,email,role,status,is_active,created_at,updated_at"),
        ),
        "12_internal_users.csv": (
            "internal_users",
            _columns(
                "id,username,display_name,password_salt,password_hash,role,staff_id,is_active,last_login_at,created_at,updated_at"
            ),
        ),
        "13_internal_user_showrooms.csv": (
            "internal_user_showrooms",
            _columns("user_id,showroom_id,created_at"),
        ),
        "14_internal_sessions.csv": (
            "internal_sessions",
            _columns("token_hash,user_id,expires_at,revoked_at,created_at"),
        ),
        "15_staff_shifts.csv": (
            "staff_shifts",
            _columns("id,sales_staff_id,showroom_id,start_at,end_at,status,created_by,created_at,updated_at"),
        ),
        "16_staff_unavailability.csv": (
            "staff_unavailability",
            _columns("id,sales_staff_id,showroom_id,start_at,end_at,reason,created_by,created_at,updated_at"),
        ),
        "17_vehicle_unavailability.csv": (
            "vehicle_unavailability",
            _columns("id,demo_vehicle_id,showroom_id,start_at,end_at,reason,created_by,created_at,updated_at"),
        ),
        "18_vehicle_transfers.csv": (
            "vehicle_transfers",
            _columns(
                "id,demo_vehicle_id,from_showroom_id,to_showroom_id,requested_by,approved_by,completed_by,status,requested_at,approved_at,completed_at,reason"
            ),
        ),
        "19_people.csv": (
            "people",
            _columns(
                "id,full_name,phone,email,preferred_channel,normalized_phone,normalized_email,created_at,updated_at"
            ),
        ),
        "20_test_drive_slots.csv": (
            "test_drive_slots",
            _columns(
                "id,showroom_id,demo_vehicle_id,start_at,end_at,status,held_until,current_booking_id,block_reason,created_at,updated_at"
            ),
        ),
        "21_slot_sales_assignments.csv": (
            "slot_sales_assignments",
            _columns("id,slot_id,sales_staff_id,assignment_role,status,created_at,updated_at"),
        ),
        "22_bookings.csv": (
            "bookings",
            _columns(
                "id,booking_code,slot_id,booker_person_id,driver_person_id,status,held_at,hold_expires_at,confirmed_at,checked_in_at,completed_at,cancelled_at,no_show_at,cancellation_reason,rescheduled_from_booking_id,replaced_by_booking_id,assigned_sales_staff_id,source_channel,customer_note,internal_note,version,created_at,updated_at"
            ),
        ),
        "23_booking_driver_details.csv": (
            "booking_driver_details",
            _columns(
                "booking_id,has_driving_license,declared_license_class,required_license_class,validity_acknowledged,license_check_status,checked_at,checked_by,rejection_reason,created_at,updated_at"
            ),
        ),
        "24_booking_reschedules.csv": (
            "booking_reschedules",
            _columns("id,old_booking_id,new_booking_id,requested_by_person_id,reason,created_at"),
        ),
        "25_booking_events.csv": (
            "booking_events",
            _columns("id,booking_id,event_type,actor_type,actor_id,payload_json,created_at"),
        ),
        "26_idempotency_records.csv": (
            "idempotency_records",
            _columns(
                "action_id,operation,request_hash,status,resource_id,response_json,error_code,created_at,expires_at"
            ),
        ),
        "27_notification_plans.csv": (
            "notification_plans",
            _columns(
                "booking_id,primary_recipient_role,copy_booker,zalo_enabled,sms_enabled,email_enabled,reminder_24h_enabled,reminder_2h_enabled,custom_plan_json,created_at,updated_at"
            ),
        ),
        "28_notification_jobs.csv": (
            "notification_jobs",
            _columns(
                "id,booking_id,recipient_person_id,notification_type,channel,scheduled_at,status,attempt_count,max_attempts,last_attempt_at,sent_at,provider_name,provider_status,provider_message_id,is_mock,provider_response_json,error_message,created_at,updated_at"
            ),
        ),
        "29_otp_challenges.csv": (
            "otp_challenges",
            _columns(
                "id,booking_id,purpose,channel,destination_masked,destination_hash,code_hash,expires_at,attempt_count,max_attempts,resend_count,status,verified_at,consumed_at,created_at"
            ),
        ),
        "30_booking_access_sessions.csv": (
            "booking_access_sessions",
            _columns("id,token_hash,booking_id,otp_challenge_id,permissions_json,expires_at,revoked_at,created_at"),
        ),
        "31_zalo_identity_links.csv": (
            "zalo_identity_links",
            _columns("id,person_id,phone_hash,zalo_user_id,is_active,linked_at"),
        ),
        "32_internal_audit_events.csv": (
            "internal_audit_events",
            _columns("id,actor_user_id,action,resource_type,resource_id,showroom_id,payload_json,created_at"),
        ),
    }

    DATASET_REFERENCES = {
        "02_vehicle_variants.csv": (("model_id", "vehicle_models", "id", "01_vehicle_models.csv"),),
        "04_sales_staff.csv": (("showroom_id", "showrooms", "id", "03_showrooms.csv"),),
        "05_demo_vehicles.csv": (
            ("showroom_id", "showrooms", "id", "03_showrooms.csv"),
            ("variant_id", "vehicle_variants", "id", "02_vehicle_variants.csv"),
        ),
        "06_test_drive_slots.csv": (
            ("showroom_id", "showrooms", "id", "03_showrooms.csv"),
            ("demo_vehicle_id", "demo_vehicles", "id", "05_demo_vehicles.csv"),
        ),
        "09_bookings.csv": (
            ("slot_id", "test_drive_slots", "id", "06_test_drive_slots.csv"),
            ("booker_person_id", "people", "id", "08_people.csv"),
            ("driver_person_id", "people", "id", "08_people.csv"),
        ),
        "07_slot_sales_assignments.csv": (
            ("slot_id", "test_drive_slots", "id", "06_test_drive_slots.csv"),
            ("sales_staff_id", "sales_staff", "id", "04_sales_staff.csv"),
        ),
        "10_booking_driver_details.csv": (("booking_id", "bookings", "id", "09_bookings.csv"),),
        "11_notification_plans.csv": (("booking_id", "bookings", "id", "09_bookings.csv"),),
        "12_notification_jobs.csv": (
            ("booking_id", "bookings", "id", "09_bookings.csv"),
            ("recipient_person_id", "people", "id", "08_people.csv"),
        ),
        "13_otp_challenges.csv": (("booking_id", "bookings", "id", "09_bookings.csv"),),
        "14_booking_access_sessions.csv": (
            ("booking_id", "bookings", "id", "09_bookings.csv"),
            ("otp_challenge_id", "otp_challenges", "id", "13_otp_challenges.csv"),
        ),
        "15_booking_events.csv": (("booking_id", "bookings", "id", "09_bookings.csv"),),
    }

    @classmethod
    def _assert_dataset_references(cls, c, filename, rows, references):
        allowed_identifiers = {table: set(columns) for table, columns in cls.DATASET_FILES.values()}
        problems = []
        for column, parent_table, parent_column, parent_file in references:
            if (
                column not in rows[0]
                or parent_table not in allowed_identifiers
                or parent_column not in allowed_identifiers[parent_table]
            ):
                raise ValueError("Invalid internal dataset reference configuration.")
            values = list({row[column] for row in rows if row[column]})
            if not values:
                continue
            found = set()
            chunk_size = 500
            for i in range(0, len(values), chunk_size):
                chunk = values[i : i + chunk_size]
                marks = ",".join("?" * len(chunk))
                chunk_found = {
                    row[0]
                    for row in c.execute(
                        f"SELECT {parent_column} FROM {parent_table} WHERE {parent_column} IN ({marks})",
                        tuple(chunk),
                    )
                }
                found.update(chunk_found)
            missing = sorted(set(values) - found)
            if missing:
                preview = ", ".join(missing[:5])
                problems.append(f"{column} missing in {parent_table}: {preview}; import {parent_file} first")
        if problems:
            raise BookingError("MISSING_DEPENDENCY", f"Cannot import {filename}: " + " | ".join(problems))

    @staticmethod
    @contextmanager
    def _open_csv_reader(source: str | Path) -> Iterator[csv.DictReader]:
        if isinstance(source, Path):
            with source.open(encoding="utf-8-sig", newline="") as handle:
                yield csv.DictReader(handle)
            return
        with io.StringIO(source.lstrip("\ufeff")) as handle:
            yield csv.DictReader(handle)

    def import_eval_dataset(self, files: Mapping[str, str | Path]) -> dict:
        """Import either the legacy 15-file dataset or the V5 32-table seed atomically."""
        supplied = {name.split("/")[-1]: text for name, text in files.items()}
        v5_names = set(self.V5_DATASET_FILES)
        legacy_names = set(self.DATASET_FILES)
        is_v5 = bool(set(supplied) & v5_names)
        if is_v5 and set(supplied) & legacy_names:
            raise BookingError("INVALID_INPUT", "Không được trộn dataset legacy và V5 trong cùng một lần import.")
        dataset_files = self.V5_DATASET_FILES if is_v5 else self.DATASET_FILES
        ignored = set() if is_v5 else {"16_import_order.csv", "17_dataset_summary.csv", "18_dataset_metadata.csv"}
        unknown = sorted(set(supplied) - set(dataset_files) - ignored)
        if unknown:
            raise BookingError("INVALID_INPUT", f"File không được hỗ trợ: {', '.join(unknown)}")
        return self._import_dataset_files(supplied, dataset_files=dataset_files, is_v5=is_v5)

    def _import_dataset_files(
        self,
        supplied: dict[str, str | Path],
        *,
        dataset_files: dict[str, tuple[str, list[str]]],
        is_v5: bool,
    ) -> dict:
        counts = {}
        skipped: list[str] = []
        v5_people_by_id: dict[str, dict[str, str]] = {}
        if is_v5 and "19_people.csv" in supplied:
            with self._open_csv_reader(supplied["19_people.csv"]) as people_reader:
                v5_people_by_id = {row["id"]: row for row in people_reader}
        current_filename = "dataset"
        try:
            with self.db.transaction(immediate=True) as c:
                if is_v5 and c.dialect == "postgres":
                    c.execute("SET CONSTRAINTS ALL DEFERRED")
                for filename, (table, expected) in dataset_files.items():
                    current_filename = filename
                    if filename not in supplied:
                        continue
                    slot_filename = "20_test_drive_slots.csv" if is_v5 else "06_test_drive_slots.csv"
                    showroom_filename = "04_showrooms.csv" if is_v5 else "03_showrooms.csv"

                    insert_columns = list(expected)
                    if not is_v5 and filename == "14_booking_access_sessions.csv":
                        insert_columns.insert(1, "token_hash")
                    if not is_v5 and filename == "10_booking_driver_details.csv":
                        insert_columns.remove("license_number")
                        insert_columns.insert(1, "has_driving_license")
                    if is_v5 and filename == "18_vehicle_transfers.csv":
                        insert_columns.extend(("effective_at", "created_at", "updated_at"))
                    if is_v5 and filename == "31_zalo_identity_links.csv":
                        insert_columns.extend(("phone", "chat_id", "updated_at"))

                    conflict_columns = self._conflict_columns(table, insert_columns)
                    marks = ",".join("?" * len(insert_columns))
                    updates = ",".join(f"{col}=excluded.{col}" for col in insert_columns if col not in conflict_columns)
                    conflict = ",".join(conflict_columns)
                    action = f"DO UPDATE SET {updates}" if updates else "DO NOTHING"
                    sql = (
                        f"INSERT INTO {table}({','.join(insert_columns)}) VALUES({marks}) "
                        f"ON CONFLICT({conflict}) {action}"
                    )
                    count = 0
                    self._report_import_progress(f"Importing {filename} -> {table}")
                    with self._open_csv_reader(supplied[filename]) as reader:
                        if reader.fieldnames != expected:
                            raise BookingError(
                                "INVALID_INPUT",
                                f"Header {filename} không đúng. Cần: {','.join(expected)}",
                            )
                        batch: list[dict[str, str]] = []
                        for row in reader:
                            batch.append(row)
                            if len(batch) < self.IMPORT_BATCH_SIZE:
                                continue
                            self._import_row_batch(
                                c,
                                sql,
                                batch,
                                filename=filename,
                                slot_filename=slot_filename,
                                showroom_filename=showroom_filename,
                                insert_columns=insert_columns,
                                is_v5=is_v5,
                                v5_people_by_id=v5_people_by_id,
                                line_offset=count,
                            )
                            count += len(batch)
                            self._report_import_progress(f"  {table}: {count:,} rows")
                            batch = []
                        if batch:
                            self._import_row_batch(
                                c,
                                sql,
                                batch,
                                filename=filename,
                                slot_filename=slot_filename,
                                showroom_filename=showroom_filename,
                                insert_columns=insert_columns,
                                is_v5=is_v5,
                                v5_people_by_id=v5_people_by_id,
                                line_offset=count,
                            )
                            count += len(batch)
                            self._report_import_progress(f"  {table}: {count:,} rows")
                    counts[table] = count
                    self._report_import_progress(f"Finished {table} ({count:,} rows)")
        except BookingError:
            raise
        except DatabaseIntegrityError as exc:
            raise BookingError(
                "INVALID_INPUT",
                f"Không thể import {current_filename}: thiếu dữ liệu phụ thuộc hoặc vi phạm constraint ({exc}).",
            ) from exc
        return {
            "imported": counts,
            "total_rows": sum(counts.values()),
            "skipped": skipped,
            "dataset_version": "v5" if is_v5 else "legacy",
            "missing_expected_files": [name for name in dataset_files if name not in supplied],
        }

    def _import_row_batch(
        self,
        connection,
        sql: str,
        rows: list[dict[str, str]],
        *,
        filename: str,
        slot_filename: str,
        showroom_filename: str,
        insert_columns: list[str],
        is_v5: bool,
        v5_people_by_id: dict[str, dict[str, str]],
        line_offset: int,
    ) -> None:
        if filename == slot_filename:
            self._normalize_slot_timestamps(
                rows,
                filename=filename,
                line_offset=line_offset,
            )
        if filename == showroom_filename:
            for line, row in enumerate(rows, start=2 + line_offset):
                self._validate_coordinates(
                    row["latitude"],
                    row["longitude"],
                    context=f"at line {line} of {filename}",
                )
        if not is_v5:
            self._assert_dataset_references(
                connection,
                filename,
                rows,
                self.DATASET_REFERENCES.get(filename, ()),
            )
        values = [
            self._row_values(
                row,
                insert_columns,
                filename=filename,
                is_v5=is_v5,
                v5_people_by_id=v5_people_by_id,
            )
            for row in rows
        ]
        connection.executemany(sql, values)

    @staticmethod
    def _conflict_columns(table: str, insert_columns: list[str]) -> tuple[str, ...]:
        if table == "internal_user_showrooms":
            return ("user_id", "showroom_id")
        for candidate in ("id", "booking_id", "showroom_id", "token_hash", "action_id"):
            if candidate in insert_columns:
                return (candidate,)
        raise ValueError(f"No conflict key configured for {table}.")

    def _row_values(
        self,
        row: dict[str, str],
        insert_columns: list[str],
        *,
        filename: str,
        is_v5: bool,
        v5_people_by_id: dict[str, dict[str, str]],
    ) -> tuple:
        values = []
        for column in insert_columns:
            if not is_v5 and filename == "10_booking_driver_details.csv" and column == "has_driving_license":
                value = "1" if row.get("declared_license_class") or row.get("license_number") else None
            elif not is_v5 and filename == "14_booking_access_sessions.csv" and column == "token_hash":
                value = self._hash(row["id"], "mock-session")
            elif (
                is_v5
                and filename == "18_vehicle_transfers.csv"
                and column
                in {
                    "effective_at",
                    "created_at",
                    "updated_at",
                }
            ):
                value = row.get("completed_at") or row.get("approved_at") or row.get("requested_at") or None
            elif is_v5 and filename == "31_zalo_identity_links.csv" and column == "phone":
                value = v5_people_by_id.get(row["person_id"], {}).get("phone") or None
            elif is_v5 and filename == "31_zalo_identity_links.csv" and column == "chat_id":
                value = row["zalo_user_id"]
            elif is_v5 and filename == "31_zalo_identity_links.csv" and column == "updated_at":
                value = row["linked_at"]
            elif is_v5 and filename == "19_people.csv" and column == "normalized_phone":
                value = row.get(column) or normalize_phone(row.get("phone") or "") or None
            elif is_v5 and filename == "19_people.csv" and column == "normalized_email":
                value = row.get(column) or (row.get("email") or "").strip().casefold() or None
            else:
                value = row[column]
            values.append(None if value == "" else value)
        return tuple(values)

    def import_eval_dataset_from_dir(self, data_dir: str | Path) -> dict:
        """Import supported eval CSV files from a directory."""
        root = Path(data_dir)
        if not root.exists() or not root.is_dir():
            raise BookingError("INVALID_INPUT", f"Eval data folder not found: {root}")
        if (root / "seed" / "01_provinces.csv").exists():
            root = root / "seed"
        dataset_files = self.V5_DATASET_FILES if (root / "01_provinces.csv").exists() else self.DATASET_FILES
        extra_files = (
            []
            if dataset_files is self.V5_DATASET_FILES
            else [
                "16_import_order.csv",
                "17_dataset_summary.csv",
                "18_dataset_metadata.csv",
            ]
        )
        files: dict[str, Path] = {}
        for filename in [*dataset_files, *extra_files]:
            path = root / filename
            if path.exists():
                files[filename] = path
        if not files:
            raise BookingError("INVALID_INPUT", f"No supported eval CSV files found in: {root}")
        return self.import_eval_dataset(files)
