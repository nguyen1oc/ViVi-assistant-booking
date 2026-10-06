import logging
import re
import time
import unicodedata
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel, Field

from src.agents.constants import (
    ADVISORY_KEYWORDS,
    BOOKING_CANCEL_KEYWORDS,
    BOOKING_MUTATION_KEYWORDS,
    BOOKING_RESCHEDULE_KEYWORDS,
    LOOKUP_KEYWORDS,
    OUT_OF_SCOPE_KEYWORDS,
    PUBLIC_LLM_UNAVAILABLE_CODE,
    PUBLIC_LLM_UNAVAILABLE_MESSAGE,
    SOVEREIGNTY_KEYWORDS,
)
from src.agents.state import AgentState
from src.agents.trace import trace_async_operation, trace_event, trace_node
from src.dependencies import usage_budget_service
from src.services.llm import extract_response_text, get_classifier_llm
from src.services.usage_budget import (
    BudgetExceededError,
    LLMCallLimitExceededError,
    invoke_with_budget,
)

logger = logging.getLogger(__name__)

DRIVER_BOOKING_SCOPE_MESSAGE = (
    "Link này dùng để ViVi hỗ trợ người lái chuẩn bị cho buổi lái thử. "
    "Các thao tác tra cứu, đổi, hủy hoặc cập nhật lịch cần được thực hiện bởi "
    "người đặt lịch qua luồng xác thực booking."
)

_DRIVER_BLOCKED_SUB_INTENTS = frozenset({
    "booking_new", "booking_availability", "booking_reschedule", "booking_cancel",
    "booking_update_details", "booking_update_notifications",
})

_DISCOVERY_VEHICLE_RE = re.compile(r"(?<![a-z0-9])(?:vf\s*\d+|ebus|xe\s+buyt\s+dien)(?![a-z0-9])")
_PHONE_CONTACT_RE = re.compile(r"(?<!\d)(?:\+?84|0)(?:[ .()-]?\d){8,10}(?!\d)")
_DISCOVERY_LOCATION_TERMS = ("showroom", "dai ly", "co so", "dia diem")
_AVAILABILITY_TERMS = ("lich", "slot", "suat", "khung gio", "gio nao", "ranh", "trong")
_CONTACT_DETAIL_TERMS = (
    "email",
    "so dien thoai",
    "so dt",
    "sdt",
    "lien he",
    "ho ten",
    "ten toi",
    "toi ten",
    "toi la",
    "nguoi dat la",
    "nguoi lai la",
)
_EXISTING_BOOKING_TERMS = (
    "da dat",
    "ma dat lich",
    "ma booking",
    "booking cua",
    "lich cua toi",
    "lich hen cua toi",
    "huy lich",
    "doi lich",
    "doi gio hen",
    "otp",
    "ma xac thuc",
)
_POST_BOOKING_QA_TERMS = (
    "bao hanh", "bao duong", "sua chua", "cuu ho", "mobile service", "pin", "sac",
    "adas", "isofix", "camera", "tieu hao", "tam di chuyen", "range", "thong so",
)
_COMMERCIAL_TERMS = ("gia", "khuyen mai", "uu dai", "tra gop", "tai chinh", "giam gia")
_CIVIC_HISTORY_TERMS = (
    "la ai",
    "sinh nam",
    "thanh lap",
    "lich su",
    "tieu su",
    "khi nao",
    "ngay nao",
)
_SOVEREIGNTY_QUESTION_TERMS = (
    "chu quyen",
    "thuoc ve",
    "la cua ai",
    "cua nuoc nao",
    "tranh chap",
)
_STREET_CONTEXT_RE = re.compile(
    r"\b(?:duong|pho|dia chi)\s+(?:hoang sa|truong sa)\b"
)


def _route_text(value: object) -> str:
    normalized = unicodedata.normalize("NFD", str(value or "").casefold().replace("đ", "d"))
    without_marks = "".join(character for character in normalized if unicodedata.category(character) != "Mn")
    return " ".join(re.findall(r"[a-z0-9@.]+", without_marks))


