# VinFast Frontend

Single-page application xây bằng React 18, React Router, Vite, Tailwind CSS và GSAP. UI sử dụng catalogue/content từ FastAPI backend; các trang marketing vẫn giữ một số media tĩnh trong source trong giai đoạn chuyển đổi.

## Yêu cầu

- Node.js 18+ (khuyến nghị Node.js 20 LTS)
- npm
- Backend chạy tại `http://localhost:8000`

## Chạy local

Khởi động backend trước, sau đó từ repository root:

```powershell
cd frontend
npm install
npm run dev
```

Mở <http://localhost:3000>. Vite proxy `/api` và `/media` tới `http://127.0.0.1:8000` theo mặc định.

Các lệnh khác:

```powershell
npm run build
npm run preview
```

`npm run build` tạo production bundle trong `frontend/dist`.

## Biến môi trường

Tạo `frontend/.env.local` nếu cần ghi đè cấu hình local:

```env
# Dùng cho Vite dev proxy; không bao gồm /api/v1
VITE_API_PROXY_TARGET=http://127.0.0.1:8000

# Dùng khi frontend gọi trực tiếp public backend; phải bao gồm /api/v1
VITE_API_BASE_URL=https://api.example.com/api/v1
```

Không cần đặt `VITE_API_BASE_URL` khi chạy local qua Vite; mặc định client dùng `/api/v1`. Biến bắt đầu bằng `VITE_` được đóng gói vào browser, vì vậy không đặt secret trong đó.

## Routes

| Route | Trang |
|---|---|
| `/` | Trang chủ |
| `/models/:carId` | Chi tiết xe |
| `/booking` | ViVi và luồng đặt lịch lái thử |
| `/after-sales` | Hậu mãi |
| `/charging` | Pin và trạm sạc |

`/cars/:carId`, `/agent` và `/home` là các redirect tương thích. Vì dùng `BrowserRouter`, web server production phải fallback các route không phải asset về `index.html`.

## Data flow

```text
Page/component
  -> src/hooks/useSiteData.js
  -> src/api/*
  -> FastAPI /api/v1
```

- Catalogue xe: `GET /vehicles` và `GET /vehicles/{id}`.
- Nội dung động: `GET /content/home`, `/content/charging`, `/content/after-sales`.
- Booking availability: `GET /booking/health`.
- Tin nhắn và các thao tác booking có cấu trúc đều đi qua `POST /chat`; LangGraph định tuyến và gọi booking tools tương ứng.
- API client cache dữ liệu trong memory, lưu `ETag`, gửi `If-None-Match` và hủy request khi component unmount.
- Khi backend không khả dụng, UI hiển thị trạng thái lỗi; catalogue không được hard-code để giả lập response thành công.

Thứ tự hiển thị xe đến từ `sortOrder` của backend. Xe hero trang chủ được chọn theo `content.home.hero.vehicleId`; nếu ID không hợp lệ, frontend fallback sang xe cá nhân featured đầu tiên rồi mới tới xe đầu tiên trong catalogue.

## Styling và responsive

- Tailwind được cấu hình trong `tailwind.config.js`; PostCSS ở `postcss.config.js`.
- CSS giao diện hiện hữu và các animation selector vẫn nằm chủ yếu trong `src/index.css` để bảo toàn UI của branch `testing` trong quá trình migration.
- `preflight` được tắt để Tailwind không reset CSS cũ ngoài ý muốn.
- GSAP chỉ dùng cho animation; các khối editorial cần cố định sử dụng CSS sticky để tránh sai vị trí sau reload.

Viewport regression nên kiểm tra: `360`, `768`, `1024`, `1440` px, màn hình desktop thấp và `prefers-reduced-motion`.

## Cấu trúc chính

```text
frontend/src/
├── api/          # HTTP client, adapters, catalogue/content/booking API
├── components/   # App shell và UI dùng chung
├── context/      # Trạng thái backend
├── data/         # Media/fallback metadata còn trong giai đoạn migration
├── hooks/        # Hooks tải catalogue/content
├── pages/        # Home, detail, booking, charging, after-sales
├── App.jsx       # Router
├── index.css
└── main.jsx
```

## Docker

Từ repository root:

```powershell
docker compose up --build
```

Frontend được phục vụ tại <http://localhost:3000> và phụ thuộc service backend. Khi deploy riêng, cấu hình reverse proxy cho `/api/v1`, `/media` hoặc build với `VITE_API_BASE_URL` phù hợp.

## Chưa implement/productionize

- Bản đồ showroom và geocoding hiện là giao diện/logic cục bộ; chưa nối Google Maps hoặc nhà cung cấp bản đồ thực tế.
- Chat ViVi còn dùng parser intent, message ID/timestamp và delay cục bộ; chưa nối streaming từ `/api/v1/chat`.
- Tra cứu lịch đã đặt, đổi/hủy lịch và OTP chưa được nối đầy đủ vào UI production.
- Conversation ID của Agent được giữ trong `sessionStorage`; memory backend vẫn là in-memory và mất khi backend restart.
- Một số marketing media, brochure và nội dung chi tiết xe vẫn import từ `src/data`/asset bundle thay vì hoàn toàn từ CMS/CDN.
- Chưa có analytics production cho view, nudge, CTA và booking funnel.
- Chưa có bộ test frontend tự động hoặc script `npm test`; hiện cần build và regression test thủ công.
- Chưa cấu hình map key; nếu bổ sung phải dùng key giới hạn domain và không đưa secret vào frontend.

## Checklist trước khi merge/deploy

```powershell
npm ci
npm run build
```

Sau đó kiểm tra thủ công:

1. Backend health và banner mất kết nối.
2. Home hero sau Ctrl+F5/F5.
3. Danh sách/chi tiết xe và ảnh không bị crop/zoom.
4. Booking: chọn xe, showroom, slot, nhập thông tin và xác nhận.
5. Sticky sections ở trang Home và Charging.
6. Responsive tại các viewport nêu trên.
