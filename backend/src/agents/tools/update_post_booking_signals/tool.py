import re
import unicodedata
from typing import Annotated, Any, TypeVar

from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState

from src.agents.trace import trace_event
from src.dependencies import profile_service, profile_update_queue
from src.services.profile.models import BookingSignalCandidate, ProfileSignalCandidate

TSignal = TypeVar("TSignal", ProfileSignalCandidate, BookingSignalCandidate)

_DIRECT_FAMILY_ATTENDANCE_RE = re.compile(
    r"\b(?:gia dinh|ca nha|nha minh|nha toi)\b[^.!?]{0,80}"
    r"\b(?:nguoi|thanh vien)\b\s*(?:se\s+)?(?:cung\s+)?"
    r"(?:den|di|tham gia)\b"
)
_ATTENDANCE_SIGNAL_KEYS = frozenset({
    "booker_attending",
    "driver_attending",
    "additional_guest_count",
    "additional_guest_context",
})


def _signal_text(value: str) -> str:
    normalized = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    without_marks = "".join(
        character
        for character in normalized
        if unicodedata.category(character) != "Mn"
    )
    return " ".join(without_marks.split())


def _drop_appointment_scoped_household_signal(
    profile_signals: list[ProfileSignalCandidate],
    booking_signals: list[BookingSignalCandidate],
    current_user_message: str,
) -> tuple[list[ProfileSignalCandidate], bool]:
    """Keep an appointment headcount out of the durable household profile."""
    has_attendance_signal = any(
        signal.key in _ATTENDANCE_SIGNAL_KEYS for signal in booking_signals
    )
    if not has_attendance_signal or not _DIRECT_FAMILY_ATTENDANCE_RE.search(
        _signal_text(current_user_message)
    ):
        return profile_signals, False
    filtered = [signal for signal in profile_signals if signal.key != "household_size"]
    return filtered, len(filtered) != len(profile_signals)


def _server_owned_provenance(
    signal: TSignal,
) -> tuple[TSignal, str]:
    """Resolve model-provided provenance under the server's deterministic policy."""
    if signal.category == "interest":
        return (
            signal.model_copy(update={"source_type": "implicit_user", "certainty": "possible", "confidence": 0.6}),
            "interest_from_question",
        )
    return (
        signal.model_copy(update={"source_type": "explicit_user", "certainty": "known", "confidence": 0.9}),
        "explicit_statement_default",
    )


