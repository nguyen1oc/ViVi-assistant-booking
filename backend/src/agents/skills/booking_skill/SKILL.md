# Booking Skill: Process for Test Drive Appointments & Booking Management

This skill details how to interact with the backend booking services using 9 unified MCP tools (`search_test_drive_options`, `hold_test_drive_slot`, `get_booking_draft`, `update_booking_draft`, `request_booking_access`, `verify_booking_access`, `get_booking_details`, `confirm_test_drive_booking`, `request_user_location`).

---

## 🚀 1. Search Test Drive Options (`search_test_drive_options`)

The `search_test_drive_options` tool consolidates multiple backend processes (normalizing vehicle details, matching textual areas to showrooms, and fetching available slots). Distances are calculated only when the client provides current-location coordinates. The Agent MUST NOT invoke sub-components separately.

### Key Input Fields:
- `vehicle_model`: The model of the vehicle (e.g., VF3, VF5, VF7, VF8, VF9).
- `vehicle_variant`: **Never send this field.** A test drive is booked at MODEL level: VF 9 Eco
  and VF 9 Plus are one bookable vehicle, not two. Leaving the field empty searches every active
  variant of the model, so the slot list for "VF 9" already contains both Eco and Plus cars.
  Sending a variant filters the list down and hides real availability from the customer.
- **Never ask the customer which variant they want.** Not "Eco hay Plus?", not any equivalent.
  Even when the customer names a variant themselves, still search the whole model so they keep
  seeing every open slot; acknowledge their preference in words and let the showroom handle it.
- `address` (optional): A textual customer location. The tool geocodes it and ranks eligible showrooms by distance. Do not use it for broad regions such as “miền Trung”; ask for a province/city instead.
- `latitude`, `longitude` (optional): Current device coordinates. Use only when the user explicitly chooses current location; this is the only mode that ranks and displays distance.
- `showroom_id` (optional): The ID of a specific showroom.
- `preferred_date` (optional): One exact date in `YYYY-MM-DD`.
- `preferred_dates` (optional): Several specific, possibly non-contiguous dates in `YYYY-MM-DD`.
- `preferred_date_from`, `preferred_date_to` (optional): An inclusive continuous date range. Both fields are required together; the range is limited to 31 days.
- When a date preference is specified, use exactly one date mode. Otherwise omit date filters. Examples: `ngày 26` → `preferred_date`; `ngày 26, 28 và 30` → `preferred_dates`; `từ 25 đến 30` → `preferred_date_from` + `preferred_date_to`.
- `preferred_time` (optional): Desired time in `HH:MM`.

### Interpret search requests before calling the tool
- You are responsible for interpreting natural-language vehicle, location, date and time requests. The backend validates structured arguments; it does not re-read the user's sentence or fill omitted fields from previous tool calls.
- Vehicle means MODEL only. Treat variants (Eco, Plus) as the same vehicle for booking purposes and
  never turn a schedule request into a variant question — `pick lúc 9h ngày 3/9` is a complete
  request when the model and showroom are already known.
- Use the latest user request first, then the current UI selection and relevant conversation history for unchanged preferences. An explicitly requested new vehicle overrides the old UI vehicle. Keep the current showroom only when the user has not changed or cleared the location.
- Send a complete search request. Carry forward a previous date/time preference only when it remains relevant; if the user asks for any date/time or clears a preference, omit it or set it to null. Never restore a cleared preference.
- When a date selection changes, replace the entire previous date mode. Do not combine an old range with a new single date or date list.
- Resolve relative dates using Current Date (Vietnam). Interpret morning/evening from the meaning of the sentence, including corrections and negation: `tôi chọn 9 giờ sáng` means `09:00`; `không phải 9 giờ tối, chọn 10 giờ sáng` means `10:00`.
- If a date/time is ambiguous or contradictory and context does not resolve it, ask a concise clarification before searching or holding. Do not invent a date or AM/PM choice to satisfy a tool call.

