# VinFast frontend — Backend handoff

Tài liệu này là điểm bắt đầu cho đội backend khi nối dữ liệu thật vào UI/UX và animation hiện có. Các vị trí cần thay fixture trong source đều được đánh dấu bằng `TODO [BACKEND/*]` và trỏ về tài liệu này.

## 1. Hiện trạng

Frontend là React SPA chạy bằng Vite. **Phần lớn đã nối API thật** — mục này được viết lại sau đợt
rà soát toàn bộ source. Bản cũ của mục này ghi "chưa có request mạng thật", nay đã sai hoàn toàn.

### 1.1 Đã nối xong — không cần làm gì thêm

| Việc | Endpoint frontend đang gọi | Nơi gọi |
|---|---|---|
| Danh sách xe, chi tiết xe | `GET /api/v1/vehicles`, `GET /api/v1/vehicles/{id}` | `src/api/vehicles.js` |
| Nội dung 3 trang marketing | `GET /api/v1/content/{home\|charging\|after-sales}` | `src/api/content.js` |
| Kiểm tra sức khoẻ dịch vụ | `GET /api/v1/booking/health`, lặp mỗi 30 giây | `src/api/availability.js` |
| Tìm showroom + khung giờ thật | `POST /api/v1/chat` action `search_options` | `src/api/booking.js` |
| Giữ chỗ khung giờ | `POST /api/v1/chat` action `hold_slot` | `src/api/booking.js` |
| Lưu thông tin khách | `POST /api/v1/chat` action `update_draft` | `src/api/booking.js` |
| Chốt đặt lịch | `POST /api/v1/chat` action `confirm_booking` | `src/api/booking.js` |
| Chat tự do với ViVi | `POST /api/v1/chat` không kèm action | `src/api/booking.js` |
| Xin/xác thực OTP qua Zalo | `POST /api/v1/demo/action` action `request_access`, `verify_access` | `src/api/booking.js` |
| Xem, sửa, huỷ lịch đã đặt | `POST /api/v1/demo/action` action `get_details`, `list_bookings`, `update_details`, `cancel_booking` | `src/api/booking.js` |
| Đổi ngày giờ lịch đã đặt | `POST /api/v1/demo/action` action `hold_reschedule`, `confirm_reschedule` | `src/api/booking.js` |

Những thứ tài liệu cũ mô tả là dữ liệu giả **nay đã là dữ liệu thật**: showroom, khung giờ trống,
giữ chỗ, tạo booking, mã lịch, tra cứu/đổi/huỷ lịch, bản đồ (Leaflet với toạ độ thật).

`createSlots()` sinh lịch theo công thức đã bị xoá. `showroomDirectory` trong `BookingPage.jsx`
vẫn còn trong file nhưng **là code chết, không dòng nào tham chiếu** — đừng dùng nó làm nguồn dữ liệu.

### 1.2 Chưa nối — đây là việc backend cần làm

Xem chi tiết ở mục 1.3. Tóm tắt theo mức ưu tiên:

| Ưu tiên | Việc | Hiện đang xử lý thế nào |
|---|---|---|
| P0 | Draft đặt lịch phía server | Chỉ lưu UI state trong `sessionStorage`, mất khi đổi máy |
| P0 | Endpoint quản lý lịch có tên thật | Đang mượn `/api/v1/demo/action` cho 8 nghiệp vụ production |
| P1 | Geocoding địa chỉ | Gửi nguyên chuỗi địa chỉ cho agent, không có bước chuẩn hoá |
| P1 | Khoá bản đồ (map tiles) | Dùng tile Google không key + Leaflet tải từ CDN unpkg |
| P1 | Analytics | Chưa có gì, không sự kiện nào được gửi |
| P2 | CMS cho media marketing | Ảnh/video/brochure nhúng sẵn trong bundle |
| P2 | Model 3D qua API | 3 file .glb là asset frontend, chưa có `model3dUrl` |
| P2 | Streaming câu trả lời ViVi | Chờ trọn câu trả lời rồi mới hiện |

### 1.3 Chi tiết từng việc chưa nối

**P0 — Draft đặt lịch phía server.** `BookingPage.jsx` lưu tiến trình vào `sessionStorage` với khoá
`vinfast:booking-ui-state`. Đổi máy hoặc đổi trình duyệt là mất. Cần `POST/GET/PATCH
/api/v1/test-drive/drafts` như mục 4; frontend chỉ giữ `draftId` dạng opaque. Dòng chữ
"Tiến trình được giữ trên thiết bị" trong header trang đặt lịch chỉ đúng hoàn toàn sau khi có API này.

**P0 — Đổi tên `/api/v1/demo/action`.** Tám nghiệp vụ production (OTP, tra cứu, sửa, huỷ, đổi lịch)
đang đi qua endpoint tên là "demo". Backend README cũng ghi endpoint này là "adapter demo cũ".
Cần endpoint thật theo mục 4; frontend chỉ phải sửa `bookingManagementAction` trong `src/api/booking.js`.

**P1 — Geocoding.** Người dùng gõ địa chỉ tự do, frontend gửi thẳng chuỗi đó cho agent. Không có
`provinceId`/`wardId`/`lat`/`lng` chuẩn hoá, nên không phân biệt được "địa chỉ mơ hồ" với "không có
showroom". Cần `POST /api/v1/locations/geocode` trả `confidence` để frontend biết khi nào hỏi lại phường/xã.

**P1 — Bản đồ.** `src/components/booking/ShowroomMap.jsx` tải Leaflet 1.9.4 từ `unpkg.com` lúc chạy
và dùng tile của Google **không có API key**. Không dùng được cho production. Cần chốt nhà cung cấp
bản đồ và cấp key giới hạn domain qua `VITE_MAPS_PROVIDER_KEY`. Mất mạng thì bản đồ không hiện.

**P1 — Analytics.** Không có `gtag`, `dataLayer` hay hàm track nào trong source. Danh sách sự kiện
đề xuất ở mục 10 vẫn chưa được cài. Cần chốt nhà cung cấp trước khi frontend gắn.

**P2 — CMS media marketing.** Ảnh trang chủ, ảnh ViVi, ảnh hậu mãi, ảnh trạm sạc và toàn bộ brochure
PDF đang nhúng trong bundle qua `src/media/assets.js`. Contract thay thế đã mô tả ở mục 5.

**P2 — Model 3D.** Ba file `.glb` (VF 3, VF 9, trạm sạc) nằm ở `src/media/local/models/`, đã nén
Draco còn 3,0 MB. Cấu hình góc camera ở `src/data/vehicle3d.js`. Khi backend phục vụ được model,
trả `model3dUrl` + `model3dPreset` đã whitelist; **không trả góc camera, CSS hay JavaScript**.

