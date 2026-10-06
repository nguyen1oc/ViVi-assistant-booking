# Debug booking bugs — 2026-08-11

## 1. Không đưa raw tool error lên giao diện

- Vấn đề: khi chọn slot stale hoặc đã qua giờ, lỗi nội bộ có thể xuất hiện dưới dạng `BookingError(...)` hoặc wrapper của ToolNode.
- Cách xử lý: `booking_skill_node` map các error code đã biết sang thông báo công khai; `action_error` chỉ chứa code ổn định để frontend xử lý.
- Fallback: nếu backend cũ trả `BookingError('...')` mà chưa có error code, chỉ phần message bên trong được dùng làm câu trả lời của ViVi.
- Kết quả: người dùng nhận câu trả lời tự nhiên trong chat, không thấy stack/error wrapper. Slot không còn khả dụng được bỏ chọn và lịch trống được tải lại.

## 2. Không để frontend bypass Agent khi nhắn “gần nhất”

- Vấn đề: `handlePrompt()` từng có regex để tự chọn showroom đầu tiên khi phát hiện “gần nhất”, nên Agent không được đọc đầy đủ ngữ cảnh hoặc quyết định.
- Cách xử lý: mọi tin nhắn nhập ở composer đều gửi qua `sendBookingMessage()`; payload có stage, xe, showroom, slot, GPS, danh sách showroom lân cận, booking ID và channel.
- Kết quả: Agent là nơi quyết định ý định và hỏi lại khi thông tin chưa đủ. Các nút chọn showroom/slot vẫn dùng structured action vì đó là thao tác UI xác định.

## 3. Chặn gửi trùng trong cùng cuộc hội thoại

- Vấn đề: người dùng có thể submit nhiều tin trong khi Agent đang xử lý, gây race trên cùng `conversation_id`.
- Cách xử lý: thêm `sendingRef`, `isSending` và `composerDisabled`; textarea, nút gửi và Enter bị khoá đến khi request kết thúc.

## 4. OTP Zalo dùng đúng challenge và mã vừa nhập

- Vấn đề: React state cập nhật bất đồng bộ có thể khiến thao tác verify đọc challenge hoặc OTP cũ nếu người dùng bấm ngay.
- Cách xử lý: `otpChallengeIdRef` lưu challenge sau khi request OTP, `otpCodeRef` lưu mã ở mỗi lần nhập/dán; verify đọc ref trước state.
- Hành vi UI: nhập từng ô cần bấm **Xác nhận**; paste đầy đủ sáu số sẽ xác thực ngay.

## 5. Giới hạn độ dài message thống nhất giữa FE và BE

- Backend và frontend cùng giới hạn 5.000 ký tự. Frontend hiển thị bộ đếm, chặn submit vượt giới hạn và chuyển lỗi validation thành thông báo có thể đọc được.
