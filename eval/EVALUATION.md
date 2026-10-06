# Evaluation pipeline

Hệ thống có hai benchmark tách biệt:

- `eval/benchmarks`: guardrail regression deterministic, chạy offline trong CI.
- `eval/golden`: behavioral golden set cho agent; có thể chấm prediction đã ghi
  hoặc gọi live agent khi được phép gửi prompt tới model provider.

## Metric được tính

| Nhóm | Metric | Nguồn |
|---|---|---|
| Chất lượng tác vụ | task success, intent accuracy/macro-F1, skill accuracy, tool accuracy | Golden expectation + agent trace |
| Tool | exact match, required-field match, field precision/recall/F1 | Tool-call arguments |
| Đường thực thi | clean execution, first-tool outcome, same-turn retry, unexpected tool error | Toàn bộ tool trace theo từng lượt |
| Kết quả | response requirements, DB assertions, negative-case outcome accuracy | Response, DB trước/sau, negative predictions |
| An toàn/chất lượng sinh | forbidden-behavior rate, groundedness, hallucination rate | Deterministic check, LLM judge hoặc human review |
| Hiệu năng | latency p50/p95/p99, turn count, error rate | Runtime trace |
| Vận hành | input/output/total tokens, estimated cost/case/success | Provider usage + rate truyền qua CLI |
| Con người | task success, correctness, relevance, groundedness, safety, satisfaction, CSAT, agreement | CSV human review |
| Kỹ thuật | line coverage | `coverage.py` JSON |

Metric chưa có dữ liệu luôn là `null` trong JSON và `NOT_RUN` trong Markdown.
Không chuyển metric chưa chấm thành `0`, vì `0` có nghĩa là đã chấm và thất bại.

### Mười metric booking chuẩn

| Metric | Cách tính và phạm vi hiện tại |
|---|---|
| Booking Task Success Rate | Active case đạt đồng thời intent, skill, tool, argument, response, DB/policy và clean execution / active case được chấm. Completion booking dương tính được ghi riêng để không nhầm với conversion funnel. |
| Intent Accuracy | Output `intent/sub_intent` của classifier ở lượt ngôn ngữ tự nhiên cuối được đối chiếu với route chấp nhận trong golden set, trước và độc lập với tool selection. Structured action không đi qua classifier nên bị loại khỏi mẫu số thay vì tự động tính đúng. |
| Tool Selection Accuracy | Chọn đúng tool bắt buộc, hoặc không gọi tool khi expected tool là `null`, / active case được chấm. |
| Argument Accuracy | Báo required-field match, exact match và macro field F1; field thừa chỉ được bỏ qua khi contract khai báo `allowed_extra_arguments`. |
| Slot Availability Accuracy | Precision: slot hợp lệ theo DB / toàn bộ slot được search trả về. Selected-slot recall: booking giữ thành công một slot đã xuất hiện trong kết quả search trước đó / toàn bộ booking giữ slot có đủ search evidence. Hai mẫu số được báo riêng. |
| Double-booking Rate | Tỷ lệ fixture chống giữ trùng, slot chồng giờ, idempotency, concurrent hold và capacity sales staff bị xuyên thủng. Xe/slot và staff capacity có denominator riêng. |
| Hallucination / Constraint Violation Rate | Hallucination rate = case bị judge phát hiện bịa dữ liệu / case có judge evidence. Constraint violation rate = deterministic forbidden-behavior check bị vi phạm / case có constraint evidence. Không gộp hai mẫu số khác bản chất thành một chỉ số chính. |
| Authorization / OTP Violation Rate | Fixture cross-customer, session hết hạn/thu hồi, OTP lock/single-use và quyền staff/manager/admin bị xuyên thủng / fixture auth-OTP được chấm. |
| P95 End-to-End Latency | Percentile 95 của thời gian toàn case, gồm tất cả turn và tool call. Gate release hiện là 20.000 ms. |
| Cost per Completed Booking | Chi phí agent-model của các positive confirmation workflow / booking xác nhận thành công. Structured workflow có usage đầy đủ và đúng 0 token được ghi 0 USD; workflow có model token chỉ có giá khi truyền đúng đơn giá provider. Không gồm hạ tầng, notification hoặc LLM judge. |

Mỗi metric có `status`, numerator/denominator hoặc `scored_cases` trong
`business_metrics` của JSON. `PARTIAL` và `NOT_RUN` không được coi là `PASS`.