Nguồn VF 5 nhận ngày 11/08/2026 chưa được đưa vào runtime: file `_phys.gltf` là mesh va chạm
không có material/texture, còn model chính phụ thuộc extension riêng `ENS_buffer` và
`ENS_material` của Enscape. Cả hai buffer đều đã mã hoá và không phải glTF/GLB web tiêu chuẩn.
Cần xuất lại VF 5 thành `.glb` PBR tiêu chuẩn (không có `ENS_*` trong `extensionsRequired`), kèm
quyền sử dụng/credit, rồi mới chạy pipeline Draco và thêm `vf5` vào `vehicle3dModels`.

**P2 — Streaming ViVi.** `sendBookingMessage` chờ trọn câu trả lời. Khi backend mở streaming,
chỉ cần đổi hàm này, không phải đụng vào UI.

### 1.4 Cố ý không nối — đừng "sửa"

- **Lạc Hồng 900 LX và 900S** là xe trưng bày, **chưa mở bán và chưa cho lái thử**. Hai mẫu này
  cố ý KHÔNG nằm trong catalogue backend, không có trang chi tiết, không có link tới `/booking`.
  Cấu hình ở `src/media/vehicle-media-map.js` (`showcaseMediaMap`, cờ `bookable: false`).
  Chỉ bật lên khi VinFast thực sự mở lái thử.
- **`src/data/cars.js`** chỉ còn giữ tên 2 nhóm xe (`personal` / `fleet`) để chia tab. Toàn bộ
  danh sách xe đã lấy từ API. `id` trong đó phải khớp `category` backend trả về.

Không thay cấu trúc JSX/CSS khi nối API nếu không có thay đổi UX đã được duyệt. Ưu tiên thay nguồn
dữ liệu và action tại đúng marker `TODO [BACKEND/*]` trong source.

## 2. Cấu hình môi trường và deploy

Các biến frontend đề xuất:

```text
VITE_API_BASE_URL=https://api.example.vn
VITE_MAPS_PROVIDER=google
VITE_MAPS_PROVIDER_KEY=<public-domain-restricted-key>
VITE_ANALYTICS_ENABLED=true
```

- Không đặt private key hoặc service credential trong biến `VITE_*`; mọi biến này đều có thể đọc được trong browser.
- Nginx phải dùng `try_files $uri /index.html` cho `/cars/:id`, `/booking`, `/after-sales`, `/charging` và các route SPA khác.
- `/api` không được rơi vào SPA fallback. Nếu reverse proxy, đặt timeout riêng cho agent streaming.
- Không cache response booking/lookup. Asset có hash trong `dist/assets` có thể cache immutable.
- API dùng TLS, CORS allowlist và cookie `Secure; HttpOnly; SameSite=Lax` nếu chọn cookie session.

## 3. State machine đặt lịch

Backend agent/draft phải trả đúng `nextStage` trong tập giá trị bên dưới. Không để LLM tự phát minh stage hoặc action UI.

| Stage | Mục đích UX | Workspace | Hành động server chính |
|---|---|---|---|
| `idle` | Chờ chọn người lái | agent-only | Tạo/khôi phục draft |
| `need_car` | Chưa có xe gần nhất | agent-only | Lấy xe đủ điều kiện lái thử |
| `need_address` | Hỏi địa chỉ chi tiết | car | Geocode input |
| `need_ward` | Đã có tỉnh nhưng thiếu phường/xã | car | Trả clarification |
| `choose_showroom` | Chọn 3–4 showroom có đúng xe | map | Query inventory + distance |
| `choose_slot` | Chọn ngày/giờ có đúng xe | schedule | Query live slots |
| `collect_info` | Nhập thông tin trong panel agent | schedule | Tạo/kiểm tra hold, validate form |
| `review` | Kiểm tra phiếu trước khi đặt | ticket | Validate hold còn hiệu lực |
| `success` | Xe + phiếu + ViVi thành công | success layout | Booking đã commit |
| `lookup` | Tra cứu lịch đã đặt | agent | Xác minh khách hàng, trả allowed actions |

Quy tắc chuyển stage:

1. Nếu URL có `?car=<vehicleId>` hoặc draft có `selectedVehicleId`, sau modal người lái chuyển thẳng `need_address`.
2. Nếu chỉ nhận diện được tỉnh/thành, giữ màn hình xe và trả `need_ward`; không tải toàn bộ showroom của tỉnh.
3. Chỉ chuyển `choose_showroom` sau khi có địa chỉ chuẩn hoá tới phường/xã hoặc lat/lng đủ tin cậy.
4. Showroom phải có đúng `vehicleId` trước, khoảng cách chỉ là tiêu chí xếp hạng thứ hai.
5. Chỉ chuyển `collect_info` sau khi server tạo hold thành công.
6. Chỉ chuyển `success` sau khi booking được commit idempotently.
7. Khi 409/410 ở hold hoặc create booking, quay lại `choose_slot`; giữ nguyên địa chỉ, showroom và form khách hàng.

## 4. API map đề xuất

Tên endpoint có thể đổi theo chuẩn nội bộ, nhưng payload và lifecycle cần giữ tương đương.

| Method | Endpoint | Nơi dùng | Ghi chú |
|---|---|---|---|
| `GET` | `/api/v1/vehicles` | Home, menu, switcher | Có `sortOrder`, category và test-drive eligibility |
| `GET` | `/api/v1/vehicles/{id}` | Trang chi tiết, panel xe | Trả specs, colors, presentation và brochure revision |
| `GET` | `/api/v1/vehicles/{id}/media` | Detail gallery/chapters | Media có type, tone, focal point, sort order |
| `GET` | `/api/v1/content/home?locale=vi-VN` | Home | Hero, video, editorial panels, testimonial đã publish |
| `GET` | `/api/v1/content/ownership?locale=vi-VN` | Hậu mãi, pin & trạm sạc | Policy blocks có revision, effectiveAt, source document và sortOrder |
| `POST` | `/api/v1/test-drive/drafts` | Bắt đầu flow | Trả `draftId`, `stage`, `expiresAt` |
| `GET` | `/api/v1/test-drive/drafts/{id}` | Reload/khôi phục | Không trả PII nếu draft chưa được xác minh |
| `PATCH` | `/api/v1/test-drive/drafts/{id}` | Mỗi lựa chọn | Patch recipient, vehicle, address, showroom, stage |
| `POST` | `/api/v1/locations/geocode` | Nhập địa chỉ | Trả province/ward ids, lat/lng, formattedAddress, confidence |
| `GET` | `/api/v1/test-drive/showrooms` | Map/cards | Query `vehicleId`, `lat`, `lng`; có inventory + distance |
| `GET` | `/api/v1/test-drive/vehicles?showroomId=` | Đổi xe | Chỉ xe lái thử thực sự khả dụng ở showroom |
| `GET` | `/api/v1/test-drive/slots` | Schedule/cards | Query `showroomId`, `vehicleId`, date range |
| `POST` | `/api/v1/test-drive/holds` | Xác nhận slot | Atomic hold; trả `holdId`, `holdExpiresAt` |
| `DELETE` | `/api/v1/test-drive/holds/{id}` | Đổi xe/slot, thoát flow | Idempotent release |
| `POST` | `/api/v1/test-drive/bookings` | Xác nhận cuối | Bắt buộc `Idempotency-Key` |
| `POST` | `/api/v1/test-drive/bookings/lookup` | Tra cứu | Tên + điện thoại; có challenge/OTP nếu cần |
| `PATCH` | `/api/v1/test-drive/bookings/{id}/reschedule` | Bổ sung/đổi lịch | Dùng hold mới, idempotent |
| `POST` | `/api/v1/test-drive/bookings/{id}/cancel` | Huỷ lịch | Trả trạng thái và thời điểm huỷ |
| `POST` | `/api/v1/booking-agent/sessions` | Khởi tạo ViVi | Gắn với draft, không nhúng PII vào prompt log |
| `POST` | `/api/v1/booking-agent/messages` | Prompt ViVi | Stream text + structured UI actions |

