"""Validate the lightweight case-level team collaboration contract."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath

try:
    from .check_evidence_graph import load_record
    from .check_revision_closure import validate_revision_closure
    from .check_review_bindings import validate_review_input_bindings
    from .check_review_independence import validate_review_record
    from .git_contract import validate_revision_pair
    from .identity_contract import validate_independent_reviewer, validate_manifest_registry
    from .gate_contract import (
        CHANGE_LEVELS,
        CHANGE_SURFACES,
        SAFE_CHECK_IDS,
        affected_gates_for_surfaces,
        change_level_for_surfaces,
        required_checks_for,
        required_review_nodes_for,
    )
except ImportError:  # pragma: no cover
    from check_evidence_graph import load_record
    from check_revision_closure import validate_revision_closure
    from check_review_bindings import validate_review_input_bindings
    from check_review_independence import validate_review_record
    from git_contract import validate_revision_pair
    from identity_contract import validate_independent_reviewer, validate_manifest_registry
    from gate_contract import CHANGE_LEVELS, CHANGE_SURFACES, SAFE_CHECK_IDS, affected_gates_for_surfaces, change_level_for_surfaces, required_checks_for, required_review_nodes_for


HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
ACTIVE_STATUSES = {"executing", "review_ready"}
RESULT_STATUSES = {"review_ready", "accepted", "revision_requested", "blocked"}
WORK_ITEM_TRANSITIONS = {
    "proposed": {"approved"},
    "approved": {"executing"},
    "executing": {"review_ready"},
    "review_ready": {"accepted", "revision_requested", "blocked"},
    "revision_requested": {"executing", "blocked"},
    "blocked": {"approved"},
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_relative(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
        return None
    if "agent_协作控制台" in path.parts:
        return None
    return str(path)


def _files_overlap(left: str, right: str) -> bool:
    a, b = left.rstrip("/"), right.rstrip("/")
    return a == b or a.startswith(b + "/") or b.startswith(a + "/")


def validate_work_item_transition(from_state: str, to_state: str) -> list[str]:
    if from_state not in WORK_ITEM_TRANSITIONS:
        return [f"unknown work-item state transition: {from_state} -> {to_state}"]
    if to_state not in WORK_ITEM_TRANSITIONS[from_state]:
        return [f"illegal work-item transition: {from_state} -> {to_state}"]
    return []


def _verify_hashed_file(workspace: Path | None, raw_path: object, expected_hash: object, label: str, errors: list[str]) -> Path | None:
    path = safe_relative(raw_path)
    if path is None:
        errors.append(f"{label} path must be safe and relative")
        return None
    if not isinstance(expected_hash, str) or not HEX64.fullmatch(expected_hash):
        errors.append(f"{label} hash is invalid")
        return None
    if workspace is None:
        errors.append(f"{label} requires a workspace")
        return None
    candidate = (workspace / path).resolve()
    try:
        candidate.relative_to(workspace.resolve())
    except ValueError:
        errors.append(f"{label} path escapes workspace")
        return None
    if not candidate.is_file():
        errors.append(f"{label} file does not exist: {path}")
        return None
    if sha256_file(candidate).lower() != expected_hash.lower():
        errors.append(f"{label} hash mismatch: {path}")
        return None
    return candidate


def _load_hashed_record(
    workspace: Path,
    raw_path: object,
    expected_hash: object,
    label: str,
    errors: list[str],
) -> dict | None:
    """Load a record only after verifying its confined path and SHA-256."""

    path = _verify_hashed_file(workspace, raw_path, expected_hash, label, errors)
    if path is None:
        return None
    try:
        record = load_record(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{label} cannot be parsed: {exc}")
        return None
    if not isinstance(record, dict):
        errors.append(f"{label} must contain a mapping")
        return None
    return record


def _load_manifest_from_validation(record: dict, workspace: Path, errors: list[str]) -> dict | None:
    path = safe_relative(record.get("project_manifest_path"))
    expected = record.get("project_manifest_sha256")
    if path is None or not isinstance(expected, str) or not HEX64.fullmatch(expected):
        return None
    candidate = (workspace / path).resolve()
    try:
        candidate.relative_to(workspace.resolve())
    except ValueError:
        return None
    if not candidate.is_file() or sha256_file(candidate).lower() != expected.lower():
        return None
    try:
        manifest = load_record(candidate)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"trusted validation record manifest cannot be parsed: {exc}")
        return None
    if not isinstance(manifest, dict):
        errors.append("trusted validation record manifest must contain a mapping")
        return None
    validate_manifest_registry(manifest, errors)
    return manifest


def _validate_trusted_validation_record(item: dict, workspace: Path, errors: list[str]) -> dict | None:
    path = _verify_hashed_file(
        workspace,
        item.get("trusted_validation_record_path"),
        item.get("trusted_validation_record_sha256"),
        "trusted validation record",
        errors,
    )
    if path is None:
        return None
    try:
        record = load_record(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"trusted validation record cannot be parsed: {exc}")
        return None
    if record.get("record_type") != "revision_validation_record":
        errors.append("trusted validation record has the wrong record_type")
    if record.get("closure_id") != item.get("trusted_validation_record_id"):
        errors.append("trusted validation record ID does not match the work item")
    for field in ("case_id", "revision_id"):
        if record.get(field) != item.get(field):
            errors.append(f"trusted validation record {field} does not match the work item")
    if record.get("new_git_revision") != item.get("result_git_revision"):
        errors.append("trusted validation record new_git_revision does not match result_git_revision")
    if record.get("base_git_revision") != item.get("source_git_revision"):
        errors.append("trusted validation record base_git_revision does not match source_git_revision")
    if record.get("change_level") != item.get("change_level") or record.get("change_surfaces") != item.get("change_surfaces"):
        errors.append("trusted validation record change scope does not match the work item")
    if not record.get("runner_version") or not record.get("execution_started_at") or not record.get("execution_finished_at"):
        errors.append("trusted validation record lacks execution metadata")
    if record.get("runner_id") != "trusted_check_runner":
        errors.append("accepted work item requires a trusted_check_runner record")
    if record.get("validation_status") != "passed":
        errors.append("trusted validation record is not passed")
    if not record.get("executor_id"):
        errors.append("trusted validation record executor_id is required")
    elif record.get("executor_id") != item.get("executor_id"):
        errors.append("trusted validation record executor_id does not match the work item")
    if not record.get("modifier_id"):
        errors.append("trusted validation record modifier_id is required")
    runner_path = safe_relative(record.get("runner_script"))
    if runner_path is None or not isinstance(record.get("runner_script_sha256"), str) or not HEX64.fullmatch(record["runner_script_sha256"]):
        errors.append("trusted validation record has no valid runner script binding")
    elif not (workspace / runner_path).is_file() or sha256_file(workspace / runner_path).lower() != record["runner_script_sha256"].lower():
        errors.append("trusted validation record runner script binding is invalid")
    evidence_root = safe_relative(record.get("evidence_root"))
    if evidence_root is None or not (workspace / evidence_root).is_dir():
        errors.append("trusted validation record evidence_root is missing")
    manifest_path = safe_relative(record.get("project_manifest_path"))
    manifest: dict | None = None
    if manifest_path is None:
        errors.append("trusted validation record requires a frozen project manifest")
    else:
        manifest_hash = record.get("project_manifest_sha256")
        manifest_file = (workspace / manifest_path).resolve()
        try:
            manifest_file.relative_to(workspace.resolve())
        except ValueError:
            errors.append("trusted validation record project manifest escapes workspace")
            return None
        if not isinstance(manifest_hash, str) or not HEX64.fullmatch(manifest_hash) or not manifest_file.is_file() or sha256_file(manifest_file).lower() != manifest_hash.lower():
            errors.append("trusted validation record project manifest binding is invalid")
        else:
            try:
                manifest = load_record(manifest_file)
                validate_manifest_registry(manifest, errors)
                if manifest.get("case_id") != item.get("case_id"):
                    errors.append("trusted validation record project manifest case_id does not match the work item")
            except Exception as exc:  # noqa: BLE001
                errors.append(f"trusted validation record project manifest cannot be parsed: {exc}")
    required = set(item.get("required_checks") or [])
    results = record.get("check_results") or []
    result_ids = {entry.get("check_id") for entry in results if isinstance(entry, dict)}
    if result_ids != required:
        errors.append("trusted validation record does not cover every required check")
    for entry in results:
        if not isinstance(entry, dict) or entry.get("check_id") not in required:
            continue
        if entry.get("status") != "passed":
            errors.append(f"trusted validation record contains a non-passed check: {entry.get('check_id')}")
        for field, hash_field in (("stdout_path", "stdout_sha256"), ("stderr_path", "stderr_sha256")):
            path = safe_relative(entry.get(field))
            expected = entry.get(hash_field)
            if path is None or not isinstance(expected, str) or not HEX64.fullmatch(expected):
                errors.append(f"trusted validation record has invalid {field}: {entry.get('check_id')}")
            elif not (workspace / path).is_file() or sha256_file(workspace / path).lower() != expected.lower():
                errors.append(f"trusted validation record {field} hash is invalid: {entry.get('check_id')}")
        if entry.get("execution_kind") == "trusted_runner":
            if entry.get("executor") != "trusted_check_runner" or entry.get("exit_code") != 0:
                errors.append(f"trusted validation record trusted check executor/exit is invalid: {entry.get('check_id')}")
        elif entry.get("execution_kind") == "human_attestation":
            if not entry.get("attestation_id"):
                errors.append(f"manual check lacks structured attestation: {entry.get('check_id')}")
            attestation_path = safe_relative(entry.get("attestation_path"))
            attestation_hash = entry.get("attestation_sha256")
            if attestation_path is None or not isinstance(attestation_hash, str) or not HEX64.fullmatch(attestation_hash):
                errors.append(f"manual check has no hashed attestation: {entry.get('check_id')}")
            elif not (workspace / attestation_path).is_file() or sha256_file(workspace / attestation_path).lower() != attestation_hash.lower():
                errors.append(f"manual check attestation hash is invalid: {entry.get('check_id')}")
        else:
            errors.append(f"trusted validation record has unknown execution_kind: {entry.get('check_id')}")
    return manifest


def _validate_independent_verdict(
    item: dict,
    workspace: Path,
    errors: list[str],
    manifest: dict | None,
) -> None:
    path = _verify_hashed_file(
        workspace,
        item.get("review_verdict_path"),
        item.get("review_verdict_sha256"),
        "independent reviewer verdict",
        errors,
    )
    if path is None:
        return
    try:
        record = load_record(path)
    except Exception as exc:  # noqa: BLE001
        errors.append(f"independent reviewer verdict cannot be parsed: {exc}")
        return
    if record.get("review_id") != item.get("review_id"):
        errors.append("review verdict review_id does not match the work item")
    if record.get("case_id") != item.get("case_id"):
        errors.append("review verdict case_id does not match the work item")
    if record.get("target_revision") != item.get("revision_id"):
        errors.append("review verdict target_revision does not match the work item revision")
    if record.get("target_git_revision") != item.get("result_git_revision"):
        errors.append("review verdict target_git_revision does not match the work item result revision")
    if record.get("reviewer_id") != item.get("reviewer_id"):
        errors.append("review verdict reviewer_id does not match the work item")
    if record.get("reviewer_role") != item.get("reviewer_role") or record.get("reviewer_role") not in {"independent_adversary", "independent_reviewer"}:
        errors.append("accepted work item requires an independent reviewer verdict")
    elif manifest is None:
        errors.append("accepted work item requires a frozen project identity registry for its reviewer")
    else:
        validate_independent_reviewer(manifest, record.get("reviewer_id"), record.get("reviewer_role"), errors)
    if record.get("verdict") not in {"PASS", "PASS_WITH_LIMITATIONS"}:
        errors.append("independent reviewer verdict is not passing")
    errors.extend(validate_review_input_bindings(record, workspace, label="independent reviewer verdict"))
    git_errors: list[str] = []
    validate_revision_pair(
        workspace,
        record.get("target_git_revision"),
        record.get("target_git_revision"),
        git_errors,
        require_result_at_head=False,
        label="independent reviewer target Git revision",
    )
    errors.extend(git_errors)
    ok, review_errors = validate_review_record(record)
    if not ok:
        errors.extend(f"invalid independent reviewer verdict: {error}" for error in review_errors)


def validate_work_item(
    item: dict,
    *,
    workspace: Path | None = None,
    source_ref: str | None = None,
    result_ref: str | None = None,
    from_status: str | None = None,
) -> list[str]:
    errors: list[str] = []
    if item.get("record_type") != "work_item":
        errors.append("record_type must be work_item")
    for field in ("work_item_id", "case_id", "source_git_revision", "objective", "executor_id", "reviewer_id", "write_owner_id", "change_level", "revision_id"):
        if not str(item.get(field, "")).strip():
            errors.append(f"{field} is required")
    status = item.get("status")
    if status not in {"proposed", "approved", "executing", "review_ready", "accepted", "revision_requested", "blocked"}:
        errors.append("status is invalid")
    previous_status = item.get("previous_status")
    if from_status is not None:
        if previous_status != from_status:
            errors.append("previous_status does not match the requested transition source")
        else:
            errors.extend(validate_work_item_transition(from_status, status))
    if status == "accepted":
        if previous_status != "review_ready":
            errors.append("accepted work item must transition from review_ready, never directly from proposed")
        else:
            errors.extend(validate_work_item_transition(previous_status, status))
    if "human_frozen" in item:
        errors.append("work item acceptance cannot imply human_frozen")
    if item.get("executor_id") == item.get("reviewer_id"):
        errors.append("self-review is prohibited: executor_id equals reviewer_id")
    if item.get("write_owner_id") != item.get("executor_id"):
        errors.append("exactly one writer is required: write_owner_id must equal executor_id")
    allowed = item.get("allowed_files")
    if not isinstance(allowed, list) or not allowed:
        errors.append("allowed_files must be non-empty")
        allowed = []
    normalized_allowed: list[str] = []
    for raw in allowed:
        normalized = safe_relative(raw)
        if normalized is None:
            errors.append(f"unsafe allowed file path: {raw}")
        else:
            normalized_allowed.append(normalized)

    level = item.get("change_level")
    surfaces = item.get("change_surfaces") or []
    if level not in CHANGE_LEVELS:
        errors.append("change_level must be R0, R1, R2, or R3")
    if not isinstance(surfaces, list) or not surfaces:
        errors.append("change_surfaces must be non-empty")
        surfaces = []
    invalid_surfaces = set(surfaces).difference(CHANGE_SURFACES)
    if invalid_surfaces:
        errors.append(f"unknown change surfaces: {sorted(invalid_surfaces)}")
    if level in CHANGE_LEVELS and not invalid_surfaces and surfaces:
        expected_level_name = change_level_for_surfaces(surfaces)
        if level != expected_level_name:
            errors.append(f"change_level does not match change_surfaces; expected {expected_level_name}")
        expected_gates = affected_gates_for_surfaces(surfaces)
        if item.get("affected_gates") != expected_gates:
            errors.append(f"affected_gates do not match change_surfaces; expected {expected_gates}")
        expected_checks = required_checks_for(
            level,
            normalized_allowed,
            change_surfaces=surfaces,
            candidate_submission_pdf="candidate_pdf" in surfaces,
        )
        if item.get("required_checks") != expected_checks:
            errors.append(f"required_checks do not match change_surfaces; expected {expected_checks}")
        expected_nodes = required_review_nodes_for(surfaces)
        if item.get("required_review_nodes") != expected_nodes:
            errors.append(f"required_review_nodes do not match change_surfaces; expected {expected_nodes}")
    unsafe_checks = set(item.get("required_checks") or []).difference(SAFE_CHECK_IDS)
    if unsafe_checks:
        errors.append(f"unknown or unsafe required checks: {sorted(unsafe_checks)}")

    result_revision = item.get("result_git_revision")
    if status in RESULT_STATUSES and not result_revision:
        errors.append(f"{status} requires result_git_revision")
    if source_ref and item.get("source_git_revision") != source_ref:
        errors.append("source_git_revision does not match source_ref")
    if result_ref and result_revision != result_ref:
        errors.append("result_git_revision does not match result_ref")
    if status == "accepted":
        if not result_revision:
            errors.append("accepted work item requires result_git_revision")
        evidence = item.get("test_evidence") or []
        evidence_ids = [entry.get("check_id") for entry in evidence if isinstance(entry, dict)]
        if set(evidence_ids) != set(item.get("required_checks") or []):
            errors.append("accepted work item test_evidence must cover every required check")
        if len(evidence_ids) != len(set(evidence_ids)):
            errors.append("test_evidence contains duplicate check IDs")
        for entry in evidence:
            if not isinstance(entry, dict):
                errors.append("test_evidence entries must be objects")
                continue
            if entry.get("status") != "passed":
                errors.append(f"accepted work item contains non-passed check: {entry.get('check_id')}")
            if entry.get("check_id") not in SAFE_CHECK_IDS:
                errors.append(f"test evidence uses unknown check: {entry.get('check_id')}")
            path = safe_relative(entry.get("evidence_path"))
            if path is None or not isinstance(entry.get("sha256"), str) or not HEX64.fullmatch(entry["sha256"]):
                errors.append(f"invalid evidence path or SHA-256: {entry.get('check_id')}")
            elif workspace is not None:
                evidence_path = workspace / path
                if not evidence_path.is_file():
                    errors.append(f"test evidence file does not exist: {path}")
                elif sha256_file(evidence_path).lower() != entry["sha256"].lower():
                    errors.append(f"test evidence hash mismatch: {path}")
        if workspace is None:
            errors.append("accepted work item requires a workspace for trusted evidence verification")
        else:
            impact = _load_hashed_record(
                workspace,
                item.get("trusted_change_impact_path"),
                item.get("trusted_change_impact_sha256"),
                "trusted change impact record",
                errors,
            )
            validation = _load_hashed_record(
                workspace,
                item.get("trusted_validation_record_path"),
                item.get("trusted_validation_record_sha256"),
                "trusted validation record",
                errors,
            )
            manifest = None
            if impact is not None and validation is not None:
                if impact.get("record_type") != "change_impact_record":
                    errors.append("trusted change impact record has the wrong record_type")
                if validation.get("record_type") != "revision_validation_record":
                    errors.append("trusted validation record has the wrong record_type")
                for item_field, record_field in (
                    ("case_id", "case_id"),
                    ("revision_id", "revision_id"),
                    ("source_git_revision", "base_git_revision"),
                    ("result_git_revision", "new_git_revision"),
                    ("change_level", "change_level"),
                    ("change_surfaces", "change_surfaces"),
                    ("affected_gates", "affected_gates"),
                    ("affected_claims", "affected_claims"),
                    ("affected_experiments", "affected_experiments"),
                    ("required_checks", "required_checks"),
                    ("required_review_nodes", "required_review_nodes"),
                ):
                    if impact.get(record_field) != item.get(item_field):
                        errors.append(f"trusted change impact {record_field} does not match the work item")
                if validation.get("closure_id") != item.get("trusted_validation_record_id"):
                    errors.append("trusted validation record closure_id does not match the work item")
                git_errors: list[str] = []
                validate_revision_pair(
                    workspace,
                    item.get("source_git_revision"),
                    item.get("result_git_revision"),
                    git_errors,
                    require_result_at_head=True,
                    label="accepted work item",
                )
                errors.extend(git_errors)
                closure_errors = validate_revision_closure(
                    impact,
                    validation,
                    workspace=workspace,
                    base_ref=item.get("source_git_revision"),
                    head_ref="HEAD",
                    verify_git=True,
                )
                errors.extend(f"trusted revision closure: {error}" for error in closure_errors)
                manifest = _load_manifest_from_validation(validation, workspace, errors)
            _validate_independent_verdict(item, workspace, errors, manifest)
    unresolved = item.get("unresolved_items") or []
    for index, entry in enumerate(unresolved):
        if not isinstance(entry, dict) or entry.get("severity") not in {"P0", "P1", "P2", "P3"}:
            errors.append(f"unresolved_items[{index}] must be structured with severity")
    if status == "accepted" and any(isinstance(entry, dict) and entry.get("severity") in {"P0", "P1"} for entry in unresolved):
        errors.append("accepted work item cannot contain unresolved P0/P1 items")
    return sorted(set(errors))


def validate_work_item_set(items: list[dict], **kwargs) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    active: list[tuple[str, str, str]] = []
    for item in items:
        item_errors = validate_work_item(item, **kwargs)
        errors.extend(f"{item.get('work_item_id', '<unknown>')}: {error}" for error in item_errors)
        item_id = item.get("work_item_id")
        if item_id in ids:
            errors.append(f"duplicate work_item_id: {item_id}")
        ids.add(item_id)
        if item.get("status") in ACTIVE_STATUSES:
            for path in item.get("allowed_files") or []:
                normalized = safe_relative(path)
                if normalized:
                    active.append((str(item_id), normalized, str(item.get("write_owner_id"))))
    for index, (left_id, left_path, _) in enumerate(active):
        for right_id, right_path, _ in active[index + 1:]:
            if left_id != right_id and _files_overlap(left_path, right_path):
                errors.append(f"overlapping active write scopes: {left_id}:{left_path} and {right_id}:{right_path}")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("work_item", type=Path, nargs="+")
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--source-ref")
    parser.add_argument("--result-ref")
    parser.add_argument("--from-status")
    args = parser.parse_args()
    try:
        items = [load_record(path) for path in args.work_item]
        errors = validate_work_item_set(
            items,
            workspace=args.workspace.resolve() if args.workspace else None,
            source_ref=args.source_ref,
            result_ref=args.result_ref,
            from_status=args.from_status,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL work item: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("FAIL work item contract")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS work item contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
