# Chạy P-053 trên máy local (không cần Docker)

Tài liệu này dành cho việc test và sửa UI/UX/animation của frontend.

## TL;DR

```bash
cd /Users/nguyenhoangminh/AI20K-Build/P-053
bash frontend/dev-local.sh
```

Mở <http://localhost:3000>. Dừng bằng `Ctrl+C`.

Lần đầu chạy cần thêm một bước cài thư viện frontend:

```bash
cd frontend && npm install
```

## Vì sao không cần Docker

Backend hỗ trợ cả PostgreSQL lẫn SQLite (`src/database/__init__.py`). Docker chỉ dùng để
dựng sẵn PostgreSQL. Chạy local với SQLite cho kết quả tương đương cho mục đích làm UI/UX,
và quan trọng hơn: **Vite dev server có hot reload**, còn container frontend chỉ phục vụ
bản build tĩnh qua nginx — sửa CSS/animation sẽ không thấy gì cho tới khi build lại image.

Đã kiểm chứng chạy được không cần Docker:

| Thành phần | Trạng thái |
|---|---|
| `GET /health`, `/api/v1/booking/health` | 200 |
| `/api/v1/vehicles`, `/api/v1/content/{home,charging,after-sales}` | 200 |
| Ảnh/video qua `/media/...` | 200 |
| `POST /api/v1/chat` với `action=search_options` (giữ chỗ, đặt lịch) | Trả dữ liệu thật, **không cần OpenAI key** |
| `npm run build` | Thành công (~3s) |

## Ba thứ cần biết

### 1. Database dùng SQLite, không dùng PostgreSQL

`.env` ở root đang có `DATABASE_URL=postgresql://user:password@localhost:5432/dbname` —
đây là giá trị placeholder của template, không phải database thật. Script `dev-local.sh`
ghi đè bằng biến môi trường `DATABASE_URL=sqlite:///./data/app.db` nên không cần sửa `.env`.

Dữ liệu seed: 6 mẫu xe, 8 showroom, 48 xe demo, 1344 khung giờ trong 7 ngày tới.
Muốn seed lại từ đầu:

```bash
cd backend
RESET_DEV_DB=1 DATABASE_URL="sqlite:///./data/app.db" AUTO_LOAD_EVAL_DATA=false \
  ../.venv/bin/python scripts/seed_dev_db.py
```

### 2. Ảnh xe phải được "publish" sang backend

Catalogue xe giờ lấy từ backend, và ảnh trả về dạng `/media/vehicles/vf3/thumbnail.png`
— tức là backend phục vụ ảnh từ `backend/data/media`, không phải từ `frontend/src/media/local`.
Nếu chưa publish, UI sẽ hiện placeholder "Ảnh đang được cập nhật".

`dev-local.sh` tự làm bước này. Ảnh trong các trang marketing (home, hậu mãi, sạc)
vẫn import trực tiếp từ `src/data/*` nên luôn hiển thị.

### 3. Chat tự do với ViVi cần API key, các thao tác đặt lịch thì không

`OPENAI_API_KEY` trong `.env` đang là `sk-your-key-here` (placeholder).

- Chọn xe → địa chỉ → showroom → khung giờ → giữ chỗ → điền form → xác nhận: **chạy bình thường**.
  Các bước này gửi `action` có cấu trúc và backend gọi thẳng tool, bỏ qua LLM
  (`booking_skill_node.py:112`, `classifier_node.py:33`).
- Gõ tin nhắn tự do cho ViVi: sẽ lỗi cho tới khi có key thật.

## Tra cứu và đổi ảnh xe

**Xem kho ảnh:**

```bash
cd frontend && npm run media:index
```

Rồi mở `frontend/media-index.html` bằng trình duyệt — toàn bộ 189 ảnh/video, nhóm theo mẫu xe,
ảnh đang dùng làm ảnh thẻ xe có viền xanh gắn nhãn **ẢNH CHÍNH**, bấm một nút là copy được
dòng code tương ứng.

