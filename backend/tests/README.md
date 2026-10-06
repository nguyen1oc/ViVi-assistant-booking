# Backend Test Suite

Đây là tài liệu vận hành riêng cho bộ test backend. Mục tiêu của suite là phát
hiện regression ở business logic, API, agent/tool boundary, guardrails, dữ liệu
golden và internal portal mà không cần gọi LLM thật hoặc dịch vụ bên ngoài.

## 1. Phạm vi và nguyên tắc

- Test phải lặp lại được: cố định thời gian, seed, database fixture và mock mọi
  provider không thuộc process hiện tại.
- Unit test không gọi mạng, không dùng API key thật và không phụ thuộc thứ tự
  chạy.
- Test có side effect phải dùng SQLite/database fixture riêng cho từng test.
- Mỗi lỗi production phải có regression test tái hiện lỗi trước khi sửa.
- Guardrail/security test phải có cả attack case và benign-near-match để kiểm
  soát đồng thời false negative và false positive.
- Dataset validation pass không đồng nghĩa agent/LLM behavior đã pass. Hai kết
  luận này phải được báo cáo riêng.

## 2. Cấu trúc

| Vị trí | Trách nhiệm |
|---|---|
| `test_guardrails/` | Unit test input/output/tool guard, pipeline và log redaction. |
| `test_api/` | Contract và integration test cho FastAPI; xác nhận request bị block không gọi agent/service. |
| `test_agents/` | Router, node, tool loop, structured action và conversation state. |
| `test_tools/` | Schema và wrapper của LangChain tools. |
| `test_services/` | Booking lifecycle, OTP/access, concurrency, notification và import. |
| `test_internal_portal/` | Authentication, authorization, route và service của portal. |
| `test_guardrail_benchmark.py` | Gắn toàn bộ dataset benchmark offline vào CI. |
| `test_golden_dataset.py` | Kiểm tra schema, deduplication và trạng thái review của golden dataset. |
| `conftest.py` | Database, clock, provider và domain fixtures dùng chung. |

## 3. Ma trận test tối thiểu

| Lớp | Happy path | Boundary | Negative/security | Side-effect assertion |
|---|---|---|---|---|
| Input guard | Câu hỏi xe/booking hợp lệ | Unicode, payload đúng ngưỡng | Injection, invalid ID, field ngoài contract | Agent không được gọi khi block |
| Output guard | Nội dung booking bình thường | Output đúng giới hạn | PII/secret/prompt leak | Public response không chứa dữ liệu gốc |
| Tool guard | Tool đúng skill | Fan-out đúng giới hạn | Cross-skill, duplicate, negated confirmation | Tool bị block không được execute |
| Booking service | Search → hold → update → confirm | Hết hạn, version, pin/xe/staff | Cross-customer access, OTP replay | DB status/event/idempotency đúng |
| API | Request/response đúng schema | Field optional và error mapping | Contract abuse, log leakage | Mock agent/service có/không được gọi đúng |
| Golden/benchmark | Dataset hợp lệ | Filter/tag/category | Duplicate ID, known gap | Report và exit code phản ánh đúng |

## 4. Chạy test

Từ thư mục gốc repo trên PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```

Chỉ chạy guardrails và API security:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  backend\tests\test_guardrails `
  backend\tests\test_api\test_guardrails.py `
  backend\tests\test_guardrail_benchmark.py -q
```

Trên Linux/macOS:

```bash
.venv/bin/python -m pytest backend/tests -q
```

Chạy một test khi điều tra lỗi:

```powershell
.\.venv\Scripts\python.exe -m pytest `
  backend\tests\test_guardrails\test_tool_guard.py::test_blocks_confirmation_when_user_phrase_is_explicitly_negated `
  -vv
```

Coverage cục bộ, giống phạm vi CI:

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests `
  --cov=backend\src --cov-report=term-missing
```

## 5. Viết test mới

Áp dụng Arrange–Act–Assert và đặt tên theo hành vi:

```python
def test_blocks_unknown_nested_booking_fields():
    # Arrange
    payload = {"booker_patch": {"full_name": "An", "is_admin": True}}

    # Act
    decision = inspect_action(payload)

    # Assert
    assert decision.allowed is False
    assert decision.code == "ACTION_FIELDS_NOT_ALLOWED"
```

Quy ước:

1. Assert cả kết quả và side effect quan trọng, ví dụ `agent.assert_not_awaited()`
   hoặc mock tool không được gọi.
2. Ưu tiên kiểm tra mã lỗi ổn định; không phụ thuộc toàn bộ câu thông báo nếu
   copy có thể thay đổi.
3. Dùng `pytest.mark.parametrize` cho một policy với nhiều biến thể đầu vào.
4. Không dùng `sleep`; điều khiển thời gian bằng clock fixture.
5. Không hardcode credential thật. Secret test phải là giá trị giả rõ ràng như
   `sk-fake` hoặc `workflow-session`.
6. Không làm test pass bằng cách nới assertion khi có regression. Xác định thay
   đổi behavior là chủ ý hay lỗi, rồi cập nhật code/policy và tài liệu cùng lúc.

## 6. Test guardrails theo risk case

Khi thêm hoặc sửa một guardrail, tối thiểu cần bốn lớp bằng chứng:

1. Unit attack case: payload độc hại bị block/redact.
2. Unit benign case: câu gần giống nhưng hợp lệ không bị over-block.
3. Boundary integration: API/tool không thực thi downstream side effect.
4. Benchmark case: thêm case version-controlled trong
   `eval/benchmarks/guardrails_cases.json`.

Mỗi case benchmark có `case_id`, `kind`, `category`, `input`, `expected` và
`tags`. `case_count` phải được cập nhật và toàn bộ case phải đạt 100% để qua
quality gate deterministic.

## 7. Golden dataset và behavioral evaluation

`eval/golden/agent_cases.json` mô tả intent, tool, arguments, DB assertions và
hành vi cấm. `test_golden_dataset.py` chỉ xác minh chất lượng cấu trúc; nó không
gọi agent thật. Vì một số case có mutation và phụ thuộc LLM/DB, behavioral run
phải dùng môi trường cô lập, model/config được pin và database có thể reset.

Không được báo “agent benchmark pass” nếu mới chỉ chạy schema validation hoặc
guardrail benchmark offline.

## 8. Release gate đề xuất

Một thay đổi liên quan agent/booking/guardrails sẵn sàng merge khi:

- targeted tests của phần thay đổi pass;
- guardrail benchmark đạt `100%` và không có case bị bỏ qua;
- full backend regression pass;
- Ruff pass trên code/test mới;
- không xuất hiện secret/PII trong failure output hoặc report;
- known gap mới được ghi rõ owner, mức độ, điều kiện đóng và không bị trình bày
  nhầm thành pass.

## 9. Điều tra test fail

1. Chạy lại đúng node bằng `-vv --tb=long`.
2. Phân loại lỗi: code regression, fixture drift, contract thay đổi có chủ ý,
   dữ liệu không deterministic hoặc dependency/environment.
3. Với security failure, giữ fail-closed và kiểm tra downstream mock/DB trước.
4. Với benchmark failure, đọc `cases[].failures` trong JSON report; không chỉ
   nhìn pass rate tổng.
5. Sau khi sửa, chạy targeted suite, benchmark, rồi full regression theo thứ
   tự để rút ngắn vòng phản hồi.
