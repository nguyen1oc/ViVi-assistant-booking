# Backend Defect Log — Test Cases of Chau

## Thông tin chung

| Thuộc tính | Giá trị |
|---|---|
| Project | P-053 — VinFast Test Drive Booking |
| Phạm vi | Backend booking service, Agent nodes/graph và Tool wrappers |
| Người phụ trách testcase | Chau |
| Ngày cập nhật | 2026-08-04 |
| Nguồn phát hiện | Automated tests trong backend/tests/test_services, test_agents, test_tools và test_api |
| Kết quả gần nhất | 187 passed, 26 xfailed, 1 skipped |

## Quy ước trạng thái

| Trạng thái | Ý nghĩa |
|---|---|
| OPEN | Đã có bằng chứng từ code/test, chưa được sửa |
| TBD | Cần BA/PO/Dev chốt requirement trước khi kết luận defect |
| IN PROGRESS | Dev đang xử lý |
| READY FOR RETEST | Dev báo đã sửa, chờ QA chạy lại |
| CLOSED | Retest pass và đã bỏ xfail |

## Danh sách tổng hợp

| Defect ID | Mô tả | Severity | Trạng thái |
|---|---|---:|---|
| CHAU-BE-001 | Nhập OTP sai nhưng attempt_count không tăng | P0 | CLOSED |
| CHAU-BE-002 | OTP không khóa sau số lần thử tối đa | P0 | CLOSED |
| CHAU-BE-003 | Booking details trả nguyên số GPLX | P0 | CLOSED — đã bỏ số GPLX |
| CHAU-BE-004 | Idempotency key dùng chéo giữa các operation | P0 | CLOSED |
| CHAU-BE-005 | Replay cancel trả cache trước khi xác thực token | P0 | CLOSED |
| CHAU-BE-006 | Notification preferences được lưu nhưng bị bỏ qua | P1 | CLOSED |
| CHAU-BE-007 | Chuyển sang Driver riêng ghi đè thông tin Booker | P0 | CLOSED |
| CHAU-BE-008 | Booking confirmed đọc được qua draft tool không cần OTP | P0 | CLOSED |
| CHAU-BE-009 | hold_slot chấp nhận TTL bằng 0 hoặc âm | P1 | CLOSED |
| CHAU-BE-010 | Xe maintenance vẫn có thể được giữ nếu slot còn available | P0 | CLOSED |
| CHAU-BE-011 | Quy tắc đặt xe có pin dưới minimum SOC chưa rõ | — | TBD policy |
| CHAU-BE-012 | Showroom ID không tồn tại trả response rỗng | P1 | CLOSED — `343570c` |
| CHAU-BE-013 | preferred_time ngoài phạm vi 24 giờ vẫn được nhận | P1 | CLOSED — `343570c` |
| CHAU-BE-014 | Partial person patch bắt nhập lại full_name | P1 | CLOSED — `343570c` |
| CHAU-BE-015 | Cam kết GPLX true vẫn bắt class và validity cũ | P1 | CLOSED — `343570c` |
| CHAU-BE-016 | Reminder được tạo trong quá khứ | P1 | CLOSED |
| CHAU-BE-017 | OTP channel không có whitelist | P1 | CLOSED |
| CHAU-BE-018 | OTP resend không enforce cooldown | P0 | CLOSED |
| CHAU-BE-019 | Importer nhận tọa độ ngoài phạm vi địa lý | P2 | CLOSED — `343570c` |
| CHAU-BE-020 | Metadata file bị bỏ qua nhưng không report skipped | P2 | OPEN |
| CHAU-AGENT-001 | Classifier chấp nhận intent ngoài enum cho phép | P1 | CLOSED — `ab1dc2d` |
| CHAU-AGENT-002 | Advise skill không fallback khi LLM phát sinh exception | P1 | CLOSED — `ab1dc2d` |
| CHAU-AGENT-003 | tool_call_count không reset giữa các user turn | P1 | CLOSED — `ab1dc2d` |
| CHAU-TOOL-002 | Skill docs có address nhưng search tool không public | P1 | CLOSED — `343570c` |
| CHAU-BE-022 | Provider exception làm notification job kẹt processing | P1 | OPEN |
| CHAU-API-001 | Chat chấp nhận message chỉ có khoảng trắng | P2 | CLOSED — `ab1dc2d` |
| CHAU-API-002 | conversation_id không giới hạn độ dài | P1 | CLOSED — `ab1dc2d` |
| CHAU-API-003 | Chat trả nguyên văn exception nội bộ cho client | P0 | CLOSED — `ab1dc2d` |

## Cập nhật retest sau khi đồng bộ `origin/testing` ngày 2026-08-04

