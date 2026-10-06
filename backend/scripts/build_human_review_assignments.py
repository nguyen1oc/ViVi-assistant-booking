"""Build a balanced two-reviewer assignment for every active golden case."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GOLDEN = PROJECT_ROOT / "eval" / "golden" / "agent_cases.json"
DEFAULT_REVIEWS = PROJECT_ROOT / "eval" / "human" / "reviews.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "eval" / "human" / "assignments.csv"
DEFAULT_REVIEWERS = ("nguyen", "chau", "minh", "loc")


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--golden", type=Path, default=DEFAULT_GOLDEN)
    command.add_argument("--reviews", type=Path, default=DEFAULT_REVIEWS)
    command.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    command.add_argument("--reviewers", default=",".join(DEFAULT_REVIEWERS))
    command.add_argument("--check", action="store_true")
    return command


def build_assignments(
    *,
    golden_path: Path,
    reviews_path: Path,
    reviewers: tuple[str, ...],
) -> list[dict[str, str]]:
    if len(reviewers) < 2 or len(reviewers) != len(set(reviewers)):
        raise ValueError("At least two unique reviewers are required")
    golden = json.loads(golden_path.read_text(encoding="utf-8-sig"))
    cases = [
        str(case["case_id"])
        for case in golden["cases"]
        if case.get("evaluation_status") == "active"
    ]
    active_ids = set(cases)
    existing: dict[str, list[str]] = defaultdict(list)
    if reviews_path.is_file():
        with reviews_path.open(encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                case_id = str(row.get("case_id") or "")
                reviewer_id = str(row.get("reviewer_id") or "")
                if (
                    case_id in active_ids
                    and reviewer_id in reviewers
                    and reviewer_id not in existing[case_id]
                    and len(existing[case_id]) < 2
                ):
                    existing[case_id].append(reviewer_id)

    selected = {case_id: list(existing[case_id]) for case_id in cases}
    load = Counter(reviewer for assigned in selected.values() for reviewer in assigned)
    reviewer_rank = {reviewer: index for index, reviewer in enumerate(reviewers)}
    for case_index, case_id in enumerate(cases):
        while len(selected[case_id]) < 2:
            eligible = [reviewer for reviewer in reviewers if reviewer not in selected[case_id]]
            chosen = min(
                eligible,
                key=lambda reviewer: (
                    load[reviewer],
                    (reviewer_rank[reviewer] - case_index) % len(reviewers),
                ),
            )
            selected[case_id].append(chosen)
            load[chosen] += 1

    return [
        {"case_id": case_id, "reviewer_id": reviewer_id}
        for case_id in cases
        for reviewer_id in selected[case_id]
    ]


def render(rows: list[dict[str, str]]) -> str:
    lines = ["case_id,reviewer_id"]
    lines.extend(f"{row['case_id']},{row['reviewer_id']}" for row in rows)
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parser().parse_args()
    reviewers = tuple(item.strip().casefold() for item in args.reviewers.split(",") if item.strip())
    rendered = render(
        build_assignments(
            golden_path=args.golden.resolve(),
            reviews_path=args.reviews.resolve(),
            reviewers=reviewers,
        )
    )
    output = args.output.resolve()
    if args.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"Human-review assignments are stale: {output}")
        print(f"Human-review assignments are current: {output}")
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered, encoding="utf-8")
    print(f"Built {output} with {len(rendered.splitlines()) - 1} assignments")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
