# VinFast Agent Benchmark V1.300 Enhanced

Thư mục này bổ sung các ca benchmark có thể chạy trực tiếp bằng evaluation runner hiện có. Không có mã nguồn ứng dụng nào cần thay đổi.

## Phạm vi

- Baseline hiện có: 57 ca trong `eval/golden/agent_cases.json`.
- Phần bổ sung: 24 ca trong `extra_cases.json`.
- Bộ hợp nhất: 81 ca trong `agent_cases_enhanced.json`.
- Dữ liệu chạy: snapshot local đang được theo dõi trong `eval/data` (319 showroom, 900 nhân viên active, 9.369 booking theo metadata baseline).
- Gói `VINFAST_TEST_DRIVE_AGENT_BENCHMARK_V1_300_CASES.zip` được dùng làm nguồn thiết kế và kiểm tra độ phủ. Không nhập nguyên trạng 300 ca vì contract tool và tên trường của gói đó không hoàn toàn khớp runtime hiện tại.

24 ca bổ sung tập trung vào các khoảng trống quan trọng của gói 300 ca: 22 ca hội thoại có từ hai lượt người dùng trở lên, 8 ca địa lý ngoài Hà Nội, 4 ca lifecycle booking, 4 ca challenge, cùng các biến thể sửa yêu cầu, typo, code-switch và giữ ngữ cảnh ngày/giờ.

## Kết quả đã chạy

Model: `gpt-5.6-luna`. Ngày chạy: 2026-08-25.

| Phạm vi | Task success | Tool accuracy | Clean execution | Argument required match |
|---|---:|---:|---:|---:|
| 24 ca bổ sung | 91,67% (22/24) | 100% | 100% | 95,83% |
| 81 ca hợp nhất | 97,53% (79/81) | 100% | 100% | 98,77% |

Hai lỗi còn lại đều là lỗi hành vi có tín hiệu rõ:

- `V1X-MT-SEARCH-003`: người dùng yêu cầu tìm ngày/giờ nhưng agent chuyển sang `hold_slot` và tự giữ chỗ.
- `V1X-MT-DATETIME-003`: sau khi đổi đồng thời xe và showroom, agent nhắc lại ngày/giờ trong câu trả lời nhưng không truyền `preferred_date` và `preferred_time` vào lần gọi tool cuối.

Báo cáo 81 ca còn ghi nhận: negative/security fixtures 16/16; double-booking rate 0%; authorization/OTP violation rate 0%; hallucination rate 0% trên 19 ca có evidence; P95 latency 15.616 ms. Human review chưa được chạy.

## Chi phí và code coverage

Đơn giá dùng để ước tính cho `gpt-5.6-luna`: 0,20 USD/1 triệu input token và 1,20 USD/1 triệu output token.

- 24 ca bổ sung: 428.479 input token + 5.940 output token; chi phí ước tính **0,092824 USD**.
- 81 ca hợp nhất: 888.882 input token + 12.637 output token; `Estimated cost` của runner là **0,192941 USD**.
- 57 ca baseline còn có LLM-judge: 130.675 input token + 10.187 output token; nếu judge dùng cùng đơn giá thì cộng thêm **0,038359 USD**.
- Tổng agent + judge ước tính cho báo cáo 81 ca: **0,231300 USD**.
- Pytest: **593/593 test đạt**, 7.567/10.224 statement được cover; line coverage **74,01%**.

Runner chưa tách cached-input token, vì vậy phép tính dùng toàn bộ input token theo giá input thường. Tool/service bên ngoài và hạ tầng không nằm trong ước tính này.

## Artifact chính

- `extra_cases.json`: 24 ca bổ sung độc lập.
- `agent_cases_enhanced.json`: bộ hợp nhất 81 ca.
- `results/schema-validation.json` và `.md`: kiểm tra schema/offline.
- `results/additions-predictions.json`: prediction hợp nhất cho 24 ca mới.
- `results/additions-report.json` và `.md`: báo cáo 24 ca mới.
- `results/full-81-predictions.json`: 57 prediction baseline đã có cộng với 24 prediction mới.
- `results/full-81-report.json` và `.md`: báo cáo tổng 81 ca.
- `runtime/*.db`: cache SQLite cô lập được tạo khi chạy lại và bị `.gitignore` loại khỏi version control vì mỗi cache có thể lớn hơn 500 MB.

## Chạy lại

Kiểm tra schema mà không gọi model:

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_agent_evaluation.py `
  --golden eval\benchmarks\vinfast_agent_v1_300_enhanced\agent_cases_enhanced.json `
  --negative-golden eval\golden\negative_cases.json `
  --json-output eval\benchmarks\vinfast_agent_v1_300_enhanced\results\schema-validation.json `
  --markdown-output eval\benchmarks\vinfast_agent_v1_300_enhanced\results\schema-validation.md
```

Chạy live toàn bộ 81 ca (có gọi model và có thể tốn thời gian/chi phí):

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_agent_evaluation.py `
  --golden eval\benchmarks\vinfast_agent_v1_300_enhanced\agent_cases_enhanced.json `
  --negative-golden eval\golden\negative_cases.json `
  --live `
  --database-cache eval\benchmarks\vinfast_agent_v1_300_enhanced\runtime\full-live.db `
  --predictions-output eval\benchmarks\vinfast_agent_v1_300_enhanced\results\full-live-predictions.json `
  --json-output eval\benchmarks\vinfast_agent_v1_300_enhanced\results\full-live-report.json `
  --markdown-output eval\benchmarks\vinfast_agent_v1_300_enhanced\results\full-live-report.md
```

`full-81-report` hiện tại là báo cáo hợp nhất từ 57 prediction baseline ngày 2026-08-24 và 24 prediction bổ sung ngày 2026-08-25; không phải một lần gọi live liên tục cho cả 81 ca.