Backend mới đã refactor booking service thành package và sửa các defect CHAU-BE-001–007, CHAU-BE-009–010 và CHAU-BE-016–018. Các marker `xfail` tương ứng đã được bỏ sau khi testcase pass.

Retest với `origin/feat/tools` commit `343570c` đã đóng 11 test items trước đây là `XFAIL`:

- CHAU-BE-012: showroom ID không tồn tại đã trả `SHOWROOM_NOT_FOUND`.
- CHAU-BE-013: hour/minute ngoài phạm vi đã trả `INVALID_INPUT` — 3 dữ liệu test.
- CHAU-BE-014: partial patch không còn bắt nhập lại `full_name`.
- CHAU-BE-015: cam kết GPLX boolean không còn bắt class và validity legacy.
- CHAU-BE-019: latitude/longitude ngoài phạm vi đã bị từ chối — 4 dữ liệu test.
- CHAU-TOOL-002: search tool đã public và forward `address`.
- CHAU-BE-008: retest xác nhận confirmed booking đã bị chặn bằng `BOOKING_DRAFT_NOT_AVAILABLE`; testcase cũ được cập nhật mã lỗi và bỏ `xfail`.
- CHAU-BE-020 vẫn được ghi nhận trong backlog, nhưng test report metadata đã được bỏ khỏi suite vì ngoài acceptance scope của MVP.

CHAU-BE-011 tiếp tục ở backlog `TBD`; test skip đã được bỏ khỏi suite cho tới khi BA/PO chốt chính sách pin tối thiểu.

## Cập nhật retest `origin/feat/agent` ngày 2026-08-04

Commit `ab1dc2d` đã sửa và đóng CHAU-AGENT-001–003 cùng CHAU-API-001–003.
Sáu testcase tương ứng đã được bỏ marker `xfail` và đều pass. CHAU-BE-022 vẫn mở
vì exception từ messaging provider vẫn thoát khỏi dispatcher.

## Defect mới từ bộ test Agent và Tool

### CHAU-AGENT-001 — Classifier không giới hạn enum intent

- Testcase: `test_classifier_rejects_unknown_llm_intent`
- Test file: `test_agents/test_nodes_unit.py`
- Expected: chỉ chấp nhận `domain`, `general`, `sensitive`.
- Actual: `RouteSchema.intent` là `str`, nên giá trị như `unknown` vẫn qua validation và bị router xử lý như domain.
- Rủi ro: output LLM sai contract có thể đi vào skill nghiệp vụ thay vì fallback an toàn.

### CHAU-TOOL-002 — Contract address giữa skill docs và tool bị lệch

- Testcase: `test_search_tool_schema_includes_documented_address`
- Test file: `test_tools/test_tool_registry.py`
- Expected theo booking skill: Agent có thể truyền `address` để tìm showroom gần nhất.
- Actual: schema `search_test_drive_options` không có tham số `address`.
- Rủi ro: LLM làm đúng hướng dẫn trong skill nhưng không thể tạo tool call hợp lệ với địa chỉ người dùng.

## Defect mới từ staff service, notification, Agent–Tool và Chat API

### CHAU-BE-022 — Provider exception làm notification job kẹt

- Testcase: `test_provider_exception_does_not_crash_dispatcher_or_stick_job`
- Actual: exception từ `send_message()` thoát khỏi dispatcher; job đã chuyển sang `processing` nhưng không được trả về `pending` hoặc `failed`.
- Rủi ro: reminder/confirmation không được retry và cả batch dừng giữa chừng.

### CHAU-AGENT-002 — Advise skill không fallback khi LLM lỗi

- Testcase: `test_advise_agent_handles_llm_exception_with_safe_response`
- Actual: exception từ LLM thoát khỏi graph và `/chat` trả HTTP 500.
- Rủi ro: lỗi provider tạm thời làm mất toàn bộ câu trả lời thay vì thông báo retry an toàn.

### CHAU-AGENT-003 — Bộ đếm tool không reset theo user turn

- Testcase: `test_classifier_resets_tool_call_counter_for_new_user_turn`
- Actual: `tool_call_count` nằm trong checkpoint nhưng classifier không reset khi nhận query mới.
- Rủi ro: sau đủ tám vòng tool trong cả conversation, các lượt chat sau có thể bị chặn tool dù là yêu cầu mới.

### CHAU-API-001 — Chat nhận message chỉ có khoảng trắng

- Testcase: `test_chat_rejects_whitespace_only_message`
- Actual: `min_length` tính cả whitespace nên request vẫn gọi Agent.
- Rủi ro: tốn tài nguyên và tạo state hội thoại rác.

### CHAU-API-002 — conversation_id không có giới hạn độ dài

- Testcase: `test_chat_rejects_oversized_conversation_id`
- Actual: chuỗi 10.000 ký tự được dùng trực tiếp làm LangGraph `thread_id`.
- Rủi ro: tăng bộ nhớ checkpoint/log và mở bề mặt resource abuse.