def _civic_policy_sub_intent(query: str) -> str | None:
    """Route civic questions by meaning while leaving booking/address uses alone."""
    normalized = _route_text(query)

    # Hoang Sa and Truong Sa are also ordinary street names. An explicit street
    # expression is location input and must continue through the domain classifier.
    if _STREET_CONTEXT_RE.search(normalized):
        return None

    has_history_question = any(term in normalized for term in _CIVIC_HISTORY_TERMS)
    if "dang cong san viet nam" in normalized and has_history_question:
        return "party_history"

    person_reference = any(
        term in normalized
        for term in ("chu tich ho chi minh", "bac ho", "nguyen ai quoc")
    )
    if person_reference and has_history_question:
        return "ho_chi_minh_history"

    sovereignty_reference = any(
        _route_text(keyword) in normalized for keyword in SOVEREIGNTY_KEYWORDS
    )
    if sovereignty_reference and (
        any(term in normalized for term in _SOVEREIGNTY_QUESTION_TERMS)
        or "bien dong" in normalized
        or ("hoang sa" in normalized and "truong sa" in normalized)
    ):
        return "sovereignty"
    return None


def _recent_discovery_context(messages: object) -> bool:
    if not isinstance(messages, list):
        return False
    for message in reversed(messages):
        if not isinstance(message, HumanMessage):
            continue
        text = _route_text(message.content)
        return bool(_DISCOVERY_VEHICLE_RE.search(text)) or any(term in text for term in _DISCOVERY_LOCATION_TERMS)
    return False


def _correct_discovery_route(
    *,
    query: str,
    messages: object,
    intent: str,
    sub_intent: str,
    contact_value: str | None = None,
) -> tuple[str, str, str | None]:
    """Keep new-booking discovery separate from existing-booking access."""
    normalized = _route_text(query)
    explicitly_existing = "@" in normalized or any(term in normalized for term in _EXISTING_BOOKING_TERMS)
    has_vehicle = bool(_DISCOVERY_VEHICLE_RE.search(normalized))
    showroom_refinement = any(term in normalized for term in _DISCOVERY_LOCATION_TERMS)
    continues_discovery = showroom_refinement and _recent_discovery_context(messages)
    test_drive_request = any(term in normalized for term in ("lai thu", "chay thu", "trai nghiem"))

    supplied_contact_details = bool(
        contact_value
        or "@" in str(query or "")
        or _PHONE_CONTACT_RE.search(str(query or ""))
        or any(
            re.search(
                rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])",
                normalized,
            )
            for term in _CONTACT_DETAIL_TERMS
        )
    )
    if (
        sub_intent == "booking_provide_contact"
        and has_vehicle
        and test_drive_request
        and not supplied_contact_details
    ):
        return (
            "domain",
            "booking_new",
            "relationship_reference_without_contact_details_is_new_booking",
        )

    if explicitly_existing or not (has_vehicle or continues_discovery):
        return intent, sub_intent, None
    if sub_intent == "booking_lookup" or (intent == "out_of_scope" and test_drive_request):
        corrected = (
            "booking_availability"
            if any(term in normalized for term in _AVAILABILITY_TERMS)
            else "booking_new"
        )
        return "domain", corrected, "new_booking_discovery_must_not_open_existing_booking_access"
    return intent, sub_intent, None


_RESCHEDULE_DATE_FIELDS = (
    "reschedule_date_type",
    "reschedule_target_date",
    "reschedule_day_offset",
)


