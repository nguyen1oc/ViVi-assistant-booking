# 2026-08-14 — Extendable mock booking window

- Added the optional `MOCK_SLOT_END_DATE=YYYY-MM-DD` setting to
  `backend/scripts/seed_dev_db.py`.
- After importing the legacy fixture, the seed script copies only the final
  day's available slots into each following day through the supplied date.
- Existing bookings, holds, blocked slots, and staff assignments are not
  copied. This keeps public MVP availability open without changing the source
  fixture CSV or invalidating its existing relations.