### CHAU-API-003 — API làm lộ exception nội bộ

- Testcase: `test_chat_does_not_expose_internal_exception_details`
- Actual: endpoint trả `detail=str(exception)` cho client.
- Rủi ro: có thể lộ host nội bộ, thông tin provider, câu SQL hoặc secret xuất hiện trong exception.

---

## CHAU-BE-001 — OTP sai không tăng attempt count

- Severity: P0 — Security
- Trạng thái: CLOSED — retest pass 2026-08-04
- Testcase: test_wrong_otp_increments_attempt_count
- Test file: test_services/test_access_security.py
- Production code: src/services/booking.py, hàm verify_access()

### Bước tái hiện

1. Tạo booking confirmed và OTP challenge còn hiệu lực.
2. Gọi verify_access() với OTP sai.
3. Đọc attempt_count trong bảng otp_challenges.

### Expected

    attempt_count = 1
    status = pending

### Actual

    attempt_count = 0
    status = pending

### Nguyên nhân nghi ngờ

Code cập nhật attempt_count rồi raise BookingError bên trong transaction. Transaction rollback khi có exception nên attempt count không được lưu.

### Tiêu chí retest

- Một lần nhập sai làm attempt count tăng đúng một đơn vị.
- Bỏ xfail và chạy lại testcase phải pass.

---

## CHAU-BE-002 — OTP không khóa sau số lần thử tối đa

- Severity: P0 — Security
- Trạng thái: CLOSED — retest pass 2026-08-04
- Testcase: test_otp_locks_after_max_attempts
- Test file: test_services/test_access_security.py

### Expected

    Sau 5 lần sai:
    attempt_count = 5
    status = locked

### Actual

    attempt_count = 0
    status = pending

Lỗi này là hậu quả trực tiếp của CHAU-BE-001.

---

## CHAU-BE-003 — Booking details trả nguyên số GPLX

- Severity: P0 — Privacy/Security
- Trạng thái: CLOSED — backend không còn lưu/trả license_number
- Testcase: test_booking_details_masks_license_number
- Test file: test_services/test_access_security.py
- Production code: get_booking_details() và _draft()

### Expected

    license_number = ********6789

Hoặc không trả license_number nếu client không cần sử dụng.

### Actual

    license_number = 790123456789

### Rủi ro

- Lộ qua Browser DevTools hoặc frontend log.
- Bị lưu trong screenshot hoặc monitoring payload.
- Client nhận nhiều PII hơn mức cần thiết.

---

## CHAU-BE-004 — Idempotency key dùng chéo operation

- Severity: P0 — Transaction integrity
- Trạng thái: CLOSED — action ID đã có namespace theo operation
- Testcase: test_idempotency_key_is_scoped_by_operation
- Test file: test_services/test_booking_management.py
- Production code: hold_slot() và confirm_booking()

### Bước tái hiện

    hold_slot(action_id = shared-action)
    confirm_booking(action_id = shared-action)

### Expected

- Hai operation không được dùng nhầm cache của nhau.
- Confirm tạo booking code hoặc trả lỗi duplicate key rõ ràng.

### Actual

- confirm_booking() trả cached response của hold_slot().
- Response vẫn có status = held.
- Booking không được confirmed.

### Đề xuất

Scope idempotency theo operation + action_id + booking/user scope.

---

## CHAU-BE-005 — Replay cancel bỏ qua access token

- Severity: P0 — Authorization
- Trạng thái: CLOSED — authorization chạy trước idempotency replay
- Testcase: test_cancel_idempotent_replay_still_requires_valid_token
- Test file: test_services/test_booking_management.py
- Production code: cancel_booking()

### Bước tái hiện

1. Cancel booking bằng token hợp lệ và action id cancel-01.
2. Gọi lại cùng action id nhưng dùng token giả.

### Expected

    ACCESS_SESSION_EXPIRED hoặc ACCESS_DENIED

### Actual

Backend trả cached success vì kiểm tra idempotency cache trước _require_access().

### Tiêu chí retest

Authentication và booking scope phải được kiểm tra trước khi trả cached response.

---

## CHAU-BE-006 — Notification preferences bị bỏ qua

- Severity: P1 — Functional/Consent
- Trạng thái: CLOSED — retest pass 2026-08-04
- Testcase: test_confirm_booking_respects_notification_preferences
- Test file: test_services/test_draft_and_confirm.py
- Production code: _create_jobs()

### Test data

    sms_enabled = 1
    email_enabled = 0
    reminder_24h_enabled = 0
    reminder_2h_enabled = 0

### Expected

Chỉ tạo booking_confirmation qua SMS.

### Actual

