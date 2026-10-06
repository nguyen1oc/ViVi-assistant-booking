# Guardrails Security Audit Report

## 1. Thông tin audit

| Thuộc tính | Giá trị |
|---|---|
| Phạm vi | Public chat input, structured actions, tool pre-execution, public output và application trace logging |
| Phương pháp | Manual code review, abuse-case modeling, unit/integration regression và deterministic benchmark |
| Thành phần | `src/guardrails`, `src/api/routes.py`, `src/agents/graph.py`, `src/agents/trace.py`, booking tool boundary |
| Ngoài phạm vi | Hạ tầng gateway/WAF, cloud IAM, secret store, provider security và pentest production |
| Benchmark | 70 curated cases: input, output, tool, conversation capability, rate limit và persistent abuse ban |
| Kết luận | Các finding trực tiếp trong phạm vi đã được remediation và có regression gate; residual risk được liệt kê riêng |

Audit này đánh giá defense-in-depth ở biên AI/tool. Nó không thay thế
authentication, authorization trong domain service, rate limiting, database
constraints, dependency scanning hoặc kiểm thử xâm nhập.

## 2. Data flow và trust boundaries

```text
Untrusted client
  │ ChatRequest / DemoActionRequest
  ▼
Pydantic schema
  │
  ├── InputGuard: normalize, payload budget, injection, action contracts
  │      └── block: safe response, no agent invocation
  ▼
Classifier / active skill
  │
  ▼
GuardedToolNode: skill allowlist, call budget, replay, mutation isolation,
  │              explicit confirmation
  ├── block: ToolMessage(error), no tool execution
  ▼
Domain service: validation, authorization, idempotency, transaction
  │
  ▼
OutputGuard: hide analysis, redact secret/PII, prompt-leak fallback, truncate
  │
  ▼
Public ChatResponse
```

Logging là một boundary song song: request, LLM message, tool args/result và
response đi qua `trace.redact()` trước khi ghi structured event.

## 3. Risk rating

- **Critical**: có thể gây mutation trái phép hoặc lộ credential có tác động
  trực tiếp trên production.
- **High**: có đường bypass/leak thực tế nhưng cần điều kiện hoặc phạm vi hẹp.
- **Medium**: defense-in-depth thiếu, denial-of-service nhỏ hoặc false-positive
  đáng kể.
- **Low**: maintainability/observability có thể làm policy drift trong tương lai.

## 4. Findings và remediation

### GR-001 — Negated confirmation được hiểu là đồng ý

| Thuộc tính | Giá trị |
|---|---|
| Mức độ | High |
| Trạng thái | Fixed |
| Vấn đề | Regex keyword có thể hiểu câu phủ định, câu hỏi về chữ “confirm” hoặc đồng ý nhận tư vấn là consent chốt booking. |
| Remediation | Loại confirmation tool khỏi free-form LLM; chỉ cho phép structured `confirm_booking` khi ba field `booking_id/version/ui_action_id` khớp chính xác tool call. |
| Unit test | `test_natural_language_alone_never_authorizes_booking_confirmation`, `test_blocks_confirmation_not_bound_to_exact_structured_payload` |
| Benchmark | `TOOL-CONFIRM-002` đến `TOOL-CONFIRM-008` |

### GR-002 — Unicode compatibility và bidi controls có thể né input pattern

| Thuộc tính | Giá trị |
|---|---|
| Mức độ | High |
| Trạng thái | Fixed |
| Vấn đề | NFC không fold full-width ASCII và danh sách ký tự loại bỏ không bao phủ toàn bộ Unicode format controls. |
| Remediation | Chuyển sang NFKC; loại category `Cf` và control character không phải tab/newline. |
| Unit test | `test_blocks_injection_obfuscated_with_unicode_compatibility_or_bidi_controls` |
| Benchmark | `INPUT-ATTACK-008` đến `INPUT-ATTACK-010` |

### GR-003 — Structured action chỉ allowlist top-level

