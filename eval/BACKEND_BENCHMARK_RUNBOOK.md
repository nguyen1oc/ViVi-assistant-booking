# Backend Benchmark Runbook

Tài liệu này là hướng dẫn copy-paste để team backend tự chạy toàn bộ benchmark hiện có của VinFast Test Drive Agent. Mọi lệnh chạy từ **root repository**.

## 1. Inventory và mục đích

| Bộ đo | Dataset/phạm vi | Có gọi LLM | Mục đích |
|---|---:|---:|---|
| Backend regression | `backend/tests` | Không | Unit/integration/API/service/tool regression |
| Guardrail benchmark | 93 case trong `eval/benchmarks/guardrails_cases.json` | Không | Input/output/tool/untrusted-content/rate-limit/abuse |
| Official agent benchmark | 61 case trong `eval/golden/agent_cases.json` | Có | Intent, skill, tool, arguments, DB, response, hallucination, latency, token |
| Negative/security fixtures | 16 case trong `eval/golden/negative_cases.json` | Không | Authorization, OTP, double-booking, concurrency, reliability |
| Stability | 61 case × 3 lần | Có | Variance, pass@3, pass-all-3 và case không ổn định |
| Profile → Sales Brief focused | 10 case trong `eval/golden/profile_sales_brief_cases.json` | Có | Tool payload → DB signals → Sales Brief đã lưu |
| Booking cost | 10 booking E2E được chọn từ official set | Có | Cost trung bình cho một booking confirmed |
| Booking → Sales Profile cost | 10 workflow được runner sinh động | Có | Cost từ chat đầu tiên đến Sales Brief được lưu |
| Enhanced 81 | Dataset lịch sử trong `eval/benchmarks/vinfast_agent_v1_300_enhanced` | Tùy chế độ | So sánh với benchmark mở rộng cũ; không thay official 61 |
| Hidden holdout | 30 case private, đã freeze | Không được chạy lại | Chỉ verify checksum/report đã đóng băng |

Không gộp các mẫu số khác nhau thành một điểm chung. Backend tests pass không có nghĩa live agent benchmark pass; guardrail 100% cũng không chứng minh Sales Brief đúng.

## 2. Chuẩn bị môi trường

### PowerShell/Windows

```powershell
git checkout full_benchmark

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

$PY = ".\.venv\Scripts\python.exe"
$RUN_ID = Get-Date -Format "yyyyMMdd-HHmmss"
$BENCH_OUT = "artifacts\agent-evaluation\backend-$RUN_ID"
New-Item -ItemType Directory -Force -Path $BENCH_OUT | Out-Null
```

Nếu `.venv` đã tồn tại thì không tạo lại. Không ghi đè `.env` đang dùng.

### Linux/macOS

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.txt

PY=.venv/bin/python
RUN_ID=$(date +%Y%m%d-%H%M%S)
BENCH_OUT="artifacts/agent-evaluation/backend-$RUN_ID"
mkdir -p "$BENCH_OUT"
```

### Biến bắt buộc cho live run

Dataset V5 lớn được `.gitignore` và không có trong clone Git sạch. Tải package ở
link Google Drive ghi trong `README.md`, giải nén sao cho thư mục được chọn có
`seed/01_provinces.csv` đến `seed/32_internal_audit_events.csv`, rồi cấu hình
đường dẫn tuyệt đối. Runner sẽ dừng với lỗi rõ ràng trước khi gọi model nếu thiếu
thư mục này.

PowerShell:

```powershell
$EVAL_DATA = "C:\duong-dan\toi\eval\data"
$env:EVAL_DATA_DIR = $EVAL_DATA
Test-Path "$EVAL_DATA\seed\01_provinces.csv"
Test-Path "$EVAL_DATA\seed\32_internal_audit_events.csv"
```

Linux/macOS:

```bash
export EVAL_DATA_DIR=/absolute/path/to/eval/data
test -f "$EVAL_DATA_DIR/seed/01_provinces.csv"
test -f "$EVAL_DATA_DIR/seed/32_internal_audit_events.csv"
```

Có thể truyền `--eval-data-dir <path>` cho live runner, stability, hidden
holdout và Sales Profile cost thay cho biến môi trường.

Đặt API/model config trong `.env` tại root repo hoặc export trong terminal:

```dotenv
OPENAI_API_KEY=<secret>
# Hoặc OPENROUTER_API_KEY=<secret>, không cần cấu hình cả hai.

