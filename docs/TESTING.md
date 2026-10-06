# Tài liệu kiểm thử

Tài liệu này mô tả chiến lược kiểm thử, cách chạy, cách chấm và bằng chứng chất
lượng của hệ thống đặt lịch lái thử VinFast. Báo cáo kết quả mới nhất tại
[`eval/results/report_final.md`](../eval/results/report_final.md) là nguồn số liệu
chính thức; tài liệu này không thay thế artifact JSON sinh bởi runner.

## 1. Mục tiêu

Bộ kiểm thử nhằm xác nhận bốn nhóm yêu cầu:

1. Nghiệp vụ booking hoạt động đúng từ tìm lịch, giữ chỗ, OTP, xác nhận, đổi và
   hủy lịch đến chống đặt trùng xe hoặc tư vấn viên.
2. Agent hiểu đúng yêu cầu, chọn đúng skill/tool, truyền đúng tham số và không
   tạo kết quả trái với dữ liệu trong database.
3. Thông tin post-booking được lưu đúng phạm vi profile/booking và xuất hiện
   chính xác trong Sales Brief.
4. Guardrails chặn input, tool call hoặc output không an toàn mà không phụ thuộc
   hoàn toàn vào việc LLM tuân thủ prompt.

## 2. Nguồn và phạm vi test

Các case agent là dữ liệu **synthetic**, được xây dựng từ contract nghiệp vụ,
luồng booking phổ biến, lỗi regression đã quan sát trong quá trình phát triển và
các tình huống khó cần chủ động kiểm tra. Kết quả phỏng vấn/người dùng thử chỉ
được dùng để tham khảo tình huống; dữ liệu cá nhân thật không được chép vào golden
dataset.

| Bộ kiểm thử | Phạm vi | Cách thực thi |
|---|---:|---|
| Backend regression | `backend/tests/` | Unit, integration, API, service và database fixture; không gọi LLM thật |
| Guardrail benchmark | 93 case | Deterministic, offline, so với baseline trong Git |
| Agent regression chính thức | 61 case | Chạy agent thật trên SQLite cô lập; gồm 49 regression và 12 challenge |
| Negative/security | 16 case | Fixture thực thi cho OTP, authorization, concurrency và double-booking |
| Groundedness/hallucination | 20 case | So response với tool evidence và trusted context bằng LLM judge |
| Stability | 61 case × 3 lần | Đo pass từng vòng, pass ít nhất một vòng và pass cả ba vòng |
| Profile → Sales Brief | 10 case | Chấm tool payload, DB signals và Sales Brief bằng assertion deterministic |
| Sales Profile cost | 10 workflow | Đo token/cost từ chat booking đến khi Sales Brief được lưu |
| Frontend/portal | 3 ứng dụng | `npm ci` và production build trong CI |

Golden set được quản lý tại [`eval/golden`](../eval/golden/README.md). Dữ liệu
live benchmark được import vào SQLite riêng và reset theo từng case; runner mặc
định không đọc hoặc ghi database production.

## 3. Cấu trúc test backend

| Thư mục/file | Nội dung kiểm thử |
|---|---|
| `backend/tests/test_services/` | Booking lifecycle, search/hold, OTP, quyền truy cập, concurrency, notification và profile brief |
| `backend/tests/test_api/` | Pydantic contract, API response, conversation security và guardrail boundary |
| `backend/tests/test_agents/` | Classifier, skill routing, tool loop, state nhiều lượt và structured action |
| `backend/tests/test_tools/` | Tool registry, schema, validation và wrapper |
| `backend/tests/test_guardrails/` | Input, output, tool, untrusted content, abuse, rate limit và trace redaction |
| `backend/tests/test_internal_portal/` | Authentication, authorization, route và service của portal |
| `backend/tests/test_golden_dataset.py` | Schema, ID, deduplication và contract của golden dataset |
| `backend/tests/test_guardrail_benchmark.py` | Tích hợp guardrail benchmark vào pytest/CI |

Mỗi test có side effect dùng database fixture cô lập. Provider bên ngoài và thời
gian hệ thống được mock/fix khi cần để kết quả có thể lặp lại.

## 4. Cách chạy

Tất cả lệnh dưới đây chạy từ thư mục gốc repository.

### 4.1 Chuẩn bị Python

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
$PY = ".\.venv\Scripts\python.exe"
```

Không commit `.env`, API key, OTP hoặc raw trace chứa PII.

### 4.2 Backend regression và kiểm tra tĩnh

```powershell
& $PY -m pytest backend\tests -q
& $PY -m ruff check backend\src backend\tests
& $PY -m ruff format --check backend\src backend\tests
& $PY -m mypy --ignore-missing-imports backend\src
```

Chạy coverage:

```powershell
& $PY -m pytest backend\tests `
  --cov=backend\src `
  --cov-report=term-missing `
  --cov-report=json:artifacts\backend-coverage.json
```

