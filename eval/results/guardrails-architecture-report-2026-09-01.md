# Báo cáo kiến trúc Guardrails hiện tại — 01/09/2026

## 1. Mục tiêu

Guardrails của project là các lớp bảo vệ deterministic đặt tại biên API, input, tool, dữ liệu truy xuất và output. Các lớp này **không phụ thuộc vào việc LLM có tự tuân thủ prompt hay không** và không gọi thêm model để quyết định allow/block.

Các rủi ro chính được bảo vệ:

- Prompt injection, role injection và yêu cầu lấy system prompt/secret.
- Payload quá lớn, quá sâu hoặc có field ngoài contract.
- Chiếm conversation, spam request và abuse lặp lại.
- Gọi tool ngoài skill, gọi tool ghi sai điều kiện hoặc tạo partial write.
- Indirect injection nằm trong tool/RAG result.
- Lộ OTP, token, API key, PII, system prompt hoặc internal analysis ở output/log.

Guardrails là một phần của defense-in-depth. Chúng không thay thế authentication, OTP authorization, validation nghiệp vụ, phân quyền DB, HTTPS, API gateway hoặc monitoring production.

## 2. Vị trí các lớp trong luồng

```text
Client
  │
  ▼
Pydantic request contract
  │
  ▼
Conversation capability + API rate limit + abuse status
  │
  ▼
InputGuard
  │ allow: chỉ chuyển sanitized message/context
  │ block: không gọi LLM hoặc tool
  ▼
Classifier / Booking skill / Post-booking skill
  │
  ▼
GuardedToolNode
  │ allow: chạy tool
  │ block: tạo ToolMessage lỗi, không chạy side effect
  ▼
Booking / Knowledge / Profile tool
  │
  ▼
UntrustedContentGuard
  │
  ▼
LLM tổng hợp câu trả lời
  │
  ▼
OutputGuard + trace redaction
  │
  ▼
Public ChatResponse
```

Ba enforcement point chính:

| Enforcement point | Vị trí | Trách nhiệm |
|---|---|---|
| API boundary | `src/api/routes.py` | Conversation token, rate limit, abuse status, input inspection và output protection |
| Agent graph boundary | `src/agents/graph.py` | Thay `ToolNode` trực tiếp bằng guarded tool node theo từng skill |
| Guardrail modules | `src/guardrails/` | Policy và implementation deterministic độc lập |

## 3. Tổng quan từng lớp

| Lớp | Guard bằng cách nào | Khi phát hiện vi phạm | Side effect có chạy không? |
|---|---|---|---:|
| Request contract | Pydantic kiểm tra kiểu và cấu trúc request | Trả validation error | Không |
| Conversation capability | Public token có nonce, issued time, HMAC-SHA256 và TTL | Token sai/hết hạn không được dùng làm internal thread ID | Không dùng thread bị giả mạo |
| Rate limit | Giới hạn theo anonymous session, IP, contact OTP và challenge OTP | Trả rate-limit response cùng thời gian retry | Không |
| Persistent abuse | Ghi strike theo subject đã SHA-256; ban ở strike thứ ba | Lần 1–2 trả safe response; lần 3 trả HTTP 403 và `Retry-After` | Không |
| Input Guard | Normalize Unicode; regex high-confidence; payload budget; context/action allowlist | Trả mã lỗi deterministic và safe message | Không gọi LLM/tool |
| Tool Guard | Allowlist theo skill; tool-call budget; duplicate/batch/state/confirmation checks | Chặn cả batch và tạo `ToolMessage(status="error")` | Không |
| Untrusted Content Guard | Gắn nhãn tool data là untrusted; scan indirect injection | Thay raw result bằng thông báo blocked trước khi đưa lại LLM | Tool đã chạy nhưng nội dung độc hại không tới LLM |
| Output Guard | Ẩn analysis; redact secret/PII; chặn prompt leak; truncate | Trả response đã sanitize hoặc safe fallback | Không tạo side effect mới |
| Trace/log redaction | Redact key nhạy cảm và credential/PII trong diagnostic text | Log/trace chỉ giữ dữ liệu đã làm sạch | Không ảnh hưởng nghiệp vụ |