MODEL_NAME=gpt-5.6-luna
CLASSIFIER_MODEL_NAME=gpt-4o-mini
LLM_TEMPERATURE=0.7
LLM_REASONING_EFFORT=low
LLM_REQUEST_TIMEOUT_SECONDS=60
LLM_MAX_RETRIES=1
EVAL_DATA_DIR=C:/absolute/path/to/eval/data
```

Yêu cầu vận hành:

- Không commit `.env`, API key hoặc raw trace chứa PII.
- Giữ nguyên model, temperature, reasoning effort và commit SHA giữa các lần stability.
- Runner mặc định dựng SQLite cô lập và cache tại `artifacts/agent-evaluation/eval-baseline.db`; không cần PostgreSQL production.
- Cache được fingerprint theo đúng seed directory, importer và schema; đổi seed sẽ tự làm cache cũ mất hiệu lực.
- Không truyền `--database-source` khi tạo baseline chính thức, trừ khi chủ động đánh giá một snapshot khác và ghi rõ trong report.
- Redis local không chạy có thể sinh warning và fallback SQL; đây không phải benchmark failure nếu case vẫn hoàn tất.
- LangSmith/trace ngoài không bắt buộc. Evidence chấm điểm đã được runner lấy từ tool trace nội bộ và DB cô lập.

### Đơn giá model

Các ví dụ dưới đây dùng rate đã cấu hình trong báo cáo dự án:

```text
gpt-5.6-luna: input $0.20/M, output $1.20/M
gpt-4o-mini: input $0.15/M, output $0.60/M
```

Đây là **rate đầu vào của phép đo**, không phải cam kết giá provider hiện tại. Trước khi báo cáo cost mới, backend phải xác minh giá áp dụng rồi thay các giá trị `--model-price` tương ứng.

## 3. Kiểm tra nhanh trước khi tốn tiền

### 3.1 Validate dataset và evaluator, không gọi model

```powershell
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\golden\agent_cases.json `
  --negative-golden eval\golden\negative_cases.json `
  --json-output "$BENCH_OUT\schema-report.json" `
  --markdown-output "$BENCH_OUT\schema-report.md"
```

Chế độ này chỉ validate và tạo inventory. Các behavioral metric sẽ là `NOT_RUN`; không được gọi đây là kết quả live.

### 3.2 Backend tests và lint

```powershell
& $PY -m pytest backend\tests -q
& $PY -m ruff check backend
```

Coverage:

```powershell
& $PY -m pytest backend\tests `
  --cov=backend\src `
  --cov-report=term-missing `
  --cov-report="json:$BENCH_OUT\coverage.json"
```

Kết quả cần ghi: tổng pass/fail/skip/warning và line coverage. Warning không được cộng thành pass hay fail nhưng phải nêu loại warning.

## 4. Guardrail benchmark — 93 case offline

Chạy toàn bộ và so với baseline đã commit:

```powershell
& $PY backend\scripts\run_guardrail_benchmark.py `
  --dataset eval\benchmarks\guardrails_cases.json `
  --verify-baseline eval\benchmarks\results\baseline.json `
  --fail-under 1.0 `
  --json-output "$BENCH_OUT\guardrails-report.json" `
  --markdown-output "$BENCH_OUT\guardrails-report.md"
```

Pass khi:

- `total_cases = 93`;
- `pass_rate = 1.0`;
- không thiếu category coverage;
- command trả exit code `0`.

Chạy một lát cắt khi debug:

