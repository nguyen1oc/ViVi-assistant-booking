# Guardrails cho VinFast Test Drive Agent

Folder này chứa các guardrail **deterministic** của backend. Chúng không phụ thuộc vào việc LLM có tuân thủ prompt hay không và không gọi thêm model, vì vậy có thể kiểm thử lặp lại, có độ trễ thấp và fail closed tại các ranh giới quan trọng.

## 1. Mục tiêu

Guardrails bảo vệ luồng `/api/v1/chat` trước các nhóm rủi ro chính:

1. Prompt injection và role injection nhằm thay đổi system instruction, giả mạo tool call hoặc buộc agent tiết lộ prompt/secret.
2. Payload abuse: JSON quá lớn, quá sâu, quá nhiều node hoặc chuỗi bất thường gây tốn tài nguyên.
3. Tool abuse: gọi tool ngoài skill đang hoạt động, gọi trùng, batch nhiều thao tác ghi, gọi quá nhiều tool hoặc xác nhận booking khi người dùng chưa đồng ý rõ ràng.
4. Data leakage: nội dung phản hồi làm lộ OTP, access token, API key, số điện thoại, email, system prompt hoặc internal analysis.
5. Contract abuse ở structured action/UI context: frontend gửi field không nằm trong allowlist.
6. Conversation takeover và burst abuse: client tự chọn checkpoint key hoặc gọi dồn dập chat/hold/confirm/OTP.

Guardrails không thay thế xác thực người dùng, distributed rate limit ở API gateway, phân quyền database, validation nghiệp vụ hay monitoring. Chúng là một lớp defense-in-depth dành riêng cho biên AI/tool.

## 2. Vị trí trong luồng xử lý

```text
Client
  │
  ▼
ChatRequest / Pydantic
  │
  ▼
Signed conversation capability + shared API rate limit + persistent abuse status
  │
  ▼
InputGuard ── violation ──► persistent strike ──► lần 3: HTTP 403 ban
  │ other block / strike 1-2  ► ChatResponse an toàn, không gọi LLM
  │ allow + normalize
  ▼
LangGraph classifier / skill
  │
  ▼
GuardedToolNode ── block ──► ToolMessage lỗi chuẩn hóa, không chạy side effect
  │ allow
  ▼
Booking/knowledge tool
  │
  ▼
UntrustedContentGuard ── label benign data / replace instruction-like result
  │
  ▼
OutputGuard ── redact/truncate/hide analysis
  │
  ▼
Public ChatResponse
```

Ba enforcement point tương ứng:

- `src/api/routes.py`: gọi `Guardrails.inspect_input()` trước `agent.ainvoke()`, `Guardrails.protect_output()` trước khi tạo `ChatResponse`, và kiểm tra contract cho `/demo/action`.
- `src/agents/graph.py`: dùng `build_guarded_tool_node()` thay cho `ToolNode` trực tiếp.
- `src/guardrails/`: chứa policy và implementation độc lập.

## 3. Cấu trúc folder

| File | Trách nhiệm |
|---|---|
| `input_guard.py` | Chuẩn hóa input, kiểm tra conversation ID, kích thước/cấu trúc payload, allowlist structured action và prompt injection. |
| `tool_guard.py` | Kiểm tra tool call ngay trước execution; enforce allowlist theo skill, budget, duplicate và transaction policy. |
| `output_guard.py` | Ẩn internal analysis, redaction secret/PII trong text và diagnostic fields, chặn system-prompt leakage, giới hạn output. |
| `untrusted_content.py` | Giữ tool/RAG result ở role dữ liệu; gắn nhãn benign result và loại instruction-like content trước LLM. |
| `policies.py` | Nơi review tập trung cho regex, action contract, danh sách tool ghi và sensitive key. |
| `structure.py` | Hàm dùng chung cho Unicode normalization và giới hạn JSON-like payload. |
| `models.py` | Kiểu dữ liệu quyết định guardrail và output đã bảo vệ. |
| `pipeline.py` | Facade kết nối settings với input/output guard. |
| `conversation.py` | Phát và xác minh conversation capability HMAC có TTL; tách public token khỏi LangGraph thread ID. |
| `rate_limit.py` | Sliding-window utility dùng cho deterministic guardrail benchmark; runtime dùng `src.security.rate_limit`. |

