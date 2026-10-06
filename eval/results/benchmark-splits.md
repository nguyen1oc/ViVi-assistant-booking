# Benchmark regression và hidden holdout

Kết quả dưới đây tách riêng bộ regression đã biết và hidden holdout chạy one-shot. Không thay case fail, không rerun để chọn kết quả đẹp hơn.

## Kết quả theo split

| Split | Task success | Số case | P95 latency |
|---|---:|---:|---:|
| Regression | **100.00%** | 57/57 | 14525.1 ms |
| Hidden holdout | **53.33%** | 16/30 | 14374.1 ms |

## Hidden holdout theo mutation

| Mutation | Task success | Số case |
|---|---:|---:|
| `expression` | 60.00% | 3/5 |
| `typo` | 40.00% | 2/5 |
| `time` | 60.00% | 3/5 |
| `showroom` | 80.00% | 4/5 |
| `multi_turn` | 0.00% | 0/5 |
| `tool_failure` | 80.00% | 4/5 |

## Human-review gate và overall

- Gate: **PARTIAL**; yêu cầu 2 review hoàn chỉnh cho mỗi case và coverage 100%.
- Coverage đạt chuẩn: **10/87 case** (11.49%).
- Overall: **WITHHELD_HUMAN_REVIEW_INSUFFICIENT**.
- Khi gate chưa đạt, không có điểm gộp nào được tính hoặc lưu trong artifact công khai.

## Bằng chứng đóng băng

- Trạng thái lần chạy: **COMPLETED**.
- Số attempt live: **1**.
- Dataset SHA-256: `5683ea861a60de11a4f7ed1ee6d992ef8844580c5ff5e8a7d7d3bce79751a975`.
- Application SHA-256: `6f2b33648d26db4dac60c93151bac7091660609ac68958c7c759adb3cdacb29a`.
- Dataset và raw trace nằm trong thư mục private bị Git bỏ qua; manifest công khai không chứa prompt/label.