### 4.3 Guardrail benchmark offline

```powershell
& $PY backend\scripts\run_guardrail_benchmark.py `
  --dataset eval\benchmarks\guardrails_cases.json `
  --verify-baseline eval\benchmarks\results\baseline.json `
  --fail-under 1.0 `
  --json-output artifacts\guardrail-benchmark\report.json `
  --markdown-output artifacts\guardrail-benchmark\report.md
```

Suite chỉ đạt khi đủ 93 case, pass rate bằng 100%, không thiếu category và lệnh
trả exit code `0`.

### 4.4 Kiểm tra contract benchmark, không gọi model

```powershell
& $PY backend\scripts\build_golden_dataset.py --check
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\golden\agent_cases.json `
  --negative-golden eval\golden\negative_cases.json `
  --json-output artifacts\agent-evaluation\inventory.json `
  --markdown-output artifacts\agent-evaluation\inventory.md
```

Lệnh này chỉ xác nhận dataset/scorer. Các behavioral metric sẽ là `NOT_RUN`; đây
không phải kết quả agent live.

### 4.5 Agent live benchmark

Live run cần API key/model config và package `eval/data/seed` hợp lệ. Nên chạy
một case smoke trước:

```powershell
& $PY backend\scripts\run_agent_evaluation.py `
  --golden eval\golden\agent_cases.json `
  --live `
  --case SEARCH-001 `
  --predictions-output artifacts\agent-evaluation\smoke-predictions.json `
  --json-output artifacts\agent-evaluation\smoke-report.json `
  --markdown-output artifacts\agent-evaluation\smoke-report.md
```

Lệnh đầy đủ, cách chạy 61 case × 3, negative fixtures, profile/brief và cost được
quy định tại
[`eval/BACKEND_BENCHMARK_RUNBOOK.md`](../eval/BACKEND_BENCHMARK_RUNBOOK.md).
Mỗi run phải lưu model, cấu hình, commit SHA, dataset hash và artifact gốc; không
chọn riêng lần chạy tốt nhất để báo cáo.

### 4.6 Frontend và portal

```powershell
Push-Location frontend
npm ci
npm run build
Pop-Location

Push-Location internal-portal\frontend
npm ci
npm run build
Pop-Location

Push-Location human-review\frontend
npm ci
npm run build
Pop-Location
```

Hiện CI frontend là build verification; repository chưa có automated browser
E2E đầy đủ cho ba giao diện. Không được mô tả build pass là UI workflow đã được
kiểm thử end-to-end.

## 5. Cách chấm các metric chính

| Metric | Công thức/evidence |
|---|---|
| Booking task success | Case pass toàn bộ intent, skill, tool, required arguments, response, DB/policy và clean execution / 61 active case |
| Classifier intent | Route classifier đúng / natural-language case có nhãn; structured action không vào mẫu số |
| Tool selection | Case chọn đúng tool bắt buộc hoặc đúng khi không gọi tool / case thực thi được |
| Required argument match | Tool call có đủ field bắt buộc / tool call được chấm |
| Argument field F1 | F1 từ precision và recall trên các field argument; field thừa chỉ được bỏ qua khi contract cho phép |
| Slot availability precision | Slot hợp lệ theo DB / toàn bộ slot agent trả về |
| Selected-slot recall | Slot được chọn có trong search evidence / booking giữ slot có đủ evidence |
| Double-booking violation | Fixture xung đột bị xuyên thủng / fixture chống trùng được chạy |
| Hallucination rate | Case bị judge xác định bịa dữ liệu / groundedness case có evidence |
| Constraint violation rate | Case vi phạm forbidden-behavior deterministic / case có constraint evidence |
| Authorization/OTP violation | Fixture quyền hoặc OTP bị xuyên thủng / fixture authorization–OTP được chạy |
| P95 end-to-end latency | Percentile 95 của thời gian hoàn tất toàn case, gồm các turn/tool theo runner |
| P95 token đầu phía client | Percentile 95 từ đầu turn đến lúc SSE phát token đầu; endpoint hiện buffer response nên không phải model TTFT |
| Cost/Sales Profile | Tổng observed agent cost của toàn bộ attempt / số Sales Profile hoàn tất |

Một case có tool lỗi ngoài dự kiến hoặc retry cùng tool trong một lượt không đạt
`clean execution`, kể cả khi trạng thái cuối đã phục hồi. Metric không có evidence
phải ghi `NOT_RUN`/`null`, không đổi thành `0`.

