"""Validate a lightweight Markdown candidate-model pool.

The checker is intentionally syntactic.  It catches empty fields and obvious
duplicates, but it does not pretend to decide whether two routes are genuinely
different; that remains a modeling and review judgment.
"""

from __future__ import annotations

import argparse
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


VALID_ROUTE_STATUS = {
    "candidate", "testing", "champion", "challenger", "paused", "rejected",
}
_HEADING = re.compile(
    r"^\s*#{2,4}\s+(M-[A-Za-z0-9][A-Za-z0-9_-]*)(?:\s*.*)?\s*$",
    re.IGNORECASE,
)
_ROUTE_HEADING = re.compile(
    r"^\s*(?P<hashes>#+)\s+(?P<route>M-[A-Za-z0-9][A-Za-z0-9_-]*)(?:\s*.*)?\s*$",
    re.IGNORECASE,
)
_FIELD = re.compile(r"^\s*-\s*([^:：]+?)\s*[：:]\s*(.*?)\s*$")
_FIELD_ALIASES = {
    "方法族": "method_family",
    "method family": "method_family",
    "method_family": "method_family",
    "核心思想": "core_idea",
    "core idea": "core_idea",
    "core_idea": "core_idea",
    "最便宜的证伪实验": "cheapest_falsifier",
    "cheapest falsifier": "cheapest_falsifier",
    "cheapest_falsifier": "cheapest_falsifier",
    "当前状态": "status",
    "状态": "status",
    "status": "status",
}
_PLACEHOLDERS = {"", "-", "—", "待填写", "待填", "待补充", "todo", "tbd", "n/a"}


@dataclass(frozen=True)
class CandidateRoute:
    route_id: str
    method_family: str
    core_idea: str
    cheapest_falsifier: str
    status: str


def _key(value: str) -> str:
    return " ".join(value.casefold().split())


def _has_value(value: str) -> bool:
    normalized = _key(value).strip(" .。_")
    return normalized not in _PLACEHOLDERS and bool(normalized)


def normalize_method_family(value: str) -> str:
    """Normalize case, whitespace and Unicode punctuation for duplicate checks."""

    normalized = unicodedata.normalize("NFKC", value).casefold()
    return "".join(
        character
        for character in normalized
        if not character.isspace() and not unicodedata.category(character).startswith("P")
    )


def parse_candidate_pool(text: str) -> List[CandidateRoute]:
    """Parse level-2 to level-4 ``M-...`` sections and known bullet fields."""

    routes: List[Dict[str, str]] = []
    current: Dict[str, str] | None = None
    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading:
            if current is not None:
                routes.append(current)
            current = {
                "route_id": heading.group(1),
                "method_family": "",
                "core_idea": "",
                "cheapest_falsifier": "",
                "status": "",
            }
            continue
        if current is None:
            continue
        field = _FIELD.match(line)
        if not field:
            continue
        alias = _FIELD_ALIASES.get(_key(field.group(1)))
        if alias is not None:
            current[alias] = field.group(2).strip()
    if current is not None:
        routes.append(current)
    return [CandidateRoute(**route) for route in routes]


def _unsupported_heading_levels(text: str) -> List[int]:
    """Return route-heading levels outside the supported Markdown range."""

    levels = {
        len(match.group("hashes"))
        for line in text.splitlines()
        if (match := _ROUTE_HEADING.match(line))
        and len(match.group("hashes")) not in {2, 3, 4}
    }
    return sorted(levels)


def validate_candidate_pool(path: Path) -> List[str]:
    """Return lightweight validation errors for a candidate pool file."""

    if not path.is_file():
        return [f"missing candidate pool: {path}"]
    text = path.read_text(encoding="utf-8")
    routes = parse_candidate_pool(text)
    errors: List[str] = []
    unsupported_levels = _unsupported_heading_levels(text)
    if unsupported_levels:
        levels = ", ".join(f"h{level}" for level in unsupported_levels)
        errors.append(
            f"unsupported candidate heading level(s): {levels}; "
            "use h2, h3 or h4 headings for routes"
        )
    if len(routes) < 3:
        errors.append("candidate pool needs at least three routes")

    seen_ids: set[str] = set()
    families: set[str] = set()
    for route in routes:
        route_id = route.route_id.strip()
        normalized_id = route_id.casefold()
        if not route_id:
            errors.append("candidate route has no route ID")
        elif normalized_id in seen_ids:
            errors.append(f"duplicate candidate route ID: {route_id}")
        seen_ids.add(normalized_id)

        if not _has_value(route.method_family):
            errors.append(f"candidate {route_id} has no method family")
        else:
            family = normalize_method_family(route.method_family)
            if not family:
                errors.append(f"candidate {route_id} has no method family")
            else:
                families.add(family)
        if not _has_value(route.core_idea):
            errors.append(f"candidate {route_id} has no core idea")
        if not _has_value(route.cheapest_falsifier):
            errors.append(f"candidate {route_id} has no cheapest falsification experiment")
        status = _key(route.status).strip("`'\"")
        if status not in VALID_ROUTE_STATUS:
            errors.append(f"candidate {route_id} has invalid status: {route.status!r}")

    if len(families) < 3:
        errors.append("candidate pool needs at least three distinct method families")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="validate a lightweight candidate-model pool")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    errors = validate_candidate_pool(args.path)
    if errors:
        print("FAIL candidate pool")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"PASS candidate pool: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
