"""Validate the methodological-independence contract for C1/C2/C3 reviews."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CRITICAL_NODES = {"C1", "C2", "C3"}
REVIEW_LENSES = {
    "semantic_constraint_audit",
    "alternative_formulation",
    "invariant_counterexample",
    "implementation_consistency",
    "evidence_claim_audit",
}
EXPECTED_REVIEW_MODE = {"C1": "blind", "C2": "challenge", "C3": "results"}
NO_DIFFERENCE = {"", "same", "none", "no difference", "无", "无差异", "相同"}
PASS_VERDICTS = {"PASS", "PASS_WITH_LIMITATIONS"}


def load_record(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("missing PyYAML; install requirements-dev.txt") from exc
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("review record must be a mapping")
    return value


def validate_review_record(record: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    node = record.get("critical_node")
    if node not in CRITICAL_NODES:
        errors.append("critical_node must be C1, C2, or C3")
    lenses = record.get("review_lens")
    if not isinstance(lenses, list) or not lenses:
        errors.append("review_lens is required and cannot be empty")
    elif any(lens not in REVIEW_LENSES for lens in lenses):
        errors.append("review_lens contains an unsupported lens")
    if node in EXPECTED_REVIEW_MODE and record.get("review_mode") != EXPECTED_REVIEW_MODE[node]:
        errors.append(f"{node} must use review_mode={EXPECTED_REVIEW_MODE[node]}")

    primary = str(record.get("primary_method_family", "")).strip().lower()
    alternative = str(record.get("alternative_method_family", "")).strip().lower()
    difference = str(record.get("methodological_difference", "")).strip().lower()
    if not primary or not alternative:
        errors.append("primary_method_family and alternative_method_family are required")
    if difference in NO_DIFFERENCE:
        errors.append("methodological_difference must describe a real challenge lens")
    if primary and alternative and primary == alternative and difference in NO_DIFFERENCE:
        errors.append("identical method families without methodological difference are not independent")

    for field in ("critical_decisions_reviewed", "what_was_checked", "what_was_not_checked", "uncertainty"):
        value = record.get(field)
        if not isinstance(value, list) or not value:
            errors.append(f"{field} must list at least one item")
    disconfirming = record.get("disconfirming_tests") or []
    counterexamples = record.get("counterexamples") or []
    if not isinstance(disconfirming, list) or not isinstance(counterexamples, list):
        errors.append("disconfirming_tests and counterexamples must be lists")
    elif not disconfirming and not counterexamples:
        errors.append("at least one disconfirming test or counterexample is required")
    if record.get("verdict") in PASS_VERDICTS and errors:
        errors.append("a PASS verdict cannot bypass the independence contract")
    return not errors, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("review_record", type=Path)
    args = parser.parse_args()
    try:
        ok, errors = validate_review_record(load_record(args.review_record))
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {exc}", file=sys.stderr)
        return 2
    if not ok:
        print("FAIL review independence")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS review independence")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