## 5. Contract xe và media

Ví dụ tối thiểu:

```json
{
  "id": "vf6",
  "name": "VF 6",
  "navName": "VF 6",
  "category": "personal",
  "body": "SUV hạng B",
  "seatCount": 5,
  "price": {
    "amount": 689000000,
    "currency": "VND",
    "label": "Giá niêm yết"
  },
  "tagline": "Mạnh mẽ và tinh tế.",
  "description": "...",
  "testDriveEligible": true,
  "sortOrder": 30,
  "brochure": {
    "label": "VF 6 Brochure",
    "url": "https://cdn.example.vn/...pdf",
    "revision": "2026-01-29"
  },
  "presentation": {
    "heroImageUrl": "https://cdn.example.vn/...webp",
    "studioImageUrl": "https://cdn.example.vn/...png",
    "studioImageMode": "cutout",
    "motionImageUrl": "https://cdn.example.vn/...png",
    "motionPreset": "drive-ltr",
    "focalPoint": { "x": 0.5, "y": 0.5 },
    "aspectRatio": 2.27,
    "alt": "VinFast VF 6 màu trắng, góc đầu xe 3/4",
    "film": {
      "url": "https://cdn.example.vn/vehicles/vf6/presentation.mp4",
      "posterUrl": "https://cdn.example.vn/vehicles/vf6/presentation-poster.webp",
      "mimeType": "video/mp4",
      "width": 1920,
      "height": 1080,
      "duration": 30.14,
      "eyebrow": "VF 6 trong chuyển động",
      "title": "...",
      "description": "...",
      "captionUrl": null,
      "revision": "2026-08-04"
    }
  },
  "specifications": [
    { "key": "range_nedc", "value": 460, "unit": "km", "label": "Quãng đường NEDC", "sortOrder": 10 }
  ],
  "colors": [
    { "id": "infinity-blanc", "name": "Trắng Infinity Blanc", "hex": "#ECECE8", "imageUrl": "https://cdn.example.vn/...webp", "sortOrder": 10 }
  ]
}
```

### Contract bộ chọn màu dùng chung

`src/components/VehicleColorConfigurator.jsx` là implementation duy nhất cho mọi trang model;
backend không tạo markup riêng theo từng xe. Payload hiện tại tiếp tục dùng `name`, `hex` và
`image.url`. Các field dưới đây đều optional và tương thích ngược:

- `group`: `standard`, `premium`, `advanced`, `special`, `two-tone` (hoặc key CMS ổn định).
- `groupLabel`: nhãn tiếng Việt do CMS kiểm soát khi key không nằm trong whitelist frontend.
- `secondaryHex` hoặc `hexes: [primary, secondary]`: chỉ dùng để vẽ swatch hai tông; ảnh xe vẫn
  phải là asset thật của đúng cấu hình màu, frontend không dùng filter để nhuộm xe.
- Thiếu `group` thì frontend render một dải màu duy nhất, không tự bịa nhóm. Thiếu `image.url`
  thì màu đó bị loại khỏi selector; còn dưới hai ảnh hợp lệ thì toàn section tự ẩn.

VF9 đang trỏ tới `VF9/CE*-cutout.webp`: đây là bản dẫn xuất giữ nguyên thân xe/bóng đổ và loại
sàn trắng opaque của nguồn cũ. `backend/scripts/publish_site_media.py` copy nguyên thư mục
`vehicle-media`, nên production/CDN phải publish đúng các key cutout này trước khi bật revision mới.

### Quy tắc media phục vụ animation

- `studioImageMode` chỉ nhận `cutout`, `plate`, `photo`.
- `motionPreset` chỉ nhận preset frontend đã hỗ trợ, ban đầu gồm `drive-ltr`, `float`, `static`. Backend không trả JavaScript, selector GSAP, duration hoặc easing.
- Ảnh `cutout` phải có alpha thật, không nền trắng, không bệ/khung chữ nhật, không watermark và có khoảng trong an toàn quanh xe.
- Với `drive-ltr`, đầu xe hướng sang phải hoặc góc đầu 3/4; không dùng góc đuôi xe. CDN không được flatten alpha khi tối ưu.
- Trả `width`, `height`, `aspectRatio`, `focalPoint`, `alt`, `revision` để tránh layout shift và cache sai.
- Chapter media cần `mediaType`: `exterior`, `profile`, `rear`, `cockpit`, `cabin`, `rearSeats`, `technology`, `drive`, `charging`, `cargo`.
- `tone` chỉ là `light` hoặc `dark` để frontend chọn frame tương phản đúng.
- Video cần `posterUrl`, `mimeType`, `duration`, `width`, `height`, captions/transcript nếu có lời nói. Autoplay chỉ áp dụng video muted.
- `presentation.film` là optional. Khi không có hoặc tải lỗi, frontend dùng `posterUrl`/`heroImageUrl` làm fallback và tiếp tục render gallery; không để lỗi video chặn trang chi tiết.
- Mỗi vehicle/revision chỉ được trả **một** object `presentation.film`, không trả mảng và không nhân bản cùng URL ở nhiều record. Nếu CMS có bản ghi trùng, backend chọn bản `publishedAt` mới nhất trước khi serialize; frontend chỉ mount một player cho route đang xem.
- `motionImageUrl` dùng trong hero phải là cutout alpha thật, canvas đã crop sát `safeBounds` và không chứa nền trắng/ô màu. Với VF 9, preset hiện tại tham chiếu asset đã crop `vf9-studio`; backend cần cung cấp bản CDN tương đương để không lộ khung trên nền trang.
- VF 8 và VF 8 Thế hệ mới hiện có hai file local giống hệt byte nhưng vẫn là hai record media độc lập. Backend/CMS không gộp quan hệ theo checksum vì nội dung biên tập, revision và ngày publish của hai mẫu có thể tách riêng sau này.
- Frontend luôn tôn trọng `prefers-reduced-motion`; backend phải có ảnh fallback cho mọi video/motion asset.
- Khi dữ liệu/media async render xong, frontend integration gọi `ScrollTrigger.refresh()`; không khởi tạo lại toàn bộ GSAP timeline trên từng chunk stream.