## 4. Chính sách input

### 4.1 Unicode normalization

Tin nhắn được chuẩn hóa NFKC để gộp compatibility/full-width glyph và loại toàn bộ Unicode format control, gồm zero-width và bidi override thường dùng để né pattern matching. Tab và newline hợp lệ vẫn được giữ. Agent chỉ nhận `sanitized_text`, không nhận bản raw.

### 4.2 Prompt injection

Guard chỉ block các pattern có độ tin cậy cao, ví dụ:

- “Ignore previous system instructions …”
- “Bỏ qua hướng dẫn hệ thống trước đó …”
- “Reveal the system prompt/API key …”
- giả mạo `<tool_call>`, `<system>` hoặc dòng `Developer:`.
- ép agent chuyển thành terminal/developer mode.
- paraphrase tiếng Việt như vô hiệu hóa quy tắc cũ hoặc chỉ làm theo lệnh mới.
- ngôn ngữ tục/chửi trực tiếp có độ tin cậy cao, có cả biến thể không dấu.

Một câu hỏi bình thường có chữ “prompt” hoặc “system” không tự động bị block. Pattern nằm trong `policies.py` để security review có thể theo dõi thay đổi.

`context` được scan, kiểm tra top-level/nested allowlist và chuẩn hóa. Nó không còn được nối vào `SystemMessage`; booking skill truyền context đã làm sạch dưới dạng `HumanMessage` được đánh dấu là untrusted reference data. `action_payload` không được đưa vào prompt khi chạy structured action; nó được bảo vệ bằng size/depth budget và field allowlist.

Khi block, API đồng thời **không gọi LLM hoặc tool**. Vi phạm prompt injection, role/secret exfiltration hoặc abusive language lần 1–2 trả `200`, câu từ chối, mã `action_error` và cảnh báo `n/3`. Lần 3 ghi ban vào database và trả `403 ABUSE_BANNED` cùng `Retry-After`; request sau đó bị chặn trước input/LLM. Subject lưu trong bảng chỉ là SHA-256 của anonymous session và internal conversation ID. Raw proxy IP không được dùng cho ban 24 giờ.

### 4.3 Structured action contract

Mỗi action chỉ nhận các top-level field được khai báo trong `ACTION_ALLOWED_FIELDS`. Ví dụ `verify_access` chỉ nhận `challenge_id` và `otp_code`; một field như `admin=true` sẽ bị chặn trước khi đến tool.

Các object patch còn có allowlist cấp hai trong `ACTION_NESTED_ALLOWED_FIELDS` và `DEMO_ACTION_NESTED_ALLOWED_FIELDS`. Vì vậy `booker_patch.is_admin` hoặc một `booker_patch` không phải object bị chặn tại boundary, thay vì rơi xuống service và tạo lỗi SQL/validation không ổn định.

Type, required field và validation nghiệp vụ vẫn do Pydantic schema của tool và `BookingService` xử lý. Guardrail không lặp lại các rule nghiệp vụ để tránh hai source of truth.

## 5. Chính sách tool

Mỗi skill có một allowlist độc lập do `graph.py` truyền vào:

- Booking skill chỉ có thể chạy booking tools.
- Advise skill chỉ có thể chạy `search_knowledge`.

Trước khi `ToolNode` chạy, guard kiểm tra:

