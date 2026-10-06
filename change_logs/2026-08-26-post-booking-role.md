# Post-Booking Role-Aware Expansion Plan

## Authenticated Booking Context for Booking Skill

After OTP verification and `get_booking_details`, Booking Skill receives trusted `confirmed_booking_context` and the authenticated participant role. This lets it answer who it is speaking with and the matching booking, vehicle, showroom, and appointment. Profile brief, contact details, and internal IDs are excluded.

## 1. Mục tiêu

Mở rộng Post-Booking Agent để:
- hiểu đúng người đang chat là `booker`, `driver`, hoặc hai role trùng nhau;
- chăm sóc/follow-up phù hợp với vai trò thực tế trong từng buổi lái thử;
- tách đúng dữ liệu thuộc **person** và dữ liệu thuộc **booking cụ thể**;
- giúp sales biết ai sẽ tham dự, ai sẽ lái, ai sẽ đánh giá/cân nhắc xe;
Nguyên tắc giữ nguyên: Post-Booking Skill phục vụ **chuẩn bị và đánh giá buổi lái thử, không phải hoàn thiện profile**.

## 2. Kiến trúc hiện tại

OpenRouter nhận:
- Current user message
- Conversation history
- System Prompt
- Post-Booking Skill Prompt
- Profile brief
- Confirmed booking context
- Participant context
- Tool definitions/results

Hệ thống giữ riêng `driver profile` và `booker profile`. Một người có thể là driver ở booking này nhưng booker ở booking khác nên không được gộp profile theo role.

Profile chỉ lưu dữ liệu **person-scoped, durable** như usage, experience, concern, interest, recurring need, test-drive goal...

`update_user_profile` hiện enqueue Redis, trả về ngay; worker merge signals vào profile. Cơ chế async này cần giữ.

## 3. Phân tách dữ liệu

### Person-scoped → User Profile
Ví dụ:
- daily commute;
- current vehicle;
- EV/driving experience;
- recurring family usage;
- charging/parking concern;
- durable interest/intent.

### Booking-scoped → Test-Drive Context
Ví dụ:
- ai sẽ tham dự;
- booker có đi cùng không;
- có thêm người thân/khách không;
- ai sẽ lái;
- ai sẽ đánh giá xe;
- mức độ tham gia vào quyết định mua;
- hậu cần hoặc context khác chỉ có ý nghĩa với booking này.

Không đưa booking-scoped facts vào user profile.

## 4. Test-Drive Context: bảng mới, schema mở

Cho phép tạo bảng mới, ví dụ:

`test_drive_context_signals`

Không dùng các cột cố định như `booker_attending`, `will_drive`, `purchase_involvement`. Mỗi row là một **booking-scoped signal** để có thể bổ sung context mới mà không migration schema.

### Field đề xuất

| Field | Ý nghĩa |
|---|---|
| `id` | Signal ID |
| `booking_id` | Booking sở hữu signal |
| `category` | Nhóm logic: `attendance`, `participation`, `evaluation`, `logistics`, `purchase`, `custom`... |
| `key` | Stable semantic key |
| `value` | JSON/JSONB: bool/string/number/list/object |
| `description` | Human-readable summary |
| `subject` | `booking`, `booker`, `driver`, `group`, `other` |
| `certainty` | `known`, `likely`, `possible` |
| `confidence` | `0..1` |
| `source_type` | `explicit_user`, `implicit_user`, `trusted_context` |
| `source_participant` | `booker`, `driver`, `system` |
| `status` | `active`, `retracted` |
| `created_at`, `updated_at` | Timestamps |

Ví dụ signal hiện tại:

```text
category=attendance
key=booker_attending
value=true
```

Nếu sau này xuất hiện context mới:

```text
category=logistics
key=wheelchair_access_needed
value=true
```

hoặc:

```text
category=custom
key=needs_child_seat_demo
value=true
```

thì không cần đổi DB schema.

Logical identity để merge:

`booking_id + subject + category + key`

Operations:
- `add`: tạo nếu chưa có;
- `revise`: thay value;
- `strengthen/weaken`: cập nhật certainty/confidence;
- `retract`: đánh dấu retracted.

`unknown` là trạng thái hợp lệ; thường chỉ đơn giản là chưa có active signal.

## 5. Participant Context

`participant_context` là **runtime view**, không phải storage schema.

Backend build từ:
- authenticated participant;
- confirmed booking;
- active `test_drive_context_signals`.

Ví dụ:

```json
{
  "role": "booker",
  "booking_participation": {
    "attending": true,
    "will_drive": true,
    "evaluation_involvement": "high",
    "purchase_involvement": "unknown"
  },
  "other_participant": {
    "role": "driver",
    "attending": true
  },
  "additional_attendees": {
    "count": 2,
    "context": "family"
  }
}
```

Các semantic key phổ biến được backend map thành view chuẩn; signal mới/chưa có mapping được đưa vào `other_booking_context`. Nhờ vậy DB vẫn extensible nhưng prompt vẫn dễ sử dụng.

## 6. Đổi tool thành `update_post_booking_signals`

Thay `update_user_profile` bằng:

`update_post_booking_signals`

Tool vẫn:
1. nhận signals;
2. inject trusted IDs;
3. enqueue **một Redis job**;
4. return ngay;
5. worker persist bất đồng bộ.

### Parameters

```json
{
  "profile_signals": [],
  "booking_signals": []
}
```

Ít nhất một array phải có dữ liệu.

### `profile_signals`

Giữ semantics hiện tại:

```text
category
key
value
description
certainty
confidence
source_type
subject = self | third_party
operation = add | strengthen | weaken | revise | retract
```

