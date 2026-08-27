"""Validate the human-only final freeze record (G12)."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path, PurePosixPath

try:
    from .check_evidence_graph import load_record
    from .gate_contract import GATE_IDS
except ImportError:  # pragma: no cover
    from check_evidence_graph import load_record
    from gate_contract import GATE_IDS


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


def validate_human_signoff(
    signoff: dict,
    *,
    actor: str | None = None,
    current_revision: str | None = None,
    workspace: Path | None = None,
) -> list[str]:
    errors: list[str] = []
    if signoff.get("record_type") != "human_signoff":
        errors.append("record_type must be human_signoff")
    for field in ("signoff_id", "case_id", "signer", "signer_id", "signer_role", "actor", "signed_at", "git_revision", "pdf_path", "pdf_sha256"):
        if not str(signoff.get(field, "")).strip():
            errors.append(f"{field} is required")
    if signoff.get("signer_role") not in {"human", "human_owner"}:
        errors.append("signer_role must be human or human_owner")
    if actor and signoff.get("actor") != actor:
        errors.append("signoff actor does not match transition actor")
    if signoff.get("signer_id") != signoff.get("actor"):
        errors.append("signer_id must match actor")
    signed_at = str(signoff.get("signed_at", ""))
    if signed_at.startswith("YYYY-"):
        errors.append("signed_at is still a placeholder")
    else:
        try:
            datetime.fromisoformat(signed_at.replace("Z", "+00:00"))
        except ValueError:
            errors.append("signed_at must be an ISO-8601 timestamp")
    if current_revision and signoff.get("git_revision") != current_revision:
        errors.append("signoff git_revision does not match current revision")
    approved = signoff.get("approved_gates")
    if approved != list(GATE_IDS):
        errors.append(f"approved_gates must equal {list(GATE_IDS)}")
    if signoff.get("decision") not in {"approved", "approved_with_limits"}:
        errors.append("G12 requires an approved decision")
    unresolved = signoff.get("unresolved_findings") or []
    open_limitations = signoff.get("open_limitations") or []
    if any(str(item).startswith(("P0", "P1")) for item in unresolved + open_limitations):
        errors.append("G12 cannot freeze with an open P0/P1 finding")
    for field in ("review_scope", "checked_items", "not_checked_items", "expertise_limitations"):
        if not isinstance(signoff.get(field), list) or not signoff[field]:
            errors.append(f"{field} must be non-empty")
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
    parser.add_argument("--current-revision")
    args = parser.parse_args()
    try:
        errors = validate_human_signoff(
            load_record(args.signoff),
            actor=args.actor,
            current_revision=args.current_revision,
            workspace=args.workspace.resolve(),
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
