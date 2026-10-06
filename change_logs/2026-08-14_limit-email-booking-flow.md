# 2026-08-14 - Limit, email OTP va booking flow

## Muc tieu

Dong bo luong booking va quan ly booking theo huong email-first, bo sung UI directive de frontend dieu huong on dinh hon, va tang do bao ve he thong bang rate limit theo session/IP/OTP.

## Thay doi backend

- Them `UiDirective` vao `ChatResponse` de backend tra ve `event`, `phase` va `allowed_actions` cho frontend sau cac tool/action quan trong.
- Bo sung mapping UI directive trong `/api/v1/chat` cho cac luong: request/verify OTP, search option, hold slot, update draft va confirm booking.
- Cap nhat classifier fallback de nhan dien cac cau hoi tra cuu lich da dat bang tieng Viet co dau/khong dau.
- Dieu chinh `AccessService.request_access()`:
  - `lookup` cho phep booking da `confirmed`, `checked_in`, `completed`, `no_show`.
  - Cac purpose thay doi/huy/doi lich van chi ap dung cho booking `confirmed`.
  - Tim booking theo `booking_code` hoac email/phone co loc status hop le.
- Cap nhat test cho structured booking action, skill node, output guard va access/OTP wrapper.
- Them test rate limit cho chat, demo action va default OTP request limit.

## Thay doi frontend

- Them state reducer `frontend/src/state/bookingInteraction.js` de quan ly mode/phase/action cua booking UI thay vi chi dua vao legacy `stage`.
- Chuan hoa context gui len agent bang `normalizeAgentContext()` va them ham reset conversation cua booking.
- Chuyen luong OTP/tra cuu sang email:
  - `requestBookingAccess()` gui `contact_value=email` va `preferred_channel=email`.
  - Form OTP hien thi email nhan OTP.
  - Loi thoai ViVi doi sang ma OTP qua email.
- Cap nhat luong workspace:
  - Tach mode dat lich moi va mode quan ly booking.
  - Chi hien action theo `allowed_actions`.
  - Cho phep dong chi tiet booking, quay lai danh sach booking, va dieu huong reschedule ro rang hon.
- Cap nhat form/profile:
  - Email la thong tin bat buoc trong flow tao/cap nhat booking.
  - So dien thoai la thong tin tuy chon trong frontend.

## Tai lieu va huong dan local

- Cap nhat `README.md` voi profile local de test OTP, rate limit, notification/reminder va Gmail.
- Bo sung huong dan reset counter, recreate backend sau khi doi `.env`, test notification due jobs va import dataset/portal local.

## Pham vi khong dua vao changelog commit nay

Khong tinh cac file plan/debug/doc tam thoi do yeu cau rieng trong qua trinh thiet ke, vi chung khong phai thay doi runtime chinh cua commit:

- `DEBUG.md`, `DEBUG_PLAN.md`
- `OTP_PERMISSION.md`
- cac file plan/adaptation report da tao rieng
- cac file artifact/local tam nhu `.tmp-home.png`, `.ai-log/.gitkeep`

## Kiem tra

- Da build frontend bang `npm.cmd run build -- --outDir .tmp-dist --emptyOutDir=true`.
- Da chay `git diff --check`.