`profile_id`, `conversation_id`, `trace_id` do backend inject.

### `booking_signals`

```text
category
key
value
description
subject = booking | booker | driver | group | other
certainty
confidence
source_type
operation = add | strengthen | weaken | revise | retract
```

`booking_id`, speaker role, `conversation_id`, `trace_id` do backend inject. Model không tự truyền identity.

Ví dụ:

```json
{
  "profile_signals": [
    {
      "category": "usage",
      "key": "school_run",
      "value": true,
      "subject": "self",
      "certainty": "known",
      "source_type": "explicit_user",
      "operation": "add"
    }
  ],
  "booking_signals": [
    {
      "category": "attendance",
      "key": "booker_attending",
      "value": true,
      "subject": "booker",
      "certainty": "known",
      "source_type": "explicit_user",
      "operation": "add"
    }
  ]
}
```

## 7. Logic bên dưới tool

```text
LLM
 ↓
update_post_booking_signals
 ↓
Validate + inject trusted IDs
 ↓
ONE Redis job
 ↓
Return immediately
 ↓
Async worker
 ├── profile_signals → User Profile
 └── booking_signals → test_drive_context_signals
```

Worker:
1. validate signal schema;
2. resolve `self/third_party` sang đúng person profile;
3. resolve booking signal subject theo booking hiện tại;
4. tách tuyệt đối profile store và booking-context store;
5. merge/revise/retract theo logical identity;
6. giữ certainty/confidence/source cho sale brief.

Một message có thể tạo cả profile và booking signals bằng **một tool invocation**. Không thêm tool round hoặc LLM call mới.

## 8. Thay đổi Post-Booking Skill Prompt

### Conversation Strategy
Giữ:
`Answer → provide value → make relevant → easy opening to share → use what was shared → next action`.

Mở rộng "useful missing context" thành:
- context giúp chăm sóc người đang chat tốt hơn;
- hoặc context giúp chuẩn bị đúng cho booking hiện tại.

Không hỏi chỉ để fill profile/test-drive context.

### Participant Boundary

Role cho biết **ai đang nói**; participation cho biết **người đó liên quan thế nào đến booking này**.

**Booker chỉ đặt giúp, không tham dự**
- ưu tiên hậu cần và acknowledgement;
- không khai thác nhu cầu lái xe cá nhân;
- nhận driver information nếu họ tự biết/chia sẻ;
- ưu tiên driver tự cung cấp preference khi cần.

**Booker tham dự**
- chăm sóc như participant;
- passenger/evaluation needs là relevant.

**Booker cũng lái**
- nhu cầu lái xe của booker là first-class profile signals.

**Driver**
- ưu tiên chuẩn bị cá nhân và bài test theo nhu cầu.

**Booker = Driver**
- dùng full advisory flow.

### Signal Capture Boundary

Prompt phải phân biệt:

```text
Durable person fact → profile_signals
Booking-specific fact → booking_signals
```

Attendance, guest count, booking-specific driving/evaluation/purchase participation không được ghi vào profile.

### Follow-Up Strategy

Agent reasoning theo 5 dimensions:

1. Attendance — Ai sẽ có mặt?
2. Driving participation — Ai sẽ thực sự lái?
3. Evaluation / purchase involvement — Ai sẽ đánh giá/cân nhắc xe?
4. Usage / motivation — Vì sao từng người quan tâm đến xe?
5. Test-drive priorities — Họ muốn xác minh điều gì?

Đây là **reasoning dimensions, không phải checklist**.

Priority:
1. role/attendance ambiguity nếu ảnh hưởng cách chăm sóc;
2. ai sẽ lái/đánh giá nếu ảnh hưởng chuẩn bị;
3. usage/motivation nếu làm thay đổi bài test;
4. concern/test-drive priority cụ thể.

Tối đa một contextual question mỗi turn. Follow-up có thể là concrete next action.

## 9. Profile brief và Sale brief

### Profile brief
Vẫn build từ Driver Profile + Booker Profile.

Backend resolve:
- current speaker;
- profile nào là `self`;
- profile nào là `other participant`;
- self-reported vs third-party reported.

Không merge hai profile.

### Sale brief

```text
Booking Brief
├── Test-Drive Context
│   ├── attendance
│   ├── driving participation
│   ├── evaluation/purchase involvement
│   ├── logistics
│   └── other booking-scoped signals
├── Driver Profile
└── Booker Profile
```

Sale brief builder render các key phổ biến theo section chuẩn; semantic key mới được gom vào `Other relevant booking context` thay vì bỏ qua.

## 10. Component flow

```text
Current Message + History
        │
        ├── Driver Profile
        ├── Booker Profile
        ├── Confirmed Booking
        └── Test-Drive Context Signals
                 │
                 ▼
       Rich Participant Context
                 │
                 ▼
         Post-Booking Prompt
                 │
                 ▼
             OpenRouter
          ┌──────┴──────┐
          │             │
     Final Response   update_post_booking_signals
                        │
                  Async Redis Queue
                   ┌────┴────┐
                   │         │
            User Profiles   Test-Drive Context Table
```

## 11. Nguyên tắc triển khai

- Giữ `driver profile + booker profile`.
- Tạo bảng riêng cho booking-scoped context.
- Dùng signal-based schema để không bị giới hạn bởi predefined fields.
- `participant_context` là runtime projection.
- Một async tool `update_post_booking_signals` ghi vào cả profile và booking context.
- Không thêm synchronous LLM/tool round.
- Backend cung cấp identity/context đúng; không hard-code conversation decision tree.
- `unknown` là hợp lệ.
- Agent luôn cung cấp giá trị trước khi khai thác thêm context.