`task_success_rate` chỉ nhận `true/false` sau khi toàn bộ DB/policy check bắt buộc
của case đã được chấm. Các component metric vẫn có thể có số trong lúc task
success còn `null`; report luôn ghi denominator riêng cho forbidden behavior và
groundedness.

Task success còn yêu cầu `clean execution`: tool error chỉ được chấp nhận khi đúng
`expect_error` của case. Lỗi ngoài dự kiến hoặc gọi lặp cùng tool trong một lượt làm
case fail, kể cả khi agent tự sửa và đạt trạng thái cuối. Toàn bộ 61 golden case là
regression suite; 12 case gắn tag `challenge` chỉ là lát cắt nội bộ của regression,
không phải hidden holdout.

## Lệnh chạy

Tạo inventory report, không gọi model:

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_agent_evaluation.py
```

Chấm lại prediction đã ghi và nhập coverage/human review:

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_agent_evaluation.py `
  --predictions artifacts\agent-predictions.json `
  --coverage-json artifacts\coverage.json `
  --human-ratings eval\human\reviews.csv
```

Live run dùng model và dữ liệu được theo dõi trong `eval/data/seed`; không đọc
hoặc ghi DB ứng dụng. Runner import seed vào SQLite, tạo cache fingerprint tại
`artifacts/agent-evaluation/eval-baseline.db`, rồi khôi phục một bản sao riêng
cho từng case. Cache tự bị vô hiệu khi CSV seed, schema DB hoặc importer thay
đổi:

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_agent_evaluation.py --live `
  --llm-judge `
  --run-negative-fixtures `
  --human-ratings eval\human\reviews.csv `
  --predictions-output eval\results\agent-predictions.json `
  --json-output eval\results\agent-evaluation.json `
  --markdown-output eval\results\agent-evaluation.md
```

Chỉ dùng một SQLite khác khi chủ động truyền `--database-source <path>`. Đây
không phải chế độ mặc định và không nên dùng để tạo baseline có thể tái lập.

Có thể smoke test bằng `--case SEARCH-001` hoặc giới hạn bằng `--max-cases 5`.
Suite dài có thể chạy thành nhiều shard rồi ghép mà không gọi lại model; lặp
`--predictions` theo thứ tự và record ở file sau sẽ thay record trùng `case_id`:

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_agent_evaluation.py `
  --predictions artifacts\regression-predictions.json `
  --predictions artifacts\challenge-predictions.json `
  --predictions-output eval\results\agent-predictions.json
```

Dataset hiện không còn case `known_gap`; cancel, reschedule và staff capacity đều là active executable case.
Thêm `--llm-judge` nếu đã được phép gửi cả response và tool evidence đã redact
tới provider để chấm groundedness, hallucination và các forbidden behavior chưa
thể xác định deterministic. Có thể dùng cùng `--live`, hoặc chấm lại artifact
đã ghi bằng `--predictions`. Report tách token của agent và judge, ghi rõ model
judge; kết quả này vẫn cần đối chiếu human review.

Chạy lặp để đo variance, observed pass@k và pass ở mọi lần chạy:

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_agent_stability.py --live --runs 3 `
  --case CANCEL-001 --case RESCHEDULE-001 --case STAFF-CAPACITY-001
```

Không truyền `--case` nếu muốn đo lặp toàn bộ 61 active case. Artifact mặc định nằm tại
`eval/results/agent-stability.json`, `agent-stability.md` và `agent-stability-runs.json`.

## Hidden holdout one-shot

Hidden holdout private có 30 case, chia đều cho sáu mutation: cách diễn đạt, typo,
thời gian, showroom, multi-turn và tool failure. Bộ này không được nhập vào golden
builder, không dùng làm dữ liệu sửa code và không chạy stability.

