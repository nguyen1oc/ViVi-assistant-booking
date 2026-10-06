"""Bảng quản trị Streamlit (không nằm trong luồng chạy chính).

streamlit đã được GỠ khỏi backend/requirements.txt ngày 17/08/2026 vì nó kéo theo
pandas + pyarrow + pydeck + altair, cộng lại ~250 MB trong .venv, mà file này không được
docker-compose hay script nào gọi tới. Muốn chạy lại:

    pip install streamlit && streamlit run backend/admin_app.py
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st
from src.config import get_settings
from src.database import Database
from src.services.booking import BookingService
from src.services.booking.errors import BookingError

DATA_DIR_CANDIDATES = (
    Path("/app/eval/data"),
    Path(__file__).resolve().parents[1] / "eval" / "data",
)

RESET_ORDER = (
    "internal_audit_events",
    "internal_notifications",
    "vehicle_transfers",
    "vehicle_unavailability",
    "staff_unavailability",
    "staff_shifts",
    "internal_sessions",
    "internal_user_showrooms",
    "internal_users",
    "booking_access_sessions",
    "otp_challenges",
    "zalo_processed_messages",
    "zalo_identity_links",
    "notification_jobs",
    "notification_plans",
    "booking_events",
    "booking_reschedules",
    "booking_driver_details",
    "idempotency_records",
    "bookings",
    "slot_sales_assignments",
    "test_drive_slots",
    "demo_vehicles",
    "vehicle_variants",
    "vehicle_models",
    "sales_staff",
    "showroom_operating_hours",
    "showroom_services",
    "showroom_source_metadata",
    "showrooms",
    "wards",
    "districts",
    "provinces",
    "people",
)

TABLES = list(dict.fromkeys(table for table in RESET_ORDER if table != "idempotency_records")) + [
    "idempotency_records"
]


@st.cache_resource
def booking_service() -> BookingService:
    database = Database(get_settings().database_url)
    database.initialize()
    return BookingService(database)


def decode_uploads(uploaded_files) -> dict[str, str]:
    files: dict[str, str] = {}
    for uploaded in uploaded_files:
        files[uploaded.name.split("/")[-1]] = uploaded.getvalue().decode("utf-8-sig")
    return files


def load_eval_dir() -> tuple[Path | None, dict[str, str]]:
    for data_dir in DATA_DIR_CANDIDATES:
        if data_dir.exists():
            return data_dir, {path.name: path.read_text(encoding="utf-8-sig") for path in sorted(data_dir.glob("*.csv"))}
    return None, {}


def reset_dataset_tables(service: BookingService) -> None:
    with service.db.transaction(immediate=True) as connection:
        for table in RESET_ORDER:
            connection.execute(f"DELETE FROM {table}")


def table_count(service: BookingService, table: str) -> int:
    with service.db.connect() as connection:
        row = connection.execute(f"SELECT count(*) AS count FROM {table}").fetchone()
    return int(row["count"] if "count" in row else row[0])


def table_rows(service: BookingService, table: str, limit: int) -> list[dict]:
    with service.db.connect() as connection:
        rows = connection.execute(f"SELECT * FROM {table} LIMIT ?", (limit,)).fetchall()
    return [dict(row) for row in rows]


st.set_page_config(page_title="VinFast Booking Admin", layout="wide")
st.title("VinFast Booking Admin")

service = booking_service()

import_tab, dashboard_tab = st.tabs(["Import data", "Dashboard"])

with import_tab:
    st.subheader("Import CSV")
    import_type = st.radio(
        "CSV type",
        ("Eval dataset CSVs", "Showroom-only CSV"),
        help="Eval dataset giu nguyen id trong file. Showroom-only dung cho CSV co code,name,address,latitude,longitude.",
    )
    mode = st.radio(
        "Import mode",
        ("Upsert uploaded rows", "Replace dataset tables first"),
        help="Replace se xoa cac bang dataset/booking truoc khi import lai.",
    )
    source = st.radio("Source", ("Upload CSV files", "Read eval/data folder"))

    files: dict[str, str] = {}
    if source == "Upload CSV files":
        uploads = st.file_uploader("CSV files", type=["csv"], accept_multiple_files=True)
        files = decode_uploads(uploads or [])
    else:
        data_dir, files = load_eval_dir()
        if data_dir:
            st.caption(f"Loaded {len(files)} CSV files from {data_dir}")
        else:
            st.warning("Khong tim thay thu muc eval/data trong container/local path.")

    selected_names = st.multiselect(
        "Files to import",
        options=sorted(files),
        default=sorted(files),
    )
    selected_files = {name: files[name] for name in selected_names}

    if selected_files:
        st.caption(", ".join(selected_files))

    if st.button("Import", type="primary", disabled=not selected_files):
        try:
            if mode == "Replace dataset tables first":
                reset_dataset_tables(service)
            if import_type == "Showroom-only CSV":
                if len(selected_files) != 1:
                    st.error("Showroom-only import chi nhan 1 file CSV.")
                    st.stop()
                result = service.import_showrooms_csv(next(iter(selected_files.values())))
            else:
                result = service.import_eval_dataset(selected_files)
            st.success("Import completed")
            st.json(result)
        except BookingError as exc:
            st.error(f"{exc.code}: {exc}")
        except Exception as exc:
            st.exception(exc)

with dashboard_tab:
    st.subheader("Database dashboard")
    counts = {table: table_count(service, table) for table in TABLES}
    cols = st.columns(4)
    for index, (table, count) in enumerate(counts.items()):
        cols[index % 4].metric(table, count)

    table = st.selectbox("Table", TABLES, index=TABLES.index("showrooms"))
    limit = st.slider("Rows", min_value=10, max_value=500, value=50, step=10)
    st.dataframe(table_rows(service, table, limit), use_container_width=True, hide_index=True)
