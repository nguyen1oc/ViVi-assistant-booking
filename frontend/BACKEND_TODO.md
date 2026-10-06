# Backend dependencies

This file records frontend needs only. It does not imply that the frontend may
mock a successful response or that backend work is included in the current batch.

## P1 — Structured vehicle catalogue summary

- Frontend need: render the homepage vehicle comparison cards with authoritative
  range, charging and exterior-color data without issuing one detail request per
  vehicle.
- Dependent screen/component: `/`, `HomePage.VehicleRail`, `useVehicleCatalog`,
  `api/adapters.js`.
- Proposed endpoint: extend existing `GET /api/v1/vehicles`; keep the current
  `category`, `featured` and `testDriveEligible` query parameters and response
  envelope.
- Proposed response additions per vehicle:

```json
{
  "range": {
    "label": "Quãng đường WLTP",
    "value": "431 km"
  },
  "charging": {
    "label": "Sạc nhanh 10–70%",
    "value": "36 phút"
  },
  "colorOptions": [
    {
      "name": "Trắng Infinity Blanc",
      "hex": "#ecece8",
      "secondaryHex": null
    }
  ]
}
```

- Validation:
  - Return explicit `null`/`[]` for unpublished facts; never substitute zero,
    a guessed number or a default color.
  - Range must name its test cycle/variant in `label`.
  - Charging time must identify its percentage window in `label`; charging
    power must retain its unit.
  - Color names must be published product names. `hex`/`secondaryHex` must be
    normalized six-digit hex colors.
  - Preserve authoritative `displayPrice`, `seats`, `testDriveEligible`,
    `sortOrder`, `revision` and ETag behavior.
- Loading/empty/error states:
  - Pending: frontend keeps catalogue-shaped skeletons visible.
  - Empty list: frontend shows the true empty-category state.
  - Request failure: frontend shows an accessible retryable error.
  - Missing field: the affected card shows `Đang cập nhật` while other facts remain usable.
- Real-time requirement: none. Product facts may retain the current catalogue
  cache policy; showroom/slot availability must not be inferred here.
- Acceptance criteria:
  - One list request is sufficient to render all default comparison facts and swatches.
  - Opening/switching a catalogue tab causes zero automatic vehicle-detail requests.
  - Data remains tied to the correct vehicle ID and backend `sortOrder`.
  - Null fields never appear as fake availability, `undefined`, or invented copy.

## P0 — Persist the selected model in a server-side booking draft

- Frontend need: the `car` chosen from the homepage must remain authoritative
  through address, showroom, slot and confirmation steps, including reload/recovery.
- Dependent screen/component: `/booking?car={vehicleId}`, `BookingPage`.
- Proposed endpoints: use the draft contract already specified in
  `BACKEND_HANDOFF.md`:
  - `POST /api/v1/test-drive/drafts`
  - `GET /api/v1/test-drive/drafts/{draftId}`
  - `PATCH /api/v1/test-drive/drafts/{draftId}`
- Proposed request/response: persist and return `selectedVehicleId`, `stage`,
  `expiresAt`, `version`, plus the selected showroom/slot only after the backend
  validates that each belongs to the same eligible vehicle flow.
- Validation:
  - Reject unknown or `testDriveEligible: false` vehicle IDs.
  - URL intent wins when starting a new draft; an older local session must not
    silently replace the explicitly selected model.
  - Showroom and slot transitions must remain consistent with the selected vehicle.
- Loading/empty/error states: restoring, restored, expired, unavailable and
  version-conflict states must be explicit; never show booking success before the
  backend confirms it.
- Real-time requirement: slot availability and holds are real-time/server-authoritative.
- Acceptance criteria: reload/retry does not change the model, create a duplicate
  draft, or present a stale model/showroom/slot combination.

## P1 — Semantic media taxonomy for vehicle detail pages

- Frontend need: place every published vehicle image and presentation film in the
  correct Exterior, Interior or Technology chapter without inferring meaning from
  a filename, array index or vehicle ID.
- Dependent screen/component: `/models/{vehicleId}`, `/cars/{vehicleId}`,
  `CarDetailPage`, `VehicleColorConfigurator`, `api/adapters.js`.
- Proposed endpoint: extend existing `GET /api/v1/vehicles/{vehicleId}`. Keep the
  current response compatible and add semantic metadata to `gallery` and
  `presentationFilm` items.