Tạo booking_confirmation, reminder_24h và reminder_2h. Tất cả bị hard-code channel = sms.

### Nguyên nhân

Notification plan được lưu vào database nhưng _create_jobs() không đọc plan và luôn tạo cố định ba jobs.

---

## CHAU-BE-007 — Driver riêng ghi đè Booker

- Severity: P0 — Data integrity
- Trạng thái: CLOSED — retest pass 2026-08-04
- Testcase: test_switching_to_separate_driver_preserves_booker
- Test file: test_services/test_draft_and_confirm.py
- Production code: update_booking_draft()

### Bước tái hiện

1. Tạo draft với driver_same_as_booker = true.
2. Booker và Driver cùng trỏ đến person_001.
3. Cập nhật driver_patch để chọn Driver khác.

### Expected

    Booker: person_001, Chau
    Driver: person_002, Nam

### Actual

    Booker: person_001, Nam
    Driver: person_001, Nam

### Nguyên nhân

Code thấy Driver đã có person ID nên update record đó, nhưng không kiểm tra ID đang được Booker dùng chung.

---

## CHAU-BE-008 — Confirmed booking đọc được qua draft tool

- Severity: P0 — Privacy/Authorization
- Trạng thái: OPEN
- Testcase: test_get_draft_rejects_confirmed_booking_without_access
- Test file: test_services/test_draft_and_confirm.py
- Production code: get_booking_draft() và _draft()

### Bước tái hiện

1. Confirm booking.
2. Gọi get_booking_draft(booking_id) không có OTP/token.

### Expected

- Từ chối vì booking không còn là held draft.
- Booking confirmed phải đi qua OTP và get_booking_details().

### Actual

Hàm trả Booker, Driver, contact, license declaration và notification plan.

---

## CHAU-BE-009 — Hold chấp nhận TTL bằng 0 hoặc âm

- Severity: P1 — Validation/Availability
- Trạng thái: CLOSED — retest pass 2026-08-04
- Testcase: test_hold_slot_rejects_non_positive_ttl[0/-1]
- Test file: test_services/test_search_and_hold.py
- Production code: hold_slot()

### Expected

- Trả INVALID_INPUT.
- Không tạo booking.
- Slot vẫn available.

### Actual

Booking held vẫn được tạo với hold_expires_at bằng hiện tại hoặc nằm trong quá khứ.

---

## CHAU-BE-010 — Xe maintenance vẫn có thể được hold

- Severity: P0 — Core business rule
- Trạng thái: CLOSED — hold đã revalidate trạng thái xe
- Testcase: test_hold_slot_rejects_vehicle_not_ready[slot_maintenance]
- Test file: test_services/test_search_and_hold.py
- Production code: search_options() và hold_slot()

### Điều kiện

    slot.status = available
    vehicle.operational_status = maintenance

### Expected ở mức nghiệp vụ

Khách không được tạo hold cho xe đang maintenance.

### Actual

hold_slot() chỉ kiểm tra slot.status và overlap nên vẫn tạo booking held.

### Quyết định kiến trúc cần chốt

Chọn một hoặc cả hai:

1. Khi xe chuyển maintenance, tự động chuyển slot liên quan sang blocked trong cùng transaction.
2. hold_slot() revalidate operational_status ngay trước khi tạo booking.

---

## CHAU-BE-011 — Chính sách minimum battery SOC chưa rõ

- Severity: Chưa đánh giá
- Trạng thái: TBD policy
- Backlog item: kiểm tra `minimum_booking_soc` sau khi BA/PO chốt thời điểm áp dụng policy.

### Câu hỏi cho BA/PO

- Pin thấp lúc đặt có block slot diễn ra sau nhiều ngày không?
- Chỉ block slot bắt đầu trong khoảng thời gian gần?
- Xe đang charging có được đặt cho ngày mai không?
- minimum_booking_soc được kiểm tra lúc search, hold hay check-in?
- Có tạo charging task thay vì từ chối booking không?

### Kết luận hiện tại

Chưa nên kết luận defect. Testcase đã được chuyển khỏi suite sang backlog cho tới khi policy được chốt.

---

## Cách chạy lại defect tests

Từ thư mục backend:

    & ..\.venv\Scripts\python.exe -m pytest tests\test_services -v

Chạy riêng một defect:

    & ..\.venv\Scripts\python.exe -m pytest tests\test_services\test_access_security.py::test_otp_locks_after_max_attempts -v

## Quy trình đóng defect

1. Dev sửa production code và ghi Defect ID trong commit/PR.
2. Chuyển trạng thái sang READY FOR RETEST.
3. QA bỏ pytest.mark.xfail của testcase tương ứng.
4. Chạy riêng testcase và toàn bộ backend suite.
5. Nếu đều pass, cập nhật trạng thái CLOSED và ghi commit đã sửa.
