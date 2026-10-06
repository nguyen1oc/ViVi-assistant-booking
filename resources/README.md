# resources/ — tư liệu tham khảo

Thư mục này giữ những gì **không phải deliverable của dự án**. Bốn tài liệu chính
thức (`architecture_diagram.md`, `PO Document.pdf`, `PRD.md`, `SPEC.md`) nằm riêng
ở [`docs/`](../docs/) để mở ra là thấy ngay, không lẫn với tư liệu nền.

| Thư mục | Là gì | Ai đụng tới |
|---|---|---|
| [`guide/`](guide/) | Sách hướng dẫn AI20K (10 chương + chuyên đề: LangGraph, BMAD, testing, devops…) | Đọc để tra cứu, không sinh ra từ code |
| [`mockups/`](mockups/) | 12 file HTML xem trước 6 loại email | **Sinh tự động — đừng sửa tay** |
| [`research/`](research/) | Khảo sát giá xe & văn phòng VinFast, nguồn cho `frontend/src/data/vehicle-prices.js` | Cập nhật tay khi khảo sát lại |

## Lưu ý về `mockups/`

Các file trong đó **được sinh ra từ chính bộ render của backend**, nên không bao
giờ lệch với thư gửi thật. Sửa tay là mất khi chạy lại. Muốn đổi giao diện thư:
sửa `backend/src/services/booking/email_templates.py` rồi chạy

```bash
python backend/scripts/preview_confirmation_email.py
```