## 4. Conversation capability

Client không được tự chọn trực tiếp LangGraph thread ID. Server phát một public conversation capability có dạng version, thời điểm phát, nonce và chữ ký HMAC-SHA256.

Khi nhận lại token, server kiểm tra:

1. Đúng cấu trúc và version.
2. Nonce đúng định dạng.
3. Chữ ký khớp bằng constant-time comparison.
4. Token chưa hết TTL và không đến từ tương lai.

Chỉ sau khi verify thành công, nonce mới được ánh xạ thành internal thread ID. Token bị sửa hoặc hết hạn không thể chiếm history của conversation khác.

Thông số hiện tại:

```text
CONVERSATION_SIGNING_SECRET: bắt buộc >= 32 byte ở production
CONVERSATION_TOKEN_TTL_SECONDS: 28.800 giây (8 giờ)
```

## 5. Rate limit và persistent abuse

Runtime áp dụng rate limit dùng chung ở public API; limiter trong `src/guardrails/rate_limit.py` chủ yếu phục vụ deterministic benchmark. Các bucket cấu hình hiện tại gồm:

| Bucket | Giới hạn hiện tại | Mục đích |
|---|---:|---|
| Chat theo anonymous session | 30 request/phút | Hạn chế spam theo phiên |
| Chat theo IP | 60 request/phút | Hạn chế burst ngắn hạn |
| Gửi OTP theo contact | 10 request/giờ | Hạn chế OTP bombing |
| Verify OTP theo challenge | 5 request/phút | Hạn chế brute force OTP |

Abuse tracker xử lý prompt injection, role/secret exfiltration và abusive language lặp lại:

```text
Strike window: 3.600 giây
Ban threshold: 3 strike
Ban duration: 86.400 giây (24 giờ)
```

Subject được lưu dưới dạng SHA-256 của anonymous session/internal conversation identity. Raw proxy IP không được dùng làm định danh ban dài hạn để tránh khóa nhầm nhiều người dùng chung NAT.

## 6. Input Guard

### 6.1 Chuẩn hóa trước khi kiểm tra

- Chuẩn hóa Unicode NFKC để gộp full-width/compatibility characters.
- Loại Unicode format control như zero-width và bidi override.
- Giữ tab/newline hợp lệ.
- Agent chỉ nhận `sanitized_text`, không nhận raw message.

Điều này ngăn các chuỗi như full-width text, zero-width character hoặc bidi control né pattern matching.

### 6.2 Prompt, role và secret injection

InputGuard scan cả message và các string trong context bằng pattern high-confidence, gồm:

- Yêu cầu bỏ qua instruction trước đó.
- Giả mạo system/developer/tool message.
- Yêu cầu tiết lộ system prompt, API key, access/authentication token.
- Yêu cầu chuyển agent sang terminal/developer mode.
- Các biến thể tiếng Việt, không dấu và mixed-language.

Guard không chặn chỉ vì xuất hiện từ khóa. Các ngoại lệ hiện có:

| Tình huống | Quyết định hiện tại |
|---|---|
| Trích dẫn hoặc giải thích câu “ignore previous instructions” | Cho phép |
| Trích dẫn nhưng yêu cầu agent thực thi nội dung injection | Chặn |
| “Token/voucher sạc” | Cho phép |
| “Authentication/access token của hệ thống” | Chặn |
| Hoàng Sa/Trường Sa, Đảng, Chủ tịch Hồ Chí Minh | InputGuard cho phép đi qua |

“Cho phép đi qua” chỉ có nghĩa guardrail không block. Chất lượng câu trả lời sau đó vẫn phụ thuộc routing, knowledge và policy của agent.

