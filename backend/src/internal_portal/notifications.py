from __future__ import annotations

from src.services.booking.common import iso

from .auth import InternalPrincipal
from .base import InternalPortalMixin
from .errors import InternalPortalError


class InternalNotificationMixin(InternalPortalMixin):
    def list_notifications(
        self,
        principal: InternalPrincipal,
        *,
        unread_only: bool = False,
        limit: int = 30,
    ) -> dict:
        where = "recipient_user_id=?"
        params: list[object] = [principal.user_id]
        if unread_only:
            where += " AND read_at IS NULL"
        with self.db.connect() as connection:
            unread_count = connection.execute(
                "SELECT count(*) FROM internal_notifications WHERE recipient_user_id=? AND read_at IS NULL",
                (principal.user_id,),
            ).fetchone()[0]
            rows = connection.execute(
                "SELECT id,booking_id,showroom_id,notification_type,title,body,read_at,created_at "
                f"FROM internal_notifications WHERE {where} ORDER BY created_at DESC LIMIT ?",
                (*params, min(max(limit, 1), 100)),
            ).fetchall()
        return {"items": [dict(row) for row in rows], "unread_count": unread_count}

    def mark_notification_read(self, principal: InternalPrincipal, notification_id: str) -> dict:
        now = iso(self.now())
        with self.db.transaction(immediate=True) as connection:
            notification = connection.execute(
                "SELECT id FROM internal_notifications WHERE id=? AND recipient_user_id=?",
                (notification_id, principal.user_id),
            ).fetchone()
            if not notification:
                raise InternalPortalError(
                    "NOTIFICATION_NOT_FOUND",
                    "Không tìm thấy thông báo.",
                    status_code=404,
                )
            connection.execute(
                "UPDATE internal_notifications SET read_at=COALESCE(read_at,?) WHERE id=? AND recipient_user_id=?",
                (now, notification_id, principal.user_id),
            )
        return {"id": notification_id, "read_at": now}

    def mark_all_notifications_read(self, principal: InternalPrincipal) -> dict:
        now = iso(self.now())
        with self.db.transaction(immediate=True) as connection:
            result = connection.execute(
                "UPDATE internal_notifications SET read_at=? WHERE recipient_user_id=? AND read_at IS NULL",
                (now, principal.user_id),
            )
        return {"updated": result.rowcount, "read_at": now}
