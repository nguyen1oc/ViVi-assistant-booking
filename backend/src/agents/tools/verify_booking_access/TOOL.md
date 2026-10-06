# Verify Booking Access Tool

## Mô tả
Xác minh OTP và tạo access session ngắn hạn, có quyền theo purpose của challenge.

## Tham số
`challenge_id`, `otp_code`.

## Quy tắc
Mỗi lần nhập sai được ghi nhận bền vững. Challenge bị khóa khi đạt giới hạn
(mặc định 5 lần); OTP hết hạn, bị thay thế, đã khóa hoặc đã dùng đều bị từ chối.