- Proposed response fields:

```json
{
  "gallery": [
    {
      "id": "vf9-interior-second-row",
      "sectionKey": "interior",
      "title": "Hàng ghế sau",
      "alt": "Khoang hành khách hàng ghế sau của VF 9",
      "url": "/media/vehicle-media/VF9/int-slide-4.webp",
      "focalPoint": "50% 50%",
      "aspectRatio": "16 / 10",
      "fit": "cover",
      "sortOrder": 30
    }
  ],
  "presentationFilm": {
    "sectionKey": "interior"
  }
}
```

- Validation:
  - `sectionKey` is one of `exterior`, `interior`, `technology` or explicit
    `uncategorized`; missing values must never be silently guessed.
  - IDs are stable and unique per vehicle; `sortOrder` is deterministic.
  - URLs are safe published media; `alt`, focal point, aspect ratio and fit match
    the asset rather than a generic template.
  - Existing typed chapters and named color images remain authoritative. The
    frontend deduplicates repeated URLs but does not discard unique media.
- Loading/empty/error states:
  - Pending detail data: frontend shows a dedicated loading state.
  - Missing category/media: the named section shows an honest updating state and
    the asset stays in the general gallery only when it is otherwise publishable.
  - Request failure: frontend shows an accessible retry action; no local fake media.
- Real-time requirement: none. Media metadata may use the current detail cache and
  ETag/revision policy.
- Acceptance criteria:
  - Every typed asset appears in the correct anchored section in backend order.
  - No categorization depends on URL text, array position or a hard-coded model ID.
  - No unique gallery asset disappears, and duplicates are shown only once.
  - Missing metadata produces an explicit general-media fallback, not a false label.

---

## Booking selection & confirmation (phát hiện khi làm Batch 5 — 16/08/2026)

Tất cả các mục dưới đây đã được kiểm chứng bằng cách gọi API thật trên máy local,
không phải suy đoán từ đọc code.

### P0 — `hold_slot` không trả ngày/giờ của slot vừa giữ
- Quan sát: `POST /api/v1/chat` với `action: "hold_slot"` trả về đúng các khoá
  `booking_id, hold_expires_at, remaining_seconds, showroom, status, version`.
  Không có `slot_time`, `slot_date` hay `start_at`.
- Vì sao là vấn đề: khi ViVi giữ chỗ từ tin nhắn tự do, frontend không có gì để
  hiển thị ngày giờ trong hộp xác nhận. Bản cũ đã lấp bằng chuỗi ghi cứng
  `'21:00 - 22:00'` và mang chuỗi đó ra tới phiếu review lẫn màn thành công —
  tức là bịa giờ hẹn. Đã gỡ ở frontend; hiện phải gọi lại `search_options`
  để tra ngược, tốn thêm một vòng mạng.
- Đề nghị: `hold_slot` trả kèm `slot` gồm `id`, `start_at`, `end_at` (ISO, có
  offset), hoặc `slot_date` + `slot_time` đã format sẵn như draft.

### P0 — `get_draft` trả `slot_date` và `slot_time` bằng `null`
- Quan sát: `action: "get_draft"` trả `slot_date: null`, `slot_time: null`, dù
  `src/services/booking/lifecycle.py::_draft` có tính hai trường này từ bảng
  `test_drive_slots`. Nhiều khả năng response model đã lược mất field.
- Hệ quả: đường dự phòng thứ hai để lấy giờ thật cũng không dùng được.

### P1 — Slot đang ở trạng thái `held` vẫn xuất hiện trong `search_options`
- Quan sát: giữ chỗ một slot xong, gọi lại `search_options` cho đúng showroom thì
  slot đó VẪN nằm trong danh sách khả dụng (120/120 slot, có cả slot vừa giữ).
- Hệ quả: hai người dùng có thể cùng thấy một khung giờ; người thứ hai chỉ biết
  mất chỗ khi bấm giữ và nhận `SLOT_NO_LONGER_AVAILABLE`. Frontend đã xử lý lỗi
  này, nhưng lọc từ backend sẽ đỡ cho người dùng hơn.

### P0 — Không có contract OTP cho việc xác nhận booking MỚI (chặn Batch 5b)
- Quan sát: `request_access` chỉ nhận `purpose` thuộc
  `lookup, reschedule, cancel, update_details, update_notifications`
  (`src/services/booking/access.py`), và chỉ chấp nhận booking đã ở trạng thái
  `confirmed` (với `lookup` thì thêm `checked_in, completed, no_show`).
  Booking đang `held` KHÔNG thể xin OTP.