def _merge_pending_reschedule(route_result: "RouteSchema", pending: dict) -> dict:
    """Merge only structured extraction with the client-held pending target.

    The classifier interprets the current message only; deterministic code
    preserves values from a prior turn. A date is atomic because a relative
    expression must clear a previous explicit date.
    """
    current = {
        "reschedule_date_type": route_result.reschedule_date_type,
        "reschedule_target_date": route_result.reschedule_target_date,
        "reschedule_day_offset": route_result.reschedule_day_offset,
        "reschedule_target_time": route_result.reschedule_target_time,
    }
    if route_result.sub_intent != "booking_reschedule" or not pending:
        return current

    date_was_supplied = any(current[field] is not None for field in _RESCHEDULE_DATE_FIELDS)
    if not date_was_supplied:
        for field in _RESCHEDULE_DATE_FIELDS:
            current[field] = pending.get(field)
    if current["reschedule_target_time"] is None:
        current["reschedule_target_time"] = pending.get("reschedule_target_time")
    return current


def _driver_scope_block(state: AgentState, query: str, *, sub_intent: str) -> dict:
    metadata = state.get("metadata") or {}
    return {
        "intent": "out_of_scope",
        "response": DRIVER_BOOKING_SCOPE_MESSAGE,
        "policy_response": DRIVER_BOOKING_SCOPE_MESSAGE,
        "messages": [HumanMessage(content=query)],
        "metadata": {**metadata, "sub_intent": sub_intent},
        "tool_call_count": 0,
    }


class RouteSchema(BaseModel):
    intent: str = Field(
        description=(
            "The classified intent of the user. Must be one of: 'domain', 'out_of_scope', "
            "or 'sensitive'."
        )
    )
    sub_intent: str = Field(
        description=(
            "Detailed classification. Must be one of: booking_new, booking_lookup, "
            "booking_availability, booking_reschedule, booking_cancel, booking_provide_contact, "
            "booking_update_details, "
            "booking_update_notifications, post_booking_advisory, vehicle_info, after_sales_info, greeting, "
            "assistant_identity, "
            "out_of_scope, others. If intent is sensitive, use others."
        )
    )
    contact_value: str | None = Field(
        default=None,
        description="Email copied exactly from the user query, or null when no email was provided.",
    )
    has_schedule_preference: bool = Field(
        description=(
            "True when the user states, changes, or asks about a preferred test-drive date, "
            "date range, day, or time, including shorthand such as '28 t mới rảnh'."
        ),
    )
    reschedule_target_date: str | None = Field(
        default=None,
        description=(
            "For booking_reschedule only: an explicit requested date as YYYY-MM-DD. "
            "Keep null for relative or ambiguous expressions."
        ),
    )
    reschedule_target_time: str | None = Field(
        default=None,
        description=(
            "For booking_reschedule only: requested local showroom time as HH:MM (24-hour). "
            "Interpret ordinary Vietnamese business-hour speech naturally: '1h30' means 13:30 "
            "unless the user explicitly says morning. Otherwise null."
        ),
    )
    reschedule_date_type: Literal[
        "explicit", "relative_to_today", "relative_to_booking", "ambiguous"
    ] | None = Field(
        default=None,
        description=(
            "How to resolve the reschedule date. Use explicit for a concrete calendar date, "
            "relative_to_today for today/tomorrow, relative_to_booking for phrases such as "
            "'hôm sau' referring to the existing appointment, and ambiguous when clarification "
            "is required (for example 'cuối tháng' without a specific day)."
        ),
    )
    reschedule_day_offset: int | None = Field(
        default=None,
        ge=0,
        le=60,
        description=(
            "Day offset for relative_to_today or relative_to_booking. For example tomorrow or "
            "the day after the current appointment is 1. Null for explicit/ambiguous dates."
        ),
    )