### 6.3 Payload budget

Input context, structured action và tool arguments bị giới hạn:

| Giới hạn | Giá trị |
|---|---:|
| Kích thước mỗi payload | 16.384 byte |
| Độ sâu tối đa | 6 |
| Tổng node tối đa | 256 |
| Độ dài mỗi string | 5.000 ký tự |

Payload rỗng sau normalize, circular/non-serializable, quá sâu, quá lớn hoặc vượt node budget bị chặn trước LLM.

### 6.4 UI context và structured action contract

- UI context chỉ nhận top-level và nested field đã khai báo.
- Legacy frontend fields được canonicalize có kiểm soát.
- Field không hợp lệ hoặc mâu thuẫn với UI stage bị loại/chặn.
- Mỗi structured action có allowlist riêng.
- Nested patch cũng có allowlist cấp hai.

Ví dụ `verify_access` chỉ nhận `challenge_id` và `otp_code`; thêm `admin=true` bị chặn tại API boundary. Type và validation nghiệp vụ cuối cùng vẫn do Pydantic tool schema và `BookingService` xử lý để tránh hai source of truth.

## 7. Tool Guard

Mỗi skill có tool allowlist riêng. Booking skill chỉ chạy booking tools; post-booking skill chỉ chạy `search_knowledge` và `update_post_booking_signals`.

Trước khi tool thực thi, guard kiểm tra:

1. Message cuối là `AIMessage` có tool call hợp lệ.
2. Số tool call trong một model response không vượt cấu hình, hiện là 3.
3. Tool thuộc allowlist của skill đang active.
4. Arguments là object và không vượt payload budget.
5. Không có hai call giống hệt nhau trong cùng response.
6. Tool có side effect phải chạy một mình, không batch cùng tool khác.
7. Booking confirmation/destructive management phải có structured confirmation bind đúng payload.

Nếu một call trong batch vi phạm, toàn bộ batch bị chặn để không tạo partial write. Guard tạo một `ToolMessage` lỗi cho từng call bị chặn, giữ đúng tool-call linkage để graph có thể xử lý tiếp mà không tạo dangling tool call.

Graph còn có giới hạn tối đa 8 tool call cho cả turn. Giới hạn này chặn loop dài; tool guard limit 3 chặn fan-out trong một model message.

## 8. Explicit confirmation và thao tác ghi

Các thao tác nhạy cảm không được ủy quyền chỉ bằng câu free-form do model tự suy ra.

Đối với `confirm_test_drive_booking`, guard chỉ cho chạy khi:

- `requested_action == confirm_booking`.
- `booking_id`, `expected_version` và `ui_action_id` khớp chính xác giữa structured payload và tool call.
- Không có phủ định như “chưa xác nhận” hoặc “đừng đặt”.

Các tool thay đổi/hủy lịch cũng phải bind với structured confirmation tương ứng. Việc này ngăn prompt injection hoặc model tự ý tạo side effect dù tool name hợp lệ.

## 9. Untrusted Content Guard

Tool/RAG result không được xem là instruction. Trước khi history được gửi lại model:

- Tool result benign vẫn giữ role `ToolMessage`, `tool_call_id`, tool name và status.
- Nội dung được bọc bằng nhãn “untrusted data, not instructions”.
- Nếu result chứa instruction-like injection, raw content bị thay hoàn toàn bằng thông báo blocked và status chuyển thành error trong bản LLM-facing.
- State/audit gốc không bị sửa, nên vẫn giữ được trace và linkage để điều tra.

Đây là defense chống indirect prompt injection từ knowledge/RAG/tool response. Pattern deterministic không thể bao phủ mọi paraphrase, nên behavioral evaluation vẫn cần thiết.

## 10. Output Guard và bảo vệ dữ liệu

OutputGuard chạy trước khi tạo public `ChatResponse`:

- Xóa internal `analysis`.
- Redact literal secret lấy từ tool result.
- Redact assignment như API key, password, OTP và standalone provider token/JWT.
- Redact customer phone, email và CCCD trong natural-language response.
- Nếu phát hiện marker system-prompt leakage, thay toàn bộ text bằng safe fallback.
- Cắt output vượt 8.000 ký tự.
- Redact đệ quy dữ liệu nhạy cảm trong `tool_input`, `action_error` và diagnostic fields.

Redaction có xét nguồn/loại dữ liệu:

- Contact công khai của showroom/tư vấn viên được lấy từ typed trusted backend result có thể được giữ.
- Contact khách hàng vẫn bị redact.
- `challenge_id` và `access_session_token` trong typed `action_data` được giữ vì frontend cần để hoàn tất workflow.
- Raw OTP, API key, password và backend token luôn bị loại khỏi public output.

Production không expose OTP qua `/demo/action`; client chỉ nhận masked destination và challenge ID. HTTPS, CORS và chính sách không log response body vẫn bắt buộc vì output guard không thể thay thế transport security.

## 11. Trace và log redaction

Trace/log guard canonicalize tên key để nhận diện các biến thể như snake_case, camelCase hoặc kebab-case. Credential, OTP, provider token, phone, email và personal ID trong nested object hoặc diagnostic text được redact trước khi ghi log.

Mục tiêu là vẫn giữ event name, trace ID, tool name, status và error code để điều tra, nhưng không lưu raw secret/PII.

## 12. Fail-closed và cấu hình production

- Input bị block: không gọi LLM hoặc tool.
- Tool bị block: không chạy side effect; trả ToolMessage lỗi chuẩn hóa.
- Indirect injection: không đưa raw tool content vào model.
- Output nghi lộ system prompt: thay toàn bộ bằng safe fallback.
- `APP_ENV=production` không cho tắt guardrails; settings validation làm startup fail nếu cấu hình không an toàn.

## 13. Kết quả xác nhận implementation hiện tại

Kết quả này chỉ dùng để xác nhận các lớp mô tả phía trên đang hoạt động theo fixture hiện có:

| Kiểm tra | Kết quả |
|---|---:|
| Deterministic guardrail benchmark | **93/93 = 100%** |
| Attack block accuracy | **100%** |
| Benign allow accuracy | **100%** |
| Output protection accuracy | **100%** |
| Guardrail unit tests | **155/155** |
| Benchmark median latency | **2,0783 ms** |
| Benchmark P95 latency | **4,0837 ms** |

Latency trên là thời gian benchmark cục bộ, không phải API production P95.

## 14. Giới hạn hiện tại

- Regex/policy deterministic không thể nhận diện toàn bộ prompt injection diễn đạt mới.
- Rate limit trong một process không thay thế distributed limiter tại gateway/shared store.
- `93/93` chứng minh fixture hiện tại pass, không phải penetration-test certificate.
- Câu civic/history và token/voucher hiện có regression test riêng nhưng chưa nằm trong dataset 93 case.
- Guardrails không đảm bảo agent trả lời đúng nghiệp vụ; correctness và hallucination được đo bằng benchmark khác.
- Sau triển khai vẫn cần đo block rate, false-positive rate, rate-limit events, abuse bans, tool-block events và output-redaction incidents.

## 15. Nguồn implementation và kết quả

- Kiến trúc: `backend/src/guardrails/README.md`.
- Input: `backend/src/guardrails/input_guard.py`.
- Tool: `backend/src/guardrails/tool_guard.py`.
- Untrusted content: `backend/src/guardrails/untrusted_content.py`.
- Output: `backend/src/guardrails/output_guard.py`.
- Conversation: `backend/src/guardrails/conversation.py`.
- Abuse: `backend/src/guardrails/abuse.py`.
- Benchmark result: `artifacts/guardrail-benchmark/current-report.json`.
