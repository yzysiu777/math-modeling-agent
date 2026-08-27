"""Fail-closed validation of trusted targeted-revision evidence.

The closure checker consumes structured results produced by the fixed trusted
runner.  It deliberately rejects the historical ``executed_checks``,
``check_exit_codes`` and ``check_outputs`` fields because those fields can be
hand-filled without proving that a check was executed.
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

try:
    from .gate_contract import (
        CHANGE_LEVELS,
        CHANGE_SURFACES,
        CHECK_IMPLEMENTATION_STATUS,
        GATE_IDS,
        SAFE_CHECK_IDS,
        affected_gates_for_surfaces,
        required_checks_for,
        required_review_nodes_for,
        validate_revision_scope,
    )
    from .check_manual_attestation import validate_manual_attestation
    from .check_review_bindings import validate_review_bindings
    from .identity_contract import validate_human_owner, validate_manifest_registry
except ImportError:  # pragma: no cover
    from gate_contract import (
        CHANGE_LEVELS,
        CHANGE_SURFACES,
        CHECK_IMPLEMENTATION_STATUS,
        GATE_IDS,
        SAFE_CHECK_IDS,
        affected_gates_for_surfaces,
        required_checks_for,
        required_review_nodes_for,
        validate_revision_scope,
    )
    from check_manual_attestation import validate_manual_attestation
    from check_review_bindings import validate_review_bindings
    from identity_contract import validate_human_owner, validate_manifest_registry


HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def load_yaml(path: Path) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("missing PyYAML; install requirements-dev.txt") from exc
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a mapping")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative_path(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    value = raw.replace("\\", "/")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
        return None
    return str(path)


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _check_file_hash(
    workspace: Path,
    raw_path: object,
    expected: object,
    *,
    label: str,
    required_root: Path | None = None,
    errors: list[str],
) -> None:
    relative = _relative_path(raw_path)
    if relative is None:
        errors.append(f"{label} must be a safe relative path")
        return
    if not isinstance(expected, str) or not HEX64.fullmatch(expected):
        errors.append(f"{label} must have a valid SHA-256")
        return
    path = (workspace / relative).resolve()
    if not _inside(workspace.resolve(), path):
        errors.append(f"{label} project manifest escapes workspace")
        return None
    if required_root is not None and not _inside(required_root, path):
        errors.append(f"{label} escapes evidence_root: {relative}")
    if not path.is_file():
        errors.append(f"{label} does not exist: {relative}")
        return
    actual = sha256_file(path)
    if actual.lower() != expected.lower():
        errors.append(f"{label} hash mismatch: {relative}")


def _same_list(left: object, right: object) -> bool:
    return list(left or []) == list(right or [])


def _timestamp(value: object, label: str, errors: list[str]) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{label} is required")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        errors.append(f"{label} must be ISO-8601")
        return None
    if parsed.tzinfo is None:
        errors.append(f"{label} must include a timezone")
        return None
    return parsed.astimezone(timezone.utc)


def _load_manifest_for_record(
    record: dict,
    *,
    workspace: Path | None,
    errors: list[str],
    label: str,
) -> dict | None:
    raw_path = record.get("project_manifest_path")
    raw_hash = record.get("project_manifest_sha256")
    if workspace is None:
        errors.append(f"{label} requires a workspace to verify the project manifest")
        return None
    relative = _relative_path(raw_path)
    if relative is None:
        errors.append(f"{label}.project_manifest_path must be a safe relative path")
        return None
    if not isinstance(raw_hash, str) or not HEX64.fullmatch(raw_hash):
        errors.append(f"{label}.project_manifest_sha256 is invalid")
        return None
    path = workspace / relative
    if not path.is_file():
        errors.append(f"{label} project manifest does not exist: {relative}")
        return None
    if sha256_file(path).lower() != raw_hash.lower():
        errors.append(f"{label} project manifest hash mismatch")
        return None
    try:
        manifest = load_yaml(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{label} project manifest cannot be parsed: {exc}")
        return None
    validate_manifest_registry(manifest, errors)
    if manifest.get("case_id") != record.get("case_id"):
        errors.append(f"{label} project manifest case_id does not match the record")
    return manifest


def _validate_approval_identity(
    impact: dict,
    approval: dict,
    errors: list[str],
    *,
    workspace: Path | None,
    now: datetime | None = None,
) -> None:
    if approval.get("record_type") != "approved_findings":
        errors.append("approval record is not approved_findings")
        return
    if approval.get("status") not in {"approved", "applied"}:
        errors.append("approval record is not active")
    identity_fields = (
        "approval_id", "case_id", "review_id", "revision_id", "base_git_revision", "new_git_revision",
        "change_level", "change_surfaces", "finding_ids", "required_review_nodes", "review_bindings",
        "candidate_submission_pdf", "candidate_pdf_path", "candidate_pdf_sha256", "affected_gates", "gate_impact",
        "executor_id", "project_manifest_path", "project_manifest_sha256",
    )
    for field in identity_fields:
        impact_value = impact.get("source_review_id") if field == "review_id" else impact.get(field)
        if approval.get(field) != impact_value:
            errors.append(f"approval and impact disagree on {field}")
    if not approval.get("allowed_files"):
        errors.append("approved revision must have a non-empty allowed_files list")
    if not approval.get("validation_check_ids"):
        errors.append("approval validation_check_ids cannot be empty")
    if approval.get("validation_commands"):
        errors.append("arbitrary validation_commands are forbidden; use safe check IDs")
    if approval.get("approver_role") != "human_owner":
        errors.append("approval approver_role must be human_owner")
    manifest = _load_manifest_for_record(approval, workspace=workspace, errors=errors, label="approval")
    if manifest is not None:
        validate_human_owner(manifest, approval.get("approver_id"), errors)
    if approval.get("approver_id") and approval.get("approver_id") in {impact.get("executor_id"), impact.get("modified_by")}:
        errors.append("executor or modifier cannot approve its own revision")
    approved_at = _timestamp(approval.get("approved_at"), "approval.approved_at", errors)
    expires_at = _timestamp(approval.get("expires_at"), "approval.expires_at", errors)
    current = now or datetime.now(timezone.utc)
    if approved_at is not None and approved_at > current:
        errors.append("approval.approved_at is in the future")
    if expires_at is not None and expires_at <= current:
        errors.append("approval has expired; fail closed")
    if approved_at is not None and expires_at is not None and expires_at <= approved_at:
        errors.append("approval.expires_at must be after approved_at")


def validate_revision_closure(
    impact: dict,
    validation: dict,
    approval: dict | None = None,
    *,
    workspace: Path | None = None,
    base_ref: str | None = None,
    head_ref: str | None = None,
    verify_git: bool = False,
) -> list[str]:
    """Return all closure errors; an empty list is a proven closure."""

    errors: list[str] = []
    if impact.get("record_type") != "change_impact_record":
        errors.append("invalid change_impact_record")
    if validation.get("record_type") != "revision_validation_record":
        errors.append("invalid revision_validation_record")

    identity_fields = (
        "revision_id", "case_id", "base_git_revision", "new_git_revision", "change_level",
        "change_surfaces", "changed_files", "approval_id", "source_review_id", "finding_ids",
        "executor_id", "project_manifest_path", "project_manifest_sha256",
    )
    for field in identity_fields:
        if impact.get(field) != validation.get(field):
            errors.append(f"impact and validation disagree on {field}")
    if impact.get("modified_by") != validation.get("modifier_id"):
        errors.append("impact and validation disagree on modifier identity")
    if not impact.get("changed_files"):
        errors.append("change impact record has no changed_files")
    if not validation.get("changed_files"):
        errors.append("validation record has no changed_files")
    if not isinstance(validation.get("closure_id"), str) or not validation.get("closure_id", "").strip():
        errors.append("closure_id is required")

    change_level = impact.get("change_level")
    surfaces = list(impact.get("change_surfaces") or [])
    invalid_surfaces = set(surfaces).difference(CHANGE_SURFACES)
    if not surfaces:
        errors.append("change_surfaces cannot be empty")
    if invalid_surfaces:
        errors.append(f"unknown change surfaces: {sorted(invalid_surfaces)}")
    if change_level not in CHANGE_LEVELS:
        errors.append("change_level must be R0, R1, R2, or R3")

    affected_gates = list(impact.get("affected_gates") or [])
    gate_impact = impact.get("gate_impact")
    scope_ok, scope_message = validate_revision_scope(
        change_level,
        affected_gates,
        change_surfaces=surfaces,
        gate_impact=gate_impact,
    )
    if not scope_ok:
        errors.append(scope_message)

    canonical_gates: list[str] = []
    canonical_checks: list[str] = []
    canonical_reviews: list[str] = []
    if change_level in CHANGE_LEVELS and surfaces:
        try:
            canonical_gates = affected_gates_for_surfaces(surfaces)
            canonical_checks = required_checks_for(
                change_level,
                impact.get("changed_files") or [],
                change_surfaces=surfaces,
                candidate_submission_pdf=bool(impact.get("candidate_submission_pdf")),
            )
            canonical_reviews = required_review_nodes_for(surfaces)
        except ValueError as exc:
            errors.append(str(exc))
            canonical_gates, canonical_checks, canonical_reviews = [], [], []
        if affected_gates != canonical_gates:
            errors.append(f"affected_gates do not match declared surfaces: expected {canonical_gates}")
        if list(impact.get("required_checks") or []) != canonical_checks:
            errors.append(f"required_checks do not match declared surfaces: expected {canonical_checks}")
        if list(impact.get("required_review_nodes") or []) != canonical_reviews:
            errors.append(f"required_review_nodes do not match declared surfaces: expected {canonical_reviews}")
        if list(validation.get("required_review_nodes") or []) != canonical_reviews:
            errors.append(f"validation required_review_nodes do not match declared surfaces: expected {canonical_reviews}")

    required = list(impact.get("required_checks") or [])
    if not required:
        errors.append("required_checks cannot be empty")
    unsafe = set(required).difference(SAFE_CHECK_IDS)
    if unsafe:
        errors.append(f"unknown or unsafe check IDs: {sorted(unsafe)}")
    if "executed_checks" in validation or "check_exit_codes" in validation or "check_outputs" in validation:
        errors.append("legacy hand-filled check evidence fields are forbidden")
    if "validation_commands" in validation:
        errors.append("validation_commands are forbidden; use safe check IDs")

    check_results = validation.get("check_results")
    if not isinstance(check_results, list) or not check_results:
        errors.append("check_results are required")
        check_results = []
    result_ids = [item.get("check_id") for item in check_results if isinstance(item, dict)]
    if len(result_ids) != len(set(result_ids)):
        errors.append("check_results contain duplicate check IDs")
    if set(result_ids) != set(required):
        errors.append(f"check_results must exactly cover required checks: required={sorted(required)} actual={sorted(set(result_ids))}")
    if any(check not in SAFE_CHECK_IDS for check in result_ids):
        errors.append("check_results contain unknown or unsafe check IDs")

    needs_identity_registry = bool(impact.get("required_review_nodes")) or any(
        CHECK_IMPLEMENTATION_STATUS.get(check_id) == "manual_required" for check_id in required
    ) or approval is not None
    if workspace is not None and (needs_identity_registry or validation.get("project_manifest_path") is not None):
        manifest = _load_manifest_for_record(validation, workspace=workspace, errors=errors, label="validation")
    else:
        manifest = None
    if validation.get("project_manifest_path") != impact.get("project_manifest_path") or validation.get("project_manifest_sha256") != impact.get("project_manifest_sha256"):
        errors.append("impact and validation project manifest binding differs")
    if validation.get("review_bindings") != impact.get("review_bindings"):
        errors.append("impact and validation review_bindings differ")
    review_errors = validate_review_bindings(
        validation.get("review_bindings"),
        list(impact.get("required_review_nodes") or []),
        case_id=str(impact.get("case_id", "")),
        revision_id=str(impact.get("revision_id", "")),
        workspace=workspace,
        manifest=manifest,
    ) if workspace is not None else ["workspace is required to validate review bindings"]
    if needs_identity_registry and manifest is None:
        review_errors.append("manual or critical review evidence requires a frozen project manifest")
    errors.extend(review_errors)

    evidence_root: Path | None = None
    if workspace is None:
        errors.append("workspace is required to verify logs and artifact hashes")
    else:
        relative_root = _relative_path(validation.get("evidence_root"))
        if relative_root is None:
            errors.append("evidence_root must be a safe relative path")
        else:
            evidence_root = (workspace / relative_root).resolve()
            if not _inside(workspace.resolve(), evidence_root):
                errors.append("evidence_root escapes workspace")
            elif not evidence_root.is_dir():
                errors.append(f"evidence_root does not exist: {relative_root}")

        runner_script = _relative_path(validation.get("runner_script"))
        if runner_script is None:
            errors.append("runner_script must be a safe relative path")
        elif not (workspace / runner_script).is_file():
            errors.append(f"runner_script does not exist: {runner_script}")
        else:
            expected = validation.get("runner_script_sha256")
            if not isinstance(expected, str) or not HEX64.fullmatch(expected):
                errors.append("runner_script_sha256 is missing or invalid")
            elif sha256_file(workspace / runner_script).lower() != expected.lower():
                errors.append("runner_script_sha256 does not match the trusted runner")
    if validation.get("runner_id") != "trusted_check_runner":
        errors.append("runner_id must be trusted_check_runner")
    if not validation.get("runner_version"):
        errors.append("runner_version is required")
    if not validation.get("execution_started_at") or not validation.get("execution_finished_at"):
        errors.append("execution timestamps are required")

    implementation_errors: list[str] = []
    if workspace is not None:
        for item in check_results:
            if not isinstance(item, dict):
                errors.append("each check_result must be an object")
                continue
            check_id = item.get("check_id")
            if check_id not in required:
                continue
            expected_implementation = CHECK_IMPLEMENTATION_STATUS.get(check_id)
            status = item.get("status")
            kind = item.get("execution_kind")
            if status != "passed":
                implementation_errors.append(f"required check failed or is not proven: {check_id}")
            if kind == "trusted_runner":
                if expected_implementation != "implemented":
                    implementation_errors.append(f"manual-required check cannot be trusted-run as passed: {check_id}")
                if item.get("executor") != "trusted_check_runner":
                    implementation_errors.append(f"trusted check has invalid executor: {check_id}")
                if item.get("exit_code") != 0:
                    implementation_errors.append(f"trusted check has nonzero exit code: {check_id}")
                if evidence_root is not None:
                    _check_file_hash(workspace, item.get("stdout_path"), item.get("stdout_sha256"), label=f"{check_id} stdout", required_root=evidence_root, errors=errors)
                    _check_file_hash(workspace, item.get("stderr_path"), item.get("stderr_sha256"), label=f"{check_id} stderr", required_root=evidence_root, errors=errors)
                    for path, expected in (item.get("artifact_hashes") or {}).items():
                        _check_file_hash(workspace, path, expected, label=f"{check_id} artifact", errors=errors)
            elif kind == "human_attestation":
                if expected_implementation != "manual_required":
                    implementation_errors.append(f"implemented check cannot be replaced by human attestation: {check_id}")
                _check_file_hash(workspace, item.get("stdout_path"), item.get("stdout_sha256"), label=f"{check_id} stdout", required_root=evidence_root, errors=errors)
                _check_file_hash(workspace, item.get("stderr_path"), item.get("stderr_sha256"), label=f"{check_id} stderr", required_root=evidence_root, errors=errors)
                _check_file_hash(workspace, item.get("attestation_path"), item.get("attestation_sha256"), label=f"{check_id} attestation", errors=errors)
                if not isinstance(item.get("attestation_id"), str) or not item.get("attestation_id").strip():
                    implementation_errors.append(f"manual-required check has no structured attestation_id: {check_id}")
                else:
                    attestation_path = _relative_path(item.get("attestation_path"))
                    if attestation_path and manifest is not None and (workspace / attestation_path).is_file():
                        try:
                            attestation = load_yaml(workspace / attestation_path)
                            attestation_errors = validate_manual_attestation(
                                attestation,
                                manifest=manifest,
                                workspace=workspace,
                                expected_case_id=str(impact.get("case_id", "")),
                                expected_revision_id=str(impact.get("revision_id", "")),
                                expected_check_id=str(check_id),
                                expected_source_review_id=impact.get("source_review_id"),
                                executor_id=str(impact.get("executor_id", "")),
                                modifier_id=str(impact.get("modified_by", "")),
                            )
                            if attestation.get("attestation_id") != item.get("attestation_id"):
                                attestation_errors.append(f"{check_id} attestation_id does not match check result")
                            errors.extend(attestation_errors)
                        except Exception as exc:  # noqa: BLE001
                            errors.append(f"{check_id} structured manual attestation cannot be read: {exc}")
            else:
                implementation_errors.append(f"check has unknown execution_kind: {check_id}")
    errors.extend(implementation_errors)

    if workspace is not None:
        for path, expected in (validation.get("output_hashes") or {}).items():
            _check_file_hash(workspace, path, expected, label="output artifact", errors=errors)
        for path, expected in (impact.get("after_hashes") or {}).items():
            if expected is not None and (not isinstance(expected, str) or not HEX64.fullmatch(expected)):
                errors.append(f"invalid after hash: {path}")
        candidate_path = impact.get("candidate_pdf_path")
        candidate_hash = impact.get("candidate_pdf_sha256")
        if impact.get("candidate_submission_pdf"):
            _check_file_hash(workspace, candidate_path, candidate_hash, label="candidate PDF", errors=errors)
        elif candidate_path is not None or candidate_hash is not None:
            errors.append("candidate PDF path/hash must be null when candidate_submission_pdf is false")

    if validation.get("validation_status") != "passed":
        errors.append("validation_status is not passed")
    unresolved = validation.get("unresolved_findings") or []
    for index, item in enumerate(unresolved):
        if not isinstance(item, dict) or item.get("severity") not in {"P0", "P1", "P2", "P3"}:
            errors.append(f"unresolved_findings[{index}] must be structured with severity")
    if any(isinstance(item, dict) and item.get("severity") in {"P0", "P1"} for item in unresolved):
        errors.append("unresolved P0/P1 findings remain")

    affected_experiments = impact.get("affected_experiments") or []
    new_experiments = validation.get("new_experiment_ids") or []
    if change_level == "R0" and (affected_experiments or new_experiments):
        errors.append("R0 cannot claim affected experiments or new experiment IDs")
    if change_level in {"R2", "R3"} and affected_experiments:
        if not new_experiments:
            errors.append("R2/R3 affected experiments require new experiment records")
        if not validation.get("output_hashes"):
            errors.append("R2/R3 affected experiments require output hashes")
    status_updates = {item.get("claim_id"): item.get("status") for item in (validation.get("claim_status_updates") or []) if isinstance(item, dict)}
    for claim_id in impact.get("affected_claims") or []:
        if status_updates.get(claim_id) not in {"downgraded", "revalidated"}:
            errors.append(f"affected claim lacks downgrade or revalidation: {claim_id}")

    for finding in validation.get("closed_findings") or []:
        if not isinstance(finding, dict):
            errors.append("closed_findings entries must be objects")
            continue
        if finding.get("source_review_id") != impact.get("source_review_id"):
            errors.append(f"finding source review mismatch: {finding.get('finding_id')}")
        if finding.get("finding_id") not in set(impact.get("finding_ids") or []):
            errors.append(f"closed finding is not in the approved finding set: {finding.get('finding_id')}")
        if finding.get("severity") in {"P0", "P1"}:
            raised_id = finding.get("raised_by_id")
            modified_id = finding.get("modified_by_id")
            closed_id = finding.get("closed_by_id")
            if closed_id in {raised_id, modified_id}:
                errors.append(f"high-risk finding must be closed by a third identity: {finding.get('finding_id')}")
            if finding.get("closed_by") not in {"human", "human_owner", "independent_adversary"}:
                errors.append(f"high-risk finding needs human or independent closure: {finding.get('finding_id')}")

    if approval is not None:
        _validate_approval_identity(impact, approval, errors, workspace=workspace)
        if approval.get("validation_check_ids") != required:
            errors.append("approval validation_check_ids must equal required_checks")
        if approval.get("allowed_files") and not all(_relative_path(path) for path in approval["allowed_files"]):
            errors.append("approval allowed_files contains an unsafe path")

    if verify_git:
        if workspace is None or not base_ref or not head_ref:
            errors.append("verify_git requires workspace, base_ref and head_ref")
        else:
            actual_base = git_revision_at(workspace, base_ref)
            actual_head = git_revision_at(workspace, head_ref)
            if actual_base != impact.get("base_git_revision"):
                errors.append("base_git_revision does not match base_ref")
            if actual_head != impact.get("new_git_revision"):
                errors.append("new_git_revision does not match head_ref")

    return sorted(set(errors))


def git_revision_at(workspace: Path, ref: str) -> str | None:
    import subprocess

    result = subprocess.run(["git", "-C", str(workspace), "rev-parse", ref], text=True, capture_output=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("change_impact_record", type=Path)
    parser.add_argument("revision_validation_record", type=Path)
    parser.add_argument("--approved-findings", type=Path)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--base-ref")
    parser.add_argument("--head-ref")
    parser.add_argument("--verify-git", action="store_true")
    args = parser.parse_args()
    try:
        impact = load_yaml(args.change_impact_record)
        validation = load_yaml(args.revision_validation_record)
        approval = load_yaml(args.approved_findings) if args.approved_findings else None
        errors = validate_revision_closure(
            impact,
            validation,
            approval,
            workspace=args.workspace.resolve(),
            base_ref=args.base_ref,
            head_ref=args.head_ref,
            verify_git=args.verify_git,
        )
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
