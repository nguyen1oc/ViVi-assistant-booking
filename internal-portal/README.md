# P053 Internal Portal

Internal Portal là web dành cho `staff`, `showroom_manager` và `operations_admin`.

## Kiến trúc

```text
internal-portal/frontend       React/Vite, chạy riêng ở port 3100
backend/src/internal_portal    Internal API, authentication, RBAC và showroom scope
backend/src/services/booking   Domain service dùng chung với Customer/AI Agent
```

Portal có frontend/deployment riêng, nhưng không nhân đôi backend nghiệp vụ. Internal API được mount tại `/api/v1/internal` trong FastAPI hiện có để mọi thay đổi booking vẫn đi qua cùng transaction và business rules.

## Phân quyền

- `staff`: **read-only**; chỉ xem booking được gán active qua `slot_sales_assignments`, hồ sơ, ca làm và thời gian không khả dụng của chính mình. Staff không được xác minh GPLX, đổi trạng thái/hủy booking, phân công lại, sửa lịch, đọc fleet, catalog, audit hoặc dữ liệu người khác.
- `showroom_manager`: quản lý đúng **một showroom**; xem và phân công booking, thực hiện transition nghiệp vụ đã whitelist, quản lý ca/không khả dụng của staff, trạng thái và khoảng khóa xe, giờ hoạt động showroom.
- `operations_admin`: global scope; quản lý showroom, catalogue, fleet, tài khoản nội bộ, audit và điều chuyển xe qua service có kiểm tra conflict.

Backend kiểm tra role/scope cho từng request. Việc ẩn menu trên frontend chỉ phục vụ trải nghiệm, không phải lớp bảo mật.
Phạm vi staff luôn được suy ra động từ showroom hiện tại của hồ sơ `sales_staff`; tài khoản không thể được cấp thêm showroom và tự mất quyền đăng nhập khi hồ sơ nhân viên ngừng hoạt động. Mọi thay đổi role, scope hoặc trạng thái tài khoản đều thu hồi session cũ.

## Tạo tài khoản

Sau khi đăng nhập bằng `operations_admin`, mở mục **Tài khoản** để tạo tài khoản
Staff, Showroom Manager hoặc Operations Admin. Mật khẩu phải có ít nhất 8 ký tự.
Staff phải được liên kết với một nhân viên đang hoạt động; Manager phải được cấp
đúng một showroom đang hoạt động. Backend kiểm tra toàn bộ role và scope, không dựa vào việc
ẩn/hiện trường trên frontend.

Operations Admin có thể sửa role/scope, khóa hoặc mở tài khoản, đặt lại mật khẩu và thu hồi toàn bộ phiên đăng nhập tại mục **Tài khoản**. Không thể khóa hoặc hạ quyền Operations Admin đang hoạt động cuối cùng.

Các bảng tài khoản, session, OTP, access session, identity link và audit không được import qua API `/admin/import/eval-dataset`. Business snapshot chỉ được seed bằng CLI trong môi trường development để tránh ghi đè trạng thái bảo mật production; active login session và notification read state không nằm trong seed.

Không có credential mặc định trong repository. Tài khoản Operations Admin đầu
tiên vẫn được provision từ thư mục `backend` bằng lệnh:

```powershell
python scripts/manage_internal_user.py `
  --username ops.admin `
  --display-name "Operations Admin" `
  --role operations_admin
```

Manager cần đúng một `--showroom-id`. Staff cần `--staff-id`; showroom của nhân viên được suy ra tự động từ hồ sơ `sales_staff`.

## API vận hành chính

Toàn bộ API nằm dưới `/api/v1/internal` và lấy role/scope từ bearer session:

- Booking: `GET /bookings`, `GET /bookings/{id}`, `PUT /bookings/{id}/assignment`, `POST /bookings/{id}/transition`, `POST /bookings/{id}/license-check`.
- Staff schedule: `GET/POST /shifts`, `PATCH /shifts/{id}`, `GET/POST /unavailability`.
- Fleet/schedule: `GET/PATCH /vehicles`, `GET/POST/DELETE /vehicle-unavailability`, `GET/PUT /showrooms/{id}/operating-hours`.
- Admin: `POST/PATCH /showrooms`, `POST/PATCH /catalog/models`, `POST/PATCH /catalog/variants`, `POST /vehicles/{id}/transfer`, `GET /vehicle-transfers`, user management và audit.

## Chạy local

Backend:

```powershell
cd backend
python -m uvicorn src.main:app --reload --port 8000
```

Portal:

```powershell
cd internal-portal/frontend
npm install
npm run dev
```

Mở <http://localhost:3100>.

## Docker

Từ repository root:

```powershell
docker compose up --build postgres db-seed backend internal-portal
```

Portal mở ở <http://localhost:3100> và proxy `/api` sang backend trong Docker network.

Human Review không thuộc portal vận hành này. Ứng dụng reviewer độc lập nằm tại
`human-review/` và sử dụng tài khoản/namespace API riêng.