### Execution Stages:

### UI synchronization rules & Tool Calling Mandate
- **MANDATORY TOOL CALLING**:
  - The clarification rule above takes precedence over these tool-calling rules when the requested date/time is unresolved. Do not call a tool with guessed arguments just to update the UI.
  - Whenever the user mentions any VinFast vehicle model (e.g. "VF3", "VF5", "VF6", "VF7", "VF8", "VF9", "VF 9", "xe VF5", etc.) or asks to view/change/switch vehicle, you MUST IMMEDIATELY call `search_test_drive_options` with `vehicle_model="<model>"` in your tool_calls. NEVER reply with text asking for location without first invoking `search_test_drive_options`. Calling the tool is required to sync the frontend side tab and vehicle selector UI.
  - **DATE/SCHEDULE INQUIRIES**: Call `search_test_drive_options` when the current request and UI context identify the vehicle and showroom and the requested schedule is unambiguous. Include exactly one date mode when the user has a date preference, and `preferred_time` when applicable; omit filters the user has cleared. If the vehicle or showroom/location is missing, do not guess or reuse an earlier confirmed booking. Acknowledge the requested date/time, ask only for the missing vehicle and/or province/city/GPS, and retain the schedule request from conversation history for the next search. NEVER claim that a date or time is available before the tool returns data.
- The booking UI context describes the currently selected vehicle and step; an explicit change in the latest user request takes precedence.
- When the user asks to view, choose, or switch to another vehicle, call `search_test_drive_options` with `vehicle_model` even if no address is known yet.
- Treat colloquial location statements as booking input, including missing accents: `t ở hcm`, `tôi đang ở Đà Nẵng`, `ở Quế Sơn`, `mình ở miền tay`. Do not treat them as out of scope.
- When the user gives a specific location, call `search_test_drive_options` with that `address` and the vehicle from the current UI context. Only ask for a vehicle if the context does not contain one.
- If the location is only a broad region (`miền Bắc`, `miền Trung`, `miền Nam`, `miền Tây`), ask for a province/city or GPS first, even when a vehicle has not been chosen. Do not claim the map changed.
- When the user asks to use their current location (for example "gần tôi", "định vị tôi", or "vị trí hiện tại"), call `request_user_location`. The browser client will ask for GPS permission and then call `search_test_drive_options` with latitude/longitude.
- A vehicle-only search updates the vehicle panel (`'car'`). Prompt the user to enter their location/address to find nearby showrooms. NEVER claim that the showroom map or showroom list has been updated when the user has not provided a location yet.
- A search containing a specific address or location updates the showroom map (`'map'`). If the tool returns `location_clarification`, ask the customer for a province/city and do not claim that the map was updated.

#### Stage 1: Showroom Selection (`search_stage = "showroom_selection"`)
- **Condition**: Vehicle model is selected.
- **Behavior**: Returns available showrooms.
- **Agent Action**:
  - If the user ONLY requested to view or switch vehicle models (no address/location specified yet): Inform the user that ViVi has updated the vehicle specification panel to the selected model (e.g. VF 9) on the interface, and ask them to provide their city/district/address to find nearby showrooms.
  - If the user provided an address/location (including any Vietnamese ward, commune, district, or province like "phường Thảo Điền", "phường Bình Hưng Hòa", "Quận 1", "Quế Sơn"): Whenever `search_test_drive_options` completes with `status = success`, ViVi MUST inform the user that the nearby showrooms have been updated on the map/list and invite them to select a showroom. NEVER output an out-of-scope fallback message when `search_test_drive_options` returns showrooms successfully. If a searched location has no direct showroom, explain politely that ViVi is displaying the nearest surrounding showrooms for them to choose.