## 6. Kết quả baseline chính thức

Baseline chốt ngày **01/09/2026**:

| Chỉ số | Kết quả |
|---|---:|
| Booking task success | **60/61 = 98,36%** |
| Pass cả ba vòng stability | **59/61 = 96,72%** |
| Classifier intent | **43/43 = 100%** |
| Tool selection | **60/60 = 100%** |
| Required argument match | **60/60 = 100%** |
| Argument field F1 | **0,9433** |
| Slot availability precision | **3.343/3.343 = 100%** |
| Double-booking violation | **0%** |
| Hallucination | **0/20 = 0%** |
| Authorization/OTP violation | **0/8 = 0%** |
| Negative/security | **16/16 = 100%** |
| Guardrail benchmark | **93/93 = 100%** |
| Full backend regression | **705 passed, 5 skipped, 0 fail** |
| Profile → Sales Brief focused | **9/10 = 90%** |
| P95 end-to-end latency | **29,88 giây** |
| P95 token đầu phía client | **21,55 giây** |
| Cost đến completed Sales Profile | **$0,023514440/profile** |

Đây là **controlled corrected report**: ba full live run gốc đã chạy đủ 61 case;
prediction của các case bị ảnh hưởng bởi fixture, scorer hoặc classifier fix được
chạy lại có kiểm soát và thay đúng vào từng full run. Không mô tả đây là một full
live run hoàn toàn mới sau mọi thay đổi.

## 7. Lỗi và giới hạn còn lại

1. `POSTBOOK-CONTEXT-001` lỗi do runtime gửi chuỗi `"unknown"` vào field boolean,
   sau đó có dangling tool call.
2. `HARD-SEARCH-DATETIME-001` chỉ pass 2/3 vì đôi lúc search xong nhưng không
   tiếp tục auto-hold.
3. `PROFILE-BRIEF-HYPOTHETICAL-NOT-FACT-001` là case fail còn lại của focused
   profile/brief do dangling tool call khi câu giả định không tạo signal.
4. 61 case là regression synthetic và chưa đại diện toàn bộ traffic, ngôn ngữ,
   thiết bị hoặc hành vi production.
5. Hallucination 0/20 chỉ có nghĩa không phát hiện hallucination trên 20 case có
   evidence; không chứng minh hệ thống không bao giờ hallucinate.
6. P95 hiện gồm chi phí fixture/DB của runner, còn SSE buffer toàn bộ response;
   hai số latency chưa phản ánh model TTFT thuần.
7. Human-review coverage chưa đủ để công bố điểm tổng hợp với hidden holdout.

Hidden holdout one-shot lịch sử đạt **16/30 = 53,33%** và được đóng băng; kết quả
này phải báo riêng, không gộp với regression hiện tại hoặc chạy lại để chọn điểm
tốt hơn.

## 8. CI và release gate

Pull request vào `testing`, `develop` hoặc `main` kích hoạt:

- Backend CI: Ruff, mypy, Bandit, guardrail benchmark, pytest + coverage,
  offline evaluation report và Docker build.
- Frontend CI: cài dependency sạch và production build cho customer app,
  internal portal và human-review portal.

Thay đổi liên quan agent/booking/guardrails chỉ nên merge khi:

1. Targeted regression của lỗi đã pass.
2. Full backend regression không có fail.
3. Guardrail benchmark đạt 93/93.
4. Golden JSON validation đạt đủ 61 case.
5. Behavioral/cost metric bị ảnh hưởng được chạy lại với artifact và provenance
   đầy đủ; metric chưa chạy phải giữ `NOT_RUN`.
6. Không có secret hoặc PII trong report được commit.

## 9. Bằng chứng và tài liệu liên quan

- Kết quả chính thức: [`eval/results/report_final.md`](../eval/results/report_final.md)
- Hướng dẫn chạy toàn bộ benchmark: [`eval/BACKEND_BENCHMARK_RUNBOOK.md`](../eval/BACKEND_BENCHMARK_RUNBOOK.md)
- Định nghĩa metric và evaluator: [`eval/EVALUATION.md`](../eval/EVALUATION.md)
- Golden dataset: [`eval/golden/README.md`](../eval/golden/README.md)
- Hallucination: [`eval/results/hallucination-evaluation-report-2026-09-01.md`](../eval/results/hallucination-evaluation-report-2026-09-01.md)
- Guardrails: [`eval/results/guardrails-architecture-report-2026-09-01.md`](../eval/results/guardrails-architecture-report-2026-09-01.md)
- Profile/Sales Brief: [`eval/results/profile-sales-brief-focused-evaluation-2026-08-30.md`](../eval/results/profile-sales-brief-focused-evaluation-2026-08-30.md)

