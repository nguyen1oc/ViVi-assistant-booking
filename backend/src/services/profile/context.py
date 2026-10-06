from __future__ import annotations

import json
import logging
from typing import Any

from src.services.profile.models import ProfileSnapshot

SECTION_TITLES = {
    "known_facts": "Known facts",
    "interests": "Interests",
    "concerns": "Concerns",
    "usage_context": "Usage context",
    "preferences": "Preferences",
    "custom_intents": "Custom signals",
    "uncertain_signals": "Uncertain signals",
}
logger = logging.getLogger("profile.context")


def _section(signal: dict[str, Any]) -> str:
    certainty = str(signal.get("certainty") or "possible")
    confidence = float(signal.get("confidence") or 0)
    category = str(signal.get("category") or "")
    if certainty == "possible" or confidence < 0.6:
        return "uncertain_signals"
    return {
        "interest": "interests",
        "concern": "concerns",
        "usage": "usage_context",
        "experience": "usage_context",
        "conversation_preference": "preferences",
        "custom_intent": "custom_intents",
    }.get(category, "known_facts")


def _display(signal: dict[str, Any]) -> str:
    description = str(signal.get("description") or "").strip()
    if description:
        return description
    value = signal.get("value")
    rendered = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else str(value)
    return f"{str(signal.get('key') or '').replace('_', ' ')}: {rendered}".strip(": ")


def build_profile_context(snapshot: ProfileSnapshot, message: str = "", *, limit: int = 40) -> dict[str, Any]:
    """Build deterministic structured and Markdown views from stored signals."""
    terms = set(message.casefold().split())
    ranked = sorted(
        snapshot.signals,
        key=lambda item: (
            sum(term in f"{item.get('key', '')} {item.get('description', '')}".casefold() for term in terms),
            float(item.get("confidence") or 0),
        ),
        reverse=True,
    )[:limit]
    sections: dict[str, list[dict[str, Any]]] = {key: [] for key in SECTION_TITLES}
    for signal in ranked:
        sections[_section(signal)].append(
            {
                "key": signal.get("key"),
                "value": signal.get("value"),
                "description": signal.get("description"),
                "certainty": signal.get("certainty"),
                "confidence": signal.get("confidence"),
                "source_type": (
                    "third_party"
                    if str(signal.get("source_ref") or "").startswith("third_party:")
                    else signal.get("source_type")
                ),
            }
        )
    result = {
        "profile_id": snapshot.id,
        "state": snapshot.state,
        "version": snapshot.version,
        "sections": sections,
    }
    logger.info(
        "profile.context.rendered profile_id=%s state=%s version=%s section_counts=%s",
        snapshot.id,
        snapshot.state,
        snapshot.version,
        {key: len(items) for key, items in sections.items()},
    )
    return result
