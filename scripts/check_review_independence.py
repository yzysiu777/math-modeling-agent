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
METHOD_FAMILIES = {
    "unknown", "other", "linear_programming", "mixed_integer_programming", "nonlinear_programming",
    "dynamic_programming", "shortest_path", "constraint_programming", "metaheuristic",
    "stochastic_programming", "robust_optimization", "simulation_optimization", "statistical_regression",
    "classification", "tree_ensemble", "neural_network", "time_series", "clustering",
    "causal_inference", "rule_based",
}
DIFFERENCE_AXES = {
    "decomposition", "relaxation", "feasibility", "invariant", "counterexample",
    "solver_paradigm", "data_split", "evidence_audit",
}
TEST_STATUSES = {"planned", "passed", "failed", "blocked"}
PASS_VERDICTS = {"PASS", "PASS_WITH_LIMITATIONS"}
TEST_FIELDS = {"test_id", "target", "input_or_case", "expected_falsifier", "actual_result", "evidence", "status"}


def load_record(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("missing PyYAML; install requirements-dev.txt") from exc
    if path.suffix.lower() == ".json":
        value = json.loads(path.read_text(encoding="utf-8"))
    else:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("review record must be a mapping")
    return value


def _nonempty(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_disconfirming_tests(value: object, field: str, errors: list[str]) -> list[dict]:
    if not isinstance(value, list):
        errors.append(f"{field} must be a list of structured tests")
        return []
    for index, test in enumerate(value):
        if not isinstance(test, dict):
            errors.append(f"{field}[{index}] must be an object")
            continue
        missing = TEST_FIELDS.difference(test)
        if missing:
            errors.append(f"{field}[{index}] missing fields: {sorted(missing)}")
        if not _nonempty(test.get("test_id")):
            errors.append(f"{field}[{index}].test_id is empty")
        if not _nonempty(test.get("target")):
            errors.append(f"{field}[{index}].target is empty")
        if not _nonempty(test.get("input_or_case")):
            errors.append(f"{field}[{index}].input_or_case is empty")
        if not _nonempty(test.get("expected_falsifier")):
            errors.append(f"{field}[{index}].expected_falsifier is empty")
        if not _nonempty(test.get("actual_result")):
            errors.append(f"{field}[{index}].actual_result is empty")
        if not isinstance(test.get("evidence"), list) or not test.get("evidence"):
            errors.append(f"{field}[{index}].evidence must be non-empty")
        if test.get("status") not in TEST_STATUSES:
            errors.append(f"{field}[{index}].status is invalid")
    return [test for test in value if isinstance(test, dict)]


def validate_review_record(record: dict) -> tuple[bool, list[str]]:
    errors: list[str] = []
    node = record.get("critical_node")
    if node not in CRITICAL_NODES:
        errors.append("critical_node must be C1, C2, or C3")
    if record.get("reviewer_role") not in {"independent_adversary", "human"}:
        errors.append("reviewer_role must be independent_adversary or human")
    if not _nonempty(record.get("reviewer_id")):
        errors.append("reviewer_id is required")
    lenses = record.get("review_lens")
    if not isinstance(lenses, list) or not lenses:
        errors.append("review_lens is required and cannot be empty")
    elif any(lens not in REVIEW_LENSES for lens in lenses):
        errors.append("review_lens contains an unsupported lens")
    if node in EXPECTED_REVIEW_MODE and record.get("review_mode") != EXPECTED_REVIEW_MODE[node]:
        errors.append(f"{node} must use review_mode={EXPECTED_REVIEW_MODE[node]}")

    primary = record.get("primary_method_family")
    alternative = record.get("alternative_method_family")
    if primary not in METHOD_FAMILIES:
        errors.append("primary_method_family is not a canonical method family")
    if alternative not in METHOD_FAMILIES:
        errors.append("alternative_method_family is not a canonical method family")
    difference = record.get("methodological_difference")
    if not isinstance(difference, dict):
        errors.append("methodological_difference must be structured")
    else:
        missing = {"axis", "primary_assumption", "alternative_assumption", "discriminating_test"}.difference(difference)
        if missing:
            errors.append(f"methodological_difference missing fields: {sorted(missing)}")
        if difference.get("axis") not in DIFFERENCE_AXES:
            errors.append("methodological_difference.axis is invalid")
        for key in ("primary_assumption", "alternative_assumption", "discriminating_test"):
            if not _nonempty(difference.get(key)):
                errors.append(f"methodological_difference.{key} is empty")
        if difference.get("primary_assumption") == difference.get("alternative_assumption"):
            errors.append("methodological_difference must state different assumptions")
    if primary == alternative and primary not in {"unknown", "other"}:
        errors.append("C1/C2/C3 must name a genuinely different alternative method family")

    for field in ("critical_decisions_reviewed", "what_was_checked", "what_was_not_checked", "uncertainty"):
        value = record.get(field)
        if not isinstance(value, list) or not value:
            errors.append(f"{field} must list at least one item")
    disconfirming = _validate_disconfirming_tests(record.get("disconfirming_tests"), "disconfirming_tests", errors)
    counterexamples = _validate_disconfirming_tests(record.get("counterexamples"), "counterexamples", errors)
    all_tests = disconfirming + counterexamples
    if not all_tests:
        errors.append("at least one structured disconfirming test or counterexample is required")
    elif record.get("verdict") in PASS_VERDICTS and not any(test.get("status") in {"passed", "failed"} for test in all_tests):
        errors.append("a PASS verdict requires an actual result from at least one falsification test")

    for index, finding in enumerate(record.get("findings") or []):
        if not isinstance(finding, dict):
            continue
        if finding.get("source_review_id") != record.get("review_id"):
            errors.append(f"finding[{index}] source_review_id does not match review_id")
        if finding.get("raised_by_id") != record.get("reviewer_id"):
            errors.append(f"finding[{index}] raised_by_id does not match reviewer_id")
        if finding.get("severity") in {"P0", "P1"} and finding.get("closed_by_id") in {record.get("reviewer_id"), finding.get("raised_by_id")}:
            errors.append(f"finding[{index}] high-risk issue cannot be closed by its raiser")

    if record.get("verdict") in PASS_VERDICTS and errors:
        errors.append("a PASS verdict cannot bypass the independence contract")
    return not errors, sorted(set(errors))


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