| Thuộc tính | Giá trị |
|---|---|
| Mức độ | High |
| Trạng thái | Fixed |
| Vấn đề | `booker_patch`, `driver_patch`, license/notification patch có thể chứa field không bao giờ hợp lệ; một object không đúng type có thể rơi xuống service. |
| Remediation | Thêm nested contract riêng cho chat và demo actions; block unknown field và non-object trước tool/service. |
| Unit test | `test_blocks_unknown_nested_structured_action_fields`, `test_blocks_non_object_nested_structured_action_field` |
| Benchmark | `INPUT-CONTRACT-003` đến `INPUT-CONTRACT-005` |

### GR-004 — Output redaction bỏ sót key naming variants và backend token

| Thuộc tính | Giá trị |
|---|---|
| Mức độ | High |
| Trạng thái | Fixed |
| Vấn đề | Exact snake-case comparison không bắt camel/kebab/space variants; `access_token` không nằm trong denylist của `action_data`. |
| Remediation | Canonicalize sensitive keys; mở rộng secret policy; redact backend access/refresh/session token, key/hash/private credential nhưng vẫn giữ hai workflow capability cần thiết. |
| Unit test | `test_redacts_sensitive_key_naming_variants_and_backend_tokens_from_action_data` |
| Benchmark | `OUTPUT-REDACTION-005`, `OUTPUT-REDACTION-006`, `OUTPUT-REDACTION-007` |

### GR-005 — Direct credential assignment và prompt marker coverage hẹp

| Thuộc tính | Giá trị |
|---|---|
| Mức độ | High |
| Trạng thái | Fixed |
| Vấn đề | Text-only secret như `openrouter_api_key=...`, `authorization: Bearer ...` hoặc một số developer/system markers có thể không có structured metadata để literal-redact. |
| Remediation | Mở rộng assignment regex và system/developer leak patterns; safe fallback thay toàn bộ response khi phát hiện prompt marker. |
| Unit test | `test_redacts_direct_credential_assignments_without_structured_secret_metadata`, `test_replaces_additional_system_prompt_leak_markers` |
| Benchmark | `OUTPUT-REDACTION-003`, `OUTPUT-LEAK-001` đến `OUTPUT-LEAK-003` |

### GR-006 — Trace logging policy drift so với public output

| Thuộc tính | Giá trị |
|---|---|
| Mức độ | High |
| Trạng thái | Fixed |
| Vấn đề | Logger có danh sách secret riêng, thiếu một số key và không redact direct credential assignment trong free text. |
| Remediation | Trace dùng sensitive-key policy tập trung, cùng canonicalization và assignment redaction; bổ sung regression test trên structured log record. |
| Unit test | `test_trace_redaction.py` |
| Benchmark | Output redaction cases kiểm chứng policy tương ứng; trace có unit gate riêng để tránh ghi report chứa log secret. |

### GR-007 — Production có thể cấu hình tắt deterministic guardrails

| Thuộc tính | Giá trị |
|---|---|
| Mức độ | Medium |
| Trạng thái | Fixed |
| Vấn đề | `GUARDRAILS_ENABLED=false` từng hợp lệ ở mọi environment. |
| Remediation | Settings fail startup nếu production tắt guardrails; debug bypass chỉ còn ở development/test. |
| Unit test | `test_production_cannot_disable_guardrails` |
| Benchmark | Không áp dụng; đây là configuration invariant. |

### GR-008 — Client tự chọn persistent conversation thread

| Thuộc tính | Giá trị |
|---|---|
| Mức độ | High |
| Trạng thái | Fixed |
| Vấn đề | `conversation_id` hợp lệ về cú pháp từng được dùng trực tiếp làm LangGraph `thread_id`, cho phép hai client cố ý dùng chung state. |
| Remediation | Public ID trở thành HMAC capability có nonce/issued-at/TTL; internal thread ID chỉ được lấy sau verify. Token sai/hết hạn tạo thread cô lập mới. |
| Unit/API test | `test_conversation.py`, `test_chat_replaces_tampered_conversation_token_with_an_isolated_thread` |
| Benchmark | `CONVERSATION-001`, `CONVERSATION-002` |

