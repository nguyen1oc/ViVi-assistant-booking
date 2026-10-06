# Get Booking Details Tool

## Mô tả
Đọc booking theo access session đã xác minh.

## Tham số
`access_session_token` và một trong `booking_id`/`booking_code`.

## Bảo mật
Service kiểm tra expiry, permission và booking scope trước khi trả dữ liệu.
