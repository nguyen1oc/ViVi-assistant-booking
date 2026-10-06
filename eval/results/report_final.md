# Báo cáo Evaluation cuối cùng — 01/09/2026

## 1. Phạm vi và nguồn số liệu

| Thuộc tính | Giá trị |
|---|---|
| Agent model | `gpt-5.6-luna` |
| Classifier model | `gpt-4o-mini` |
| Golden chính | 61 case active, 12 challenge |
| Golden SHA-256 | `F59D8552FC77F5E0FE0F736529B8121B99EDF78EB454A377FA6000B230026DAA` |
| Negative/security | 16 case |
| Profile → Sales Brief focused | 10 case |

Ba full live run gốc đã chạy đủ 61 case. Những case bị ảnh hưởng bởi fixture, scorer hoặc classifier fix được chạy live lại riêng rồi thay đúng prediction vào full run tương ứng để chấm lại. Do đó kết quả hiện tại là **controlled corrected report**, không được mô tả là một full live run hoàn toàn mới sau mọi thay đổi.

## 2. Kết quả chính mới nhất

| Metric | Kết quả | Mẫu số | Cách đo |
|---|---:|---:|---|
| Booking task success | **60/61 = 98,36%** | 61 task | Case chỉ pass khi intent, skill, tool, arguments, response, DB và execution bắt buộc đều đạt |
| Classifier intent | **43/43 = 100%** | 43 natural-language case | So classifier route theo contract độc lập; structured action bị loại |
| Tool selection | **60/60 = 100%** | 60 case thực thi được | Tool trace thực tế |
| Required argument match | **60/60 = 100%** | 60 case | So field bắt buộc trong tool arguments |
| Argument field F1 | **0,9433** | 60 case | Precision/recall trên toàn bộ argument field được chấm |
| Slot availability precision | **3.343/3.343 = 100%** | 3.343 slot | Đối chiếu từng slot được trả với DB cô lập |
| Selected-slot recall | **11/11 = 100%** | 11 lựa chọn | Slot được chọn phải xuất hiện trong evidence khả dụng |
| Double-booking violation | **0%** | 4 vehicle/slot + 1 staff fixture | Kiểm tra xung đột bằng executable fixture |
| Hallucination | **0/20 = 0%** | 20 groundedness case | LLM judge đối chiếu response với tool evidence và trusted context |
| Constraint violation | **0/60 = 0%** | 60 case | Deterministic forbidden-behavior checks và taxonomy |
| Authorization/OTP violation | **0/8 = 0%** | 8 fixture | Executable OTP/authorization scenarios |
| Negative/security | **16/16 = 100%** | 16 fixture | Negative benchmark |
| P95 end-to-end latency | **29.878,31 ms (29,88 giây)** | 61 case | Latency-only live rerun, không dùng LLM judge; timer hiện gồm cả chuẩn bị fixture và kiểm tra DB sau lượt chat nên chưa phải latency thuần người dùng |
| P95 token đầu tiên phía client | **21.549,06 ms (21,55 giây)** | 87 lượt chat/action trong 61 case | P95 thời gian từ đầu turn đến lúc response sẵn sàng để `/chat/stream` phát token SSE đầu tiên; endpoint hiện buffer toàn bộ response nên đây là TTFT phía client, không phải TTFT trực tiếp của model |
| Cost từ chat đến completed Sales Profile | **$0,023514440/profile** | 10/10 profile hoàn tất | Tổng observed agent cost `$0,235144400` chia 10; không tính judge và hạ tầng |

## 3. Stability

Task success của ba vòng sau khi thống nhất fixture/profile/auto-hold contract:

| Vòng | Pass | Fail | Error | Task success |
|---|---:|---:|---:|---:|
| 1 | 60 | 0 | 1 | **98,36%** |
| 2 | 59 | 1 | 1 | **96,72%** |
| 3 | 60 | 0 | 1 | **98,36%** |

- Pass ít nhất một vòng: **60/61 = 98,36%**.
- Pass cả ba vòng: **59/61 = 96,72%**.
- `HARD-SEARCH-DATETIME-001`: pass **2/3**, chưa ổn định.
- `POSTBOOK-CONTEXT-001`: error **0/3**.
- P95 trung bình: **30.673 ms**, dao động **17.475–53.953 ms**.

Classifier fix mới được xác nhận bằng unit test và một targeted live run. Chưa tuyên bố classifier stability 3/3 sau fix.

## 4. Các case profile và post-booking

### `POSTBOOK-PROFILE-SIGNAL-001` — pass 3/3

Agent ghi đúng durable profile signal:

```text
profile_signals[0].key = household_size
profile_signals[0].value = 4
profile_signals[0].subject = self
booking_signals = []
```

Scorer dùng taxonomy để phân biệt dữ liệu bền vững với context của một booking. False positive `store_booking_context_as_profile` đã được loại bỏ.

### `POSTBOOK-CONTEXT-001` — error 0/3

Sau khi fixture được sửa đúng schema, runtime lộ payload sai:

```text
driver_attending = "unknown"
driver_will_drive = "unknown"
```