#### Stage 2: Slot Selection (`search_stage = "slot_selection"`)
- **Condition**: A specific showroom is selected (`showroom_id` is supplied).
- **Behavior**: Returns a list of open timeslots (`slots[]`) at the showroom.
- **Date UI contract**: Use `highlighted_dates` from the tool result as the only source for calendar highlights. It contains only requested dates that actually have available slots. `focused_date` represents a single-date request; `requested_dates` represents separate dates; `requested_date_range` represents a continuous range.
- **Agent Action**: Show available slots and guide the user to select their preferred time. **STRICT LIMIT**: When listing available timeslots in text response, you MUST list **at most 5 slots** per date (e.g. top 5 earliest or most convenient slots). NEVER list more than 5 slots in plain text. **If the user specifies a timeslot in their message (e.g. "21 giờ 8/8 đi", "tôi chọn 22:30 ngày 7/8", etc.), you MUST verify it matches the available slots. If the user's request is contradictory (e.g. choosing "Thứ 6 ngày 8/8" while August 8th is Saturday), you must clarify the correct date with them instead of guessing. Otherwise, immediately call `hold_test_drive_slot` to hold the slot for them.** Do not tell them to click the UI if they have already told you their choice in text chat!
- **Weekly Boundary Rule**: A calendar week runs strictly from Monday to Sunday. When listing dates for "tuần sau" (next week), only list dates from Monday to Sunday of next week (e.g., Aug 24 to Aug 30). Do NOT group Monday of the week after next (e.g., Aug 31) into "tuần sau".

---

## 🔏 1.5. Hold Test Drive Slot (`hold_test_drive_slot`)
- **Purpose**: Reserve an available slot in `held` status for 15 minutes.
- **Agent Action**: Call this tool immediately when the user requests or selects a specific timeslot in the text chat (e.g., "tôi chọn 21:00", "lấy 22:30 ngày 7/8", etc.).
- **Inputs**:
  - `slot_id`: The ID of the slot to hold.
  - `ui_action_id`: A unique idempotency key that **must start with `hold:`** (for example `hold:chat-<uuid>`). Reuse the same key only when retrying the exact same hold request.
- **Behavior**: This will trigger the confirmation modal on the screen. The user can then click "Xác nhận" to confirm.

---

## 📋 2. Draft Booking Management (`get_booking_draft` & `update_booking_draft`)

When a user selects a slot, the system creates a temporary held reservation (Draft Booking) in `held` state with a time-to-live (`hold_expires_at`).

### Step 2.1: Retrieve Draft (`get_booking_draft`)
- **Purpose**: Retrieve the current held draft details for forms and validations.
- **Important Outputs**:
  - `missing_required_fields[]`: Mandatory fields that must be filled before confirmation.
  - `validation_warnings[]`: Non-blocking validations (e.g., license nearing expiry).
  - `remaining_seconds`: Remaining seconds of the hold.
  - `is_ready_to_confirm`: Boolean indicating if all data is valid and the booking is ready.

### Step 2.2: Update Draft (`update_booking_draft`)
- **Purpose**: Apply partial patches to the draft from the user's input.
- **Inputs**:
  - `booker_patch`: Contact details of the booker.
  - `driver_patch`: Driver information (if different from booker).
  - `has_valid_license_commitment`: Boolean — `true` if the driver confirms they have a valid driving license, `false` if not. **DO NOT ask for license number or license class.** Only ask: *"Bạn có giấy phép lái xe hợp lệ không?"*
  - `notification_plan_patch`: Notification channels (SMS, Email, Zalo).
  - `expected_version`: Version token to prevent dirty write conflicts between UI and Agent.
- **Rules**:
  - Updates only succeed if the draft is `held` and not expired (`remaining_seconds` > 0).
  - **Do not** use this tool to change slots or finalize/confirm bookings.
  - **Never** ask the user for `license_number` or `license_class`. The system only requires a boolean commitment.