@trace_node("classifier")
async def classifier_node(state: AgentState, config: RunnableConfig | None = None) -> dict:
    diagnostic_started = time.perf_counter()
    query = state.get("query", "")
    context = state.get("context") or {}
    metadata = state.get("metadata") or {}
    previous_assistant_message = ""
    for message in reversed(state.get("messages") or []):
        if isinstance(message, AIMessage):
            previous_assistant_message = extract_response_text(message)
            if previous_assistant_message:
                break
    history_scan_ms = (time.perf_counter() - diagnostic_started) * 1000
    trace_id = metadata.get("trace_id", "")
    previous_skill = state.get("active_skill", "")
    pending_reschedule = context.get("pendingReschedule") or {}
    post_booking_active = bool((state.get("post_booking_context") or {}).get("active"))
    is_driver_invitation = (state.get("participant_context") or {}).get("role") == "driver"
    if state.get("requested_action"):
        if is_driver_invitation:
            return _driver_scope_block(state, query, sub_intent="driver_booking_scope")
        trace_event(
            "classifier.bypass",
            trace_id=trace_id,
            reason="structured_action",
            query=query,
            context=context,
        )
        return {
            "intent": "domain",
            "active_skill": "booking",
            "previous_active_skill": previous_skill,
            "messages": [HumanMessage(content=query)],
            "metadata": {**metadata, "sub_intent": "booking"},
            "tool_call_count": 0,
        }
    if not query:
        trace_event("classifier.empty_query", trace_id=trace_id)
        return {
            "intent": "domain",
            "active_skill": "booking",
            "previous_active_skill": previous_skill,
            "messages": [HumanMessage(content="")],
            "metadata": {**metadata, "sub_intent": "empty_query"},
            "tool_call_count": 0,
        }

    # Check basic keywords as immediate priority bypass for sensitive subjects
    # to avoid LLM hallucinations and save API token cost
    lower_query = query.lower()

    civic_sub_intent = _civic_policy_sub_intent(query)
    if civic_sub_intent:
        trace_event(
            "classifier.keyword_route",
            trace_id=trace_id,
            intent="sensitive",
            sub_intent=civic_sub_intent,
        )
        return {
            "intent": "sensitive",
            "messages": [HumanMessage(content=query)],
            "metadata": {**metadata, "sub_intent": civic_sub_intent},
            "tool_call_count": 0,
        }

    if any(kw in lower_query for kw in OUT_OF_SCOPE_KEYWORDS):
        trace_event("classifier.keyword_route", trace_id=trace_id, intent="sensitive", sub_intent="out_of_scope_code")
        return {"intent": "sensitive", "messages": [HumanMessage(content=query)], "metadata": {**metadata, "sub_intent": "out_of_scope_code"}, "tool_call_count": 0}

    today_vietnam = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date().isoformat()
    # Construct prompt for the LLM classifier dynamically based on system_prompt.md
    prompt = (
        "You classify requests for a VinFast test-drive assistant.\n"
        "\n"
        "Choose exactly one intent:\n"
        "- domain: the request is meaningfully related to VinFast vehicles, test-drive booking, "
        "booking management, test-drive preparation, vehicle evaluation, or support surrounding "
        "the user's test-drive journey.\n"
        "- out_of_scope: the request is unrelated to the responsibilities of a VinFast test-drive "
        "assistant and does not require safety-sensitive handling.\n"
        "- sensitive: the request requires safety or policy-sensitive handling, such as requests "
        "involving harmful or dangerous activity, illegal wrongdoing, privacy abuse, credentials "
        "or secrets, or other content that should not be handled as a normal domain request.\n"
        "\n"
        "Important boundaries:\n"
        "- Never classify a request as sensitive merely because it is unfamiliar, ambiguous, "
        "unsupported, or outside the assistant's domain.\n"
        "- A benign unrelated request is out_of_scope, not sensitive.\n"
        "- A request related to the user's test-drive journey is domain even when it is not a "
        "booking transaction.\n"
        "- Greetings and questions about ViVi's identity, role, or supported capabilities are "
        "domain. Never classify them as out_of_scope.\n"
        "- When a request is ambiguous but has a reasonable interpretation within the test-drive "
        "journey, prefer domain.\n"
        "\n"
        "For intent=domain, choose exactly one sub_intent:\n"
        "- booking_new\n"
        "- booking_lookup\n"
        "- booking_availability\n"
        "- booking_reschedule\n"
        "- booking_cancel\n"
        "- booking_provide_contact\n"
        "- booking_update_details\n"
        "- booking_update_notifications\n"
        "- post_booking_advisory\n"
        "- vehicle_info\n"
        "- after_sales_info\n"
        "- greeting\n"
        "- assistant_identity\n"
        "- others\n"
        "\n"
        "Domain sub-intent rules:\n"
        "- booking_new: create or start a new test-drive booking.\n"
        "- booking_lookup: retrieve or check an existing booking.\n"
        "- booking_availability: check which test-drive dates or times are free.\n"
        "- booking_reschedule: change the booking date, time, or slot.\n"
        "- booking_cancel: cancel an existing booking.\n"
        "- booking_provide_contact: the user is SUPPLYING contact details (full name, email, phone) for the booking they are currently making — their own details, the driver's details, or both in one sentence. This is a mandatory step of every new booking, not a request to manage an existing one. Typical shape: a name and an email stated as facts, often naming a second person (\"bạn tôi là …\", \"người lái là …\"), with no verb asking to look up, change, or cancel anything.\n"
        "- booking_update_details: explicit request to modify or update registered contact details or information of the person who booked an existing booking (e.g. change contact name, phone number, email). Never use this for general questions about passengers, family, children, pets, or ride preparation.\n"
        "- booking_update_notifications: change booking notification preferences.\n"
        "- post_booking_advisory: after a confirmed booking, guidance that helps the user prepare for, participate in, or evaluate the upcoming test drive, including questions about passengers, family members, children, child seats, pets, luggage, or vehicle features.\n"
        "- vehicle_info: general VinFast vehicle/product questions not specifically tied to preparing for an already-confirmed test drive (e.g. asking about car models, seat capacity for 4 or 7 people, range, charging).\n"
        "- after_sales_info: factual warranty, maintenance, repair, rescue, battery rescue, or Mobile Service questions. These are domain questions, including after a confirmed booking; commercial eligibility, discounts, financing, and operational commitments are not after_sales_info.\n"
        "- greeting: a social opening or greeting directed at ViVi, for example 'hi', 'hello', 'xin chào', or 'alo'.\n"
        "- assistant_identity: a question about who ViVi is, ViVi's role, or what ViVi can help with, for example 'bạn là ai?' or 'ViVi hỗ trợ gì?'.\n"
        "- others: domain requests that do not fit another domain sub_intent.\n"
        "\n"
        "Use booking_lookup when the user wants to view, find, check, or retrieve an existing booking.\n"
        "A request that names a vehicle or showroom and asks for test-drive availability is NOT "
        "booking_lookup unless the user explicitly says the booking already exists, gives a booking "
        "CODE, or asks to manage an appointment already made.\n"
        "CRITICAL — AN EMAIL IS NOT A LOOKUP SIGNAL. Every new booking requires the customer to hand "
        "over a name and an email, so an address on its own says nothing about which booking is meant. "
        "Decide from what the user is ASKING for, never from the presence of '@'. A turn that only "
        "states who someone is and how to reach them, with no request to view, change, or cancel "
        "anything, is booking_provide_contact — not booking_lookup and not booking_update_details.\n"
        "Mentioning only a relationship or intended driver without supplying a name, email, or phone is NOT "
        "booking_provide_contact. For example, 'Tôi đặt lịch giúp em trai tôi lái thử VF 7' is booking_new.\n"
        "When UI stage is choose_slot, collect_info, or review, a booking is already under way: prefer "
        "booking_provide_contact for contact details given in that state. Only classify as a management "
        "intent when the user names a DIFFERENT, already-confirmed appointment.\n"
        "IMPORTANT: When the user mentions changing/switching a vehicle model (e.g. 'đổi VF8', 'đổi xe VF5', "
        "'chuyển sang VF7', 'xem xe VF3'), classify as booking_new (NOT booking_reschedule). Only use "
        "booking_reschedule when the user explicitly asks to change an existing appointment time/date "
        "('đổi lịch', 'đổi giờ hẹn', 'dời sang buổi chiều', 'chuyển sang ngày mai', "
        "'cho tôi hẹn trễ hơn').\n"
        "\n"
        "Use booking_availability whenever the user asks which dates/times are free or available, "
        "including informal forms such as 'rảnh ngày 25-26', 'ngày 26 27 có lịch không', "
        "'từ 25 đến 30', or 'tuần sau có giờ nào'.\n"
        "CRITICAL AVAILABILITY PRECEDENCE: a statement of when the user is free is an availability "
        "request even when it is not phrased as a question and omits words such as 'ngày' or 'giờ'. "
        "Examples: 'thôi 28 t mới rảnh', 'chắc 27 được á', 'tầm 3 giờ chiều nha', and "
        "'cuối tuần tôi mới đi được' are booking_availability. When UI stage=choose_slot, prefer "
        "booking_availability for any date/time preference refinement; use booking_new only when "
        "the user explicitly starts another booking or changes the vehicle/location. Set "
        "has_schedule_preference=true for these date/time refinements.\n"
        "A user stating a location is a booking request, including casual or missing-accent "
        "Vietnamese such as 't ở hcm', 'tôi đang ở Đà Nẵng', 'ở Quế Sơn', and "
        "'mình ở miền tay'. Classify these as booking_new.\n"
        "A broad region such as miền Bắc/Trung/Nam/Tây still belongs to booking_new; "
        "the booking skill will ask for a province or city.\n"
        "Classify 'hi' as domain/greeting. Classify 'bạn là ai?' and 'bạn hỗ trợ gì?' as "
        "domain/assistant_identity.\n"
        "\n"
        "Use UI context as supporting evidence, not as a replacement for the user's request. "
        "A successful/confirmed booking makes post_booking_advisory more likely for subsequent "
        "test-drive-related guidance, unless the user is clearly requesting another booking action.\n"
        "\n"
        "If intent is out_of_scope, use sub_intent=out_of_scope. If intent is sensitive, use sub_intent=others.\n"
        "\n"
        "If the query contains an email, copy it exactly to contact_value. "
        "Otherwise return null. Never invent contact_value. Copying an address here is bookkeeping "
        "only — it must never push the classification toward a lookup or management intent. When the "
        "turn carries two people's addresses, copy the first and still classify the turn on its "
        "meaning.\n"
        "For booking_reschedule, extract the requested destination date/time into the reschedule fields. "
        f"Today in Vietnam is {today_vietnam}. For a concrete date (including an unambiguous weekday), "
        "set date_type=explicit and return YYYY-MM-DD. For today/tomorrow set date_type=relative_to_today "
        "with day_offset 0/1 and do not calculate the ISO date. If 'hôm sau' refers to the current "
        "appointment, set date_type=relative_to_booking and day_offset=1. Use date_type=ambiguous and "
        "leave the date null for expressions such as 'cuối tháng' that need clarification. Use 24-hour showroom time; in normal "
        "Vietnamese booking speech, '1h30' means 13:30 unless 'sáng' is explicit. Do not infer a date "
        "or time the user did not state. Set all reschedule fields to null for other intents.\n"
        "When Pending reschedule context is present and the user supplies a missing/corrected date or time, "
        "classify the turn as booking_reschedule. Extract ONLY the date/time fields stated in this message; "
        "leave fields not stated here null. Application code merges them with the pending target.\n"
        "\n"
        f"UI context: channel={context.get('channel', '')}, "
        f"stage={context.get('stage', '')}.\n"
        f"Confirmed post-booking context active: {post_booking_active}.\n"
        f"Previous active skill: {previous_skill or '(none)'}.\n"
        f"Pending reschedule context: {pending_reschedule or '(none)'}.\n"
        f"Previous ViVi message: {previous_assistant_message or '(none)'}\n"
        f"User query: {query}"
    )
    prompt_build_ms = (time.perf_counter() - diagnostic_started) * 1000 - history_scan_ms

    try:
        llm_build_started = time.perf_counter()
        llm = get_classifier_llm()
        llm_build_ms = (time.perf_counter() - llm_build_started) * 1000
        if llm is None:
            raise RuntimeError("LLM is not configured")
        structured_output_started = time.perf_counter()
        structured_llm = llm.with_structured_output(RouteSchema)
        structured_output_ms = (time.perf_counter() - structured_output_started) * 1000
        trace_event(
            "diagnostic.classifier_pre_invoke",
            trace_id=trace_id,
            history_scan_ms=round(history_scan_ms, 2),
            prompt_build_ms=round(prompt_build_ms, 2),
            llm_build_ms=round(llm_build_ms, 2),
            structured_output_ms=round(structured_output_ms, 2),
            elapsed_before_request_ms=round((time.perf_counter() - diagnostic_started) * 1000, 2),
            state_message_count=len(state.get("messages") or []),
            prompt_chars=len(prompt),
        )
        llm_request_log_started = time.perf_counter()
        trace_event("llm.request", trace_id=trace_id, node="classifier", prompt=prompt)
        trace_event(
            "diagnostic.classifier_request_trace",
            trace_id=trace_id,
            llm_request_log_ms=round((time.perf_counter() - llm_request_log_started) * 1000, 2),
        )
        result = await trace_async_operation(
            "llm.classifier",
            trace_id=trace_id,
            input={"model": getattr(llm, "model_name", "") or "classifier", "prompt": prompt},
            awaitable=invoke_with_budget(
                structured_llm,
                prompt,
                model=getattr(llm, "model_name", "") or "classifier",
                metadata=metadata,
                budget=usage_budget_service,
                call_purpose="classifier",
                config=config,
            ),
        )
        from typing import cast

        route_result = cast(RouteSchema, result)
        intent = route_result.intent
        if intent not in {"domain", "out_of_scope", "sensitive"}:
            intent = "domain"

        sub_intent = route_result.sub_intent
        intent, sub_intent, discovery_correction = _correct_discovery_route(
            query=query,
            messages=state.get("messages"),
            intent=intent,
            sub_intent=sub_intent,
            contact_value=route_result.contact_value,
        )
        if discovery_correction:
            trace_event(
                "classifier.route_correction",
                trace_id=trace_id,
                to_sub_intent=sub_intent,
                reason=discovery_correction,
            )
        if (
            intent == "domain"
            and context.get("stage") == "choose_slot"
            and not post_booking_active
            and route_result.has_schedule_preference
            and sub_intent in {"booking_new", "booking_reschedule", "others"}
        ):
            trace_event(
                "classifier.route_correction",
                trace_id=trace_id,
                from_sub_intent=sub_intent,
                to_sub_intent="booking_availability",
                reason="schedule_preference_while_choosing_slot",
            )
            sub_intent = "booking_availability"
        if is_driver_invitation and sub_intent in _DRIVER_BLOCKED_SUB_INTENTS:
            return _driver_scope_block(state, query, sub_intent="driver_booking_scope")
        if intent == "domain" and not post_booking_active and sub_intent == "post_booking_advisory":
            intent = "out_of_scope"
            sub_intent = "post_booking_required"
        normalized_query = _route_text(query)
        if post_booking_active and intent == "out_of_scope" and (
            any(term in normalized_query for term in _POST_BOOKING_QA_TERMS)
            or (
                _DISCOVERY_VEHICLE_RE.search(normalized_query)
                and not any(term in normalized_query for term in _COMMERCIAL_TERMS)
            )
        ):
            intent = "domain"
            sub_intent = "after_sales_info"
        use_post_booking = intent == "domain" and post_booking_active and (
            sub_intent in {"post_booking_advisory", "vehicle_info", "after_sales_info"}
            or (is_driver_invitation and sub_intent == "booking_lookup")
        )
        active_skill = "post_booking" if use_post_booking else "booking"
        trace_event(
            "llm.response",
            trace_id=trace_id,
            node="classifier",
            intent=intent,
            sub_intent=sub_intent,
            active_skill=active_skill,
        )
        reschedule_entities = _merge_pending_reschedule(route_result, pending_reschedule)
        return {
            "intent": intent,
            "active_skill": active_skill,
            "previous_active_skill": previous_skill,
            "messages": [HumanMessage(content=query)],
            "metadata": {**metadata, "sub_intent": sub_intent},
            "intent_entities": {
                "contact_value": route_result.contact_value,
                **reschedule_entities,
            },
            "tool_call_count": 0,
        }
    except (BudgetExceededError, LLMCallLimitExceededError) as e:
        internal_error_code = (
            "LLM_BUDGET_EXCEEDED" if isinstance(e, BudgetExceededError) else "LLM_CALL_LIMIT_EXCEEDED"
        )
        trace_event("llm.limit", trace_id=trace_id, node="classifier", error_code=internal_error_code)
        return {
            "intent": "sensitive",
            "messages": [HumanMessage(content=query)],
            "response": PUBLIC_LLM_UNAVAILABLE_MESSAGE,
            "policy_response": PUBLIC_LLM_UNAVAILABLE_MESSAGE,
            "action_error": PUBLIC_LLM_UNAVAILABLE_CODE,
            "metadata": {**metadata, "sub_intent": "llm_limit"},
            "tool_call_count": 0,
        }
    except Exception as e:
        trace_event("llm.error", trace_id=trace_id, node="classifier", error=str(e))
        # Log the specific error for debugging before falling back to keyword classifier
        logger.warning("Classifier LLM call failed (%s: %s), falling back to keyword matching.", type(e).__name__, e)
        if any(phrase in lower_query for phrase in LOOKUP_KEYWORDS):
            fallback_sub_intent = "booking_lookup"
        elif any(phrase in lower_query for phrase in BOOKING_RESCHEDULE_KEYWORDS):
            fallback_sub_intent = "booking_reschedule"
        elif any(phrase in lower_query for phrase in BOOKING_CANCEL_KEYWORDS):
            fallback_sub_intent = "booking_cancel"
        elif any(phrase in lower_query for phrase in BOOKING_MUTATION_KEYWORDS):
            fallback_sub_intent = "booking_new"
        else:
            fallback_sub_intent = "fallback_domain"
        active_skill = (
            "post_booking"
            if post_booking_active
            and (
                any(phrase in lower_query for phrase in ADVISORY_KEYWORDS)
                or any(term in _route_text(query) for term in _POST_BOOKING_QA_TERMS)
                or (
                    bool(_DISCOVERY_VEHICLE_RE.search(_route_text(query)))
                    and not any(term in _route_text(query) for term in _COMMERCIAL_TERMS)
                )
                or (is_driver_invitation and fallback_sub_intent == "booking_lookup")
            )
            else "booking"
        )
        if is_driver_invitation and fallback_sub_intent in _DRIVER_BLOCKED_SUB_INTENTS:
            return _driver_scope_block(state, query, sub_intent="driver_booking_scope")
        trace_event(
            "classifier.fallback_route",
            trace_id=trace_id,
            intent="domain",
            active_skill=active_skill,
            sub_intent=fallback_sub_intent,
        )
        return {
            "intent": "domain",
            "active_skill": active_skill,
            "previous_active_skill": previous_skill,
            "messages": [HumanMessage(content=query)],
            "metadata": {**metadata, "sub_intent": fallback_sub_intent},
            "tool_call_count": 0,
        }
