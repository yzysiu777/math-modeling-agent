"""Validate structured human evidence for a manual-required check."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

try:
    from .check_evidence_graph import load_record
    from .identity_contract import validate_human_owner, validate_independent_reviewer, validate_manifest_registry
except ImportError:  # pragma: no cover
    from check_evidence_graph import load_record
    from identity_contract import validate_human_owner, validate_independent_reviewer, validate_manifest_registry


HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
MANUAL_ROLES = {"human_owner", "independent_adversary", "independent_reviewer"}


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
    return str(path)


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


def validate_manual_attestation(
    attestation: dict,
    *,
    manifest: dict | None,
    workspace: Path,
    expected_case_id: str,
    expected_revision_id: str,
    expected_check_id: str,
    expected_source_review_id: str | None,
    executor_id: str,
    modifier_id: str,
    now: datetime | None = None,
) -> list[str]:
    errors: list[str] = []
    if attestation.get("record_type") != "manual_attestation":
        errors.append("manual evidence must be a structured manual_attestation record")
        return errors
    fields = ("attestation_id", "case_id", "revision_id", "check_id", "attestor_role", "attestor_id", "source_review_id", "decision", "executor_id", "modifier_id")
    for field in fields:
        if not isinstance(attestation.get(field), str) or not attestation[field].strip():
            errors.append(f"manual_attestation.{field} is required")
    for field, expected in (
        ("case_id", expected_case_id),
        ("revision_id", expected_revision_id),
        ("check_id", expected_check_id),
        ("source_review_id", expected_source_review_id),
    ):
        if expected is not None and attestation.get(field) != expected:
            errors.append(f"manual_attestation.{field} does not match the active revision")
    if attestation.get("attestor_role") not in MANUAL_ROLES:
        errors.append("attestor_role must be a registered human_owner or independent reviewer")
    if attestation.get("executor_id") != executor_id or attestation.get("modifier_id") != modifier_id:
        errors.append("manual_attestation executor/modifier identity does not match the active revision")
    attestor_id = attestation.get("attestor_id")
    if attestor_id in {executor_id, modifier_id}:
        errors.append("manual attestor must be independent of executor and modifier")
    if manifest is None:
        errors.append("manual_attestation requires a frozen project manifest")
    else:
        validate_manifest_registry(manifest, errors)
        if attestation.get("attestor_role") == "human_owner":
            validate_human_owner(manifest, attestor_id, errors)
        elif attestation.get("attestor_role") in {"independent_adversary", "independent_reviewer"}:
            validate_independent_reviewer(manifest, attestor_id, attestation.get("attestor_role"), errors)
    signed_at = _timestamp(attestation.get("signed_at"), "signed_at", errors)
    if signed_at is not None and signed_at > (now or datetime.now(timezone.utc)):
        errors.append("signed_at cannot be in the future")
    if attestation.get("decision") not in {"passed", "accepted"}:
        errors.append("manual_attestation decision must be passed or accepted")
    artifacts = attestation.get("evidence_artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        errors.append("evidence_artifacts must contain at least one hashed artifact")
        artifacts = []
    artifact_ids: set[str] = set()
    for index, artifact in enumerate(artifacts):
        if not isinstance(artifact, dict):
            errors.append(f"evidence_artifacts[{index}] must be an object")
            continue
        artifact_id = artifact.get("artifact_id")
        if not isinstance(artifact_id, str) or not artifact_id.strip() or artifact_id in artifact_ids:
            errors.append(f"evidence_artifacts[{index}] has a duplicate or empty artifact_id")
        artifact_ids.add(str(artifact_id))
        relative = safe_relative(artifact.get("path"))
        expected_hash = artifact.get("sha256")
        if relative is None:
            errors.append(f"evidence_artifacts[{index}] path is unsafe")
            continue
        if not isinstance(expected_hash, str) or not HEX64.fullmatch(expected_hash):
            errors.append(f"evidence_artifacts[{index}] sha256 is invalid")
            continue
        path = (workspace / relative).resolve()
        try:
            path.relative_to(workspace.resolve())
        except ValueError:
            errors.append(f"evidence_artifacts[{index}] escapes workspace")
            continue
        if not path.is_file():
            errors.append(f"evidence artifact does not exist: {relative}")
        elif sha256_file(path).lower() != expected_hash.lower():
            errors.append(f"evidence artifact hash mismatch: {relative}")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("attestation", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--revision-id", required=True)
    parser.add_argument("--check-id", required=True)
    parser.add_argument("--source-review-id", required=True)
    parser.add_argument("--executor-id", required=True)
    parser.add_argument("--modifier-id", required=True)
    args = parser.parse_args()
    try:
        errors = validate_manual_attestation(
            load_record(args.attestation),
            manifest=load_record(args.manifest),
            workspace=args.workspace.resolve(),
            expected_case_id=args.case_id,
            expected_revision_id=args.revision_id,
            expected_check_id=args.check_id,
            expected_source_review_id=args.source_review_id,
            executor_id=args.executor_id,
            modifier_id=args.modifier_id,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL manual attestation: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("FAIL manual attestation")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS manual attestation")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
