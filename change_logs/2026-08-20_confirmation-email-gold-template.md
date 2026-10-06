# 2026-08-20 - Thư xác nhận lịch lái thử: bản nền đen nhấn vàng

## Mục tiêu

Thay thư xác nhận lịch lái thử bằng bản thiết kế mới (nền đen, nhấn vàng, có ảnh
xe), và nối vào luồng gửi tự động sẵn có để khách bấm xác nhận là nhận được thư
cá nhân hoá theo đúng lịch của họ.

## Thay đổi backend

- `email_templates.py`: thêm `render_booking_confirmation_email()`, dựng theo bản
  duyệt ở `docs/mockups/email-phieu-xac-nhan-awe.html`. `render_booking_email()`
  định tuyến `booking_confirmation` sang bộ render mới; nhắc lịch, đổi giờ và huỷ
  vẫn dùng bản nền sáng cũ vì tiêu đề "Phiếu xác nhận lịch hẹn" không đúng với chúng.
- `RenderedEmail` thêm trường `sms_text`. `plain_text` là nhánh text/plain của
  email, dài cả chục dòng; trước đây SMS và Zalo dùng chung trường này nên tin
  nhắn xác nhận bị vỡ thành một khối dài. `background.py` nay chọn theo kênh.
- `background.py`: câu SELECT của `_render_notification` lấy thêm `m.code`,
  `m.seat_count`, địa chỉ và toạ độ showroom, cùng thông số phiên bản xe
  (`estimated_range_km`, `motor_power_kw`, `battery_capacity_kwh`).
- `background.py`: xoá ~35 dòng mã chết nằm sau `return` trong `_render_notification`.
- `config.py`: thêm `public_site_url` (mặc định `https://vinfast-mvp.pages.dev`).
  Email không hiểu đường dẫn tương đối nên link trong thư bắt buộc phải tuyệt đối.
- `notifications.py`: `InMemoryMessagingProvider` ghi lại `inline_images` để test
  bắt được trường hợp thân thư trỏ `cid:` mà không có ảnh đi kèm.
- `scripts/make_email_watermarks.py` (mới): sinh ảnh chìm cho từng mẫu xe, ghi vào
  cả `backend/data/media` lẫn `frontend/src/media/local`. Chạy tay, cần Pillow;
  tầng gửi thư không cần Pillow.

## Thứ tự các khối (chốt 21/08)

Header · nav · tiêu đề + thanh vàng tên khách · **lời báo của ViVi** (tên xe tô
vàng đậm) · nút 1 · card thông tin lịch · **mô tả xe MỘT đoạn** · **lưới ảnh** ·
footer.

Mạch đọc: báo tin trước, thông tin lịch ngay sau, xong mới tới giới thiệu xe và
ảnh. Bản trước để cụm ảnh ngay dưới thanh tên khách, đẩy thông tin lịch xuống quá
sâu. Đừng đảo lại.

## Cá nhân hoá lấy từ đâu

Toàn bộ lấy từ `row` của `_render_notification`, không có gì đặt cứng theo một
khách hay một mẫu xe: tên và liên hệ khách, mã lịch, giờ hẹn, showroom kèm địa chỉ
và link Google Maps theo toạ độ, nhân viên phụ trách, mẫu xe và phiên bản. Hai
đoạn giới thiệu xe dựng từ thông số thật trong cơ sở dữ liệu; thông số nào không
có thì bỏ hẳn mệnh đề đó, không đoán. Ảnh xe chọn theo `vehicle_models.code`.

## Điểm cần biết

- Ảnh chỉ hiện khi `MEDIA_BASE_URL` là URL tuyệt đối. Ở local mặc định là `/media`
  nên thư bỏ luôn phần ảnh thay vì gửi cho khách một mớ ô ảnh vỡ.
- Ảnh chìm mới sinh phải được đẩy lên R2, nếu không thư trên môi trường thật hiện
  card nền đen trơn.
- VF6 chưa có ảnh xe nào chụp trên nền đen nên không có ảnh chìm.
- VF3, VF5, VF9 kho ảnh chỉ có ảnh cutout nền đen nên vài ô trong lưới hơi chìm;
  cần bổ sung ảnh có nền cho ba mẫu này.
- Hiệu ứng chuyển động chỉ chạy ở Apple Mail và Samsung Mail. Gmail, Outlook,
  Yahoo bỏ qua và hiện bản tĩnh.

## Test

- Thêm 3 test trong `tests/test_services/test_background_notifications.py`: thư
  xác nhận cá nhân hoá đúng lịch, SMS dùng bản rút gọn, nhắc lịch vẫn giữ bản nền sáng.
- `pytest`: 344 passed, 5 skipped. `ruff check` và `mypy` sạch.