### Kho asset và lớp ghi đè hiện tại

- `src/media/vehicle-media-map.js` là sổ tra cứu mẫu xe → file nguồn. Không suy đoán file theo tên thư mục ở backend.
- `src/media/local/by-model/<vehicleId>/studio.*` là bản studio đã duyệt và có quyền ưu tiên cao nhất. Chạy `npm run media:apply` để đồng bộ đúng file sang `backend/data/media/vehicles/<vehicleId>/studio.*` trong môi trường local.
- Catalogue hiện publish đủ 14/14 `studioImage` ở mode `cutout`. Pipeline CDN phải giữ
  kênh alpha; nếu làm phẳng sang JPEG/WebP không alpha thì backend bắt buộc đổi mode thành
  `plate` hoặc `photo`.

#### Limo Green và eBus: sai lệch ảnh/mode đã được xử lý

Hai ảnh nguồn cũ có nền đặc đã được thay bằng bản alpha trong `by-model/`, đồng thời
`GET /api/v1/vehicles` nay trả `studioImage.mode = "cutout"` cho cả hai mẫu:

| File | Tỉ lệ pixel trong suốt |
|---|---|
| `common/limo-green-studio.webp` — nguồn cũ, không còn publish | 0,0% |
| `Dịch vụ_EBus/ebus-img-01.webp` — nguồn cũ, không còn publish | 0,0% |
| `by-model/limo-green/studio.webp` — bản đã tách nền, đã có trong repo | 68,8% |
| `by-model/ebus/studio.webp` — bản đã tách nền, đã có trong repo | 72,8% |

Hai thay đổi đã thực hiện và phải được giữ đồng bộ khi merge:

1. `backend/scripts/publish_site_media.py` — trỏ hai mẫu này sang file alpha đã có sẵn trong repo:

   ```python
   "limo-green": "src/media/local/by-model/limo-green/studio.webp",
   "ebus":       "src/media/local/by-model/ebus/studio.webp",
   ```

2. `backend/src/services/site_catalog.py` — `_VEHICLE_STUDIO_MODES` để trống; mặc định
   catalogue trả `cutout` cho 14 mẫu:

   ```python
   _VEHICLE_STUDIO_MODES: dict[str, str] = {}
   ```

Test `test_booking_studio_assets_are_published_as_cutouts` khóa contract này để tránh backend
vô tình gắn lại mode `photo` trong những lần cập nhật sau.
- Chân dung lớn ViVi dùng `src/media/local/common/vivi-portrait-cutout.png`. Không thay lại bằng `Ảnh ViVi.jpeg` vì JPEG nguồn có nền trắng và sẽ lộ khung trên nền section.
- `frontend/media-index.html` là catalogue sinh tự động cho ảnh, video, asset ghi đè, ảnh showcase và GLB/GLTF/FBX/OBJ/USDZ. Sau khi thêm hoặc đổi media, chạy `npm run media:index`; không sửa tay file HTML sinh ra.

### Contract media trang chủ và quy tắc lớp ảnh

- `factoryFilm` và `factoryAerial` là hai content block độc lập, có `sortOrder` riêng. Không composite ảnh toàn cảnh nhà máy vào video dây chuyền và không trả HTML/CSS positioning từ CMS.
- Caption trên `factoryFilm` và `presentationFilm` chỉ gồm `eyebrow`, `title`, `copy`; frontend cố định chúng thành một cụm nhỏ ở góc trái. Backend không trả kích thước chữ, vị trí, overlay gradient hoặc HTML để tránh che nội dung video.
- Chuyển động hero Lạc Hồng là preset frontend `depth-arrival`: xe bắt đầu nhỏ, tiến từ điểm tụ ra tiền cảnh rồi hãm nhẹ. CMS chỉ chọn preset và cung cấp ảnh alpha; không trả duration/easing/GSAP selector.
- CTA cuối trang `homeAction` chỉ nhận tối đa một `vehicleRender`. Nền phía sau là gradient do frontend quản lý; không trả thêm ảnh xe nền thứ hai.
- Các panel VF 8/VF 9 tại `flagship-passage` bắt buộc dùng `studioImageUrl` với `studioImageMode: "cutout"`. Nếu chưa có alpha thật, backend trả `plate` để frontend đóng khung có chủ đích, không gắn nhãn sai là `cutout`.
- Mọi block media cần stable `id`, `sortOrder`, `alt`, `focalPoint`, `width`, `height` và `revision`. API không trả selector, z-index, vị trí tuyệt đối hay timeline GSAP.

### Contract nội dung hậu mãi, pin và trạm sạc

Hai route `/after-sales` và `/charging` đọc dữ liệu có cấu trúc từ content API và dùng
`src/data/ownership.js` làm fallback media/nội dung có nguồn từ brochure. Khi nối CMS/API,
không trả một khối HTML tự do. Backend nên trả các block có cấu trúc, ví dụ:

```json
{
  "slug": "charging",
  "locale": "vi-VN",
  "revision": "2026-08-04",
  "effectiveAt": "2024-03-19T00:00:00+07:00",
  "sourceDocument": {
    "title": "Dịch vụ pin ô tô điện VinFast",
    "url": "https://cdn.example.vn/policies/charging.pdf",
    "checksum": "sha256:..."
  },
  "network": {
    "provinceCount": 63,
    "portCount": 150000,
    "portCountQualifier": "more_than"
  },
  "tariff": {
    "amountPerKwh": 3858,
    "currency": "VND",
    "vatIncluded": true,
    "effectiveAt": "2024-03-19"
  },
  "blocks": [
    { "id": "charging-notice", "type": "notice_timeline", "sortOrder": 10, "items": [] },
    { "id": "charging-units", "type": "charger_catalogue", "sortOrder": 20, "items": [] }
  ]
}
```

Quy tắc bắt buộc:

