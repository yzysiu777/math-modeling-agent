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
    from gate_contract import CHANGE_LEVELS, CHANGE_SURFACES, SAFE_CHECK_IDS, affected_gates_for_surfaces, change_level_for_surfaces, required_checks_for, required_review_nodes_for


HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
ACTIVE_STATUSES = {"executing", "review_ready"}
RESULT_STATUSES = {"review_ready", "accepted", "revision_requested", "blocked"}


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


def validate_work_item(
    item: dict,
    *,
    workspace: Path | None = None,
    source_ref: str | None = None,
    result_ref: str | None = None,
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
    unresolved = item.get("unresolved_items") or []
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
    args = parser.parse_args()
    try:
        items = [load_record(path) for path in args.work_item]
        errors = validate_work_item_set(
            items,
            workspace=args.workspace.resolve() if args.workspace else None,
            source_ref=args.source_ref,
            result_ref=args.result_ref,
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