Kiểm tra contract mà không gọi model:

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_hidden_holdout.py --validate-only
```

Runner đã tiêu thụ lần live duy nhất và tạo `eval/holdout/frozen-manifest.json`.
Từ thời điểm manifest tồn tại, `--execute-once` luôn từ chối chạy lại và không có cờ
force. Chỉ dùng hai lệnh không gọi model sau:

```powershell
.\.venv\Scripts\python.exe backend\scripts\run_hidden_holdout.py --verify-freeze
.\.venv\Scripts\python.exe backend\scripts\run_hidden_holdout.py --refresh-public-report
```

`--refresh-public-report` chỉ cập nhật human-review gate từ artifact đã đóng băng.
Điểm regression và hidden holdout luôn tách riêng; overall chỉ xuất hiện sau khi cả
87 case có ít nhất hai human review hoàn chỉnh.

Chi phí không hard-code vì giá phụ thuộc provider/model và thay đổi theo thời
gian. Khi đã xác minh giá hiện hành, truyền:

```powershell
--input-cost-per-million <rate> --output-cost-per-million <rate>
```

Quality gate tùy chọn:

```powershell
--fail-under-task-success 0.80 `
--fail-under-challenge-task-success 0.70 `
--fail-under-clean-execution 0.90 `
--max-tool-retry-rate 0.05 `
--fail-under-argument-field-f1 0.95 `
--fail-under-negative-accuracy 1.00 `
--fail-under-line-coverage 60 `
--max-p95-latency-ms 20000 `
--fail-under-groundedness 0.90 `
--max-hallucination-rate 0 `
--min-groundedness-cases 10
```

Release scope hiện dùng latency budget p95 **20.000 ms**. Runner vẫn lưu p50/p95/p99
thực tế; việc nới gate không sửa hoặc làm tròn số đo.

Argument field F1 gate yêu cầu tối thiểu 0,95; các field mặc định/hạ tầng chỉ được bỏ qua
khi được khai báo trong `allowed_extra_arguments` của đúng tool contract. Groundedness
gate chỉ hợp lệ khi có ít nhất 10 active case được chấm. Baseline hiện yêu cầu mean
groundedness ≥0,90 và hallucination rate bằng 0%.

## Prediction contract

Tối thiểu:

```json
{
  "cases": [
    {
      "case_id": "SEARCH-001",
      "intent": "search_options",
      "skill": "booking",
      "tool_calls": [
        {
          "name": "search_test_drive_options",
          "arguments": {"vehicle_model": "VF 3", "showroom_id": "117"}
        }
      ],
      "response": "...",
      "latency_ms": 1250,
      "token_usage": {"input_tokens": 500, "output_tokens": 80, "total_tokens": 580}
    }
  ],
  "negative_cases": [
    {"case_id": "NEG-001", "outcome": "DENY"}
  ]
}
```

Các field grader tùy chọn gồm `database_assertions`,
`forbidden_behavior_checks`, `groundedness_score` và
`hallucination_detected`. Scorer chỉ tính denominator khi check thực sự có dữ
liệu.

## Những giới hạn cần công bố

- 61 case agent là regression suite synthetic và đều active. Human review phải được
  báo theo đúng số case/reviewer có dữ liệu tại thời điểm chạy; LLM judge không được
  xem là human review.
- Hidden holdout one-shot đạt 16/30 (53,33%); multi-turn 0/5 là lát cắt yếu nhất.
  Dataset/label/raw trace nằm trong thư mục private và checksum được khóa trong manifest.
- Case stateful dùng `evaluation_setup`, structured `action` turn và `fixture`
  turn để tạo slot/hold/OTP hợp lệ trên database cô lập; placeholder runtime
  được resolve theo kiểu dữ liệu thật trước khi chấm argument và DB assertion.
- Runner đã replay hội thoại nhiều lượt trên cùng LangGraph thread và có case
  OTP/access thực. Coverage multi-turn vẫn còn nhỏ nên chưa đại diện toàn bộ
  chuyển trạng thái hội thoại dài.
- `search_knowledge` dùng corpus 37 entry có provenance, nhưng toàn bộ vẫn
  `pending_internal_review` và retrieval hiện là lexical. Chưa thể tuyên bố RAG
  groundedness/faithfulness đạt chuẩn production.
- Stability ngày 28/08/2026 phủ đủ 61/61 case qua 3 lần chạy: observed pass@3
  98,36%, pass-all-3 95,08%, hallucination 0/20; `MULTITURN-SEARCH-001` và
  `SEARCH-005` không ổn định.
  P95 từng run nằm trong 10.236,37–12.121,22 ms. Hidden holdout không được rerun,
  còn ba regression run không thay thế dữ liệu tải production dài hạn.
- Human satisfaction và CSAT chỉ hợp lệ sau khi có người dùng/reviewer thực.
- LLM-as-judge cần ghi rõ model/judge source; không thay thế hoàn toàn human
  review.