```powershell
& $PY backend\scripts\run_guardrail_benchmark.py --kind input
& $PY backend\scripts\run_guardrail_benchmark.py --kind output
& $PY backend\scripts\run_guardrail_benchmark.py --kind tool
& $PY backend\scripts\run_guardrail_benchmark.py --category explicit_confirmation
```

Không dùng kết quả lát cắt thay kết quả 93 case.

## 5. Negative/security fixtures — 16 case

Chạy độc lập, không gọi LLM:

```powershell
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\golden\agent_cases.json `
  --negative-golden eval\golden\negative_cases.json `
  --run-negative-fixtures `
  --fail-under-negative-accuracy 1.0 `
  --predictions-output "$BENCH_OUT\negative-predictions.json" `
  --json-output "$BENCH_OUT\negative-report.json" `
  --markdown-output "$BENCH_OUT\negative-report.md"
```

Đọc `negative_security` trong JSON. Pass khi `scored_cases = total_cases = 16`, `accuracy = 1.0` và từng nhóm authorization/OTP, vehicle slot, staff capacity, concurrency/reliability không có fixture fail.

Các metric agent của lệnh này là `NOT_RUN` vì không có live prediction; đó là trạng thái đúng.

## 6. Official live benchmark — đủ 61 case

### 6.1 Smoke một case

```powershell
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\golden\agent_cases.json `
  --live `
  --case SEARCH-001 `
  --model-price "gpt-5.6-luna=0.20,1.20" `
  --model-price "gpt-4o-mini=0.15,0.60" `
  --predictions-output "$BENCH_OUT\smoke-predictions.json" `
  --json-output "$BENCH_OUT\smoke-report.json" `
  --markdown-output "$BENCH_OUT\smoke-report.md"
```

Smoke chỉ xác nhận môi trường và provider hoạt động; không đại diện kết quả 61 case.

### 6.2 Full 61 case có judge và negative fixtures

```powershell
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\golden\agent_cases.json `
  --negative-golden eval\golden\negative_cases.json `
  --live `
  --llm-judge `
  --run-negative-fixtures `
  --model-price "gpt-5.6-luna=0.20,1.20" `
  --model-price "gpt-4o-mini=0.15,0.60" `
  --predictions-output "$BENCH_OUT\official-61-predictions.json" `
  --json-output "$BENCH_OUT\official-61-report.json" `
  --markdown-output "$BENCH_OUT\official-61-report.md"
```

Không dùng `--max-cases` hoặc `--case` trong full run. `--llm-judge` cần thiết để chấm các case groundedness/hallucination chưa có deterministic evidence; nếu bỏ, một số metric có thể `NOT_RUN` hoặc task success chưa được chấm đầy đủ.

Các field bắt buộc kiểm tra trong JSON:

```text
run.status
run.attempted_active_cases
run.scored_active_cases
quality.task_success_rate
quality.challenge_task_success_rate
quality.intent_accuracy
quality.tool_accuracy
quality.argument_mean_field_f1
quality.database_assertion_pass_rate
quality.clean_execution_rate
quality.hallucination_rate
negative_security.accuracy
performance.latency_p50_ms / latency_p95_ms / latency_p99_ms
usage.input_tokens / output_tokens / total_tokens
usage.estimated_cost / judge_estimated_cost / estimated_total_eval_cost
cases[].run_status / checks / observed
```

Không chỉ nhìn tỷ lệ tổng. Mọi case `failed`, `error`, `ungraded` hoặc `not_run` phải được liệt kê bằng `case_id` và failure check cụ thể.

### 6.3 Release gate tùy chọn

Chỉ thêm gate sau khi đã thống nhất threshold cho release:

```powershell
--fail-under-task-success 0.80 `
--fail-under-challenge-task-success 0.70 `
--fail-under-clean-execution 0.90 `
--max-tool-retry-rate 0.05 `
--fail-under-argument-field-f1 0.95 `
--fail-under-negative-accuracy 1.00 `
--max-p95-latency-ms 20000 `
--fail-under-groundedness 0.90 `
--max-hallucination-rate 0 `
--min-groundedness-cases 10
```

Runner vẫn ghi artifact trước khi trả exit code `1`, vì vậy khi gate fail phải đọc report thay vì chỉ chạy lại cho đến khi đẹp.

## 7. Stability — 61 case × 3 lần

Đây là lệnh tốn nhiều thời gian và token nhất. Chỉ chạy sau khi smoke, targeted test và một full run đã ổn.

```powershell
& $PY backend\scripts\run_agent_stability.py `
  --live `
  --runs 3 `
  --llm-judge `
  --golden eval\golden\agent_cases.json `
  --negative-golden eval\golden\negative_cases.json `
  --runs-output "$BENCH_OUT\stability-3-runs.json" `
  --json-output "$BENCH_OUT\stability-3.json" `
  --markdown-output "$BENCH_OUT\stability-3.md"
```

Đọc:

- `run_count = 3`;
- `case_count = fully_scored_case_count = 61`;
- `case_pass_at_k_rate`: case pass ít nhất một trong ba lần;
- `case_pass_all_k_rate`: case pass cả ba lần;
- `unstable_case_ids`: case có kết quả thay đổi giữa các lần;
- `metric_variance.*.mean/stddev/min/max`;
- `cases[].successes`, `pass_rate`, `pass_all_k`.

Không chọn riêng lần chạy tốt nhất làm kết quả chính thức. Hidden holdout không được đưa vào stability.

Targeted stability khi điều tra lỗi:

```powershell
& $PY backend\scripts\run_agent_stability.py `
  --live --runs 3 `
  --case POSTBOOK-PROFILE-SIGNAL-001 `
  --case POSTBOOK-BOOKING-SIGNAL-001 `
  --runs-output "$BENCH_OUT\postbook-targeted-runs.json" `
  --json-output "$BENCH_OUT\postbook-targeted-stability.json" `
  --markdown-output "$BENCH_OUT\postbook-targeted-stability.md"
```

Targeted result không được dùng thay full 61 × 3.

## 8. Profile → Sales Brief focused — 10 case

Suite này bắt đúng chuỗi:

`confirmed booking → chat post-booking → update_post_booking_signals → profile/booking signal trong DB → portal generate_sales_brief → brief lưu DB`

Chạy smoke một case:

```powershell
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\golden\profile_sales_brief_cases.json `
  --live `
  --case PROFILE-BRIEF-DURABLE-HOUSEHOLD-001 `
  --model-price "gpt-5.6-luna=0.20,1.20" `
  --model-price "gpt-4o-mini=0.15,0.60" `
  --predictions-output "$BENCH_OUT\profile-brief-smoke-predictions.json" `
  --json-output "$BENCH_OUT\profile-brief-smoke-report.json" `
  --markdown-output "$BENCH_OUT\profile-brief-smoke-report.md"
```

Chạy đủ 10 case:

```powershell
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\golden\profile_sales_brief_cases.json `
  --live `
  --model-price "gpt-5.6-luna=0.20,1.20" `
  --model-price "gpt-4o-mini=0.15,0.60" `
  --predictions-output "$BENCH_OUT\profile-brief-10-predictions.json" `
  --json-output "$BENCH_OUT\profile-brief-10-report.json" `
  --markdown-output "$BENCH_OUT\profile-brief-10-report.md"
```

Primary release gate của suite là `quality.task_success_rate`: một case chỉ pass khi route, tool, required payload, response, clean execution và **toàn bộ** DB/brief assertions cùng pass. Đọc thêm:

- `quality.argument_required_match_rate` và `argument_mean_field_f1` để bắt sai schema;
- `quality.database_assertion_pass_rate` để bắt signal/brief sai;
- `cases[].checks.database` và prediction `database_assertions[]` để thấy expected/actual;
- `cases[].observed.response` để đọc brief thật;
- `quality.clean_execution_rate` và retry/error rate để bắt backend phải “tự cứu” payload.