async def queue_post_booking_signals(
    profile_signals: list[ProfileSignalCandidate],
    booking_signals: list[BookingSignalCandidate],
    profile_id: Annotated[str, InjectedState("profile_id")],
    metadata: Annotated[dict[str, Any], InjectedState("metadata")],
    participant_context: Annotated[dict[str, Any], InjectedState("participant_context")],
    current_user_message: str = "",
) -> dict[str, Any]:
    """Queue validated profile and appointment signals for durable processing.

    Shared by the interactive tool and the background repair worker so both
    paths apply identical provenance and participant-scoping rules.
    """

    raw_profile_signals = [signal.model_dump() for signal in profile_signals]
    raw_booking_signals = [signal.model_dump() for signal in booking_signals]
    profile_signals, dropped_appointment_household = (
        _drop_appointment_scoped_household_signal(
            profile_signals,
            booking_signals,
            current_user_message,
        )
    )
    if dropped_appointment_household:
        trace_event(
            "profile_signal.scope_corrected",
            trace_id=str(metadata.get("trace_id") or ""),
            rule="appointment_headcount_is_not_household_size",
        )
    profile_resolutions = [_server_owned_provenance(signal) for signal in profile_signals]
    booking_resolutions = [_server_owned_provenance(signal) for signal in booking_signals]
    profile_signals = [signal for signal, _ in profile_resolutions]
    booking_signals = [signal for signal, _ in booking_resolutions]
    trace_event(
        "profile_signal.provenance_resolved",
        trace_id=str(metadata.get("trace_id") or ""),
        raw={"profile_signals": raw_profile_signals, "booking_signals": raw_booking_signals},
        resolved={
            "profile_signals": [signal.model_dump() for signal in profile_signals],
            "booking_signals": [signal.model_dump() for signal in booking_signals],
        },
        rules={
            "profile_signals": [rule for _, rule in profile_resolutions],
            "booking_signals": [rule for _, rule in booking_resolutions],
        },
    )
    if not profile_signals and not booking_signals:
        trace_event("profile_signal.queue_skipped", trace_id=str(metadata.get("trace_id") or ""), reason="no_signals")
        return {"status": "skipped", "reason": "no_signals"}
    speaker_role = str(participant_context.get("role") or "")
    booking_id = str(participant_context.get("booking_id") or "")
    if booking_signals and (speaker_role not in {"booker", "driver"} or not booking_id):
        trace_event("profile_signal.queue_skipped", trace_id=str(metadata.get("trace_id") or ""), reason="booking_context_not_resolved")
        return {"status": "skipped", "reason": "booking_context_not_resolved"}
    updates: dict[str, list[dict[str, Any]]] = {}
    for signal in profile_signals:
        target = profile_id
        candidate = signal.model_dump(exclude={"subject"})
        if signal.subject == "third_party":
            if speaker_role not in {"booker", "driver"} or not booking_id:
                continue
            try:
                target = profile_service.resolve_booking_other_participant_profile(booking_id, speaker_role).id
            except KeyError:
                continue
            candidate.update({"certainty": "possible", "confidence": min(signal.confidence, .35), "source_type": "implicit_user", "operation": "add"})
        if target:
            updates.setdefault(target, []).append(candidate)
    queued = await profile_update_queue.enqueue_post_booking(
        profile_updates=[{"profile_id": key, "candidates": value} for key, value in updates.items()],
        booking_id=booking_id, booking_candidates=booking_signals, speaker_role=speaker_role or "system",
        conversation_id=str(metadata.get("conversation_id") or ""), trace_id=str(metadata.get("trace_id") or ""),
    )
    trace_event("profile_signal.queue_result", trace_id=str(metadata.get("trace_id") or ""), status="queued" if queued else "unavailable", profile_signal_count=len(profile_signals), booking_signal_count=len(booking_signals))
    return {"status": "queued" if queued else "unavailable", "profile_signal_count": len(profile_signals), "booking_signal_count": len(booking_signals)}


