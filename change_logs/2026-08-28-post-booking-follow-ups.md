# Post-Booking Advisory và Follow-up Buttons

## Thêm mới

- API trả tối đa hai follow-up buttons qua trường `follow_ups` cho một lượt tư vấn hậu đặt lịch đã hoàn tất.
- Hiển thị follow-up cho lời chào sau khi đặt lịch thành công và khi Driver vào từ link mời, với nội dung riêng cho Booker/Driver.
- Follow-up chỉ xuất hiện sau khi câu trả lời của ViVi đã in xong trên giao diện.
- Bổ sung intent `after_sales_info` để các câu hỏi hậu mãi phù hợp vẫn đi vào Post-Booking skill khi đã có lịch lái thử xác nhận.
- Bổ sung ngữ cảnh khám phá người tham gia buổi lái thử (`participant_discovery_missing`), đồng thời nhận diện trường hợp Booker và Driver là cùng một người.

## Điều chỉnh Post-Booking Agent

- Cập nhật `SKILL.md` để giữ thứ tự khai thác intent theo role và booking context; follow-up có hai hướng: đào sâu nội dung vừa tư vấn và thông tin xe/chính sách hậu mãi liên quan.
- Follow-up không điều hướng về topic cũ, không là menu chung, và không tự khẳng định thông tin cá nhân hay intent chưa được người dùng nói rõ.
- Khi cần một dữ kiện thực tế để cá nhân hóa, agent hỏi tối đa một câu trong prose và không kèm follow-up buttons.
- Click follow-up chỉ chọn hướng hội thoại; không là bằng chứng để cập nhật profile hoặc booking signal.
- Khắc phục phản hồi rỗng sau tool call: agent phải trả phần tư vấn đầy đủ thay vì chỉ trả hidden follow-up block.
- Thêm lượt repair khi mô hình chỉ lặp lại nguyên văn tin nhắn người dùng hoặc không tạo được nội dung hiển thị.
- Xóa follow-up cũ khi lượt trả lời mới không có follow-up hợp lệ.

## Dữ liệu, knowledge và vận hành

- Mở rộng trusted knowledge cho các câu hỏi xe và hậu mãi dùng trong Post-Booking advisory.
- Bổ sung các kiểm thử node/API liên quan đến định tuyến Post-Booking và an toàn ngữ cảnh hội thoại.
- Tạm vô hiệu hóa `human-review-api` và `human-review` trong Docker Compose.

## Lưu ý tương thích

- Follow-up chỉ dành cho lượt hội thoại Post-Booking đã hoàn tất; booking action, UI workflow và lỗi/fallback không trả follow-up.
- Lịch sử chat trong `sessionStorage` có thể vẫn giữ lời chào cũ cho đến khi người dùng xóa key `vinfast:booking-ui-state` hoặc mở phiên mới.