### GR-009 — Raw UI context nằm trong system role

| Thuộc tính | Giá trị |
|---|---|
| Mức độ | High |
| Trạng thái | Fixed |
| Vấn đề | Arbitrary client context được JSON-encode rồi nối vào `SystemMessage`. |
| Remediation | Top-level/nested context allowlist, type/value bounds, normalization; context sạch được gửi bằng `HumanMessage` đánh dấu untrusted data. |
| Unit/API test | `test_context_contract_*`, `test_booking_skill_sends_context_as_untrusted_human_data_not_system_instructions` |
| Benchmark | `INPUT-CONTEXT-001`, `INPUT-CONTEXT-002` |

### GR-010 — Standalone token và formatted PII lọt output/log redaction

| Thuộc tính | Giá trị |
|---|---|
| Mức độ | High |
| Trạng thái | Fixed |
| Vấn đề | Token không có `key=` metadata, phone dạng `(+84) ...` và CCCD 12 số không khớp policy cũ. |
| Remediation | Thêm provider/JWT token patterns, Vietnamese phone variants và personal-ID marker cho output lẫn trace. |
| Unit test | `test_redacts_standalone_provider_tokens_parenthesized_phone_and_personal_id`, `test_trace_redacts_standalone_token_parenthesized_phone_and_personal_id` |
| Benchmark | `OUTPUT-REDACTION-008` |

### GR-011 — Public mutation/chat boundary không có application rate limit

| Thuộc tính | Giá trị |
|---|---|
| Mức độ | High |
| Trạng thái | Fixed trong single process; distributed control vẫn open |
| Vấn đề | Chat, hold, confirm và OTP chỉ dựa vào domain cooldown hoặc hạ tầng chưa kiểm chứng. |
| Remediation | Public API middleware dùng database counter theo anonymous session và IP ngắn hạn; OTP có domain limit riêng. Không còn limiter runtime thứ hai. |
| Unit/API test | `test_rate_limit.py`, `test_chat_rate_limit_returns_retry_after_without_calling_agent`, `test_demo_*_rate_limit*` |
| Benchmark | `RATE-LIMIT-001` |

### GR-012 — Prompt injection/profanity lặp lại không dẫn tới ban

| Thuộc tính | Giá trị |
|---|---|
| Mức độ | High |
| Trạng thái | Fixed |
| Vấn đề | Input guard từng chặn từng request độc lập nhưng không tích lũy vi phạm, nên cùng client có thể thử payload độc hại liên tục. |
| Remediation | Nhận diện thêm paraphrase và abusive language; lưu SHA-256 subject trong database; strike thứ 3 trong một giờ tạo ban 24 giờ theo signed conversation + anonymous session. |
| Unit/API test | `test_abuse.py`, `test_chat_bans_ip_and_conversation_after_three_mixed_abuse_violations` |
| Benchmark | `INPUT-ATTACK-015/016`, `INPUT-ABUSE-001..003`, `ABUSE-BAN-001` |

## 5. Control matrix

| Threat | Prevent | Detect/test | Residual control |
|---|---|---|---|
| Prompt/role injection | NFKC + high-confidence patterns + context scan | Input unit/API/benchmark | Skill allowlist và domain authorization vẫn là primary containment |
| Tool privilege escalation | Per-skill allowlist | Tool unit/benchmark | Tool schema và service permission checks |
| Duplicate/batched mutation | Fingerprint + mutation isolation | Tool unit/benchmark | Idempotency key và DB transaction |
| Accidental confirmation | Structured action + exact payload binding; tool absent from free-form LLM | Unit/API/benchmark | Optimistic version và idempotency record |
| Payload abuse | Byte/depth/node/string/call budget | Unit/API/benchmark | Gateway body/rate limits |
| Secret/PII leak | Key/text redaction + prompt fallback | Output/trace/API/benchmark | Minimize data before LLM, HTTPS, proxy log policy |
| Cross-booking access | Access-session scope in service | Service negative tests | OTP limits, token TTL/revocation, database constraints |
| Conversation takeover | Signed bearer capability + TTL | Unit/API/benchmark | Session storage, HTTPS, no token logging |
| Burst abuse | Process-local IP/resource sliding window | Unit/API/benchmark | Distributed gateway/WAF limit |
| Repeated hostile input | Persistent 3-strike ban by hashed session + conversation | Unit/API/benchmark + mutation test | Authenticated account subject và admin unban flow |