- Kết luận: không thể thêm bước OTP trước khi chốt lịch nếu backend chưa mở
  `purpose` mới cho booking `held`. Batch 5b dừng ở đây, chưa code gì.

### P1 — `confirm_booking` chỉ có một trạng thái (ảnh hưởng Batch 5c)
- Quan sát: response luôn là `status: "confirmed"` (ghi cứng ở `lifecycle.py`),
  kèm `booking_code`, `confirmed_at`, `advisor`.
- Kết luận: kế hoạch Batch 5c muốn biểu diễn `received / pending / confirmed`
  nhưng backend không phát sinh hai trạng thái đầu. Frontend KHÔNG tự dựng thêm
  trạng thái không có thật. Khi nào backend có luồng chờ duyệt thì mở lại việc này.

### Đã xử lý — Nhả chỗ đang giữ
- Frontend gọi `release_hold(booking_id)` khi đổi slot, đổi xe hoặc khi TTL 5 phút hết hạn.
- Backend đồng thời cleanup hold hết hạn và tự thu hồi hold cũ trước khi giữ lại slot.

### Ghi chú vận hành — dữ liệu slot local hết hạn
- 16/08/2026: toàn bộ 1344 slot trong `backend/data/app.db` nằm trong 09→15/08 nên
  mọi tìm kiếm đều trả 0 kết quả và không thể đặt lịch. `_extend_mock_slots` trong
  `scripts/seed_dev_db.py` chỉ chạy ở nhánh eval-dataset, nên với setup local
  (`AUTO_LOAD_EVAL_DATA=false`) nó không bao giờ được gọi.
- Đề nghị: gọi `_extend_mock_slots` ở cả nhánh fixture, hoặc bổ sung ghi chú vào
  `RUN_LOCAL.md` về việc phải nạp thêm slot định kỳ.

---

## Tra cứu · đổi · huỷ lịch (Batch 7 — 16/08/2026)

### P0 — Xin OTP trả HTTP 500 khi Gmail chưa bật
- Quan sát: `POST /api/v1/demo/action` action `request_access` với
  `preferred_channel: "email"` → 500. Log backend:
  `ValueError: ZaloOtpSender only supports the zalo channel`.
- Nguyên nhân: `dependencies.py` chọn `otp_sender = gmail_provider or zalo_otp_sender`.
  Env hiện tại có `ZALO_BOT_ENABLED=true` nhưng KHÔNG có `GMAIL_ENABLED`, nên sender là
  ZaloOtpSender — vốn ném ValueError với mọi kênh khác `zalo`.
- Hệ quả: TOÀN BỘ luồng tra cứu / đổi lịch / huỷ lịch không dùng được.
- Quyết định của product owner (16/08/2026): **giữ OTP qua email**, sẽ bật Gmail.
  Cần điền vào `.env`: `GMAIL_ENABLED=true`, `GMAIL_CLIENT_ID`, `GMAIL_CLIENT_SECRET`,
  `GMAIL_REFRESH_TOKEN`, `GMAIL_SENDER_EMAIL`. Nhớ **khởi động lại backend** sau khi sửa
  `.env` — `dependencies.py` dựng sender ngay lúc import module.
- Đề nghị thêm: đừng để lỗi cấu hình thoát ra thành 500. Trả mã có tên
  (vd `OTP_CHANNEL_UNAVAILABLE`) để frontend phân biệt "cấu hình sai" với "mạng lỗi".

### P2 — Rate limit OTP rất dễ tự khoá khi test
- Mỗi lần gọi `request_access` lại gia hạn cửa sổ chờ; gọi lặp vài lần là nhảy sang
  `RATE_LIMIT_EXCEEDED` khoá ~24 phút cho contact đó. Khi test thủ công phải gọi ĐÚNG
  một lần rồi chờ, hoặc đổi sang email/SĐT khác.

### Đã sửa ở frontend trong batch này (không cần backend)
- `confirmReschedule` gọi thừa `update_details` ngay trước `confirm_reschedule`, và lệnh đó
  gán `phone`/`email` của NGƯỜI ĐẶT cho người lái → đổi lịch là mất liên hệ riêng của người
  lái (mâu thuẫn với Batch 6). Nó còn suy ra "hai người là một" bằng cách so sánh TÊN.
  Đã bỏ hẳn lệnh này: `confirm_reschedule` không yêu cầu cập nhật hồ sơ trước.