Không có LLM judge trong suite này; chấm bằng tool trace, truy vấn DB và deterministic brief assertions. Công thức chi tiết nằm tại `eval/results/profile-sales-brief-focused-evaluation-2026-08-30.md`.

## 9. Cost per Completed Booking — 10 booking thật trong DB cô lập

Không dùng full 61 cost chia cho 10. Tử số phải chỉ gồm token/cost của đúng 10 workflow booking E2E dưới đây.

```powershell
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\golden\agent_cases.json `
  --live `
  --case CONFIRM-001 `
  --case CONFIRM-E2E-002 `
  --case CONFIRM-E2E-003 `
  --case CONFIRM-E2E-004 `
  --case CONFIRM-E2E-005 `
  --case CONFIRM-E2E-006 `
  --case CONFIRM-E2E-007 `
  --case CONFIRM-E2E-008 `
  --case CONFIRM-E2E-009 `
  --case CONFIRM-E2E-010 `
  --model-price "gpt-5.6-luna=0.20,1.20" `
  --model-price "gpt-4o-mini=0.15,0.60" `
  --predictions-output "$BENCH_OUT\booking-cost-10-predictions.json" `
  --json-output "$BENCH_OUT\booking-cost-10-report.json" `
  --markdown-output "$BENCH_OUT\booking-cost-10-report.md"
```

Phép tính:

```text
Total agent cost
  = Σ(input token của model × input rate/M
    + output token của model × output rate/M)

Cost per Completed Booking
  = Total agent cost của mọi attempt trong run / số booking confirmed pass toàn bộ case
```

Kiểm tra trong `business_metrics.cost_per_completed_booking`:

- `status = COMPLETE`;
- `completed_bookings = positive_confirmation_attempts = 10`;
- `cost = total_agent_cost / 10`;
- `tokens_per_completed_booking = total_tokens / 10`;
- từng selected slot có search evidence và booking cuối ở trạng thái `confirmed`.

Không bật `--llm-judge` vì judge không thuộc agent cost. Không cộng DB, Redis, hosting, email/SMS/Zalo hoặc nhân sự.

Lưu ý: nếu chạy model price cho full 61, không dùng `cost_per_completed_booking` của full report làm số kinh doanh vì tử số khi đó có thể chứa cost của các case không phải booking completion. Số chính thức phải lấy từ run 10 booking riêng này.

## 10. Cost từ booking đầu tiên đến Sales Profile — 10 workflow

Runner chuyên dụng thực hiện:

`chat/search → hold → customer details → confirm → post-booking profile → booking signals → sales portal → generate và lưu Sales Brief`

Smoke một workflow:

```powershell
& $PY backend\scripts\run_sales_profile_cost.py `
  --cases 1 `
  --prefix sales-profile-cost-smoke `
  --output-dir $BENCH_OUT
```

Chạy đủ 10 workflow:

```powershell
& $PY backend\scripts\run_sales_profile_cost.py `
  --cases 10 `
  --prefix sales-profile-cost-10 `
  --output-dir $BENCH_OUT
```

Artifact:

```text
sales-profile-cost-10-golden.json
sales-profile-cost-10-predictions.json
sales-profile-cost-10-report.json
sales-profile-cost-10-report.md
```

Kiểm tra `sales_profile_cost` trong JSON:

- `status = COMPLETE`;
- `completed_flows = 10`;
- mọi `cases[].completed = true`;
- không có `failed_assertions`;
- `cost_per_completed_sales_profile = total_cost / completed_flows`;
- `phase_breakdown` tách `booking_chat`, `post_booking_profile_chat`, `sales_brief_generation`;
- `retry_attempts` và attempt lỗi vẫn phải nằm trong tử số nếu dùng retry-inclusive report.

Runner này đang pin price table của dự án trong `DEFAULT_PRICES`. Phải xác minh/update price table trước khi dùng số cost trong báo cáo mới. Exit code `0` chỉ cho biết runner hoàn tất; vẫn phải kiểm tra `completed_flows` và assertion trong JSON.

