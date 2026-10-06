# Hidden challenge holdout

Thư mục này giữ bằng chứng công khai cho hidden holdout, không chứa prompt, expected label hay raw trace.

Quy tắc:

- `eval/golden/agent_cases.json` gồm đúng 57 case và là regression suite cố định.
- Hidden holdout phải phủ sáu nhóm mutation: `expression`, `typo`, `time`, `showroom`, `multi_turn`, `tool_failure`.
- Dataset thật và raw artifact nằm trong `eval/holdout/private/`, bị Git bỏ qua.
- `frozen-manifest.json` được tạo ngay trước lần gọi model đầu tiên. File tồn tại đồng nghĩa attempt đã bị tiêu thụ, kể cả attempt lỗi.
- Không có cờ force/rerun và không thay case fail.
- Điểm regression và hidden holdout luôn báo riêng.
- Overall chỉ được công bố khi mọi case của cả hai split có ít nhất hai human review hoàn chỉnh.

Kiểm tra dataset trước khi chạy, không gọi model:

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_hidden_holdout.py --validate-only
```

Chạy đúng một lần:

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_hidden_holdout.py --execute-once
```

Sau khi chạy, chỉ xác minh checksum:

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_hidden_holdout.py --verify-freeze
```

Khi có thêm human review, dựng lại riêng báo cáo/gate từ artifact đã đóng băng; lệnh này
không gọi agent hoặc model:

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_hidden_holdout.py --refresh-public-report
```

Hai báo cáo công khai được tạo tại `eval/results/benchmark-splits.json` và
`eval/results/benchmark-splits.md`.
