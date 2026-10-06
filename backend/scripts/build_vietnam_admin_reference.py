#!/usr/bin/env python3
"""Extract Vietnam's 2025 two-tier administrative codes from official Gazette text."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = PROJECT_ROOT / "backend" / "reference" / "vietnam_admin_units_2025.csv"
SOURCE_URL = "https://vanban.chinhphu.vn/?pageid=27160&docid=214409"
PROVINCE_LINE = re.compile(r"^\s*\d+\s+(\d{2})\s+((Thành phố|Tỉnh)\s+.+?)\s*$")
PROVINCE_HEADING = re.compile(r"^\s*(\d{2})\.\s+(THÀNH PHỐ|TỈNH)\s+(.+?)\s*$")
WARD_LINE = re.compile(r"^\s*(\d{5})\s+((Phường|Xã|Đặc khu)\s+.+?)\s*$")


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description="Build the official 2025 province/ward reference CSV.")
    command.add_argument(
        "--source-text",
        type=Path,
        nargs="+",
        required=True,
        help="One or more UTF-8 Gazette texts extracted with pdftotext -layout.",
    )
    command.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return command


def _split_unit_name(value: str) -> tuple[str, str]:
    for unit_type in ("Thành phố", "Đặc khu", "Tỉnh", "Phường", "Xã"):
        prefix = f"{unit_type} "
        if value.startswith(prefix):
            return unit_type, value.removeprefix(prefix).strip()
    raise SystemExit(f"Unsupported administrative unit name: {value!r}")


def extract(source_text: str) -> list[dict[str, str]]:
    provinces: dict[str, tuple[str, str]] = {}
    for line in source_text.splitlines():
        match = PROVINCE_LINE.match(line)
        if match:
            provinces[match.group(1)] = _split_unit_name(match.group(2))
    if len(provinces) != 34:
        raise SystemExit(f"Expected 34 province codes, extracted {len(provinces)}")

    rows: list[dict[str, str]] = []
    current_province_code: str | None = None
    for line in source_text.splitlines():
        heading = PROVINCE_HEADING.match(line)
        if heading:
            current_province_code = heading.group(1)
            if current_province_code not in provinces:
                raise SystemExit(f"Ward appendix references unknown province {current_province_code}")
            continue
        ward = WARD_LINE.match(line)
        if not ward or not current_province_code:
            continue
        ward_unit_type, ward_name = _split_unit_name(ward.group(2))
        province_unit_type, province_name = provinces[current_province_code]
        rows.append(
            {
                "province_code": current_province_code,
                "province_name": province_name,
                "province_unit_type": province_unit_type,
                "ward_code": ward.group(1),
                "ward_name": ward_name,
                "ward_unit_type": ward_unit_type,
                "effective_from": "2025-07-01",
                "source_url": SOURCE_URL,
            }
        )

    ward_codes = {row["ward_code"] for row in rows}
    if len(rows) != 3_321 or len(ward_codes) != len(rows):
        raise SystemExit(f"Expected 3,321 unique ward codes, extracted {len(rows)} rows/{len(ward_codes)} codes")
    if {row["province_code"] for row in rows} != set(provinces):
        raise SystemExit("Not every official province has ward rows")
    expected_province_names = {"01": "Hà Nội", "79": "Hồ Chí Minh", "96": "Cà Mau"}
    for code, expected_name in expected_province_names.items():
        if provinces[code][1] != expected_name:
            raise SystemExit(
                f"Province {code} parsed as {provinces[code][1]!r}, expected {expected_name!r}"
            )
    return rows


def main() -> int:
    args = parser().parse_args()
    source_text = "\n".join(path.read_text(encoding="utf-8") for path in args.source_text)
    rows = extract(source_text)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Built {output} with 34 provinces and {len(rows):,} wards")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