## 6. Residual risks và open actions

### RR-001 — Regex không bao phủ mọi prompt injection

- Mức độ: Medium.
- Chấp nhận tạm thời: Có.
- Lý do: homoglyph đa script, encoding nhiều lớp và semantic jailbreak không thể
  được giải quyết đầy đủ bằng regex.
- Containment: tool allowlist, action contract, authorization, output redaction.
- Điều kiện đóng/giảm: bổ sung adversarial corpus từ incident/red-team; cân nhắc
  classifier riêng nhưng không thay deterministic boundaries.

### RR-002 — Workflow capability vẫn xuất hiện trong `action_data`

- Mức độ: Medium.
- `challenge_id` và `access_session_token` được giữ có chủ ý để frontend hoàn
  tất OTP flow; chúng không được phép xuất hiện trong natural-language response,
  log hoặc diagnostic `tool_input`.
- Yêu cầu vận hành: HTTPS, CORS allowlist, không log response body ở proxy/APM,
  không persist token dài hạn trong browser, TTL/revocation bắt buộc.

### RR-003 — Draft booking ID là capability trước khi xác thực OTP

- Mức độ: Medium.
- `get/update/confirm` held draft dùng opaque booking ID và optimistic version
  trong luồng tạo booking. Đây là domain design, không chỉ guardrail.
- Open action: threat-model entropy, lifetime, draft-capability binding và replay;
  cân nhắc draft capability token riêng nếu public exposure mở rộng.

### RR-004 — Distributed rate limiting/gateway controls nằm ngoài process

- Mức độ: High nếu endpoint public Internet không có gateway protection.
- App dùng public API middleware với database counters; IP chỉ là tín hiệu rate-limit ngắn hạn, không phải subject của abuse ban 24 giờ.
  Cần kiểm chứng deployment: distributed limit dùng chung giữa instance;
  request body limit; trusted client-IP handling và alert burst/anomaly.

### RR-005 — Live LLM behavior chưa được chứng minh bởi offline benchmark

- Mức độ: Medium.
- `eval/golden` hiện có behavioral specification nhưng schema validation không
  phải behavioral pass.
- Open action: chạy live evaluation trên DB cô lập, pin model/prompt/config,
  chấm tool/arguments/response/DB assertion và báo riêng known gaps.

## 7. Release checklist

- [ ] `APP_ENV=production` không thể khởi động khi guardrails tắt.
- [ ] Targeted guardrail/API tests pass.
- [ ] 70/70 deterministic benchmark cases pass.
- [ ] Full backend regression và Ruff pass.
- [ ] Không có raw secret/PII trong stdout, logs hoặc generated report.
- [ ] Action/tool mới đã cập nhật top-level và nested contract.
- [ ] Mutating tool mới đã được phân loại và có confirmation/idempotency policy.
- [ ] Gateway rate limit, HTTPS, CORS và proxy logging được kiểm chứng ở deployment.
- [ ] Residual risk/open action mới có owner và điều kiện đóng.

## 8. Cách cập nhật audit

Mỗi policy change phải cập nhật đồng thời code, test, benchmark dataset và phần
finding/control liên quan. Không chuyển finding sang `Fixed` nếu mới chỉ có tài
liệu hoặc unit test nhưng enforcement path chưa được nối vào API/graph thực tế.