Hai field chỉ nhận boolean. Tool validation thất bại, sau đó graph còn function call không có ToolMessage tương ứng và request kế tiếp lỗi:

```text
No tool output found for function call ...
```

Đây là lỗi backend thật, không nới benchmark. Backend cần bỏ signal chưa biết thay vì gửi chuỗi `"unknown"`, đồng thời luôn tạo ToolMessage cho mọi tool call kể cả validation error.

### Profile → Sales Brief focused

- Kết quả focused: **9/10 = 90%**.
- Trong 9 case thực thi được: intent, tool, arguments và DB/brief assertions đều **9/9**.
- Ba case family/attendance từng lỗi đều pass.
- Case còn lỗi: `PROFILE-BRIEF-HYPOTHETICAL-NOT-FACT-001`, HTTP 400 do dangling tool call khi câu giả định không tạo signal.

## 5. Exact datetime và auto-hold

Contract hiện tại: khi người dùng nêu đúng showroom, ngày và giờ cụ thể, agent phải search để xác minh rồi gọi `hold_test_drive_slot` ngay.

`HARD-SEARCH-DATETIME-001`:

- Hai vòng search rồi hold, DB booking/slot đều `held`.
- Một vòng chỉ search và trả danh sách, không hold.

Case pass **2/3**. Đây là runtime nondeterminism, không phải hallucination vì các slot được trả vẫn đúng tool evidence.

## 6. Hallucination

Hallucination được chấm trên 20 case có tag `groundedness`:

```text
Hallucination Rate
= số case hallucination_detected = true / số case được judge
= 0 / 20
= 0%
```

Groundedness case chỉ pass khi `groundedness_score >= 0,9` và `hallucination_detected = false`. Groundedness trung bình hiện tại là **0,9955**.

Chi tiết đầy đủ: `eval/results/hallucination-evaluation-report-2026-09-01.md`.

## 7. Guardrails

- Deterministic guardrail benchmark: **93/93 = 100%**.
- Guardrail unit tests: **155/155**.
- Attack block, benign allow và output protection accuracy: **100%** trên fixture hiện có.
- Local benchmark median: **2,0783 ms**; P95: **4,0837 ms**.

Guardrails gồm conversation capability, rate limit, abuse ban, InputGuard, ToolGuard, UntrustedContentGuard, OutputGuard và trace redaction.

Chi tiết kiến trúc: `eval/results/guardrails-architecture-report-2026-09-01.md`.

## 8. Cost

### Cost từ chat đầu đến Sales Profile

Dedicated natural-language flow hoàn tất **10/10**:

| Pha | Token | Cost |
|---|---:|---:|
| Booking chat | 172.977 | $0,035011400 |
| Post-booking profile chat | 920.125 | $0,190005800 |
| Sales Brief generation | 22.526 | $0,010127200 |
| **Tổng** | **1.115.628** | **$0,235144400** |

```text
Average cost per completed Sales Profile
= $0,235144400 / 10
= $0,023514440/profile
```

Không tính judge, DB/Redis, hosting, email, SMS hoặc Zalo.

## 9. Kiểm thử kỹ thuật

| Suite | Kết quả |
|---|---:|
| Classifier + evaluator regression mới | **94 passed**, 0 fail |
| Ruff trên code/test đã sửa | **Pass** |
| Golden JSON validation | **61 case hợp lệ** |
| Full backend sau classifier/evaluator fix | **705 passed, 5 skipped, 0 fail**, 183 warnings |
| Guardrail benchmark hiện tại | **93/93** |
| Guardrail unit tests hiện tại | **155/155** |

## 10. Kết luận

Kết quả hiện tại phù hợp để trình bày:

- **60/61 = 98,36%** ở corrected run mới nhất.
- **59/61 = 96,72%** pass ổn định cả ba vòng.
- Classifier intent mới nhất: **43/43 = 100%**.
- Hallucination: **0/20**.
- Guardrails: **93/93**.

Không che hai vấn đề backend còn lại:

1. `POSTBOOK-CONTEXT-001`: invalid `"unknown"` boolean và dangling tool call.
2. `HARD-SEARCH-DATETIME-001`: đôi lúc không tiếp tục auto-hold.

## 11. Artifact

- Corrected full report mới nhất: `artifacts/agent-evaluation/backend-20260901-classifier-fix/report-final.json`.
- Corrected predictions: `artifacts/agent-evaluation/backend-20260901-classifier-fix/report-final-predictions.json`.
- Latency-only live rerun: `artifacts/agent-evaluation/backend-20260901-latency-only/latency-report.json`.
- Client-visible TTFT calculation: `artifacts/agent-evaluation/backend-20260901-latency-only/ttft-report.md`.
- Targeted classifier live run: `artifacts/agent-evaluation/backend-20260901-classifier-fix/book-other-report.json`.
- Contract-fix stability: `artifacts/agent-evaluation/backend-20260901-contract-fix/corrected-stability-3.json`.
- Guardrail result: `artifacts/guardrail-benchmark/current-report.json`.
