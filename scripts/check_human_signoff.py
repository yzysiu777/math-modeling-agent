"""Validate the human-only final freeze record (G12)."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

try:
    from .check_evidence_graph import load_record
    from .gate_contract import GATE_IDS
    from .identity_contract import validate_human_owner, validate_manifest_registry
except ImportError:  # pragma: no cover
    from check_evidence_graph import load_record
    from gate_contract import GATE_IDS
    from identity_contract import validate_human_owner, validate_manifest_registry


HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
        return None
    return str(path)


def resolve_head_revision(workspace: Path) -> str | None:
    result = subprocess.run(
        ["git", "-C", str(workspace), "rev-parse", "HEAD"],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def validate_human_signoff(
    signoff: dict,
    *,
    actor: str | None = None,
    current_revision: str | None = None,
    workspace: Path | None = None,
    manifest: dict | None = None,
) -> list[str]:
    errors: list[str] = []
    if signoff.get("record_type") != "human_signoff":
        errors.append("record_type must be human_signoff")
    for field in ("signoff_id", "case_id", "signer", "signer_id", "signer_role", "actor", "signed_at", "git_revision", "pdf_path", "pdf_sha256"):
        if not str(signoff.get(field, "")).strip():
            errors.append(f"{field} is required")
    if signoff.get("signer_role") != "human_owner":
        errors.append("signer_role must be human_owner")
    if actor and signoff.get("actor") != actor:
        errors.append("signoff actor does not match transition actor")
    if signoff.get("signer_id") != signoff.get("actor"):
        errors.append("signer_id must match actor")
    if manifest is None:
        errors.append("G12 requires the frozen project manifest identity registry")
    else:
        validate_manifest_registry(manifest, errors)
        if manifest.get("case_id") != signoff.get("case_id"):
            errors.append("project manifest case_id does not match signoff case_id")
        validate_human_owner(manifest, signoff.get("signer_id"), errors)
        if signoff.get("actor") in {"human", "human_owner", "codex", "claude", "codex-agent"}:
            errors.append("actor must be a registered human identity, not a role or model name")
    signed_at = str(signoff.get("signed_at", ""))
    if signed_at.startswith("YYYY-"):
        errors.append("signed_at is still a placeholder")
    else:
        try:
            datetime.fromisoformat(signed_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append("signed_at must be an ISO-8601 timestamp")
    resolved_revision = current_revision
    if resolved_revision is None and workspace is not None:
        resolved_revision = resolve_head_revision(workspace)
    if not resolved_revision:
        errors.append("current Git revision is required and must be resolved from HEAD")
    elif signoff.get("git_revision") != resolved_revision:
        errors.append("signoff git_revision does not match current revision resolved from HEAD")
    approved = signoff.get("approved_gates")
    if approved != list(GATE_IDS):
        errors.append(f"approved_gates must equal {list(GATE_IDS)}")
    if signoff.get("decision") not in {"approved", "approved_with_limits"}:
        errors.append("G12 requires an approved decision")
    unresolved = signoff.get("unresolved_findings") or []
    for index, item in enumerate(unresolved):
        if not isinstance(item, dict) or item.get("severity") not in {"P0", "P1", "P2", "P3"}:
            errors.append(f"unresolved_findings[{index}] must be structured with severity")
    if any(isinstance(item, dict) and item.get("severity") in {"P0", "P1"} for item in unresolved):
        errors.append("G12 cannot freeze with an open P0/P1 finding")
    open_limitations = signoff.get("open_limitations") or []
    if any(isinstance(item, dict) and item.get("severity") in {"P0", "P1"} for item in open_limitations):
        errors.append("G12 cannot freeze with an open P0/P1 limitation")
    for field in ("review_scope", "checked_items", "not_checked_items", "expertise_limitations"):
        if not isinstance(signoff.get(field), list) or not signoff[field]:
            errors.append(f"{field} must be non-empty")
    manifest_relative = _safe_relative(signoff.get("project_manifest_path"))
    if manifest_relative is None:
        errors.append("project_manifest_path must be a safe relative path")
    elif not isinstance(signoff.get("project_manifest_sha256"), str) or not HEX64.fullmatch(signoff["project_manifest_sha256"]):
        errors.append("project_manifest_sha256 is invalid")
    elif workspace is not None:
        manifest_file = (workspace / manifest_relative).resolve()
        try:
            manifest_file.relative_to(workspace.resolve())
        except ValueError:
            errors.append("project_manifest_path escapes workspace")
        else:
            if not manifest_file.is_file():
                errors.append(f"project manifest does not exist: {manifest_relative}")
            elif sha256_file(manifest_file).lower() != signoff["project_manifest_sha256"].lower():
                errors.append("project manifest hash does not match signoff")
    relative = _safe_relative(signoff.get("pdf_path"))
    if relative is None:
        errors.append("pdf_path must be a safe relative path")
    elif not isinstance(signoff.get("pdf_sha256"), str) or not HEX64.fullmatch(signoff["pdf_sha256"]):
        errors.append("pdf_sha256 is invalid")
    elif workspace is None:
        errors.append("workspace is required to verify the final PDF")
    else:
        pdf = (workspace / relative).resolve()
        try:
            pdf.relative_to(workspace.resolve())
        except ValueError:
            errors.append("pdf_path escapes workspace")
        else:
            if not pdf.is_file():
                errors.append(f"final PDF does not exist: {relative}")
            elif sha256_file(pdf).lower() != signoff["pdf_sha256"].lower():
                errors.append("final PDF hash does not match signoff")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("signoff", type=Path)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--actor")
    parser.add_argument("--current-revision", help="optional assertion; HEAD is always resolved automatically")
    args = parser.parse_args()
    try:
        signoff = load_record(args.signoff)
        manifest_path = args.workspace.resolve() / _safe_relative(signoff.get("project_manifest_path")) if _safe_relative(signoff.get("project_manifest_path")) else None
        manifest = load_record(manifest_path) if manifest_path else None
        head_revision = resolve_head_revision(args.workspace.resolve())
        if args.current_revision and args.current_revision != head_revision:
            print("FAIL human signoff: supplied current revision does not match HEAD", file=sys.stderr)
            return 1
        errors = validate_human_signoff(
            signoff,
            actor=args.actor,
            current_revision=head_revision,
            workspace=args.workspace.resolve(),
            manifest=manifest,
        )
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL human signoff: {exc}", file=sys.stderr)
        return 2
    if errors:
        print("FAIL human signoff")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS human signoff")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
