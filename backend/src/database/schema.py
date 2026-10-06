"""Database schema metadata and DDL for the booking service."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TableSchema:
    name: str
    columns: frozenset[str]


TABLES = {
    "provinces": TableSchema(
        "provinces",
        frozenset(
            {
                "id",
                "code",
                "name",
                "normalized_name",
                "unit_type",
                "effective_from",
                "effective_to",
                "is_active",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "districts": TableSchema(
        "districts",
        frozenset(
            {
                "id",
                "province_id",
                "code",
                "name",
                "normalized_name",
                "unit_type",
                "effective_from",
                "effective_to",
                "is_active",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "wards": TableSchema(
        "wards",
        frozenset(
            {
                "id",
                "district_id",
                "province_id",
                "code",
                "name",
                "normalized_name",
                "unit_type",
                "effective_from",
                "effective_to",
                "is_active",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "vehicle_models": TableSchema(
        "vehicle_models",
        frozenset(
            {
                "id",
                "code",
                "name",
                "vehicle_type",
                "required_license_class",
                "license_requirement_note",
                "seat_count",
                "test_drive_eligible",
                "is_active",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "vehicle_variants": TableSchema(
        "vehicle_variants",
        frozenset(
            {
                "id",
                "model_id",
                "code",
                "name",
                "battery_capacity_kwh",
                "estimated_range_km",
                "motor_power_kw",
                "default_test_drive_minutes",
                "is_active",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "showrooms": TableSchema(
        "showrooms",
        frozenset(
            {
                "id",
                "code",
                "name",
                "province_id",
                "district_id",
                "ward_id",
                "address",
                "normalized_address",
                "latitude",
                "longitude",
                "phone",
                "email",
                "timezone",
                "region",
                "map_visible",
                "is_active",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "showroom_source_metadata": TableSchema(
        "showroom_source_metadata",
        frozenset(
            {
                "showroom_id",
                "public_source_id",
                "source_system",
                "source_url",
                "verification_status",
                "quality_status",
                "source_checked_at",
                "notes",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "showroom_services": TableSchema(
        "showroom_services",
        frozenset(
            {
                "showroom_id",
                "test_drive_enabled",
                "service_enabled",
                "delivery_enabled",
                "charging_enabled",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "showroom_operating_hours": TableSchema(
        "showroom_operating_hours",
        frozenset(
            {
                "id",
                "showroom_id",
                "day_of_week",
                "open_time",
                "close_time",
                "is_closed",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "demo_vehicles": TableSchema(
        "demo_vehicles",
        frozenset(
            {
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
            }
        ),
    ),
    "sales_staff": TableSchema(
        "sales_staff",
        frozenset(
            {
                "id",
                "showroom_id",
                "employee_code",
                "full_name",
                "phone",
                "email",
                "role",
                "status",
                "is_active",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "test_drive_slots": TableSchema(
        "test_drive_slots",
        frozenset(
            {
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
            }
        ),
    ),
    "people": TableSchema(
        "people",
        frozenset(
            {
                "id",
                "full_name",
                "phone",
                "email",
                "preferred_channel",
                "normalized_phone",
                "normalized_email",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "bookings": TableSchema(
        "bookings",
        frozenset(
            {
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
                "no_show_at",
                "cancellation_reason",
                "rescheduled_from_booking_id",
                "replaced_by_booking_id",
                "assigned_sales_staff_id",
                "source_channel",
                "customer_note",
                "internal_note",
                "version",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "booking_driver_details": TableSchema(
        "booking_driver_details",
        frozenset(
            {
                "booking_id",
                "has_driving_license",
                "declared_license_class",
                "required_license_class",
                "validity_acknowledged",
                "license_check_status",
                "checked_at",
                "checked_by",
                "rejection_reason",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "notification_plans": TableSchema(
        "notification_plans",
        frozenset(
            {
                "booking_id",
                "primary_recipient_role",
                "copy_booker",
                "zalo_enabled",
                "sms_enabled",
                "email_enabled",
                "reminder_24h_enabled",
                "reminder_2h_enabled",
                "custom_plan_json",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "notification_jobs": TableSchema(
        "notification_jobs",
        frozenset(
            {
                "id",
                "booking_id",
                "recipient_person_id",
                "notification_type",
                "channel",
                "scheduled_at",
                "status",
                "attempt_count",
                "max_attempts",
                "last_attempt_at",
                "sent_at",
                "provider_name",
                "provider_status",
                "provider_message_id",
                "is_mock",
                "provider_response_json",
                "error_message",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "otp_challenges": TableSchema(
        "otp_challenges",
        frozenset(
            {
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
                "consumed_at",
                "created_at",
            }
        ),
    ),
    "booking_access_sessions": TableSchema(
        "booking_access_sessions",
        frozenset(
            {
                "id",
                "token_hash",
                "booking_id",
                "otp_challenge_id",
                "permissions_json",
                "expires_at",
                "revoked_at",
                "created_at",
            }
        ),
    ),
    "booking_events": TableSchema(
        "booking_events",
        frozenset({"id", "booking_id", "event_type", "actor_type", "actor_id", "payload_json", "created_at"}),
    ),
    "booking_reschedules": TableSchema(
        "booking_reschedules",
        frozenset({"id", "old_booking_id", "new_booking_id", "requested_by_person_id", "reason", "created_at"}),
    ),
    "idempotency_records": TableSchema(
        "idempotency_records",
        frozenset(
            {
                "action_id",
                "operation",
                "request_hash",
                "status",
                "resource_id",
                "response_json",
                "error_code",
                "created_at",
                "expires_at",
            }
        ),
    ),
    "slot_sales_assignments": TableSchema(
        "slot_sales_assignments",
        frozenset({"id", "slot_id", "sales_staff_id", "assignment_role", "status", "created_at", "updated_at"}),
    ),
    "internal_users": TableSchema(
        "internal_users",
        frozenset(
            {
                "id",
                "username",
                "display_name",
                "password_salt",
                "password_hash",
                "role",
                "staff_id",
                "is_active",
                "last_login_at",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "internal_user_showrooms": TableSchema(
        "internal_user_showrooms",
        frozenset({"user_id", "showroom_id", "created_at"}),
    ),
    "internal_sessions": TableSchema(
        "internal_sessions",
        frozenset({"token_hash", "user_id", "expires_at", "revoked_at", "created_at"}),
    ),
    "internal_notifications": TableSchema(
        "internal_notifications",
        frozenset(
            {
                "id",
                "recipient_user_id",
                "booking_id",
                "showroom_id",
                "notification_type",
                "title",
                "body",
                "read_at",
                "created_at",
            }
        ),
    ),
    "staff_shifts": TableSchema(
        "staff_shifts",
        frozenset(
            {
                "id",
                "sales_staff_id",
                "showroom_id",
                "start_at",
                "end_at",
                "status",
                "created_by",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "staff_unavailability": TableSchema(
        "staff_unavailability",
        frozenset(
            {
                "id",
                "sales_staff_id",
                "showroom_id",
                "start_at",
                "end_at",
                "reason",
                "created_by",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "vehicle_unavailability": TableSchema(
        "vehicle_unavailability",
        frozenset(
            {
                "id",
                "demo_vehicle_id",
                "showroom_id",
                "start_at",
                "end_at",
                "reason",
                "created_by",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "vehicle_transfers": TableSchema(
        "vehicle_transfers",
        frozenset(
            {
                "id",
                "demo_vehicle_id",
                "from_showroom_id",
                "to_showroom_id",
                "requested_by",
                "approved_by",
                "completed_by",
                "status",
                "requested_at",
                "approved_at",
                "completed_at",
                "reason",
                # Legacy portal compatibility. New V5 rows derive these values.
                "effective_at",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "internal_audit_events": TableSchema(
        "internal_audit_events",
        frozenset(
            {
                "id",
                "actor_user_id",
                "action",
                "resource_type",
                "resource_id",
                "showroom_id",
                "payload_json",
                "created_at",
            }
        ),
    ),
    "guardrail_abuse_subjects": TableSchema(
        "guardrail_abuse_subjects",
        frozenset(
            {
                "subject_hash",
                "strike_count",
                "strike_window_started_at",
                "banned_until",
                "last_violation_code",
                "updated_at",
            }
        ),
    ),
    "zalo_identity_links": TableSchema(
        "zalo_identity_links",
        frozenset(
            {
                "id",
                "person_id",
                "phone_hash",
                "zalo_user_id",
                "is_active",
                "linked_at",
                # Legacy columns remain available during migration.
                "phone",
                "chat_id",
                "updated_at",
            }
        ),
    ),
    "zalo_processed_messages": TableSchema(
        "zalo_processed_messages",
        frozenset({"message_id", "processed_at"}),
    ),
    "rate_limit_counters": TableSchema(
        "rate_limit_counters",
        frozenset({"bucket_key", "window_start", "expires_at", "count", "created_at", "updated_at"}),
    ),
    "llm_budget_ledger": TableSchema(
        "llm_budget_ledger",
        frozenset(
            {
                "id",
                "usage_date",
                "session_id",
                "client_ip",
                "conversation_id",
                "model",
                "estimated_cost_usd",
                "actual_cost_usd",
                "estimated_input_tokens",
                "estimated_output_tokens",
                "actual_input_tokens",
                "actual_output_tokens",
                "status",
                "created_at",
                "finalized_at",
            }
        ),
    ),
    "user_profiles": TableSchema(
        "user_profiles",
        frozenset({"id", "state", "merged_into_profile_id", "version", "created_at", "updated_at", "last_seen_at"}),
    ),
    "user_profile_identities": TableSchema(
        "user_profile_identities",
        frozenset(
            {
                "id",
                "profile_id",
                "identity_type",
                "identity_value",
                "trust_level",
                "source",
                "created_at",
                "last_seen_at",
            }
        ),
    ),
    "user_profile_signals": TableSchema(
        "user_profile_signals",
        frozenset(
            {
                "id",
                "profile_id",
                "category",
                "key",
                "value_json",
                "description",
                "certainty",
                "confidence",
                "source_type",
                "source_ref",
                "observed_at",
                "status",
                "superseded_by_signal_id",
                "created_at",
                "updated_at",
            }
        ),
    ),
    "booking_profile_summaries": TableSchema(
        "booking_profile_summaries",
        frozenset({"booking_id", "summary_markdown", "generated_at", "updated_at"}),
    ),
    "test_drive_context_signals": TableSchema(
        "test_drive_context_signals",
        frozenset({"id", "booking_id", "category", "key", "value_json", "description", "subject", "certainty", "confidence", "source_type", "source_participant", "source_ref", "status", "superseded_by_signal_id", "created_at", "updated_at"}),
    ),
    "driver_chat_invitations": TableSchema(
        "driver_chat_invitations",
        frozenset(
            {
                "id",
                "booking_id",
                "driver_person_id",
                "token_hash",
                "status",
                "expires_at",
                "sent_at",
                "revoked_at",
                "created_at",
                "updated_at",
            }
        ),
    ),
}

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS provinces (
 id TEXT PRIMARY KEY, code TEXT UNIQUE, name TEXT, normalized_name TEXT, unit_type TEXT,
 effective_from TEXT, effective_to TEXT, is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
 created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS districts (
 id TEXT PRIMARY KEY, province_id TEXT REFERENCES provinces(id), code TEXT UNIQUE, name TEXT,
 normalized_name TEXT, unit_type TEXT, effective_from TEXT, effective_to TEXT,
 is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)), created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS wards (
 id TEXT PRIMARY KEY, district_id TEXT REFERENCES districts(id), province_id TEXT REFERENCES provinces(id),
 code TEXT UNIQUE, name TEXT, normalized_name TEXT, unit_type TEXT, effective_from TEXT, effective_to TEXT,
 is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)), created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS vehicle_models (
 id TEXT PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 vehicle_type TEXT NOT NULL, required_license_class TEXT,
 license_requirement_note TEXT, seat_count INTEGER,
 test_drive_eligible INTEGER NOT NULL DEFAULT 1 CHECK(test_drive_eligible IN (0,1)),
 is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS vehicle_variants (
 id TEXT PRIMARY KEY, model_id TEXT NOT NULL REFERENCES vehicle_models(id), code TEXT NOT NULL,
 name TEXT NOT NULL, battery_capacity_kwh REAL, estimated_range_km REAL, motor_power_kw REAL,
 default_test_drive_minutes INTEGER,
 is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)), created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(model_id,code)
);
CREATE TABLE IF NOT EXISTS showrooms (
 id TEXT PRIMARY KEY, code TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
 province_id TEXT REFERENCES provinces(id), district_id TEXT REFERENCES districts(id), ward_id TEXT REFERENCES wards(id),
 address TEXT NOT NULL, normalized_address TEXT,
 latitude REAL NOT NULL, longitude REAL NOT NULL, phone TEXT, email TEXT,
 timezone TEXT NOT NULL DEFAULT 'Asia/Ho_Chi_Minh', region TEXT,
 map_visible INTEGER NOT NULL DEFAULT 1 CHECK(map_visible IN (0,1)),
 is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS showroom_source_metadata (
 showroom_id TEXT PRIMARY KEY REFERENCES showrooms(id), public_source_id TEXT, source_system TEXT,
 source_url TEXT, verification_status TEXT, quality_status TEXT, source_checked_at TEXT, notes TEXT,
 created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS showroom_services (
 showroom_id TEXT PRIMARY KEY REFERENCES showrooms(id),
 test_drive_enabled INTEGER NOT NULL DEFAULT 0 CHECK(test_drive_enabled IN (0,1)),
 service_enabled INTEGER NOT NULL DEFAULT 0 CHECK(service_enabled IN (0,1)),
 delivery_enabled INTEGER NOT NULL DEFAULT 0 CHECK(delivery_enabled IN (0,1)),
 charging_enabled INTEGER NOT NULL DEFAULT 0 CHECK(charging_enabled IN (0,1)),
 created_at TEXT, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS showroom_operating_hours (
 id TEXT PRIMARY KEY, showroom_id TEXT NOT NULL REFERENCES showrooms(id), day_of_week INTEGER NOT NULL,
 open_time TEXT, close_time TEXT, is_closed INTEGER NOT NULL DEFAULT 0 CHECK(is_closed IN (0,1)),
 created_at TEXT, updated_at TEXT, UNIQUE(showroom_id,day_of_week), CHECK(day_of_week BETWEEN 0 AND 6)
);
CREATE TABLE IF NOT EXISTS demo_vehicles (
 id TEXT PRIMARY KEY, showroom_id TEXT NOT NULL REFERENCES showrooms(id), variant_id TEXT NOT NULL REFERENCES vehicle_variants(id),
 asset_code TEXT NOT NULL UNIQUE, vin TEXT UNIQUE, plate_number TEXT,
 operational_status TEXT NOT NULL DEFAULT 'available' CHECK(operational_status IN ('available','in_use','charging','maintenance','out_of_service')),
 battery_soc REAL, minimum_booking_soc REAL NOT NULL DEFAULT 0,
 charging_status TEXT NOT NULL DEFAULT 'unknown' CHECK(charging_status IN ('not_charging','charging','fully_charged','unknown')),
 is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)), created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sales_staff (
 id TEXT PRIMARY KEY, showroom_id TEXT NOT NULL REFERENCES showrooms(id), employee_code TEXT NOT NULL UNIQUE,
 full_name TEXT NOT NULL, phone TEXT, email TEXT, role TEXT NOT NULL DEFAULT 'sales_consultant',
 status TEXT NOT NULL DEFAULT 'active', is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS test_drive_slots (
 id TEXT PRIMARY KEY, showroom_id TEXT NOT NULL REFERENCES showrooms(id), demo_vehicle_id TEXT NOT NULL REFERENCES demo_vehicles(id),
 start_at TEXT NOT NULL, end_at TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'available' CHECK(status IN ('available','held','booked','blocked')),
 held_until TEXT, current_booking_id TEXT, block_reason TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 CHECK(end_at > start_at), UNIQUE(demo_vehicle_id,start_at,end_at)
);
CREATE TABLE IF NOT EXISTS people (
 id TEXT PRIMARY KEY, full_name TEXT NOT NULL, phone TEXT, email TEXT, preferred_channel TEXT NOT NULL DEFAULT 'sms',
 normalized_phone TEXT, normalized_email TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS bookings (
 id TEXT PRIMARY KEY, booking_code TEXT UNIQUE, slot_id TEXT NOT NULL REFERENCES test_drive_slots(id),
 booker_person_id TEXT REFERENCES people(id), driver_person_id TEXT REFERENCES people(id),
 status TEXT NOT NULL CHECK(status IN ('held','confirmed','expired','cancelled','rescheduled','checked_in','completed','no_show')),
 held_at TEXT NOT NULL, hold_expires_at TEXT, confirmed_at TEXT, checked_in_at TEXT, completed_at TEXT,
 cancelled_at TEXT, no_show_at TEXT, cancellation_reason TEXT,
 rescheduled_from_booking_id TEXT REFERENCES bookings(id) DEFERRABLE INITIALLY DEFERRED,
 replaced_by_booking_id TEXT REFERENCES bookings(id) DEFERRABLE INITIALLY DEFERRED,
 assigned_sales_staff_id TEXT REFERENCES sales_staff(id),
 source_channel TEXT NOT NULL DEFAULT 'web', customer_note TEXT, internal_note TEXT,
 version INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS booking_driver_details (
 booking_id TEXT PRIMARY KEY REFERENCES bookings(id) ON DELETE CASCADE,
 has_driving_license INTEGER CHECK(has_driving_license IS NULL OR has_driving_license IN (0,1)),
 declared_license_class TEXT, required_license_class TEXT NOT NULL,
 validity_acknowledged INTEGER NOT NULL DEFAULT 0 CHECK(validity_acknowledged IN (0,1)),
 license_check_status TEXT NOT NULL DEFAULT 'not_provided'
  CHECK(license_check_status IN ('not_provided','declared','pending','pending_in_person','verified','rejected','declared_ineligible')),
 checked_at TEXT, checked_by TEXT REFERENCES sales_staff(id), rejection_reason TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 CHECK(has_driving_license != 0 OR validity_acknowledged = 0)
);
CREATE TABLE IF NOT EXISTS notification_plans (
 booking_id TEXT PRIMARY KEY REFERENCES bookings(id) ON DELETE CASCADE,
 primary_recipient_role TEXT NOT NULL DEFAULT 'driver', copy_booker INTEGER NOT NULL DEFAULT 0,
 zalo_enabled INTEGER NOT NULL DEFAULT 0, sms_enabled INTEGER NOT NULL DEFAULT 1, email_enabled INTEGER NOT NULL DEFAULT 1,
 reminder_24h_enabled INTEGER NOT NULL DEFAULT 1, reminder_2h_enabled INTEGER NOT NULL DEFAULT 1,
 custom_plan_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS notification_jobs (
 id TEXT PRIMARY KEY, booking_id TEXT NOT NULL REFERENCES bookings(id), recipient_person_id TEXT NOT NULL REFERENCES people(id),
 notification_type TEXT NOT NULL, channel TEXT NOT NULL, scheduled_at TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','processing','retrying','sent','failed','cancelled')),
 attempt_count INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 3,
 last_attempt_at TEXT, sent_at TEXT, provider_name TEXT, provider_status TEXT, provider_message_id TEXT,
 is_mock INTEGER NOT NULL DEFAULT 1 CHECK(is_mock IN (0,1)), provider_response_json TEXT, error_message TEXT,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS otp_challenges (
 id TEXT PRIMARY KEY, booking_id TEXT NOT NULL REFERENCES bookings(id), purpose TEXT NOT NULL,
 channel TEXT NOT NULL, destination_masked TEXT NOT NULL, destination_hash TEXT NOT NULL, code_hash TEXT NOT NULL,
 expires_at TEXT NOT NULL, attempt_count INTEGER NOT NULL DEFAULT 0, max_attempts INTEGER NOT NULL DEFAULT 5,
 resend_count INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'pending',
 verified_at TEXT, consumed_at TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS booking_access_sessions (
 id TEXT PRIMARY KEY, token_hash TEXT NOT NULL UNIQUE, booking_id TEXT NOT NULL REFERENCES bookings(id),
 otp_challenge_id TEXT NOT NULL REFERENCES otp_challenges(id), permissions_json TEXT NOT NULL,
 expires_at TEXT NOT NULL, revoked_at TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS zalo_identity_links (
 id TEXT PRIMARY KEY, person_id TEXT REFERENCES people(id), phone_hash TEXT UNIQUE, zalo_user_id TEXT UNIQUE,
 is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)), linked_at TEXT NOT NULL,
 phone TEXT UNIQUE, chat_id TEXT UNIQUE, updated_at TEXT
);
CREATE TABLE IF NOT EXISTS zalo_processed_messages (
 message_id TEXT PRIMARY KEY, processed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS rate_limit_counters (
 bucket_key TEXT NOT NULL, window_start TEXT NOT NULL, expires_at TEXT NOT NULL,
 count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 PRIMARY KEY(bucket_key, window_start)
);
CREATE TABLE IF NOT EXISTS llm_budget_ledger (
 id TEXT PRIMARY KEY, usage_date TEXT NOT NULL, session_id TEXT NOT NULL, client_ip TEXT NOT NULL,
 conversation_id TEXT, model TEXT NOT NULL, estimated_cost_usd REAL NOT NULL,
 actual_cost_usd REAL, estimated_input_tokens INTEGER NOT NULL DEFAULT 0,
 estimated_output_tokens INTEGER NOT NULL DEFAULT 0, actual_input_tokens INTEGER,
 actual_output_tokens INTEGER, status TEXT NOT NULL,
 created_at TEXT NOT NULL, finalized_at TEXT
);
CREATE TABLE IF NOT EXISTS booking_events (
 id TEXT PRIMARY KEY, booking_id TEXT NOT NULL REFERENCES bookings(id), event_type TEXT NOT NULL,
 actor_type TEXT NOT NULL, actor_id TEXT, payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS booking_reschedules (
 id TEXT PRIMARY KEY, old_booking_id TEXT NOT NULL REFERENCES bookings(id),
 new_booking_id TEXT NOT NULL REFERENCES bookings(id), requested_by_person_id TEXT REFERENCES people(id),
 reason TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS idempotency_records (
 action_id TEXT PRIMARY KEY, operation TEXT NOT NULL, request_hash TEXT,
 status TEXT NOT NULL DEFAULT 'succeeded', resource_id TEXT,
 response_json TEXT NOT NULL, error_code TEXT, created_at TEXT NOT NULL, expires_at TEXT
);
CREATE TABLE IF NOT EXISTS slot_sales_assignments (
 id TEXT PRIMARY KEY, slot_id TEXT NOT NULL REFERENCES test_drive_slots(id), sales_staff_id TEXT NOT NULL REFERENCES sales_staff(id),
 assignment_role TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 UNIQUE(slot_id, sales_staff_id, assignment_role)
);
CREATE TABLE IF NOT EXISTS internal_users (
 id TEXT PRIMARY KEY, username TEXT NOT NULL UNIQUE, display_name TEXT NOT NULL,
 password_salt TEXT NOT NULL, password_hash TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('staff','showroom_manager','operations_admin')),
 staff_id TEXT REFERENCES sales_staff(id), is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0,1)),
 last_login_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 CONSTRAINT internal_users_role_staff_binding_check
 CHECK((role='staff' AND staff_id IS NOT NULL) OR (role<>'staff' AND staff_id IS NULL))
);
CREATE TABLE IF NOT EXISTS internal_user_showrooms (
 user_id TEXT NOT NULL REFERENCES internal_users(id) ON DELETE CASCADE,
 showroom_id TEXT NOT NULL REFERENCES showrooms(id), created_at TEXT NOT NULL,
 PRIMARY KEY(user_id,showroom_id)
);
CREATE TABLE IF NOT EXISTS internal_sessions (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES internal_users(id) ON DELETE CASCADE,
 expires_at TEXT NOT NULL, revoked_at TEXT, created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS internal_notifications (
 id TEXT PRIMARY KEY, recipient_user_id TEXT NOT NULL REFERENCES internal_users(id) ON DELETE CASCADE,
 booking_id TEXT NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
 showroom_id TEXT NOT NULL REFERENCES showrooms(id),
 notification_type TEXT NOT NULL CHECK(notification_type IN ('booking_confirmed')),
 title TEXT NOT NULL, body TEXT NOT NULL, read_at TEXT, created_at TEXT NOT NULL,
 UNIQUE(recipient_user_id,booking_id,notification_type)
);
CREATE TABLE IF NOT EXISTS staff_shifts (
 id TEXT PRIMARY KEY, sales_staff_id TEXT NOT NULL REFERENCES sales_staff(id),
 showroom_id TEXT NOT NULL REFERENCES showrooms(id), start_at TEXT NOT NULL, end_at TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'scheduled' CHECK(status IN ('scheduled','cancelled')),
 created_by TEXT NOT NULL REFERENCES internal_users(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
 CHECK(end_at > start_at)
);
CREATE TABLE IF NOT EXISTS staff_unavailability (
 id TEXT PRIMARY KEY, sales_staff_id TEXT NOT NULL REFERENCES sales_staff(id),
 showroom_id TEXT NOT NULL REFERENCES showrooms(id), start_at TEXT NOT NULL, end_at TEXT NOT NULL,
 reason TEXT NOT NULL, created_by TEXT NOT NULL REFERENCES internal_users(id),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, CHECK(end_at > start_at)
);
CREATE TABLE IF NOT EXISTS vehicle_unavailability (
 id TEXT PRIMARY KEY, demo_vehicle_id TEXT NOT NULL REFERENCES demo_vehicles(id),
 showroom_id TEXT NOT NULL REFERENCES showrooms(id), start_at TEXT NOT NULL, end_at TEXT NOT NULL,
 reason TEXT NOT NULL, created_by TEXT NOT NULL REFERENCES internal_users(id),
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, CHECK(end_at > start_at)
);
CREATE TABLE IF NOT EXISTS vehicle_transfers (
 id TEXT PRIMARY KEY, demo_vehicle_id TEXT NOT NULL REFERENCES demo_vehicles(id),
 from_showroom_id TEXT NOT NULL REFERENCES showrooms(id), to_showroom_id TEXT NOT NULL REFERENCES showrooms(id),
 requested_by TEXT NOT NULL REFERENCES internal_users(id), approved_by TEXT REFERENCES internal_users(id),
 completed_by TEXT REFERENCES internal_users(id),
 status TEXT NOT NULL CHECK(status IN ('requested','approved','completed','cancelled')),
 requested_at TEXT, approved_at TEXT, completed_at TEXT, reason TEXT,
 effective_at TEXT, created_at TEXT, updated_at TEXT,
 CHECK(from_showroom_id <> to_showroom_id)
);
CREATE TABLE IF NOT EXISTS internal_audit_events (
 id TEXT PRIMARY KEY, actor_user_id TEXT NOT NULL REFERENCES internal_users(id),
 action TEXT NOT NULL, resource_type TEXT NOT NULL, resource_id TEXT,
 showroom_id TEXT REFERENCES showrooms(id), payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS guardrail_abuse_subjects (
 subject_hash TEXT PRIMARY KEY, strike_count INTEGER NOT NULL,
 strike_window_started_at TEXT NOT NULL, banned_until TEXT,
 last_violation_code TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_profiles (
 id TEXT PRIMARY KEY,
 state TEXT NOT NULL CHECK(state IN ('anonymous','trusted','merged')),
 merged_into_profile_id TEXT REFERENCES user_profiles(id), version INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_seen_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS user_profile_identities (
 id TEXT PRIMARY KEY, profile_id TEXT NOT NULL REFERENCES user_profiles(id),
 identity_type TEXT NOT NULL CHECK(identity_type IN ('conversation','anon_session','person','email_hash','phone_hash')),
 identity_value TEXT NOT NULL, trust_level TEXT NOT NULL CHECK(trust_level IN ('anonymous','trusted')),
 source TEXT NOT NULL, created_at TEXT NOT NULL, last_seen_at TEXT NOT NULL,
 UNIQUE(identity_type,identity_value)
);
CREATE TABLE IF NOT EXISTS user_profile_signals (
 id TEXT PRIMARY KEY, profile_id TEXT NOT NULL REFERENCES user_profiles(id), category TEXT NOT NULL,
 key TEXT NOT NULL, value_json TEXT NOT NULL, description TEXT,
 certainty TEXT NOT NULL CHECK(certainty IN ('known','likely','possible')),
 confidence REAL, source_type TEXT NOT NULL CHECK(source_type IN ('explicit_user','implicit_user','trusted_domain')),
 source_ref TEXT, observed_at TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','superseded','retracted')),
 superseded_by_signal_id TEXT REFERENCES user_profile_signals(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS booking_profile_summaries (
 booking_id TEXT PRIMARY KEY REFERENCES bookings(id) ON DELETE CASCADE,
 summary_markdown TEXT NOT NULL,
 generated_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS test_drive_context_signals (
 id TEXT PRIMARY KEY, booking_id TEXT NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
 category TEXT NOT NULL, key TEXT NOT NULL, value_json TEXT NOT NULL, description TEXT,
 subject TEXT NOT NULL CHECK(subject IN ('booking','booker','driver','group')),
 certainty TEXT NOT NULL CHECK(certainty IN ('known','likely','possible')), confidence REAL,
 source_type TEXT NOT NULL CHECK(source_type IN ('explicit_user','implicit_user','trusted_domain')),
 source_participant TEXT NOT NULL CHECK(source_participant IN ('booker','driver','system')),
 source_ref TEXT, status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','superseded','retracted')),
 superseded_by_signal_id TEXT REFERENCES test_drive_context_signals(id), created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS driver_chat_invitations (
 id TEXT PRIMARY KEY, booking_id TEXT NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
 driver_person_id TEXT NOT NULL REFERENCES people(id), token_hash TEXT NOT NULL UNIQUE,
 status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','expired','revoked')),
 expires_at TEXT NOT NULL, sent_at TEXT, revoked_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_variants_model_active ON vehicle_variants(model_id,is_active);
CREATE INDEX IF NOT EXISTS idx_showrooms_active ON showrooms(is_active);
CREATE INDEX IF NOT EXISTS idx_demo_lookup ON demo_vehicles(showroom_id,variant_id,operational_status,is_active);
CREATE INDEX IF NOT EXISTS idx_slots_search ON test_drive_slots(showroom_id,start_at,status);
CREATE INDEX IF NOT EXISTS idx_slots_vehicle_time ON test_drive_slots(demo_vehicle_id,start_at,end_at);
CREATE INDEX IF NOT EXISTS idx_sales_showroom ON sales_staff(showroom_id,status);
CREATE INDEX IF NOT EXISTS idx_people_normalized_phone ON people(normalized_phone);
CREATE INDEX IF NOT EXISTS idx_people_normalized_email ON people(normalized_email);
CREATE INDEX IF NOT EXISTS idx_slot_sales_slot ON slot_sales_assignments(slot_id,status);
CREATE INDEX IF NOT EXISTS idx_slot_sales_staff ON slot_sales_assignments(sales_staff_id,status,assignment_role);
CREATE INDEX IF NOT EXISTS idx_bookings_expiry ON bookings(status,hold_expires_at);
CREATE INDEX IF NOT EXISTS idx_otp_active ON otp_challenges(booking_id,status,expires_at);
CREATE INDEX IF NOT EXISTS idx_jobs_due ON notification_jobs(status,scheduled_at);
CREATE INDEX IF NOT EXISTS idx_events_timeline ON booking_events(booking_id,created_at);
CREATE INDEX IF NOT EXISTS idx_access_booking_expiry ON booking_access_sessions(booking_id,expires_at);
CREATE INDEX IF NOT EXISTS idx_zalo_identity_chat ON zalo_identity_links(chat_id);
CREATE INDEX IF NOT EXISTS idx_internal_sessions_user_expiry ON internal_sessions(user_id,expires_at);
CREATE INDEX IF NOT EXISTS idx_internal_notifications_user_read ON internal_notifications(recipient_user_id,read_at,created_at);
CREATE INDEX IF NOT EXISTS idx_internal_user_showrooms_showroom ON internal_user_showrooms(showroom_id,user_id);
CREATE UNIQUE INDEX IF NOT EXISTS idx_internal_users_staff_unique ON internal_users(staff_id) WHERE staff_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_staff_shifts_staff_time ON staff_shifts(sales_staff_id,start_at,end_at);
CREATE INDEX IF NOT EXISTS idx_staff_unavailability_staff_time ON staff_unavailability(sales_staff_id,start_at,end_at);
CREATE INDEX IF NOT EXISTS idx_vehicle_unavailability_vehicle_time ON vehicle_unavailability(demo_vehicle_id,start_at,end_at);
CREATE INDEX IF NOT EXISTS idx_vehicle_transfers_vehicle_time ON vehicle_transfers(demo_vehicle_id,effective_at);
CREATE INDEX IF NOT EXISTS idx_internal_audit_time ON internal_audit_events(created_at);
CREATE INDEX IF NOT EXISTS idx_guardrail_abuse_banned_until ON guardrail_abuse_subjects(banned_until);
CREATE INDEX IF NOT EXISTS idx_rate_limit_expiry ON rate_limit_counters(expires_at);
CREATE INDEX IF NOT EXISTS idx_llm_budget_date_status ON llm_budget_ledger(usage_date,status);
CREATE INDEX IF NOT EXISTS idx_llm_budget_session_date ON llm_budget_ledger(session_id,usage_date,status);
CREATE INDEX IF NOT EXISTS idx_llm_budget_ip_date ON llm_budget_ledger(client_ip,usage_date,status);
CREATE INDEX IF NOT EXISTS idx_user_profiles_merged ON user_profiles(merged_into_profile_id);
CREATE INDEX IF NOT EXISTS idx_profile_signals_status ON user_profile_signals(profile_id,status);
CREATE INDEX IF NOT EXISTS idx_profile_signals_key ON user_profile_signals(profile_id,category,key,status);
CREATE INDEX IF NOT EXISTS idx_booking_profile_summaries_generated ON booking_profile_summaries(generated_at);
CREATE INDEX IF NOT EXISTS idx_test_drive_context_active ON test_drive_context_signals(booking_id,subject,category,key,status);
CREATE INDEX IF NOT EXISTS idx_driver_chat_invitation_booking ON driver_chat_invitations(booking_id,status,expires_at);
"""