### When to call it
- **Call `update_booking_draft` as soon as the customer states contact details while a draft exists.** Handing over a name and an email is a mandatory step of every booking, not a request to look anything up. Do NOT call `request_booking_access` for it: an email typed during a booking in progress is form input, not proof of identity for an existing appointment, and sending an OTP there derails the flow.
- One sentence often carries **two people**. `tôi tên Nguyễn Hoàng Minh, minh@example.com, bạn tôi là Trần B, b@example.com` means `booker_patch` for the speaker and `driver_patch` for the other person — one call, both patches. Never drop the second person, and never merge them into one contact.
- Phrases marking the second person as the driver include `bạn tôi`, `người lái là`, `người đi lái thử là`, `chồng/vợ/anh/chị tôi`. When the roles are genuinely unclear, ask one short question rather than guessing which address belongs to whom.
- Details may arrive piecemeal across turns. Patch what the user just gave and leave every other field untouched; the tool applies partial patches.

---

## 🔐 3. Access Verification for Existing Bookings

To view or edit existing bookings, users must authenticate using an OTP challenge.

```mermaid
sequenceDiagram
    participant User as User
    participant Agent as AI Agent
    participant Tool as MCP Tools

    User->>Agent: Request lookup/edit/cancel booking
    Agent->>Tool: request_booking_access(purpose) when email is missing
    Tool-->>Agent: Directs browser to show the email form
    User->>Agent: Submit registered email through the form
    Agent->>Tool: request_booking_access(contact_value=email, purpose, preferred_channel="email")
    Tool-->>Agent: Returns challenge_id & destination_masked
    Agent->>User: Notify that OTP has been sent to destination_masked. Prompt for OTP.
    User->>Agent: Provide OTP code
    Agent->>Tool: verify_booking_access(challenge_id, otp_code)
    Tool-->>Agent: Returns access_session_token & booking_id
```

### Step 3.1: Request OTP Access Challenge (`request_booking_access`)
- **Inputs**:
  - `contact_value`: Registered email address. Use this as the primary identifier for lookup.
  - `booking_code` (optional): Only include this if the user voluntarily provides a booking code.
  - `purpose`: Reason for lookup. **ALWAYS use `"manage"` for all booking management inquiries (lookup, reschedule, cancel, view)** to grant the user a unified session with full permissions (both reschedule and cancellation buttons enabled).
- **Security Rule**:
  - NEVER output the raw `contact_value` in the response. Always use `destination_masked` returned from the tool.
  - `booking_code` is not an authentication secret. Always return and display its complete value exactly as provided by the tool; never mask or truncate it in chat messages or workspace data.
- **Missing email behavior**:
  - When the user requests lookup, reschedule, cancellation, detail updates, or notification updates without an email, call this tool immediately with `purpose="manage"` and omit `contact_value`.
  - The tool returns `requires_contact_value=true`; the browser renders the email form. Do not respond with only a chat request for the email.

### Step 3.2: Verify OTP Challenge (`verify_booking_access`)
- **Inputs**:
  - `challenge_id`: The ID returned during the request step.
  - `otp_code`: The OTP code entered by the user.
- **Rules**:
  - OTPs are single-use. If verification succeeds, you receive an `access_session_token`.
  - This token is required for all subsequent queries on this booking.

---

## 🔍 4. View Confirmed Booking Details (`get_booking_details`)

- **Purpose**: Get comprehensive details of a booking after verification.
- **Inputs**:
  - `booking_id` or `booking_code`.
  - `access_session_token` (mandatory).
- **Rules**:
  - Always enforce token check. Show only permissions allowed under the token's scope (`permissions[]`).
  - After access is verified, show the full `booking_code`; continue protecting OTP codes, access tokens, and contact details.

---

## 🎫 5. Confirm Booking (`confirm_test_drive_booking`)
- **Purpose**: Finalize the draft booking and generate a permanent booking code.
- **Agent Action**: This tool is not available to free-form text chat. Ask the user to review the booking and use the UI confirmation button. Only the structured `confirm_booking` action may dispatch it.
- **Inputs**:
  - `booking_id`: The ID of the draft booking.
  - `expected_version`: The current version of the booking.
  - `ui_action_id`: The exact idempotency ID from the same structured UI action.
