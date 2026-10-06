# VinFast Test Drive Booking Backend

FastAPI backend cho website VinFast, gồm catalogue/nội dung website dạng read-only, nghiệp vụ đặt lịch lái thử, LangGraph Agent, SQLite và các công cụ import/publish media.

## Yêu cầu

- Python 3.11+
- `pip` và virtual environment (khuyến nghị)
- Node.js/npm chỉ cần khi upload media lên Cloudflare R2 bằng Wrangler

## Chạy local

Các lệnh dưới đây chạy từ thư mục `backend` để đường dẫn SQLite và media được resolve đúng:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

macOS/Linux:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Sau khi khởi động:

- Health check: <http://localhost:8000/health>
- Swagger UI: <http://localhost:8000/docs>
- API base: `http://localhost:8000/api/v1`
- Media local: `http://localhost:8000/media/...`

Schema SQLite được khởi tạo tự động. Database mặc định nằm tại `backend/data/app.db`.

## Cấu hình môi trường

Backend đọc `.env` ở repository root trước, sau đó đọc `backend/.env`; giá trị trong `backend/.env` có độ ưu tiên cao hơn. Không commit file chứa secret.

```env
APP_ENV=development
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

DATABASE_URL=sqlite:///./data/app.db

OPENAI_API_KEY=
OPENROUTER_API_KEY=
MODEL_NAME=gpt-4o-mini
CLASSIFIER_MODEL_NAME=
LLM_TEMPERATURE=0.7

MEDIA_ROOT=./data/media
MEDIA_BASE_URL=/media
SITE_CATALOG_PATH=./data/site_catalog.json
CHROMA_PERSIST_DIR=./data/chroma
```

`DATABASE_URL` hỗ trợ PostgreSQL cho production và SQLite cho test/phát triển nhỏ. Nếu không dùng Agent/LLM, có thể để trống các API key; catalogue, content và booking service vẫn chạy.

### Demo mô phỏng trên production

Giữ `APP_ENV=production` và đặt `FLOATING_DEMO_ENABLED=true` trên backend để bật
API tìm showroom/khung giờ cho nút demo. Biến này mặc định là `false`; sau khi đổi
cấu hình cần khởi động lại dịch vụ hoặc tạo revision mới. Bản backend triển khai
phải có hỗ trợ demo trên production.

Demo chỉ mô phỏng giữ chỗ và xác nhận trên giao diện, không tạo lịch thật hay bỏ
qua OTP. Kiểm tra bằng `GET /api/v1/floating-demo/capabilities`: khi bật sẽ trả
`{"enabled": true}`. Nếu tắt, API options trả mã `FLOATING_DEMO_DISABLED`.

## API chính

| Method | Endpoint | Mục đích |
|---|---|---|
| `GET` | `/health` | Kiểm tra tiến trình FastAPI |
| `GET` | `/api/v1/booking/health` | Kiểm tra booking service/database |
| `GET` | `/api/v1/vehicles` | Danh sách xe; hỗ trợ lọc category, featured và test-drive eligibility |
| `GET` | `/api/v1/vehicles/{vehicle_id}` | Chi tiết một mẫu xe |
| `GET` | `/api/v1/content/{page}` | Nội dung `home`, `charging` hoặc `after-sales` |
| `POST` | `/api/v1/chat` | Entry point của LangGraph Agent |
| `GET` | `/api/v1/status` | Trạng thái Agent |
| `POST` | `/api/v1/chat` | Tin nhắn Agent và structured booking actions từ frontend |
| `POST` | `/api/v1/demo/action` | Adapter demo cũ, không còn được booking frontend sử dụng |

Catalogue/content trả `ETag`, hỗ trợ `If-None-Match` và cache revalidation.

## Catalogue và media

Backend có snapshot mặc định trong `src/services/site_catalog.py`. Nếu `SITE_CATALOG_PATH` tồn tại, JSON đó được validate và dùng thay snapshot mặc định.

Validate và publish một CMS snapshot:

```powershell
python scripts/import_site_catalog.py path\to\input.json data\site_catalog.json
```

Copy media hiện có từ frontend sang local media origin:

```powershell
python scripts/publish_site_media.py ..\frontend data\media
```

Production có thể đặt `MEDIA_BASE_URL=https://cdn.example.com`; API sẽ tự chuyển các URL `/media/...` sang CDN origin. Upload Cloudflare R2:

```powershell
.\scripts\upload_r2_media.ps1 -Bucket your-bucket -MediaRoot data\media -DryRun
.\scripts\upload_r2_media.ps1 -Bucket your-bucket -MediaRoot data\media
```

## Test và kiểm tra code

```powershell
python -m pytest tests -v
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy src
```

Trên môi trường có `make`, có thể dùng `make run`, `make test` hoặc `make check`.

## Docker

Từ repository root:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Compose mặc định chạy PostgreSQL ở service `postgres`. Backend mở ở port `8000`, frontend ở port `3000`; `backend/data` được mount để giữ media local.

## Kiến trúc chính

```text
backend/
├── scripts/                 # Import catalogue, publish/upload media
├── src/
│   ├── agents/              # LangGraph, skills và tools
│   ├── api/                 # Booking/Agent API và site catalogue API
│   ├── models/              # Pydantic request/response models
│   ├── services/booking/    # Transaction và business rules đặt lịch
│   ├── services/site_catalog.py
│   ├── config.py
│   ├── database.py
│   └── main.py
└── tests/
```

Nghiệp vụ giữ slot, draft, xác nhận, OTP, tra cứu/chỉnh sửa booking, notification jobs, audit events và idempotency nằm trong booking service; API và Agent tools chỉ là adapter.

## Chưa implement/productionize

- Catalogue/content vẫn là snapshot Python/JSON read-only; chưa có CMS hoặc CRUD admin lưu vào database.
- `/api/v1/demo/action` vẫn được giữ cho demo/test cũ nhưng booking frontend đã chuyển sang LangGraph `/api/v1/chat`.
- `search_knowledge` chưa có RAG/vector search thực tế.
- Frontend đã kết nối LangGraph nhưng streaming và persistence lịch sử hội thoại production chưa hoàn thiện.
- Chưa có worker/gateway production để gửi notification ra SMS/email thực tế.
- Authentication/authorization cho admin, distributed rate limiting ở gateway và secret management production chưa hoàn thiện; backend đã có limiter theo process và bắt buộc signing/OTP secret ở production.
- Public admin/import/dashboard API đã bị gỡ; thao tác seed/import được thực hiện bằng script có quyền truy cập database.
- Một số catalogue detail như màu xe, chapter và gallery vẫn rỗng hoặc chưa đủ media.
- Chưa có framework migration có version; production hiện tạo/bổ sung schema qua database initialization và cần migration rõ ràng cho thay đổi schema lớn.

## Logging

Log được ghi xoay vòng tại `backend/logs/backend.log` (tối đa 5 MB mỗi file, giữ 5 bản). Theo dõi realtime trên PowerShell:

```powershell
Get-Content logs\backend.log -Wait
```
