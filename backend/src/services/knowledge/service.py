from __future__ import annotations

import json
import re
import unicodedata
from datetime import date
from pathlib import Path
from typing import Any

_BLOCKED_REVIEW_STATUSES = {"expired", "rejected", "superseded"}


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value).casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _compact(value: object) -> str:
    return _normalize(value).replace(" ", "")


def _values(value: object) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


class KnowledgeService:
    def __init__(self, *, allow_pending_review: bool = True) -> None:
        path = Path(__file__).with_name("post_booking_trusted_knowledge.json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict) or not isinstance(payload.get("entries"), list):
            raise ValueError("Trusted knowledge dataset must be an object containing entries[]")

        self.metadata = {key: value for key, value in payload.items() if key != "entries"}
        self.allow_pending_review = allow_pending_review
        self.entries: list[dict[str, Any]] = payload["entries"]
        self._validate_entries()

    def _validate_entries(self) -> None:
        required = set(self.metadata.get("rules", {}).get("required_fields", []))
        seen: set[str] = set()
        for index, entry in enumerate(self.entries):
            if not isinstance(entry, dict):
                raise ValueError(f"Knowledge entry {index} must be an object")
            missing = required.difference(entry)
            if missing:
                raise ValueError(f"Knowledge entry {index} is missing: {sorted(missing)}")
            entry_id = str(entry["id"])
            if entry_id in seen:
                raise ValueError(f"Duplicate knowledge entry id: {entry_id}")
            seen.add(entry_id)
            provenance = entry.get("provenance")
            if not isinstance(provenance, dict):
                raise ValueError(f"Knowledge entry {entry_id} requires provenance")
            if not provenance.get("source_uri") or not provenance.get("market"):
                raise ValueError(f"Knowledge entry {entry_id} has incomplete provenance")

    @staticmethod
    def _is_review_eligible(entry: dict[str, Any], today: date) -> bool:
        provenance = entry["provenance"]
        if _normalize(provenance.get("review_status")) in _BLOCKED_REVIEW_STATUSES:
            return False
        next_review = provenance.get("next_review_date")
        if provenance.get("time_sensitivity") == "high" and next_review:
            try:
                if date.fromisoformat(str(next_review)) < today:
                    return False
            except ValueError:
                return False
        return True

    @staticmethod
    def _scope_matches(
        entry: dict[str, Any], *, market: str, model: str, trim: str, model_year: str
    ) -> bool:
        provenance = entry["provenance"]
        entry_market = _normalize(provenance.get("market"))
        if entry_market not in {_normalize(market), "global general"}:
            return False

        models = _values(provenance.get("models"))
        if model and models and _compact(model) not in {_compact(item) for item in models}:
            return False
        trims = _values(provenance.get("trims"))
        if trim and trims and not any(_normalize(trim) in _normalize(item) for item in trims):
            return False
        years = _values(provenance.get("model_years"))
        if model_year and years and _normalize(model_year) not in {_normalize(item) for item in years}:
            return False
        return True

    def search(
        self,
        query: str,
        *,
        model_code: str = "",
        topics: list[str] | None = None,
        market: str = "",
        trim: str = "",
        model_year: str = "",
        limit: int = 5,
    ) -> dict[str, Any]:
        normalized_query = _normalize(query)
        words = {word for word in normalized_query.split() if len(word) > 1}
        requested_topics = {_normalize(item) for item in (topics or [])}
        requested_market = market or str(self.metadata.get("market_default") or "VN")
        requested_model = model_code or self._infer_model(query)
        requested_year = model_year or self._infer_model_year(query)
        ranked: list[tuple[int, dict[str, Any]]] = []
        live_boundaries: list[dict[str, str]] = []
        today = date.today()

        for entry in self.entries:
            if not self._is_review_eligible(entry, today):
                continue
            review_status = _normalize(entry["provenance"].get("review_status"))
            if review_status != "approved" and not self.allow_pending_review:
                continue
            if not self._scope_matches(
                entry,
                market=requested_market,
                model=requested_model,
                trim=trim,
                model_year=requested_year,
            ):
                continue

            retrieval = entry.get("retrieval") or {}
            tags = _values(retrieval.get("tags"))
            searchable = _normalize(
                " ".join([str(entry["topic"]), str(entry["title"]), str(entry["content"]), *tags])
            )
            searchable_words = set(searchable.split())
            if retrieval.get("live_data_required"):
                if words.intersection(searchable_words):
                    live_boundaries.append({"title": str(entry["title"]), "content": str(entry["content"])})
                continue

            topic = _normalize(entry["topic"])
            score = sum(2 for word in words if word in searchable_words)
            score += sum(1 for word in words if word in searchable and word not in searchable_words)
            score += 8 if normalized_query and normalized_query in searchable else 0
            score += 6 if requested_topics and any(
                topic == item or topic.startswith(f"{item} ") for item in requested_topics
            ) else 0
            if requested_model and _values(entry["provenance"].get("models")):
                score += 8
            if trim and _values(entry["provenance"].get("trims")):
                score += 4
            if requested_year and _values(entry["provenance"].get("model_years")):
                score += 4
            if score:
                ranked.append((score, entry))

        ranked.sort(key=lambda item: (-item[0], str(item[1]["id"])))
        matches = [entry for _, entry in ranked[: max(1, min(limit, 10))]]
        pending = any(entry["provenance"].get("review_status") != "approved" for entry in matches)
        facts = [
            {
                "id": entry["id"],
                "topic": entry["topic"],
                "title": entry["title"],
                "content": entry["content"],
                "source": entry["source"],
                "source_uri": entry["provenance"]["source_uri"],
                "publisher": entry["provenance"].get("publisher"),
                "review_status": entry["provenance"].get("review_status"),
                "scope": {
                    key: entry["provenance"].get(key)
                    for key in ("market", "models", "trims", "model_years", "standard")
                },
            }
            for entry in matches
        ]
        return {
            "query": query,
            "filters": {
                "market": requested_market,
                "model": requested_model,
                "trim": trim,
                "model_year": requested_year,
                "topics": topics or [],
            },
            "matched_topics": list(dict.fromkeys(str(entry["topic"]) for entry in matches)),
            "facts": facts,
            "source_labels": list(dict.fromkeys(str(entry["source"]) for entry in matches)),
            "live_data_boundaries": live_boundaries,
            "dataset": self.metadata.get("dataset"),
            "schema_version": self.metadata.get("schema_version"),
            "review_warning": (
                "Some results are pending internal review and are not production-approved."
                if pending
                else None
            ),
        }

    def _infer_model(self, query: str) -> str:
        compact_query = _compact(query)
        known_models = sorted(
            {
                str(model)
                for entry in self.entries
                for model in _values(entry.get("provenance", {}).get("models"))
            },
            key=lambda item: len(_compact(item)),
            reverse=True,
        )
        for model in known_models:
            if _compact(model) in compact_query:
                return model
        return ""

    @staticmethod
    def _infer_model_year(query: str) -> str:
        match = re.search(r"\b(20\d{2})\b", query)
        return match.group(1) if match else ""