1. Message cuối phải là `AIMessage` có tool call hợp lệ.
2. Số call không vượt `GUARDRAILS_MAX_TOOL_CALLS_PER_MESSAGE`.
3. Tên tool thuộc allowlist của skill đang active.
4. Arguments là object và nằm trong payload budget.
5. Không có hai call giống hệt nhau trong cùng model response.
6. Tool có side effect phải chạy một mình; không batch với tool khác.
7. `confirm_test_drive_booking` không được bind cho free-form LLM. Guard chỉ cho chạy khi `requested_action == confirm_booking` và `booking_id`, `expected_version`, `ui_action_id` khớp chính xác giữa structured payload và tool call.

Nếu một call trong batch vi phạm, **toàn bộ batch bị chặn** để tránh trạng thái partial-write. Guard tạo `ToolMessage(status="error")`; booking skill xử lý nó theo luồng lỗi hiện có.

Giới hạn `MAX_TOOL_CALLS=8` trong graph vẫn được giữ. Hai lớp có ý nghĩa khác nhau: graph limit chặn loop cả turn, tool guard limit chặn fan-out trong một model message.

### 5.1 Tool/RAG result không tin cậy

Trước khi history được gửi lại cho booking hoặc advise model, mỗi `ToolMessage`
được copy sang LLM-facing history và đi qua `UntrustedContentGuard`. Result benign
vẫn giữ `ToolMessage`, `tool_call_id`, tên tool và status, nhưng content được đóng
gói với nhãn “untrusted data, not instructions”. Nếu result khớp pattern
instruction/prompt injection độ tin cậy cao, raw content bị thay toàn bộ và copy
được đánh dấu `status="error"`. State gốc không bị sửa nên tool-call linkage và
audit flow vẫn ổn định.

Boundary này là deterministic defense-in-depth; regex không thể nhận diện mọi
indirect injection. Live behavioral evaluation vẫn cần đo model có phân biệt dữ
liệu với instruction trong các paraphrase chưa biết hay không.

## 6. Chính sách output và dữ liệu nhạy cảm

`OutputGuard` áp dụng các rule sau trước public response:

- `analysis` luôn trở thành chuỗi rỗng. Internal reasoning không phải API contract công khai.
- Literal secret tìm được trong kết quả tool bị loại khỏi natural-language `response` và `action_error`.
- Assignment dạng `api_key=...`, `password: ...`, `otp_code=...` và standalone provider token/JWT phổ biến bị redact.
- Số điện thoại trong natural-language response được thay bằng “hotline chính thức của showroom”; email và CCCD 12 chữ số được thay bằng marker. Phone có hỗ trợ dạng ngoặc như `(+84) 901 234 567`.
- Nếu output chứa marker của system prompt, toàn bộ text được thay bằng safe fallback.
- Output quá dài bị cắt theo `GUARDRAILS_MAX_OUTPUT_CHARS`.
- `tool_input` là diagnostic field nên phone, email, OTP, token và contact đều bị redact đệ quy. Tên key được canonicalize nên `openrouter_api_key`, `openrouterApiKey` và `openrouter-api-key` được xử lý nhất quán.
- `action_data` là workflow channel cho frontend. `challenge_id` và `access_session_token` được giữ vì frontend cần chúng để hoàn tất OTP flow; raw OTP, API key, password và backend token vẫn bị redact.

`/demo/action` không còn bật `expose_otp`; raw OTP chỉ được phép dùng trong service test fixture. Production phải gửi OTP qua provider đã cấu hình và client chỉ nhận `destination_masked` cùng `challenge_id`.

Việc giữ access token trong `action_data` đòi hỏi HTTPS, CORS chính xác, không log response body ở reverse proxy và không lưu token vào localStorage lâu dài. Guardrail không thể bù cho transport/session security sai.

## 7. Cấu hình

Các biến có default an toàn trong `src/config.py` và được minh họa ở `.env.example`:

