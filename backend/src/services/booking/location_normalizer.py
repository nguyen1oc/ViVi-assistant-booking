"""Canonicalise Vietnamese locality aliases before showroom matching.

This module intentionally resolves only unambiguous city-level aliases. It never
selects a showroom: callers still receive every matching showroom and let the
agent or UI ask the customer to choose when necessary.
"""

from __future__ import annotations

import re
import unicodedata

# Keys and values are accent-free because input is normalised before lookup.
# Keep this allow-list narrow: abbreviations that can refer to more than one
# locality must not silently be converted here.
CITY_ALIASES: dict[str, str] = {
    "ha noi": "ha noi",
    "hanoi": "ha noi",
    "hn": "ha noi",
    "ho chi minh": "ho chi minh",
    "tp ho chi minh": "ho chi minh",
    "thanh pho ho chi minh": "ho chi minh",
    "hcm": "ho chi minh",
    "tp hcm": "ho chi minh",
    "tphcm": "ho chi minh",
    "sai gon": "ho chi minh",
    "saigon": "ho chi minh",
    "sg": "ho chi minh",
}

_ALIAS_PATTERNS = tuple(
    (re.compile(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"), canonical)
    for alias, canonical in sorted(CITY_ALIASES.items(), key=lambda item: len(item[0]), reverse=True)
)

_IGNORED_TOKENS = frozenset({"duong", "phuong", "xa", "quan", "huyen", "thi", "tran", "thanh", "pho", "tp", "so"})

_BROAD_REGION_CLARIFICATIONS = (
    (
        "mien tay",
        "Miền Tây khá rộng. Quý khách cho ViVi xin tỉnh/thành cụ thể, ví dụ Cần Thơ, Long An, An Giang hoặc Kiên Giang.",
    ),
    (
        "mien trung",
        "Miền Trung khá rộng. Quý khách cho ViVi xin tỉnh/thành cụ thể, ví dụ Đà Nẵng, Quảng Nam, Huế hoặc Nghệ An.",
    ),
    (
        "mien nam",
        "Miền Nam khá rộng. Quý khách cho ViVi xin tỉnh/thành cụ thể, ví dụ TP.HCM, Bình Dương, Cần Thơ hoặc Đồng Nai.",
    ),
    (
        "mien bac",
        "Miền Bắc khá rộng. Quý khách cho ViVi xin tỉnh/thành cụ thể, ví dụ Hà Nội, Hải Phòng hoặc Bắc Giang.",
    ),
)


def normalize_location_text(value: str) -> str:
    """Return a lowercase, accent-free location string with known aliases expanded."""
    ascii_value = unicodedata.normalize("NFD", value.casefold().replace("đ", "d"))
    ascii_value = "".join(character for character in ascii_value if unicodedata.category(character) != "Mn")
    ascii_value = " ".join(re.findall(r"[a-z0-9]+", ascii_value))
    for pattern, canonical in _ALIAS_PATTERNS:
        ascii_value = pattern.sub(canonical, ascii_value)
    return ascii_value


def broad_region_clarification(value: str) -> str | None:
    """Ask for a province/city when the location is only a broad Vietnamese region.

    This is intentionally available to the chat layer as well as catalog search,
    so a missing vehicle model cannot cause an ambiguous region to fall through
    to a generic out-of-scope reply.
    """
    normalized = normalize_location_text(value)
    for region, prompt in _BROAD_REGION_CLARIFICATIONS:
        if re.search(rf"(?<![a-z0-9]){re.escape(region)}(?![a-z0-9])", normalized):
            return prompt
    return None


def normalize_location_tokens(value: str) -> set[str]:
    """Return searchable tokens after expanding unambiguous locality aliases."""
    return {
        token
        for token in normalize_location_text(value).split()
        if token not in _IGNORED_TOKENS and (len(token) > 1 or token.isdigit())
    }