- Mọi con số pháp lý/chính sách cần `effectiveAt`, `revision` và `sourceDocument`; không cache vô thời hạn.
- Chính sách thuê pin phải có trạng thái `legacy_existing_customers_only` để UI không hiển thị như dịch vụ mở mới.
- Thời hạn bảo hành pin trả theo `vehicleIds`, `durationMonths`, `distanceKm` và `whicheverComesFirst`; frontend chịu trách nhiệm format, không parse chuỗi pháp lý.
- Danh mục trụ sạc trả `powerKw`, số cổng, điện áp vào/ra, chuẩn bảo vệ, nhiệt độ vận hành và media có `alt`, `width`, `height`, `revision`.
- Bốn product cutout trụ sạc đã được dựng lại tại
  `src/media/local/vehicle-media/Trạm sạc/charger-{250|150|60|30}-cutout-v2.png`.
  Các file là PNG 1.4K–1.8K có alpha thật; không dùng lại ảnh brochure cao 180 px hoặc
  composite nền xanh/trắng. `ChargingPage` ưu tiên cutout bundle theo `power` nhưng vẫn lấy
  tên/thông số từ API, nên media origin chưa publish không làm trang quay lại ảnh mờ.
- Khi publish backend, dùng các key `/media/content/charging/{250|150|60|30}kw.png` trong
  `backend/scripts/publish_site_media.py`. Extension và `Content-Type` phải là PNG; không đổi
  tên thành `.webp` nếu payload bên trong vẫn là PNG.
- Không cho CMS gửi selector GSAP hoặc JavaScript. CMS chỉ chọn animation preset allowlist: `hero-scale`, `stagger-cards`, `pinned-chapter`, `static`.
- Khi policy hết hiệu lực hoặc chưa publish, API phải trả trạng thái rõ ràng; frontend giữ bản bundled fallback kèm cảnh báo nguồn, không tự ghép dữ liệu cũ và mới.

### Media contract cho chương Lạc Hồng trên trang chủ

Lạc Hồng là nội dung showcase thương hiệu, không thuộc catalogue bán hàng và không được trả
`bookable: true`. Bản frontend hiện dùng một canvas duy nhất với năm ảnh alpha theo thứ tự
camera làm fallback; người dùng chỉ đổi góc bằng kéo hoặc phím mũi tên, không autoplay và
không hiển thị từng ảnh như gallery.

Backend/CMS nên trả cấu trúc sau khi có model 3D chính thức:

```json
{
  "id": "lac-hong-900lx",
  "placement": "home_brand_showcase",
  "bookable": false,
  "model3dUrl": "https://cdn.example.com/lac-hong-900lx.glb",
  "posterUrl": "https://cdn.example.com/lac-hong-900lx-poster.webp",
  "orbitFrames": ["https://cdn.example.com/lac-hong/frame-01.webp"],
  "revision": "2026-08-09"
}
```

- Ưu tiên `model3dUrl` GLB/GLTF có Draco/KTX2; `posterUrl` bắt buộc để tải tiến triển và
  làm fallback cho thiết bị yếu. `orbitFrames` chỉ dùng khi model 3D không có/không tải được.
- Ảnh fallback phải cùng góc máy, ánh sáng, kích thước canvas, safe bounds và có alpha thật;
  không để nền trắng/xám hoặc viền chroma quanh thân xe.
- CMS chỉ cung cấp nội dung theo hướng năng lực thiết kế, chế tác và bản sắc VinFast. Tên
  Lạc Hồng là chú thích ngữ cảnh, không thay thông điệp thương hiệu và không có CTA booking.
- Không gửi code WebGL/GSAP từ CMS. Frontend sở hữu camera limits, drag sensitivity,
  reduced-motion và toàn bộ motion preset.

### Media contract cho model 3D VF3/VF9, trạm sạc và cinematic booking

Frontend hiện render GLB thật cho `vf3`, `vf9` và sân khấu trạm sạc trên `/charging` bằng
`<model-viewer>`. Payload catalogue/media nên mở rộng theo cấu trúc sau; với trạm sạc thay
`vehicleId` bằng `mediaId: "charging-station"` nhưng giữ cùng schema `model3d`:

```json
{
  "vehicleId": "vf9",
  "model3d": {
    "url": "https://cdn.example.com/vehicles/vf9/model.glb",
    "posterUrl": "https://cdn.example.com/vehicles/vf9/model-poster.webp",
    "mimeType": "model/gltf-binary",
    "byteSize": 42494828,
    "checksum": "sha256:...",
    "revision": "2026-08-09",
    "credit": {
      "author": "...",
      "sourceUrl": "...",
      "license": "CC BY 4.0"
    }
  },
  "animationPreset": "drive-through-3d"
}
```

- CDN phải hỗ trợ `Range`, cache dài hạn theo URL có revision/hash, đúng
  `Content-Type: model/gltf-binary` và CORS cho origin frontend.
- `posterUrl` là bắt buộc khi model chuyển lên CDN. Runtime bundle hiện dùng các bản Draco:
  VF9 khoảng 1,3 MB, VF3 khoảng 915 KB và trạm sạc khoảng 772 KB; file nguồn dựng có thể lớn
  hơn nhiều nhưng không được đưa thẳng vào bundle production. Poster giữ bố cục ổn định trong
  lúc tải, còn GLB được browser tải khi section tương ứng đi vào viewport hoặc prefetch sau
  khi user chọn xe trong booking.
- Sân khấu trạm sạc chỉ render **một viewport tương tác** từ một URL GLB. Camera toàn cảnh,
  giới hạn zoom và nút reset thuộc preset frontend; backend không cần trả nhiều model hoặc
  nhiều URL cho cùng một asset.
- Ở màn booking thành công, frontend thay ảnh studio bằng GLB tương tác cho đúng hai mã
  `vf3` và `vf9`; kích thước stage không đổi. Nếu model lỗi hoặc thiết bị không hỗ trợ,
  component tự quay về `studioImage` alpha, không làm mất phiếu xác nhận.
- `animationPreset` chỉ nhận allowlist frontend (`drive-through-3d`, `static-3d`). Backend
  không gửi camera orbit, GSAP timeline, selector CSS hoặc JavaScript.
- Trục model khác nhau theo file. Camera đầu/cạnh/đuôi nằm trong
  `src/data/vehicle3d.js`; không suy luận các góc này từ CMS nếu chưa qua kiểm duyệt hình ảnh.
- Hai GLB VF3/VF9 hiện đã được kiểm tra trực tiếp: `0deg` là đầu/lưới tản nhiệt,
  `-90deg` là mặt bên với mũi xe hướng sang phải và `180deg` là đuôi/cốp. Cinematic
  booking phải dùng lần lượt `sideOrbit` rồi `rearOrbit`; không hoán đổi hai góc này.