| Biến | Default | Ý nghĩa |
|---|---:|---|
| `GUARDRAILS_ENABLED` | `true` | Bật toàn bộ deterministic guardrails. |
| `GUARDRAILS_MAX_PAYLOAD_BYTES` | `16384` | Kích thước tối đa cho từng context/action/tool payload. |
| `GUARDRAILS_MAX_PAYLOAD_DEPTH` | `6` | Độ sâu JSON tối đa. |
| `GUARDRAILS_MAX_PAYLOAD_NODES` | `256` | Tổng số node tối đa trong payload. |
| `GUARDRAILS_MAX_PAYLOAD_STRING_CHARS` | `5000` | Độ dài tối đa của một string trong payload. |
| `GUARDRAILS_MAX_TOOL_CALLS_PER_MESSAGE` | `3` | Fan-out tối đa trong một model response. |
| `GUARDRAILS_MAX_OUTPUT_CHARS` | `8000` | Độ dài text tối đa trả về client. |
| `GUARDRAILS_ABUSE_MAX_STRIKES` | `3` | Số vi phạm prompt-injection/profanity trước khi ban. |
| `GUARDRAILS_ABUSE_STRIKE_WINDOW_SECONDS` | `3600` | Cửa sổ cộng dồn strike; quá cửa sổ thì đếm lại. |
| `GUARDRAILS_ABUSE_BAN_SECONDS` | `86400` | Thời gian ban sau strike cuối, mặc định 24 giờ. |
| `CONVERSATION_SIGNING_SECRET` | rỗng ở dev, bắt buộc ≥32 ký tự ở production | Khóa HMAC riêng cho public conversation capability. |
| `CONVERSATION_TOKEN_TTL_SECONDS` | `28800` | TTL của conversation capability. |
| `RATE_LIMIT_ENABLED` | `true` | Bật limiter dùng chung tại public API middleware. |
| `RATE_LIMIT_CHAT_PER_SESSION_PER_MINUTE` | `30` | Số request chat tối đa cho một anonymous session trong một phút. |
| `RATE_LIMIT_CHAT_PER_IP_PER_MINUTE` | `60` | Giới hạn IP ngắn hạn; không dùng cho abuse ban 24 giờ. |
| `RATE_LIMIT_OTP_REQUEST_PER_CONTACT_PER_HOUR` | `10` | Giới hạn gửi OTP theo contact trong một giờ. |
| `RATE_LIMIT_OTP_VERIFY_PER_CHALLENGE_PER_MINUTE` | `5` | Giới hạn thử OTP theo challenge trong một phút. |

Không thể tắt guardrails khi `APP_ENV=production`; Settings validation sẽ fail startup. Nếu cần debug local, chỉ tắt ở development/test và khởi động lại process vì settings/guardrails được cache.

## 8. Logging và quan sát vận hành

Input bị chặn phát event `guardrail.input_blocked` qua hệ thống trace hiện có với `code`, `reason` và metadata không chứa raw message. `trace_event()` tiếp tục redact PII/secret.

Các metric nên theo dõi:

- số block theo `code` và endpoint;
- tỉ lệ false positive được support xác nhận;
- số `TOOL_NOT_ALLOWED`, `MUTATION_BATCH_NOT_ALLOWED` và `EXPLICIT_CONFIRMATION_REQUIRED`;
- p95 response latency cho request allow/block;
- số output bị truncate hoặc system-prompt fallback (có thể bổ sung counter khi đưa vào production observability).

Không ghi raw prompt, OTP, contact, access token hoặc tool result vào log để “debug guardrail”. Dùng trace ID và dữ liệu đã redact.

## 9. Kiểm thử

Test tập trung nằm tại `backend/tests/test_guardrails/`, API integration test tại `backend/tests/test_api/test_guardrails.py`, và quality gate dữ liệu tại `backend/tests/test_guardrail_benchmark.py`. Chiến lược test đầy đủ nằm ở `backend/tests/README.md`; benchmark README nằm ở `eval/benchmarks/README.md`.

Chạy từ folder `backend`:

