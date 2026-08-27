"""Check that a recorded targeted validation really closes a revision.

This checker validates records and safe check identifiers only. It never
executes command strings supplied by a YAML file.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from .gate_contract import CHANGE_LEVELS, MINIMUM_AFFECTED_GATES, SAFE_CHECK_IDS, required_checks_for, validate_revision_scope
except ImportError:  # pragma: no cover
    from gate_contract import CHANGE_LEVELS, MINIMUM_AFFECTED_GATES, SAFE_CHECK_IDS, required_checks_for, validate_revision_scope


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("missing PyYAML; install requirements-dev.txt") from exc
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping")
    return value


def validate_revision_closure(impact: dict, validation: dict, approval: dict | None = None) -> list[str]:
    errors: list[str] = []
    if impact.get("record_type") != "change_impact_record":
        errors.append("invalid change_impact_record")
    if validation.get("record_type") != "revision_validation_record":
        errors.append("invalid revision_validation_record")
    for field in ("revision_id", "case_id", "base_git_revision", "new_git_revision", "change_level"):
        if impact.get(field) != validation.get(field):
            errors.append(f"impact and validation disagree on {field}")
    if impact.get("changed_files") != validation.get("changed_files"):
        errors.append("impact and validation changed_files differ")
    if not impact.get("changed_files"):
        errors.append("change impact record has no changed_files")
    change_level = impact.get("change_level")
    if change_level not in CHANGE_LEVELS:
        errors.append("change_level must be R0, R1, R2, or R3")

    required = impact.get("required_checks") or []
    executed = validation.get("executed_checks") or []
    if not required:
        errors.append("required_checks cannot be empty")
    if change_level in CHANGE_LEVELS and impact.get("changed_files"):
        canonical = set(required_checks_for(change_level, impact["changed_files"]))
        missing_canonical = canonical.difference(required)
        if missing_canonical:
            errors.append(f"required_checks omit canonical checks: {sorted(missing_canonical)}")
    unsafe = set(required).difference(SAFE_CHECK_IDS) | set(executed).difference(SAFE_CHECK_IDS)
    if unsafe:
        errors.append(f"unknown or unsafe check IDs: {sorted(unsafe)}")
    missing = set(required).difference(executed)
    if missing:
        errors.append(f"required checks lack execution evidence: {sorted(missing)}")
    exit_codes = validation.get("check_exit_codes") or {}
    outputs = validation.get("check_outputs") or {}
    for check in required:
        if check not in exit_codes:
            errors.append(f"missing exit code for required check: {check}")
        elif exit_codes[check] != 0:
            errors.append(f"required check failed: {check}")
        if check not in outputs or not str(outputs[check]).strip():
            errors.append(f"missing output evidence for required check: {check}")
    if validation.get("validation_status") != "passed":
        errors.append("validation_status is not passed")

    affected_gates = impact.get("affected_gates") or []
    scope_ok, scope_message = validate_revision_scope(change_level, affected_gates)
    if not scope_ok:
        errors.append(scope_message)
    minimum_gates = MINIMUM_AFFECTED_GATES.get(change_level, frozenset())
    if not minimum_gates.issubset(set(affected_gates)):
        errors.append(f"affected_gates are below {change_level} minimum: {sorted(minimum_gates)}")
    if change_level == "R0" and (impact.get("affected_experiments") or validation.get("new_experiment_ids")):
        errors.append("R0 cannot claim affected experiments or new experiment IDs")
    if change_level in {"R2", "R3"} and impact.get("affected_experiments"):
        if not validation.get("new_experiment_ids"):
            errors.append("R2/R3 affected experiments require new experiment records")
        if not validation.get("output_hashes"):
            errors.append("R2/R3 affected experiments require output hashes")

    status_updates = {
        item.get("claim_id"): item.get("status")
        for item in (validation.get("claim_status_updates") or [])
        if isinstance(item, dict)
    }
    for claim_id in impact.get("affected_claims") or []:
        if status_updates.get(claim_id) not in {"downgraded", "revalidated"}:
            errors.append(f"affected claim lacks downgrade or revalidation: {claim_id}")

    modified_by = impact.get("modified_by")
    for finding in validation.get("closed_findings") or []:
        if finding.get("severity") in {"P0", "P1"}:
            closed_by = finding.get("closed_by")
            if closed_by == modified_by:
                errors.append(f"high-risk finding closed by modifier: {finding.get('finding_id')}")
            if closed_by not in {"human", "human_owner", "independent_adversary"}:
                errors.append(f"high-risk finding needs human or independent closure: {finding.get('finding_id')}")
    unresolved = validation.get("unresolved_findings") or []
    if unresolved and any(str(item).startswith(("P0", "P1")) for item in unresolved):
        errors.append("unresolved P0/P1 findings remain")

    if approval is not None:
        if approval.get("record_type") != "approved_findings":
            errors.append("invalid approved_findings record")
        if not approval.get("allowed_files"):
            errors.append("approved revision must have a non-empty allowed_files list")
        if approval.get("change_level") != change_level:
            errors.append("approval and change impact levels differ")
        if approval.get("validation_check_ids") != required:
            errors.append("approval validation_check_ids must equal required_checks")
        if approval.get("validation_commands"):
            errors.append("arbitrary validation_commands are forbidden; use safe check IDs")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("change_impact_record", type=Path)
    parser.add_argument("revision_validation_record", type=Path)
    parser.add_argument("--approved-findings", type=Path)
    args = parser.parse_args()
    try:
        impact = load_yaml(args.change_impact_record)
        validation = load_yaml(args.revision_validation_record)
        approval = load_yaml(args.approved_findings) if args.approved_findings else None
        errors = validate_revision_closure(impact, validation, approval)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {exc}", file=sys.stderr)
        return 2
    if errors:
        print("FAIL targeted validation closure")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS targeted validation closure")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