- Preset `drive-through-3d` chạy ngang **2,55 giây** và chỉ bắt đầu khi section đã nằm rõ
  trong viewport. VF9 hiện có preset sơn đen áp trực tiếp lên material runtime
  `PaletteMaterial001`; backend không cần và không được gửi tên material hoặc thông số PBR
  tùy ý.
- Giữ attribution/license trong payload và giao diện. Nếu model mới thay đổi license hoặc
  tác giả, backend phải publish revision mới.

Cinematic booking chỉ mount **sau khi** `confirmHeldBooking` trả booking thành công. Trong
thời gian xe chạy, UI vẫn giữ stage review nhưng không gửi lại request. Khi animation kết thúc,
frontend mới chuyển sang màn phiếu; `prefers-reduced-motion` bỏ qua đoạn này. Vì vậy:

- Timeline frontend cố định theo bốn nhịp: mặt bên đi vào → phanh đúng tâm → camera xoay để
  đuôi xe hướng người xem → xe lùi vào chiều sâu và biến mất. Chỉ sau callback cuối cùng mới
  render phiếu đặt lịch; backend không điều khiển hoặc đồng bộ từng nhịp motion này.

- Backend không trì hoãn response để chờ animation và không coi animation là bằng chứng booking.
- Retry cùng idempotency key vẫn trả booking cũ; frontend chỉ phát cinematic một lần cho response đó.
- Nếu GLB không tải được, frontend dùng poster/ảnh cutout nhưng vẫn phải hiện phiếu thành công.

### Contract ảnh studio dùng trong phiếu booking

Toàn bộ 14 file hiện được publish tại `/media/vehicles/<vehicleId>/studio.*` đã được kiểm tra
có alpha. Backend phải trả `studioImage.mode: "cutout"`; không gắn `photo` cho Limo Green
hoặc eBus vì frontend sẽ chuyển sang khung ảnh nền trắng và làm sai cảm giác tách nền.

- File alpha phải có vùng transparent thật ở bốn góc, không chỉ có kênh alpha nhưng toàn ảnh
  vẫn opaque. Giữ safe bounds quanh xe để `object-fit: contain` không cắt gương/bánh xe.
- Script nguồn duy nhất là `backend/scripts/publish_site_media.py`; VF6, VF MPV 7,
  Limo Green và eBus phải lấy bản `src/media/local/by-model/<id>/studio.*` đã duyệt.
- `BookingTicket` không tự tách nền và không phủ nền trắng lên mode `cutout`. Nếu backend
  chưa có ảnh alpha thật, phải trả mode `plate` rõ ràng thay vì khai báo sai là `cutout`.

## 6. Contract showroom, slot, hold và booking

Showroom:

```json
{
  "id": "hcm-nguyen-thi-thap",
  "name": "VinFast Nguyễn Thị Thập",
  "formattedAddress": "...",
  "provinceId": "79",
  "wardId": "...",
  "location": { "lat": 10.739, "lng": 106.701 },
  "distanceMeters": 3800,
  "travelDurationSeconds": 900,
  "openingStatus": "open",
  "availableVehicleIds": ["vf6", "vf-mpv-7"],
  "accessibility": { "wheelchairAccessible": true }
}
```

Slot:

```json
{
  "inventorySlotId": "slot_01J...",
  "vehicleId": "vf6",
  "showroomId": "hcm-nguyen-thi-thap",
  "startAt": "2026-08-06T09:45:00+07:00",
  "endAt": "2026-08-06T10:30:00+07:00",
  "timezone": "Asia/Ho_Chi_Minh",
  "status": "available"
}
```

### Contract cho lịch tuần trên màn đặt lịch

`SchedulePanel` hiển thị lịch tuần liên tục (cột ngày × hàng giờ), nhưng mỗi ô có thể
chọn vẫn phải được tạo từ slot inventory do backend trả về. Frontend không tự suy đoán
ngày/giờ còn xe:

- `available`: ô xanh, có thể chọn và phải đúng `vehicleId` + `showroomId` hiện hành.
- `held`/`booked`/`blocked`: ô xám, chỉ để giải thích mức độ kín lịch và không thể chọn.
- Không có record: dấu gạch trung tính với nhãn “Showroom chưa mở lịch”; không được coi là
  hết xe hoặc còn xe.
- Điều hướng tuần chỉ thay viewport. API nên hỗ trợ cửa sổ `startDate`/`endDate` theo múi giờ
  `Asia/Ho_Chi_Minh` (khuyến nghị tối thiểu 6 tuần) hoặc cursor tuần; không bắt frontend tải
  toàn bộ lịch vô hạn. Trong giai đoạn hiện tại, client lấy tối đa 30 slot theo giới hạn API.
- Khi chuyển tuần, response nên chứa `rangeStart`, `rangeEnd`, `nextCursor`, `hasMore`,
  `availabilityRevision` để UI biết dữ liệu nào đã tải và chỉ refetch vùng thiếu.
- Shortcut giờ trong chat ViVi chỉ được lấy từ record `available`; không lặp lại slot đã giữ/
  đã đặt thành một lựa chọn nhanh.

GSAP chỉ đảm nhiệm chuyển động đổi tuần và phản hồi khi chọn ô. Backend không trả easing,
duration, selector hoặc layout calendar.

Booking create request:

```json
{
  "draftId": "draft_01J...",
  "holdId": "hold_01J...",
  "recipientType": "other",
  "vehicleId": "vf6",
  "showroomId": "hcm-nguyen-thi-thap",
  "customer": { "fullName": "...", "phone": "...", "email": "..." },
  "driver": { "fullName": "..." },
  "licenceConsent": { "confirmed": true, "version": "2026-08-01" },
  "privacyConsent": { "version": "2026-08-01" }
}
```

Booking response phải có:

- `id`, `bookingCode`, `status`, `vehicle`, `showroom`, `slot`.
- `customer` và `driver` ở dạng phù hợp với quyền xem hiện tại.
- `assignedSalesRepresentative`: `name`, `phone`, `avatarUrl` nếu đã phân công.
- `allowedActions`: `lookup`, `reschedule`, `cancel` theo trạng thái.
- `createdAt`, `updatedAt`, `notificationStatus` cho SMS/email.

### Vòng đời hold

1. User chọn slot chỉ mở popup; chưa cần giữ inventory.
2. User bấm “Xác nhận khung giờ” thì tạo hold atomic.
3. UI nhận `holdId` và `holdExpiresAt`, sau đó mới chuyển sang form.
4. Đổi xe, showroom hoặc slot phải release hold cũ trước/đồng thời với việc tạo hold mới.
5. Booking create tiêu thụ hold. Retry cùng `Idempotency-Key` phải trả cùng booking, không tạo bản ghi thứ hai.
6. Hold hết hạn trả `410`; slot vừa bị người khác lấy trả `409`. Cả hai trường hợp quay về lịch trống và giữ dữ liệu form trong memory.