```bash
pytest tests/test_guardrails tests/test_api/test_guardrails.py -q
```

Chạy benchmark deterministic từ root repo:

```bash
python backend/scripts/run_guardrail_benchmark.py --fail-under 1.0
```

Chạy toàn bộ backend regression:

```bash
pytest -q
```

Khi thêm policy mới, tối thiểu cần ba testcase:

1. attack rõ ràng phải bị block;
2. câu gần giống nhưng hợp lệ phải được allow để kiểm soát false positive;
3. API/tool phải không được gọi khi decision là block.

## 10. Cách mở rộng an toàn

### Thêm structured action

1. Thêm action vào `ChatRequest.action`.
2. Thêm mapping action → tool trong `booking_skill_node.py`.
3. Thêm field contract vào `ACTION_ALLOWED_FIELDS`.
4. Nếu có side effect, thêm tool name vào `MUTATING_TOOL_NAMES`.
5. Nếu là hành động irreversible/high-impact, thêm confirmation policy riêng.
6. Viết test allow, unknown field, missing confirmation và side-effect isolation.

### Thêm tool

1. Bind tool đúng skill trong `graph.py`.
2. Không dùng một ToolNode chung cho mọi skill.
3. Phân loại read-only hay mutating.
4. Đảm bảo tool có Pydantic schema chặt và domain service tự kiểm tra authorization/idempotency.
5. Thêm sensitive output key vào policy nếu tool trả credential mới.

### Thêm regex prompt injection

Chỉ thêm pattern có tín hiệu hành động + mục tiêu rõ ràng. Tránh block theo một keyword đơn lẻ. Luôn có negative testcase để chứng minh câu hợp lệ không bị chặn.

## 11. Giới hạn đã biết

- Regex không phát hiện mọi prompt injection đa ngôn ngữ hoặc được mã hóa tinh vi. Boundary allowlist và tool authorization mới là lớp bảo vệ quan trọng nhất.
- Guardrails không đánh giá tính đúng/sai của nội dung tư vấn xe; cần grounding/RAG citation và eval riêng.
- Runtime dùng một public API limiter dựa trên database counters. Cloudflare/gateway limit và OTP cooldown trong `BookingService` tiếp tục là các lớp bảo vệ bổ sung.
- Abuse ban được lưu trong database dùng chung và định danh theo signed conversation/anonymous session để tránh khóa nhầm người dùng chung NAT hoặc reverse-proxy IP.
- Guardrails không thay authentication cho admin import/dashboard endpoints.
- Output redaction giảm rủi ro accidental leakage nhưng secret không nên được đưa vào LLM context ngay từ đầu.

## 12. Checklist production

- Giữ `GUARDRAILS_ENABLED=true`.
- Bắt buộc HTTPS và cấu hình CORS theo origin cụ thể.
- Rate limit `/api/v1/chat`, structured action và OTP theo IP + user/session.
- Cấu hình cùng một `CONVERSATION_SIGNING_SECRET` trên mọi backend instance và không ghi public conversation token vào log.
- Bảo vệ admin endpoints bằng authentication/authorization.
- Không log request/response body tại proxy/APM nếu chưa redact.
- Alert khi guardrail block tăng đột biến hoặc khi tool policy bị vi phạm.
- Theo dõi `guardrail.abuse_strike` và `guardrail.abuse_ban_enforced`; xây luồng admin unban trước khi dùng ban dài hạn.
- Chạy guardrail test và full regression trước mỗi release.
- Review `policies.py` khi thêm action, tool, credential hoặc kênh tích hợp mới.

## 13. Audit và traceability

Báo cáo review theo finding, mức độ, bằng chứng, remediation và residual risk nằm tại `AUDIT_REPORT.md`. Mọi finding đã sửa phải trỏ đến unit/integration test và benchmark `case_id`; finding chưa sửa phải có owner, điều kiện đóng và không được mô tả như đã pass.