Chấm lại prediction đã có, không gọi model:

```powershell
& $PY backend\scripts\run_sales_profile_cost.py `
  --cases 10 `
  --predictions-input "$BENCH_OUT\sales-profile-cost-10-predictions.json" `
  --prefix sales-profile-cost-10-rescored `
  --output-dir $BENCH_OUT
```

## 11. Rescore artifact mà không gọi lại model

Official 61:

```powershell
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\golden\agent_cases.json `
  --negative-golden eval\golden\negative_cases.json `
  --predictions "$BENCH_OUT\official-61-predictions.json" `
  --model-price "gpt-5.6-luna=0.20,1.20" `
  --model-price "gpt-4o-mini=0.15,0.60" `
  --json-output "$BENCH_OUT\official-61-rescored.json" `
  --markdown-output "$BENCH_OUT\official-61-rescored.md"
```

Profile–brief:

```powershell
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\golden\profile_sales_brief_cases.json `
  --predictions "$BENCH_OUT\profile-brief-10-predictions.json" `
  --model-price "gpt-5.6-luna=0.20,1.20" `
  --model-price "gpt-4o-mini=0.15,0.60" `
  --json-output "$BENCH_OUT\profile-brief-10-rescored.json" `
  --markdown-output "$BENCH_OUT\profile-brief-10-rescored.md"
```

Dataset SHA trong report phải khớp dataset dùng lúc tạo prediction. Nếu golden contract đã đổi, phải ghi rõ đây là rescore theo contract mới, không được gọi là rerun.

## 12. Chạy theo shard rồi merge

Có thể chạy các nhóm case thành nhiều prediction file, sau đó merge/rescore mà không gọi lại model. File truyền sau thắng nếu trùng `case_id`.

```powershell
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\golden\agent_cases.json `
  --predictions "$BENCH_OUT\shard-1-predictions.json" `
  --predictions "$BENCH_OUT\shard-2-predictions.json" `
  --predictions-output "$BENCH_OUT\merged-predictions.json" `
  --json-output "$BENCH_OUT\merged-report.json" `
  --markdown-output "$BENCH_OUT\merged-report.md"
```

Chỉ gọi run `COMPLETE` khi `attempted_active_cases = scored_active_cases = 61`. Không merge targeted rerun vào baseline mà không giữ lại provenance của base run và replacement run.

## 13. Enhanced 81 — historical/optional

Bộ này dùng để so sánh lịch sử, không thay baseline 61 hiện tại.

Validate offline:

```powershell
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\benchmarks\vinfast_agent_v1_300_enhanced\agent_cases_enhanced.json `
  --negative-golden eval\golden\negative_cases.json `
  --json-output "$BENCH_OUT\enhanced-81-schema.json" `
  --markdown-output "$BENCH_OUT\enhanced-81-schema.md"
```

Live run:

```powershell
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\benchmarks\vinfast_agent_v1_300_enhanced\agent_cases_enhanced.json `
  --negative-golden eval\golden\negative_cases.json `
  --live `
  --model-price "gpt-5.6-luna=0.20,1.20" `
  --model-price "gpt-4o-mini=0.15,0.60" `
  --predictions-output "$BENCH_OUT\enhanced-81-predictions.json" `
  --json-output "$BENCH_OUT\enhanced-81-report.json" `
  --markdown-output "$BENCH_OUT\enhanced-81-report.md"
```

Không trộn điểm 81 case lịch sử với điểm official 61 trong cùng headline.

## 14. Hidden holdout — tuyệt đối không chạy live lại

Manifest freeze đã tồn tại. Không dùng `--execute-once`, không tạo cờ force và không đưa hidden cases vào stability.

Chỉ owner có đủ private artifact mới chạy:

```powershell
& $PY backend\scripts\run_hidden_holdout.py --verify-freeze
& $PY backend\scripts\run_hidden_holdout.py --refresh-public-report
```