- `holdReschedule` ghi đè giờ hẹn trên phiếu bằng giờ MỚI ngay khi vừa giữ chỗ, trong khi
  backend vẫn giữ lịch cũ tới lúc xác nhận. Đã bỏ, giờ cũ được giữ tới khi chốt.
- `confirmCancellation` bỏ qua response; nay kiểm `booking_status === 'cancelled'` trước
  khi báo đã huỷ.

---

## Hướng dẫn sau đặt lịch (Batch 8 — 16/08/2026)

Màn thành công nay có khối `BookingNextSteps` trả lời 4 câu: mang gì · đến đâu · khi nào ·
gọi ai. Mọi dòng đều lấy từ dữ liệu backend thật; thiếu thì hiển thị trung thực.

Đã dùng được: `showroom.address`, `showroom.phone`, `showroom.latitude/longitude` (dựng link
chỉ đường), `slot.start_at` + `slot.end_at` (tính thời lượng), `confirm_booking.advisor`.

### P1 — Không có API trả hạng GPLX yêu cầu theo mẫu xe
- `vehicle_models` trong DB có cột hạng GPLX và câu ghi chú (seed: "Yeu cau GPLX hang B1
  tro len"), nhưng `GET /vehicles/{id}` KHÔNG trả về. `booking_driver_details.
  required_license_class` cũng không xuất hiện ở response nào frontend gọi được.
- Hệ quả: mục "Mang theo" chỉ nói được chung chung "đúng hạng cho mẫu xe đã đăng ký",
  không nói được "hạng B1". Frontend KHÔNG tự suy ra hạng.
- Đề nghị: thêm `requiredLicenseClass` + `licenseNote` vào vehicle detail, hoặc trả trong
  response `confirm_booking`.

### P1 — Không có API trả kế hoạch nhắc lịch theo booking
- Backend tạo `notification_jobs` lúc xác nhận (đã kiểm trong DB: `booking_confirmation`,
  `reminder_24h`, `reminder_2h`, kênh email + sms), nhưng không trả kế hoạch này trong
  `confirm_booking` nên frontend đang nói cứng "trước 24 giờ và 2 giờ".
- Nếu showroom nào đó tắt nhắc lịch hoặc đổi mốc, giao diện sẽ nói sai.
- Đề nghị: trả `notificationPlan` (danh sách mốc + kênh) trong response xác nhận.

### P2 — Không xác nhận được là thông báo có gửi THÀNH CÔNG không
- Job được tạo, nhưng trạng thái gửi không phản hồi về frontend. Kèm với việc Gmail chưa
  bật (xem mục Batch 7), câu "chúng tôi gửi xác nhận qua email" hiện chưa được bảo chứng.
- Đề nghị: trả trạng thái gửi của `booking_confirmation` để UI nói đúng.

### P2 — `slot.end_at` từng bị frontend làm rơi
- `groupSlots` trước đây chỉ giữ `start_at`, nên không tính được thời lượng buổi lái thử.
  Đã sửa ở frontend (giữ `end_at`, `durationMinutes`). Ghi lại để backend biết field này
  đang được dùng, đừng bỏ khỏi payload.

## Ảnh mức sạc trang /charging trả 404 (phát hiện 17/08/2026)

`GET /content/pages/charging` trả `/media/content/charging/{30,60,150,250}kw.png`, nhưng file
trên đĩa backend là `.webp` (`backend/data/media/content/charging/150kw.webp`). Kết quả: 4 ảnh
mức công suất trên trang /charging luôn 404 và hiện "Ảnh đang được cập nhật".

Frontend KHÔNG sửa được: `resolveVehicleMedia` chỉ viết lại `/media/vehicle-media/` và
`/media/vehicles/` sang asset bundle; `/media/content/` đi thẳng tới backend.

Sửa một trong hai: đổi đuôi trong dữ liệu content thành `.webp`, hoặc cho tầng phục vụ media
thử đuôi khác khi tra thẳng trượt.

## Upsell 3 mẫu xe ở khung chat đặt lịch (Batch 9 — 18/08/2026)

### P1 — Chưa có API lưu và trả 3 mẫu xe mà sale admin muốn đẩy

- Nhu cầu của frontend: khách mở thẳng ViVi mà chưa xem xe nào thì khối đầu tiên
  họ nhìn thấy là 3 mẫu showroom đang muốn bán. Người quyết định 3 mẫu đó là sale
  admin, nên danh sách phải nằm ở backend, không nằm trong code frontend.
- Màn hình phụ thuộc: `/booking`, `BookingPage`, `components/booking/BookingUpsell.jsx`,
  `hooks/useSiteData.useBookingUpsell`, `api/upsell.js`.
- Endpoint đề xuất cho phía khách (công khai, có ETag để dùng chung cache với
  `/vehicles` và `/content/{page}`):

```
GET /api/v1/settings/booking-upsell
```

```json
{
  "data": {
    "vehicleIds": ["vf3", "vf9"],
    "headline": "Showroom đang ưu tiên",
    "note": "Còn xe demo trong tuần này",
    "updatedAt": "2026-08-18T09:00:00Z"
  }
}
```

- Endpoint đề xuất cho trang admin (cần xác thực nhân viên):

```
PUT /api/v1/admin/settings/booking-upsell
```

```json
{
  "vehicleIds": ["vf3", "vf9"],
  "headline": "Showroom đang ưu tiên",
  "note": "Còn xe demo trong tuần này"
}
```

- Ràng buộc phía backend:
  - `vehicleIds` nhận đúng 3 phần tử, không trùng nhau, và mỗi id phải là xe đang
    publish với `testDriveEligible = true`. Sai thì trả `422 INVALID_INPUT` kèm id
    có vấn đề, đừng lặng lẽ bỏ bớt.
  - Thứ tự trong mảng là thứ tự hiển thị trái sang phải. Giữ nguyên thứ tự admin xếp.
  - `headline` và `note` để trống được. Trống thì frontend dùng chữ mặc định
    "Showroom đang ưu tiên" và ẩn dòng phụ.
  - `PUT` xong phải làm mới ETag của `GET` để khách nhận cấu hình mới ngay lần tải kế.
- Hành vi frontend hiện tại khi chưa có endpoint: `useBookingUpsell` bắt lỗi, không
  chặn luồng đặt lịch, và chạy bộ mặc định `['vf3', 'vf8', 'vf9']` trong
  `api/upsell.js:DEFAULT_UPSELL_VEHICLE_IDS`. Đây là giá trị mặc định của một tuỳ chọn
  cấu hình, không phải dữ liệu xe bịa ra: thông tin từng chiếc xe vẫn lấy từ
  `GET /vehicles`. Hook trả thêm `source: 'admin' | 'default'` để bên admin kiểm tra
  được là cấu hình đã về tới trang khách hay chưa.
- Muốn đổi số ô upsell khác 3: sửa `UPSELL_SLOT_COUNT` trong `api/upsell.js` VÀ lưới
  `.booking-upsell__grid` trong `index.css`. Hai chỗ này phải đi cùng nhau.

## Màu xe: 3 màu mặc định gán cứng đè lên bảng màu thật (phát hiện 18/08/2026)

### P0 — ĐỪNG gán bộ màu mặc định cho mọi mẫu xe

- Chuyện đã xảy ra: commit `dc336b5` (PR #55) thêm vào vòng lặp dựng danh mục trong
  `backend/src/services/site_catalog.py` một bộ ba màu gán cứng, áp cho **cả 14 mẫu**:

```python
color_options = [
    {"name": "Trắng Infinity Blanc", "hex": "#ECECE8", "secondaryHex": None},
    {"name": "Đen Jet Black",        "hex": "#121314", "secondaryHex": None},
    {"name": "Xanh VinFast Blue",    "hex": "#0C64E6", "secondaryHex": None},
]
```

- Hậu quả, cả hai đều nghiêm trọng:
  1. **Sai sự thật.** VF 3 thật ra là Xám Zenith Grey / Hồng Rose Pink / Đỏ Crimson Red.
     Trang khách hiện tên màu bịa cho 14 mẫu xe như thể đó là màu chính hãng.
  2. **Chặn luôn đường dữ liệu đúng.** Bảng màu bổ sung bên frontend
     (`src/data/vehicle-colors.js`) chỉ nhảy vào khi backend trả **rỗng**. Có 3 màu giả
     là mảng không rỗng, nên bảng thật không bao giờ được dùng nữa.
- Điều này vi phạm đúng điều kiện đã ghi ở mục "P1 — Structured vehicle catalogue
  summary" phía trên file này: *"never substitute zero, a guessed number or a default
  color"*.
- Ràng buộc phía backend:
  - `colorOptions` trong `GET /vehicles` và `colors` trong `GET /vehicles/{id}` chỉ được
    chứa màu chính hãng có thật của **đúng mẫu đó**.
  - Mẫu chưa có dữ liệu màu thì trả `[]`. Frontend đã xử lý sẵn: hiện `Đang cập nhật`,
    hoặc lấy bảng màu bổ sung nếu mẫu đó có trong bảng.
  - Không dùng màu của mẫu này làm mặc định cho mẫu khác, kể cả để "cho đỡ trống".
- Cách kiểm tra nhanh trước khi merge: nếu hai mẫu xe khác nhau trả về danh sách màu
  giống hệt nhau, gần như chắc chắn là đang gán cứng.
- Trạng thái: đã sửa cục bộ ngày 18/08/2026 (`color_options` để rỗng, màu thật đi ra qua
  `_COLORS_BY_VEHICLE` ở endpoint chi tiết). **Bản sửa này chưa có trên nhánh `testing`** —
  ai pull `testing` về vẫn sẽ thấy 14 mẫu cùng 3 màu.

## Bảng màu chính hãng còn thiếu 8/14 mẫu (18/08/2026)

### P1 — Publish màu thật cho các mẫu backend đang trả rỗng

- Backend hiện có màu thật (`_COLORS_BY_VEHICLE`) cho 6/14 mẫu: `vf3` (3 màu), `vf5` (4),
  `vf7` (5), `vf8` (6), `vf9` (7), `herio-green` (3). Tám mẫu còn lại trả rỗng.
- Frontend đang vá tạm 5 mẫu bằng `src/data/vehicle-colors.js` (chép từ vinfast.vn,
  swatch là **ảnh chip** chứ không phải mã hex, vì sơn có kim loại nên không quy về hex
  phẳng được):

| Mẫu | Số màu frontend đang vá | Ghi chú |
|---|---|---|
| `vf8-the-he-moi` | 12 | swatch SVG |
| `minio-green` | 14 | swatch webp |
| `limo-green` | 4 | swatch webp |
| `ec-van` | 4 | swatch png |
| `nerio-green` | 4 | có hex, không có swatch ảnh |

- Ba mẫu **không có nguồn màu ở đâu cả**, đang hiện `Đang cập nhật`: `vf6`, `vf-mpv-7`,
  `ebus`. Cần bộ phận sản phẩm cung cấp trước, đừng tự suy ra từ ảnh studio.
- Khi backend publish màu thật cho mẫu nào, **xoá mẫu đó khỏi `vehicle-colors.js`**.
  Bảng bổ sung là chỗ vá tạm, không phải nguồn thứ hai để hai bên cùng giữ dữ liệu.
- Ràng buộc: mỗi màu cần `name` là tên thương mại chính thức, kèm `hex` sáu chữ số
  **hoặc** ảnh swatch. Màu hai tông (ví dụ "Vàng Summer Yellow · nóc Jet Black") phải nói
  rõ trong `name` hoặc tách `secondaryHex`.

## Danh mục xe vẫn bắt frontend gọi N+1 request (18/08/2026)

### P1 — `GET /vehicles` trả `colorOptions` rỗng nên dải xe phải gọi thêm từng mẫu

- Mục "P1 — Structured vehicle catalogue summary" ở đầu file đã yêu cầu việc này. PR #55
  có thêm trường `colorOptions` vào response, nhưng đổ dữ liệu giả vào (xem mục P0 ngay
  trên), nên sau khi dọn thì trường này lại rỗng. Yêu cầu gốc **vẫn chưa xong**.
- Hệ quả hiện tại: `hooks/useSiteData.useVehicleColorOptions` phải gọi
  `GET /vehicles/{id}` cho từng xe thuộc tab đang mở chỉ để lấy swatch.
- Khi `GET /vehicles` trả `colorOptions` thật: **xoá hẳn hook `useVehicleColorOptions`**
  và đọc thẳng `car.colorOptions` trong `api/adapters.js`. Ghi chú này đã có sẵn ở
  `hooks/useSiteData.js` dòng ~121.
