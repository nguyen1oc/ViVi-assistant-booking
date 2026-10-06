from __future__ import annotations

from src.services.booking.base import BookingBase
from src.services.booking.common import iso, new_id

_id = new_id


class DashboardService(BookingBase):
    def get_dashboard(self, limit: int = 50) -> dict:
        """Return a read-only operational snapshot without OTP or raw license data."""
        with self.db.connect() as c:
            booking_counts = {
                r["status"]: r["count"] for r in c.execute("SELECT status,count(*) count FROM bookings GROUP BY status")
            }
            slot_counts = {
                r["status"]: r["count"]
                for r in c.execute("SELECT status,count(*) count FROM test_drive_slots GROUP BY status")
            }
            rows = c.execute(
                """SELECT b.id,b.booking_code,b.status,b.source_channel,b.version,b.created_at,b.updated_at,
                s.start_at,s.end_at,sh.name showroom_name,m.name vehicle_model,v.name vehicle_variant,
                bp.full_name booker_name,dp.full_name driver_name
                FROM bookings b JOIN test_drive_slots s ON s.id=b.slot_id

                JOIN showrooms sh ON sh.id=s.showroom_id JOIN demo_vehicles d ON d.id=s.demo_vehicle_id
                JOIN vehicle_variants v ON v.id=d.variant_id JOIN vehicle_models m ON m.id=v.model_id
                LEFT JOIN people bp ON bp.id=b.booker_person_id LEFT JOIN people dp ON dp.id=b.driver_person_id
                ORDER BY b.updated_at DESC LIMIT ?""",
                (min(max(limit, 1), 200),),
            ).fetchall()
            pending_jobs = c.execute(
                "SELECT count(*) FROM notification_jobs WHERE status IN ('pending','processing')"
            ).fetchone()[0]
            active_holds = c.execute(
                "SELECT count(*) FROM bookings WHERE status='held' AND hold_expires_at>?", (iso(self.now()),)
            ).fetchone()[0]
        return {
            "booking_counts": booking_counts,
            "slot_counts": slot_counts,
            "active_holds": active_holds,
            "pending_notification_jobs": pending_jobs,
            "recent_bookings": [dict(r) for r in rows],
            "generated_at": iso(self.now()),
        }
