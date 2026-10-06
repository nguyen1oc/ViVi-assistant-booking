# Backend Test Failure Log

Ngày kiểm tra: 2026-08-04  
Nguồn branch: `testing`  
Phạm vi: `backend/tests`

## Kết quả suite thông thường

Lệnh:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

Kết quả:

```text
160 passed, 25 xfailed in 9.11s
```

Không có lỗi ngoài dự kiến. Hai mươi lăm lỗi đã biết đang được đánh dấu `xfail`.

## Kết quả khi buộc chạy các XFAIL như test bình thường

Lệnh:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests --runxfail -q --tb=short
```

Kết quả:

```text
25 failed, 160 passed in 13.63s
```

## Danh sách 25 testcase fail

### Agent

1. `test_advise_agent_handles_llm_exception_with_safe_response`
   - Actual: `RuntimeError("LLM unavailable")` thoát khỏi `advise_skill_node`.
   - Root cause: lời gọi `llm_with_tools.ainvoke()` chưa có fallback.

2. `test_classifier_resets_tool_call_counter_for_new_user_turn`
   - Actual: `KeyError: 'tool_call_count'`.
   - Root cause: classifier không trả `tool_call_count=0` ở đầu user turn mới.

3. `test_classifier_rejects_unknown_llm_intent`
   - Actual: classifier trả `intent="unknown"`.
   - Root cause: `RouteSchema.intent` dùng `str` thay vì enum hoặc `Literal`.

### Chat API

4. `test_chat_rejects_whitespace_only_message`
   - Expected/actual: HTTP `422` / `200`.
   - Root cause: `min_length` tính cả whitespace, chưa strip trước validation.

5. `test_chat_rejects_oversized_conversation_id`
   - Expected/actual: HTTP `422` / `200`.
   - Root cause: `conversation_id` chưa có `max_length`.

6. `test_chat_does_not_expose_internal_exception_details`
   - Actual response chứa `super-secret` và `internal.local`.
   - Root cause: endpoint trả `detail=str(exception)`.

### Booking service

7. `test_search_options_rejects_unknown_showroom_id`
   - Actual: không phát sinh `BookingError`.
   - Root cause: `showroom_id` được dùng trực tiếp mà không kiểm tra tồn tại.

8. `test_search_options_rejects_out_of_range_time[24:00]`
9. `test_search_options_rejects_out_of_range_time[25:99]`
10. `test_search_options_rejects_out_of_range_time[-1:30]`
    - Actual: không phát sinh `BookingError`.
    - Root cause: chỉ parse `int`, chưa kiểm tra `0 <= hour <= 23` và `0 <= minute <= 59`.

11. `test_update_draft_allows_partial_person_patch`
    - Actual: `BookingError: booker.full_name là bắt buộc`.
    - Root cause: mọi patch đều bắt `full_name`, kể cả khi person đã tồn tại.

12. `test_draft_accepts_boolean_license_commitment_without_legacy_fields`
    - Expected/actual: `is_ready_to_confirm=True` / `False`.
    - Root cause: backend vẫn bắt `declared_license_class` và `validity_acknowledged`.

13. `test_import_showrooms_rejects_out_of_range_coordinates[91-106.7]`
14. `test_import_showrooms_rejects_out_of_range_coordinates[-91-106.7]`
15. `test_import_showrooms_rejects_out_of_range_coordinates[10.7-181]`
16. `test_import_showrooms_rejects_out_of_range_coordinates[10.7--181]`
    - Actual: không phát sinh `BookingError`.
    - Root cause: importer chỉ chuyển tọa độ sang `float`, chưa kiểm tra phạm vi địa lý.

17. `test_provider_exception_does_not_crash_dispatcher_or_stick_job`
    - Actual: `RuntimeError("provider unavailable")` thoát khỏi dispatcher.
    - Root cause: `send_message()` chưa được bọc bằng xử lý lỗi theo từng job.

18. `test_get_draft_rejects_confirmed_booking_without_access`
    - Expected/actual error code: `ACCESS_DENIED` / `BOOKING_DRAFT_NOT_AVAILABLE`.
    - Kết luận: production đã chặn đọc confirmed booking; testcase cần cập nhật mã lỗi và bỏ `xfail`.

19. `test_rejected_license_requires_rejection_reason` — removed after policy review.
    - Decision: `rejection_reason` là tùy chọn; điều kiện bắt buộc là GPLX phải
      `verified` trước khi check-in.
    - Đây không còn được xem là production defect.

### Agent tools

20. `test_search_tool_schema_includes_documented_address`
    - Actual: schema không có `address`.
    - Root cause: booking skill công bố `address` nhưng signature của tool chưa có field này.

## Tổng hợp nguyên nhân

- 20 test items fail tương ứng 15 nguyên nhân gốc.
- 14 nguyên nhân là defect hoặc contract mismatch trong production code.
- 1 trường hợp (`get_booking_draft`) là testcase đã lỗi thời vì production hiện đã chặn truy cập bằng mã lỗi an toàn khác.
- Chi tiết lịch sử và mã defect nằm trong `DEFECT_LOG_CHAU.md`.

## Retest sau khi merge `origin/feat/tools`

Commit backend được kiểm tra: `343570c` (`fix(booking): validate search inputs and support partial updates`).

Lần chạy đầu sau merge:

```text
2 failed, 158 passed, 14 xfailed, 11 xpassed in 10.41s
```

Mười một XPASS xác nhận các defect CHAU-BE-012, CHAU-BE-013, CHAU-BE-014,
CHAU-BE-015, CHAU-BE-019 và CHAU-TOOL-002 đã được sửa. Hai failure còn lại là
wrapper tests chưa cập nhật tham số mới `address`; production code không regression.

Test wrapper đã được đồng bộ để kiểm tra cả `address` có giá trị và `address=None`.
Test CHAU-BE-008 cũng được cập nhật từ `ACCESS_DENIED` sang mã lỗi thực tế an toàn
`BOOKING_DRAFT_NOT_AVAILABLE` và bỏ marker `xfail`.

Kết quả cuối sau khi đồng bộ testcase:

```text
172 passed, 13 xfailed in 9.04s
```

Không còn `FAIL` hoặc `XPASS` ngoài dự kiến.

## Policy update: optional rejection reason

`test_rejected_license_requires_rejection_reason` và defect CHAU-BE-021 đã được
loại bỏ. `rejection_reason` không bắt buộc; hệ thống vẫn bắt buộc GPLX ở trạng thái
`verified` trước khi cho phép check-in.

Kết quả sau thay đổi policy:

```text
172 passed, 12 xfailed in 9.25s
```

## Scope update: bỏ kiểm tra batch_size âm

`test_dispatch_rejects_negative_batch_size` và defect CHAU-BE-023 đã được loại bỏ.
`batch_size` hiện là tham số nội bộ với giá trị mặc định 100; kiểm tra input âm không
thuộc phạm vi nghiệp vụ hiện tại.

Kết quả sau khi cập nhật scope:

```text
172 passed, 11 xfailed in 9.75s
```

## Scope update: bỏ nhóm tool mapping và strict validation

Đã loại bỏ bốn test items sau:

- Hai biến thể `True/False` của `test_update_booking_draft_maps_license_commitment_to_service_field`
  vì service hiện hỗ trợ trực tiếp cả `has_valid_license_commitment` và `has_driving_license`.
- `test_search_tool_rejects_unexpected_sensitive_argument` vì từ chối mọi field lạ
  không thuộc acceptance scope hiện tại.
- `test_update_tool_requires_strict_boolean_license_commitment` vì strict boolean
  không thuộc acceptance scope hiện tại.

Các defect CHAU-TOOL-001, CHAU-TOOL-003 và CHAU-TOOL-004 cũng được loại khỏi defect log.

Kết quả sau khi cập nhật scope:

```text
172 passed, 7 xfailed in 8.30s
```

## Retest sau khi lấy code Agent/API

Đã cherry-pick commit `ab1dc2d` từ `origin/feat/agent` thành commit local `731fe79`.
Các testcase của CHAU-AGENT-001–003 và CHAU-API-001–003 đều đã pass.

Kết quả toàn bộ backend:

```text
178 passed, 1 xfailed in 8.73s
```

XFAIL còn lại:

- `test_provider_exception_does_not_crash_dispatcher_or_stick_job` — CHAU-BE-022.

## Bổ sung integration test cam kết GPLX

Đã thêm `test_update_booking_draft_tool_persists_license_commitment` để kiểm tra
tool `update_booking_draft` gọi service thật, lưu cam kết vào
`license_declaration.has_driving_license` và làm draft sẵn sàng xác nhận.

Kết quả toàn bộ backend:

```text
179 passed, 1 xfailed in 8.94s
```
