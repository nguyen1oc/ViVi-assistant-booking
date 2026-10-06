from __future__ import annotations

import json
import unicodedata
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class PayloadLimits:
    max_bytes: int
    max_depth: int
    max_nodes: int
    max_string_chars: int


def normalize_text(value: str) -> str:
    """Canonicalize compatibility forms and remove invisible controls.

    NFKC folds full-width Latin characters and other compatibility glyphs that
    attackers commonly use to evade ASCII-oriented policy patterns. Format
    controls (including bidi overrides and zero-width characters) are removed
    because they have no business meaning in this Vietnamese booking channel.
    Newlines and tabs remain available for normal messages.
    """
    normalized = unicodedata.normalize("NFKC", value)
    cleaned: list[str] = []
    for character in normalized:
        category = unicodedata.category(character)
        if category == "Cf" or (category == "Cc" and character not in {"\n", "\r", "\t"}):
            continue
        cleaned.append(character)
    return "".join(cleaned).strip()


def fold_text_for_policy(value: str) -> str:
    """Return an accent-insensitive form used only for policy matching."""
    normalized = normalize_text(value).replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFKD", normalized)
    return "".join(character for character in decomposed if unicodedata.category(character) != "Mn")


def iter_strings(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield str(key)
            yield from iter_strings(item)
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            yield from iter_strings(item)


def validate_payload(value: Any, limits: PayloadLimits) -> str | None:
    """Return a private rejection reason when a JSON-like payload is abusive."""
    try:
        encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str).encode("utf-8")
    except (TypeError, ValueError):
        return "payload is not serializable"
    if len(encoded) > limits.max_bytes:
        return f"payload exceeds {limits.max_bytes} bytes"

    nodes = 0

    def walk(item: Any, depth: int) -> str | None:
        nonlocal nodes
        nodes += 1
        if nodes > limits.max_nodes:
            return f"payload exceeds {limits.max_nodes} nodes"
        if depth > limits.max_depth:
            return f"payload exceeds depth {limits.max_depth}"
        if isinstance(item, str) and len(item) > limits.max_string_chars:
            return f"payload string exceeds {limits.max_string_chars} characters"
        if isinstance(item, Mapping):
            for key, nested in item.items():
                if len(str(key)) > 128:
                    return "payload contains an oversized key"
                violation = walk(nested, depth + 1)
                if violation:
                    return violation
        elif isinstance(item, Sequence) and not isinstance(item, (str, bytes, bytearray)):
            for nested in item:
                violation = walk(nested, depth + 1)
                if violation:
                    return violation
        return None

    return walk(value, 0)