@tool
async def update_post_booking_signals(
    profile_signals: list[ProfileSignalCandidate],
    booking_signals: list[BookingSignalCandidate],
    profile_id: Annotated[str, InjectedState("profile_id")],
    metadata: Annotated[dict[str, Any], InjectedState("metadata")],
    participant_context: Annotated[dict[str, Any], InjectedState("participant_context")],
    current_user_message: Annotated[str, InjectedState("query")],
) -> dict[str, Any]:
    """Queue profile and appointment signals extracted from the current user turn.

    The caller supplies both ``profile_signals`` and ``booking_signals``. Use an
    empty array when the current turn contains no supported signal for that scope.
    This tool records side-effect context asynchronously; never expose queue state to
    the user.

    Scope selection:
        - ``profile_signals`` are durable facts, needs, habits, usage patterns,
          experience, interests, concerns, test-drive goals, or conversation
          preferences that may remain useful beyond this appointment.
        - ``booking_signals`` are appointment-specific participation or logistics:
          attendance, who will drive, evaluation/purchase involvement, additional
          guests, appointment constraints, or other booking-only context.
        - Preserve the scope of the user's statement. A profile fact may personalize
          booking advice, but it must not populate or confirm a booking fact unless
          the user explicitly states that relationship, and vice versa.
        - Missing facts remain unknown. Plausibility, correlation, or common behavior
          is not evidence for another signal.

    Profile signal parameter rules:
        - For the current participant's own durable statement, use ``subject="self"``.
        - Use ``subject="third_party"`` sparingly only when the participant clearly
          states a useful durable fact about another person. Do not infer another
          person's preferences, concerns, experience, or purchase intent from the
          current participant's behavior.
        - Prefer stable reusable keys over duplicate/free-form variants.
        - Allowed categories are ``fact``, ``usage``, ``experience``, ``interest``,
          ``concern``, ``test_drive_goal``, ``conversation_preference``
          and ``custom_intent``.
        - Registered profile keys are ``household_size``, ``primary_use``,
          ``commute_distance_km``, ``ev_experience``, ``home_charging_access``,
          ``vehicle_interest``, ``feature_interest``, ``policy_interest``,
          ``test_drive_priority``, ``current_vehicle_pain_points``, and
          ``response_style``. Any new profile key must begin with ``custom.`` and
          include a description.
        - Key contracts: ``household_size`` is ``fact`` with integer >= 1;
          ``primary_use`` and ``commute_distance_km`` are ``usage``;
          ``ev_experience`` is ``experience``; ``home_charging_access`` is ``fact``;
          ``vehicle_interest``, ``feature_interest``, and ``policy_interest`` are
          ``interest``; ``test_drive_priority`` is ``test_drive_goal``;
          ``current_vehicle_pain_points`` is ``concern``; and ``response_style`` is
          ``conversation_preference``. ``urban_commute`` and ``city_commute`` are
          accepted aliases for ``primary_use``.
        - The following values are recommendations, not a closed enum. Prefer these
          stable labels when they fit: ``primary_use`` = ``urban_commute``,
          ``highway_commute``, ``long_trip``, ``family_use``;
          ``ev_experience`` = ``first_ev``, ``ev_owner``, ``ev_experienced``;
          ``home_charging_access`` = ``home_charging_available``,
          ``apartment_no_home_charging``, ``workplace_charging``,
          ``no_regular_charging``; ``feature_interest`` = ``charging``, ``adas``,
          ``parking_cameras_and_sensors``, ``phone_connectivity``, ``comfort``,
          ``noise_insulation``, ``cargo_space``; ``test_drive_priority`` =
          ``parking_and_vehicle_size``, ``family_space_and_comfort``,
          ``child_seat_fit_and_access``, ``elderly_entry_exit_comfort``,
          ``cargo_fit``, ``noise_insulation``, ``ride_comfort``,
          ``urban_maneuvering``, ``highway_stability``; and
          ``current_vehicle_pain_points`` = ``parking``, ``rear_space``,
          ``ride_comfort``, ``noise``, ``cargo_space``, ``tech``, ``charging``.
          ``policy_interest`` must be a list of objects such as
          ``{"topic": "maintenance", "vehicle_model": "VF 3"}``; include every
          directly supported policy/model pair.
          Send a list for ``primary_use``, ``feature_interest``,
          ``test_drive_priority``, and ``current_vehicle_pain_points``. A single
          string for these keys is accepted and normalized to a one-item list.
          For every list-valued signal, use ``add`` or ``strengthen`` to append
          distinct entries; use ``revise`` only when the supplied list is intended
          to replace the previous list entirely.
        - Use ``fact`` for stable descriptive facts; ``usage`` for recurring/expected
          usage patterns; ``experience`` for prior relevant experience; ``interest``
          for a stable topic/model/feature being explored; ``concern`` for an
          expressed concern; ``test_drive_goal`` for something the user wants to
          evaluate during the drive; and ``conversation_preference`` for durable
          guidance/style preferences.
        - A question about a model, warranty, battery, charging, ADAS, price, or
          after-sales policy may create ``category="interest"`` with a stable
          topic/model value. It does not establish ownership, purchase intent,
          concern, usage, or a durable preference.
        - Use ``add`` for a new supported signal, ``revise`` when the user clearly
          replaces/corrects an active value, and ``retract`` when the user explicitly
          withdraws a previously stored signal. Do not keep contradictory active
          values when the new statement is clearly a correction.
        - Do not persist weak or speculative inferences as profile facts.
          Use ``interest`` only when the user's actual question, exploration, or
          topic selection provides direct evidence that they are interested in
          a model, feature, policy, or topic. Do not infer additional interests,
          needs, preferences, or intents beyond what the user's statement supports.

    Booking signal parameter rules:
        - ``participant_context.role`` identifies who is speaking for this booking;
          it is not itself a durable purchasing role.
        - Booking signal ``subject`` must be one of ``booking``, ``booker``,
          ``driver``, or ``group``. Never use ``subject="self"`` for booking signals.
        - Use ``booker`` or ``driver`` for facts specifically about that participant,
          ``group`` for additional guests/group-level participation, and ``booking``
          for appointment-wide logistics or constraints.
        - Attendance, who will drive, evaluation/purchase involvement, guests, and
          appointment logistics always belong to ``booking_signals`` rather than
          durable profile data.
        - Registered booking keys include ``booker_attending``, ``driver_attending``,
          ``additional_guest_count``, ``additional_guest_context``,
          ``booker_will_drive``, ``driver_will_drive``, and
          ``*_evaluation_involvement`` / ``*_purchase_involvement``.
        - ``additional_guest_count`` counts only people in addition to the registered
          booker/driver participants explicitly said to attend. It is not the total
          group size. If the speaker says a total that includes them, first record
          the speaker's ``*_attending=true`` signal, then subtract that explicitly
          attending registered participant from the total. Never create aliases such
          as ``custom.total_attendee_count`` for this registered concept.
        - Preserve every explicitly named guest relationship, age, accessibility
          need, and relevant role in ``additional_guest_context``. Keep the user's
          specificity (for example husband versus generic spouse); do not collapse
          or translate it into a less specific label.
        - ``participant_context.same_person=true`` means the registered booker and
          registered driver are one person. If the user names a different person who
          will drive instead, do not assign that fact to ``driver_will_drive``. Set
          the speaking registered participant's ``*_will_drive=false`` and represent
          the named person as ``custom.additional_driver`` with ``subject="group"``
          and a value containing their relationship and ``will_drive=true``.
        - If no registered key fits a new booking case, use ``custom.*`` rather than
          inventing another top-level key.
        - Do not create a separate identity for an additional guest. Represent guest
          information with ``subject="group"`` plus a registered or ``custom.*`` key.
        - Treat ``unknown`` as unanswered. An absent guest count is not zero.
        - A report about another participant is normally booking context unless the
          user clearly states a durable fact about that person. That person's own
          explicit statement takes precedence over third-party reports.

    Evidence and non-inference rules:
        - Only create signals that are directly supported by the user's statement; do
          not infer additional facts merely because they seem plausible from the available
          details. Example: `Gia đình tôi có 4 người` supports a durable profile fact such
          as `household_size=4` (`category="fact"`, `subject="self"`), but by itself does
          NOT establish attendance, guest count, who will drive, evaluation involvement, or
          any other appointment fact. Conversely, `Tôi sẽ đến buổi lái thử cùng vợ và con gái
          2 tuổi` supports booking signals about attendance and accompanying guests, but does
          NOT establish `household_size=3` because the user did not state that these are all
          members of the household.
        - Button clicks select a conversation direction; the click itself is not
          durable profile or booking evidence.
        - Topic selection alone does not establish a durable fact or another person's
          preference.
        - If an unknown booking fact would materially improve advice, leave it
          unknown so the conversation layer can ask the user instead of inferring it.

    Privacy and provenance:
        - Do not send email addresses, contacts, OTPs, authentication tokens, or
          transient/private data that is not a supported signal.
        - You may send ``source_type``, ``certainty``, and ``confidence`` as your
          extraction judgement. The backend records both the raw judgement and its
          deterministic resolved provenance; the backend value is authoritative.
        - Never present an inferred signal as a confirmed user fact.
    """
    return await queue_post_booking_signals(
        profile_signals=profile_signals,
        booking_signals=booking_signals,
        profile_id=profile_id,
        metadata=metadata,
        participant_context=participant_context,
        current_user_message=current_user_message,
    )
