# 2026-08-13 — Mypy remediation

## Mục tiêu

Khắc phục lỗi mypy đang chặn backend CI/CD, trước khi merge vào `main`.

## Thay đổi

- Khai báo các booking operation services là mixin của `BookingBase`, phản ánh cách `BookingService` compose chúng và cấp dependency chung (`db`, `now`, OTP/messaging providers) tại runtime.
- Thêm fallback typing cho các helper/attribute được cung cấp bởi sibling mixin, để mypy không báo sai `attr-defined` khi phân tích từng mixin độc lập.
- Sửa các annotation cụ thể ở guardrail output, PostgreSQL optional import, database transaction, importer, booking OTP error, Zalo update ID, LangGraph tool output và API graph invocation.

## Hành vi deploy

Không đổi API contract hoặc luồng booking. Đây là thay đổi typing/validation để backend CI có thể chạy mypy nhất quán.

## Follow-up test fixes

- Khôi phục thứ tự positional của `request_access(booking_code, contact_value, purpose)` để tương thích tool, API test và booking access flow.
- Khôi phục import `datetime` cho time context trong system prompt.
- Cập nhật test ToolNode theo public error contract hiện tại: UI nhận thông điệp an toàn, còn `action_error` giữ error code.
- Thắt chặt access session: token OTP chỉ đọc/thao tác trên đúng booking đã xác minh, không mở rộng sang booking khác của cùng số điện thoại.
