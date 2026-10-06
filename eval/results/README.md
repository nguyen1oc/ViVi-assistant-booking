# Evaluation reports

- `report_final.md`: báo cáo tổng mới nhất và là source of truth để trình bày.
- `archive/report_[dd-mm-yy].md`: snapshot báo cáo tổng cũ, chỉ dùng để đối chiếu lịch sử.
- `hallucination-evaluation-report-2026-09-01.md`: báo cáo chuyên đề cách chấm hallucination và 20 groundedness case.
- `guardrails-architecture-report-2026-09-01.md`: báo cáo chuyên đề các lớp guardrails và cách enforcement.
- `profile-sales-brief-focused-evaluation-2026-08-30.md`: báo cáo focused profile → Sales Brief.
- `agent-*` và `benchmark-splits*`: artifact/report máy sinh từ các runner cũ; không thay thế `report_final.md`.

Khi có đợt chốt số liệu mới:

1. Chuyển `report_final.md` hiện tại vào `archive/report_[dd-mm-yy].md`.
2. Tạo `report_final.md` mới từ artifact của đợt chạy vừa chốt.
3. Không ghi đè snapshot đã archive và không dùng report cũ làm số liệu trình bày hiện tại.