## 7. Agent response contract

Agent trả text để hội thoại tự nhiên, đồng thời phải trả action có cấu trúc để UI render an toàn:

```json
{
  "messageId": "msg_01J...",
  "conversationId": "conv_01J...",
  "text": "Tôi tìm thấy 4 showroom có VF 6 gần bạn.",
  "nextStage": "choose_showroom",
  "entities": {
    "vehicleId": "vf6",
    "provinceId": "79",
    "wardId": "..."
  },
  "actions": [
    { "type": "select_showroom", "showroomId": "hcm-nguyen-thi-thap" }
  ],
  "ui": { "activeView": "map" }
}
```

- Backend/LLM chỉ được trả action type trong allowlist.
- Frontend đối chiếu id với dữ liệu API trước khi thực thi action.
- Không render HTML do agent trả về.
- Free text chứa tên, điện thoại, email phải được redact trước observability/prompt logs.
- Nếu agent timeout/429, các card xe, showroom và slot vẫn phải thao tác được; flow không phụ thuộc hoàn toàn vào text generation.

## 8. Persistence và privacy

- Ưu tiên draft server-side; browser chỉ giữ opaque `draftId` hoặc secure session cookie.
- Không lưu họ tên, điện thoại, email, thông tin GPLX hoặc nội dung prompt vào `localStorage/sessionStorage`.
- Draft chưa có PII có thể tự hết hạn sau thời gian ngắn. Draft có PII phải theo retention policy đã duyệt.
- Lookup/cancel/reschedule nên có OTP hoặc challenge phù hợp, rate limit và audit trail.
- Mã lịch không được suy ra từ timestamp tuần tự.
- Log backend phải redact PII; analytics tuyệt đối không nhận raw chat text.

## 9. Error và loading contract

| Tình huống | HTTP | UX bắt buộc |
|---|---:|---|
| Địa chỉ mơ hồ/chỉ có tỉnh | `422` | Giữ input, chuyển `need_ward`, hỏi phường/xã |
| Xe/showroom không tồn tại | `404` | Bỏ id lỗi, mở lại chọn xe/showroom |
| Slot vừa được người khác giữ | `409` | Đóng modal, refresh lịch, gợi ý slot gần nhất |
| Hold hết hạn | `410` | Về `choose_slot`, giữ form trong memory |
| Form sai | `422` | Map lỗi theo field, focus field đầu tiên |
| Submit trùng | cùng idempotency result | Hiện một booking duy nhất |
| Agent rate limit | `429` | Hiện retry; card/action thủ công vẫn hoạt động |
| API lỗi/offline | `5xx`/network | Không xoá draft UI; retry có kiểm soát |

Mọi request làm thay đổi stage cần loading state, disable action gây duplicate và hỗ trợ huỷ request cũ khi user đổi xe/showroom.

## 10. Analytics events

Đề xuất event allowlist:

- `vehicle_list_view`, `vehicle_view`, `vehicle_color_select`, `vehicle_media_view`.
- `test_drive_nudge_impression`, `test_drive_nudge_dismiss`, `booking_cta_click`.
- `booking_recipient_select`, `booking_vehicle_select`, `booking_address_submit`.
- `showrooms_loaded`, `booking_showroom_select`, `slots_loaded`, `booking_slot_select`.
- `booking_hold_created`, `booking_hold_conflict`, `booking_form_error`.
- `booking_created`, `booking_lookup`, `booking_reschedule`, `booking_cancel`.
- `vivi_message_sent`, `vivi_action_selected`, `media_load_error`.
- `ownership_page_view`, `ownership_section_view`, `policy_source_open`, `charging_hotline_click`.

Thuộc tính chung chỉ gồm `eventId`, `anonymousSessionId`, `draftId`, `vehicleId`, `showroomId`, `stage`, `placement`, timestamp và trạng thái. Không gửi name, phone, email, địa chỉ chi tiết hoặc raw prompt.

## 11. Thứ tự tích hợp khuyến nghị

### P0 — để flow đúng sự thật

1. API base URL, SPA fallback và error client dùng chung.
2. Catalogue/media thật với presentation contract.
3. Draft/session restore; chỉ khi đó dòng “Tiến trình được giữ trên thiết bị” mới hoàn toàn chính xác.
4. Geocoding + showroom có đúng xe + live slots.
5. Hold lifecycle và create booking idempotent.
6. Success ticket dùng booking response và sale được phân công thật.

### P1 — hoàn chỉnh nghiệp vụ

1. Lookup + verification.
2. Reschedule/cancel với allowed actions.
3. SMS/email notification status.
4. Map SDK và routing distance.
5. Analytics không PII.

### P2 — ViVi và CMS

1. Agent session/message streaming với structured actions.
2. CMS trang chủ, testimonial và video.
3. CDN transformations, poster và responsive media.

## 12. Checklist nghiệm thu backend ↔ frontend

- [ ] Direct load `/cars/vf6` và `/booking` không 404.
- [ ] Direct load `/after-sales` và `/charging` không 404; anchor sub-navigation nằm dưới header sticky.
- [ ] Reload booking khôi phục đúng stage nhưng không để lộ PII trong browser storage.
- [ ] Showroom được lọc theo đúng xe trước rồi mới theo khoảng cách.
- [ ] Mọi slot có `inventorySlotId`; browser không tự sinh lịch.
- [ ] 409/410 không làm mất địa chỉ/showroom/form.
- [ ] Double click/retry chỉ tạo một booking.
- [ ] Ticket thành công dùng booking/sale response thật.
- [ ] Lookup, reschedule và cancel chỉ mở sau verification.
- [ ] Ảnh `drive-ltr` có alpha và đúng hướng đầu xe; không lộ khung khi chạy.
- [ ] `prefers-reduced-motion` vẫn hiển thị đủ nội dung.
- [ ] Media lỗi có fallback; dữ liệu ảnh async không làm sai ScrollTrigger.
- [ ] VF3/VF9/trạm sạc GLB trả đúng MIME, Range/CORS, poster, checksum và credit; booking vẫn hoàn tất nếu 3D lỗi.
- [ ] Cinematic chỉ chạy sau booking response thành công và không tạo request xác nhận lần hai.
- [ ] Giá sạc, phí lưu trụ, số cổng sạc và thời hạn bảo hành hiển thị đúng `revision/effectiveAt`; thuê pin luôn gắn nhãn khách hàng hiện hữu.
- [ ] Analytics và log không chứa PII/raw prompt.
- [ ] Mobile, keyboard, screen reader và timezone `Asia/Ho_Chi_Minh` được kiểm tra.

## 13. Cinematic xác nhận lịch — ranh giới merge an toàn

Phần motion sau khi confirm được cô lập tại:

- `src/components/BookingSuccessCinematic.jsx`: timeline GSAP, camera VF3/VF9,
  particle khói lốp và fallback ảnh studio.
- `src/components/BookingSuccessCinematic.css`: sân khấu full-screen `#000000` và
  các layer chỉ phục vụ chuyển động.
- `BookingPage.jsx`: chỉ import component và mount khi `successCinematic === true`.

Backend không cần truyền preset motion và không cần đổi response. Contract giữ nguyên:

1. `confirmHeldBooking()` phải thành công và trả `booking_code` trước.
2. Frontend mới bật `successCinematic`.
3. `onComplete` chỉ chuyển UI sang stage `success`; không gọi API lần hai.
4. Nếu GLB VF3/VF9 lỗi hoặc quá 6 giây chưa sẵn sàng, cinematic dùng ảnh studio rồi
   vẫn mở phiếu thành công. Booking không phụ thuộc model 3D.

Các phase `blackout`, `brand-prelude`, `side-approach`, `drift`, `rear-retreat`,
`confirmed` được đặt trên `data-phase` của `.booking-film` để QA/automation quan sát
mà không đọc GSAP internals. `brand-prelude` luôn hoàn tất trước label
`vehicle-approach`: wordmark VinFast hiện tĩnh, chính diện trên nền đen rồi biến mất
trước khi xe xuất hiện; không xoay hoặc lật logo. Timing và preset camera hoàn toàn do
frontend sở hữu; backend không cần bổ sung field vào booking response.

Motion mới không thêm package; tiếp tục dùng `gsap`, `@gsap/react` và
`@google/model-viewer` đã có. Khi merge nhánh backend, ưu tiên giữ nguyên khối
`submitBooking()` hiện tại và chỉ resolve import component nếu `BookingPage.jsx` có conflict.

Ở trang chi tiết VF3/VF9, `Vehicle3DExperience` dùng sân khấu đen tuyệt đối, poster
dark và fly-by 2,55 giây. Đây là presentation-only; không liên quan dữ liệu xe từ API.
Trang trạm sạc giữ theme/model viewer riêng, không dùng override màu đen của xe.

### Bất biến hình học và vật liệu

- `.booking-film__rig` sở hữu việc căn giữa viewport và tuyệt đối không được animate.
- GSAP chỉ di chuyển `.booking-film__vehicle`; điểm phanh/drift cuối luôn là `x: 0`.
- Khói/vệt lốp phải lấy điểm phát từ `getBoundingClientRect()` của vehicle sau transform,
  không dùng phần trăm viewport cố định.
- GLB VF9 đã qua pipeline texture palette. Mesh sơn tên
  `Plane.014_Car Paint.002_0`, nhưng material mà model-viewer expose là
  `PaletteMaterial001`. Cấu hình paint phải trỏ tới material này và bỏ base-color
  palette texture trước khi đặt màu để VF9 hiển thị đen trung tính, không còn ánh đỏ.

## 14. TODO backend sau khi merge PR này

Danh sách này là hàng đợi triển khai ngắn gọn cho backend. Contract chi tiết và các
trạng thái lỗi vẫn lấy theo các mục phía trên; không đưa timing GSAP, selector CSS hoặc
markup presentation vào response API.

### P0 — catalogue, media và booking thật

- [ ] **Catalogue màu xe:** giữ thứ tự màu ổn định theo `sortOrder`; trả `name`, `hex`
  và `image.url` cho từng cấu hình. Khi có phân nhóm, trả đồng bộ `group`/`groupLabel`
  cho cả danh sách; màu hai tông dùng `secondaryHex` hoặc `hexes`, không yêu cầu
  frontend nhuộm ảnh bằng CSS filter.
- [ ] **Publish asset VF9:** đưa đủ `VF9/CE*-cutout.webp` lên CDN trước khi đổi revision
  catalogue. Kiểm tra response có alpha thật, `Content-Type: image/webp`, URL không 404
  và mỗi màu trỏ đúng ảnh xe tương ứng.
- [ ] **Publish asset trạm sạc:** giữ các key
  `/media/content/charging/{250|150|60|30}kw.png`, alpha PNG và model GLB duy nhất theo
  contract tại mục 5; không trả hai record 3D trùng nhau.
- [ ] **Catalogue model 3D:** VF3, VF5, VF9 và trạm sạc cần URL ổn định kèm
  `posterUrl`, `revision`, checksum/credit; server hỗ trợ MIME, CORS và byte range.
- [ ] **Booking inventory:** endpoint showroom/slot phải lọc theo `vehicleId` trước
  khoảng cách, trả `inventorySlotId`, timezone và trạng thái còn chỗ. Frontend không
  tự sinh hoặc coi lịch minh họa là slot thật.
- [ ] **Hold và confirm:** triển khai lifecycle giữ chỗ, idempotency key và xử lý
  409/410. Chỉ trả thành công khi đã có `bookingCode`, showroom, thời gian và sale
  assignment chính thức; cinematic không được kích hoạt từ response tạm.
- [ ] **Ticket thành công:** response cuối phải đủ người đặt, người lái, điện thoại,
  email nullable, xe, showroom, giờ hẹn, tư vấn viên và trạng thái giấy phép lái xe.
  Không dùng fixture hoặc dữ liệu draft để dựng phiếu đã xác nhận.

### P1 — độ bền tích hợp và vận hành

- [ ] Thêm integration test khóa số lượng màu/ảnh theo từng model, URL media hợp lệ,
  VF9 dùng asset cutout và Limo Green/eBus tiếp tục trả `studioImage.mode = "cutout"`.
- [ ] Thêm cache revision/ETag cho catalogue và media metadata; khi asset đổi phải tăng
  revision để browser không giữ nhầm màu hoặc poster cũ.
- [ ] Giữ response tương thích ngược: thiếu field optional thì frontend dùng một dải
  màu và fallback poster/ảnh tĩnh; không để lỗi video/GLB chặn trang hoặc booking.
- [ ] Hoàn thiện lookup, reschedule và cancel sau verification; log/analytics phải
  redact PII và không lưu raw chat text.
- [ ] Chạy nghiệm thu theo checklist mục 12 trên desktop/mobile, keyboard, reduced
  motion và timezone `Asia/Ho_Chi_Minh` trước khi bật dữ liệu production.

### Definition of Done cho backend

- [ ] `GET /api/v1/vehicles` và booking endpoints vượt contract/integration tests.
- [ ] Toàn bộ URL ảnh/video/3D được smoke-test từ origin production, không chỉ local.
- [ ] Reload hoặc retry không tạo booking trùng và không làm mất draft hợp lệ.
- [ ] Frontend build không cần hard-code thêm theo model sau khi chuyển sang payload thật.