**Đổi ảnh một mẫu xe** — bỏ file vào thư mục mang đúng mã xe, không cần sửa code:

```text
src/media/local/by-model/vf9/studio.png
```

Bốn tên file được nhận: `thumbnail` · `studio` · `hero` · `video`. Xoá file đi là tự quay về ảnh cũ.

Ảnh marketing thì F5 thấy ngay. Ảnh thẻ xe do backend phục vụ nên chạy lại `dev-local.sh`
(hoặc `npm run media:apply`) một lần để đẩy sang. Dùng đúng đuôi file mà backend đang phục vụ —
script sẽ báo nếu sai.

Bảng "mẫu xe nào dùng ảnh nào" nằm ở [src/media/vehicle-media-map.js](src/media/vehicle-media-map.js).

**Xe Lạc Hồng** (900 LX và 900S) là xe trưng bày, chưa mở lái thử nên không nằm trong catalogue
và không có nút đặt lịch. Ảnh đã tách nền ở `src/media/local/showcase/`, ảnh gốc chưa tách nền
giữ ở `src/media/local/originals/` — xem [originals/README.md](src/media/local/originals/README.md)
để biết ảnh nào ra ảnh nào. Ảnh gốc không nằm trong bản build nên không làm web nặng thêm.

## Vòng lặp sửa UI/UX

1. Chạy `bash frontend/dev-local.sh`, mở <http://localhost:3000>.
2. Sửa file trong `frontend/src/` → trình duyệt tự cập nhật (hot reload), không cần restart.
3. Các file hay đụng tới:
   - `src/index.css` — 9236 dòng, chứa gần như toàn bộ style và animation selector.
   - `src/pages/HomePage.jsx`, `CarDetailPage.jsx`, `BookingPage.jsx` (1801 dòng),
     `AfterSalesPage.jsx`, `ChargingPage.jsx`.
   - `src/components/booking/*` — workspace xe, bản đồ showroom, form, modal.
4. Trước khi commit: `cd frontend && npm run build`.

Viewport cần kiểm tra: 360 / 768 / 1024 / 1440 px, và bật `prefers-reduced-motion`.

## Lỗi thường gặp

**Trang trắng / lỗi `Cannot find module 'tailwindcss'`** — `node_modules` cũ hơn `package.json`
(backend mới thêm Tailwind). Chạy `cd frontend && npm install`.

**Port 3000 báo bận, Vite nhảy sang 3001/3002** — còn dev server cũ đang chạy nền và
phục vụ code cũ. Dọn:

```bash
pkill -f "vite --host 0.0.0.0 --port 3000"
```

**Banner "mất kết nối" trên UI** — backend chưa chạy hoặc chết. UI ping
`/api/v1/booking/health` mỗi 30 giây (`src/context/BackendStatusContext.jsx`).
Kiểm tra: `curl http://localhost:8000/health`.

**Ảnh xe hiện "Ảnh đang được cập nhật"** — chưa publish media. Xoá
`backend/data/media` rồi chạy lại `dev-local.sh`.

## Nếu vẫn muốn chạy bằng Docker

Cần xử lý trước 3 điểm, nếu không `docker compose up --build` sẽ fail:

1. **Cài Docker Desktop** — máy hiện chưa có (`docker: command not found`).
2. **`eval/data` không tồn tại** (thư mục `data/` bị `.gitignore` loại trừ). Service
   `db-seed` sẽ raise `No supported eval CSV files found` → `backend` không bao giờ khởi động
   vì `depends_on: db-seed: service_completed_successfully`. Phải tải bộ CSV
   `01_…`→`15_…` từ Google Drive (link trong README root) về `eval/data`.
3. **Service `admin` trỏ tới image `p-053-backup-backend:latest`** (`docker-compose.yml:63`)
   — image này không có trên Docker Hub và không có `build:` context, nên compose sẽ fail
   khi pull. Đây là lỗi phía backend cần sửa.

Kể cả khi Docker chạy được, frontend trong container là bản build tĩnh — không dùng để
sửa UI/UX được.