Nếu thiếu `eval/holdout/private`, báo thiếu quyền/artifact; không tự tái tạo hidden dataset từ public regression cases.

## 15. Thứ tự chạy khuyến nghị

### Khi sửa backend/profile/brief

1. Targeted pytest của module vừa sửa.
2. Full backend tests và Ruff.
3. Guardrail 93 case.
4. Profile–Sales Brief smoke.
5. Profile–Sales Brief đủ 10 case.
6. Official 61 full run.
7. Negative fixtures 16 case.
8. Stability 3 lần chỉ trước release hoặc sau thay đổi model/prompt/tool boundary lớn.
9. Cost booking và cost Sales Profile khi model, prompt, số lượt gọi hoặc pricing thay đổi.

### Khi chỉ sửa guardrail

1. Guardrail targeted unit tests.
2. Guardrail benchmark 93 case.
3. Benign near-match cases để kiểm tra over-blocking.
4. Full backend tests.
5. Official 61 nếu guardrail nằm trên agent input/output/tool path.

## 16. Checklist báo cáo kết quả

Mọi báo cáo gửi reviewer phải có:

- commit SHA và branch;
- ngày/giờ, máy chạy và Python version;
- dataset path, dataset version/SHA và số case;
- model/classifier/judge, temperature, reasoning effort;
- run mode: live, rescore, stability hoặc negative fixture;
- `attempted/scored/not_run/error`;
- numerator/denominator của từng metric;
- danh sách case fail/unstable, không chỉ tỷ lệ tổng;
- P50/P95/P99 latency và phạm vi latency;
- input/output/total token theo model;
- rate dùng tính cost, total cost và các khoản loại trừ;
- retry/provider failure có nằm trong cost hay không;
- đường dẫn predictions JSON, report JSON và report Markdown.

Không ghi `0%` cho metric chưa chạy. Dùng đúng `NOT_RUN`, `PARTIAL` hoặc `COMPLETE` từ report.

## 17. Troubleshooting

### `Live evaluation requires OPENAI_API_KEY or OPENROUTER_API_KEY`

Runner chưa đọc được provider key. Kiểm tra `.env` nằm ở root repo hoặc export key trong đúng terminal. Không in key ra log.

### Redis warning

Benchmark mặc định có thể fallback SQL. Nếu report/case vẫn complete thì ghi warning, không tự coi là fail. Nếu mục tiêu là benchmark Redis/concurrency thật thì phải dùng suite tích hợp riêng và mô tả hạ tầng.

### Metric là `NOT_RUN`

Kiểm tra có prediction cho đúng case không, có bật `--llm-judge` cho groundedness/hallucination không, có chạy negative fixtures không và token usage có được provider trả về không. Không đổi `NOT_RUN` thành 0.

### Dataset/cache thay đổi

Runner tự fingerprint seed/schema/importer và invalid cache khi cần. Nếu cache bị lỗi, đổi sang một path cache mới trong `artifacts`, không trỏ sang DB production.

### Tool retry nhưng DB cuối đúng

Case vẫn có thể fail `clean_execution`. Đọc `checks.execution.observed_tool_errors`, `unexpected_tool_errors` và `retry_groups`; không chỉ đọc DB cuối.

### Profile đúng trong câu trả lời nhưng Sales Brief sai

Đọc đủ ba lớp evidence: payload của `update_post_booking_signals`, signal active trong DB và `booking_profile_summaries.summary_markdown`. Không kết luận prompt hay backend chỉ từ câu trả lời chat.

## Tài liệu liên quan

- Metric và scorer tổng quát: `eval/EVALUATION.md`
- Golden contract 61 case: `eval/golden/README.md`
- Guardrail benchmark: `eval/benchmarks/README.md`
- Backend test suite: `backend/tests/README.md`
- Profile–Sales Brief findings và công thức: `eval/results/profile-sales-brief-focused-evaluation-2026-08-30.md`
