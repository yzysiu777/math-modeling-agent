"""Check approved revision boundaries and then targeted-validation closure.

The two results are intentionally reported separately. A clean allowlist is
not evidence that the affected experiments passed, and passing experiments do
not authorize files outside the allowlist.
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path, PurePosixPath

try:
    from .check_revision_closure import load_yaml, validate_revision_closure
except ImportError:  # pragma: no cover
    from check_revision_closure import load_yaml, validate_revision_closure


def _normalize_relative(raw: str) -> str:
    path = PurePosixPath(str(raw).replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
        raise ValueError(f"path must be relative and confined: {raw}")
    return str(path)


def changed_files(base_ref: str, head_ref: str = "HEAD") -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_ref}...{head_ref}"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    return [_normalize_relative(line) for line in result.stdout.splitlines() if line]


def git_file_sha256(ref: str, relative: str) -> str | None:
    result = subprocess.run(
        ["git", "show", f"{ref}:{relative}"],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return None
    return hashlib.sha256(result.stdout).hexdigest()


def git_revision(ref: str) -> str | None:
    result = subprocess.run(["git", "rev-parse", ref], text=True, capture_output=True, check=False)
    if result.returncode:
        return None
    return result.stdout.strip()


def validate_revision_boundary(
    approval: dict,
    impact: dict,
    *,
    base_ref: str = "main",
    head_ref: str = "HEAD",
) -> list[str]:
    errors: list[str] = []
    if approval.get("record_type") != "approved_findings":
        errors.append("approval record is not approved_findings")
    if approval.get("status") not in {"approved", "applied"}:
        errors.append("approval record is not active")
    allowed_raw = approval.get("allowed_files") or []
    if not allowed_raw:
        errors.append("allowed_files is empty; fail closed")
    try:
        allowed = {_normalize_relative(item) for item in allowed_raw}
        forbidden = {_normalize_relative(item) for item in (approval.get("forbidden_files") or [])}
    except ValueError as exc:
        errors.append(str(exc))
        allowed, forbidden = set(), set()
    if approval.get("validation_commands"):
        errors.append("validation_commands are forbidden; use validation_check_ids")
    if not approval.get("validation_check_ids"):
        errors.append("validation_check_ids cannot be empty")

    recorded_base = impact.get("base_git_revision")
    actual_base = git_revision(base_ref)
    if recorded_base and actual_base and recorded_base != actual_base:
        errors.append("base_git_revision does not match base_ref")
    recorded_head = impact.get("new_git_revision")
    actual_head = git_revision(head_ref)
    if recorded_head and actual_head and recorded_head != actual_head:
        errors.append("new_git_revision does not match head_ref")

    try:
        actual = changed_files(base_ref, head_ref)
    except Exception as exc:  # noqa: BLE001
        return errors + [str(exc)]
    recorded = [_normalize_relative(item) for item in (impact.get("changed_files") or [])]
    if not recorded:
        errors.append("change impact record has no changed_files")
    if set(actual) != set(recorded):
        errors.append(f"actual and recorded changed files differ: actual={actual}, recorded={recorded}")
    for path in actual:
        if path in forbidden or any(path.startswith(item.rstrip("/") + "/") for item in forbidden):
            errors.append(f"forbidden file changed: {path}")
        if path not in allowed:
            errors.append(f"file outside non-empty allowlist changed: {path}")

        before = git_file_sha256(base_ref, path)
        after = git_file_sha256(head_ref, path)
        before_hashes = impact.get("before_hashes") or {}
        after_hashes = impact.get("after_hashes") or {}
        if path not in before_hashes:
            errors.append(f"missing before hash: {path}")
        if path not in after_hashes:
            errors.append(f"missing after hash: {path}")
        recorded_before = before_hashes.get(path)
        recorded_after = after_hashes.get(path)
        if recorded_before != before:
            errors.append(f"before hash mismatch: {path}")
        if recorded_after != after:
            errors.append(f"after hash mismatch: {path}")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("approved_findings", type=Path)
    parser.add_argument("--change-record", type=Path, required=True)
    parser.add_argument("--validation-record", type=Path, required=True)
    parser.add_argument("--base-ref", default="main")
    parser.add_argument("--head-ref", default="HEAD")
    args = parser.parse_args()
    try:
        approval = load_yaml(args.approved_findings)
        impact = load_yaml(args.change_record)
        validation = load_yaml(args.validation_record)
        boundary_errors = validate_revision_boundary(
            approval, impact, base_ref=args.base_ref, head_ref=args.head_ref
        )
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {exc}", file=sys.stderr)
        return 2
    if boundary_errors:
        print("FAIL modification boundary")
        print("\n".join(f"- {error}" for error in boundary_errors))
        return 1
    print("PASS modification boundary")
    closure_errors = validate_revision_closure(impact, validation, approval)
    if closure_errors:
        print("FAIL targeted validation closure")
        print("\n".join(f"- {error}" for error in closure_errors))
        return 1
    print("PASS targeted validation closure")
    print("PASS approved revision")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
