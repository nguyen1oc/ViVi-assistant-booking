# Update Booking Draft Tool

## Mô tả
Patch Booker, Driver, khai báo giấy phép và notification plan của booking `held`.

## Tham số
`booking_id`; các object patch tùy chọn; `expected_version` để chống ghi đè.

`license_patch` chỉ nhận `has_driving_license: true|false`. Hệ thống không thu
thập số hoặc hạng GPLX; giấy phép thật được kiểm tra trực tiếp tại showroom.

## Quy tắc
Không đổi slot và không xác nhận booking. Service từ chối hold hết hạn hoặc version conflict.
