"""Fail-closed Git commit, diff, and file-content facts.

The functions in this module are intentionally independent of approval or
workflow policy.  A closure, work item, state transition, or approval may
reuse these facts, but none of them may replace the repository-derived
changed-file set or the before/after content hashes with self-reported data.
"""

from __future__ import annotations

import re
import subprocess
import hashlib
from pathlib import Path
from typing import Callable


FULL_GIT_SHA = re.compile(r"^[0-9a-fA-F]{40}$")
FULL_FILE_SHA = re.compile(r"^[0-9a-fA-F]{64}$")


def _normalize_relative(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    value = raw.replace("\\", "/")
    parts = value.split("/")
    if value.startswith("/") or ".." in parts or value in {"", "."}:
        return None
    return "/".join(part for part in parts if part not in {""}) or None


def resolve_head(workspace: Path) -> str | None:
    """Return the repository HEAD as a canonical full commit SHA."""

    result = subprocess.run(
        ["git", "-C", str(workspace), "rev-parse", "--verify", "HEAD^{commit}"],
        text=True,
        capture_output=True,
        check=False,
    )
    value = result.stdout.strip().lower()
    return value if result.returncode == 0 and FULL_GIT_SHA.fullmatch(value) else None


def resolve_commit(workspace: Path, revision: object) -> str | None:
    """Resolve only a full SHA-1 commit identifier, never a symbolic ref."""

    if not isinstance(revision, str) or not FULL_GIT_SHA.fullmatch(revision):
        return None
    result = subprocess.run(
        ["git", "-C", str(workspace), "rev-parse", "--verify", f"{revision}^{{commit}}"],
        text=True,
        capture_output=True,
        check=False,
    )
    value = result.stdout.strip().lower()
    if result.returncode != 0 or not FULL_GIT_SHA.fullmatch(value):
        return None
    # A record must carry the canonical full SHA, not an alternate spelling.
    return value if value == revision.lower() else None


def is_ancestor(workspace: Path, ancestor: str, descendant: str) -> bool:
    result = subprocess.run(
        ["git", "-C", str(workspace), "merge-base", "--is-ancestor", ancestor, descendant],
        text=True,
        capture_output=True,
        check=False,
    )
    return result.returncode == 0


def changed_files(workspace: Path, base_ref: str, result_ref: str) -> list[str]:
    """Return the repository-derived changed paths between two revisions.

    Rename detection is disabled deliberately.  A rename is then represented
    as a deletion plus an addition, which gives the before/after hash contract
    an unambiguous ``null`` side for each path.
    """

    result = subprocess.run(
        [
            "git", "-C", str(workspace), "diff", "--name-only", "--no-renames",
            f"{base_ref}^{{commit}}", f"{result_ref}^{{commit}}",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "git diff failed")
    paths: list[str] = []
    for line in result.stdout.splitlines():
        relative = _normalize_relative(line)
        if relative is None:
            raise RuntimeError(f"git diff returned an unsafe path: {line!r}")
        paths.append(relative)
    return paths


def file_sha256(workspace: Path, revision: str, relative: str) -> str | None:
    """Return a committed file's SHA-256, or ``None`` if absent at revision."""

    normalized = _normalize_relative(relative)
    if normalized is None:
        return None
    result = subprocess.run(
        ["git", "-C", str(workspace), "show", f"{revision}^{{commit}}:{normalized}"],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        return None
    return hashlib.sha256(result.stdout).hexdigest()


# Descriptive compatibility alias for callers that use the historical name.
git_file_sha256 = file_sha256


def _call_changed_files(
    workspace: Path | None,
    base_ref: str,
    result_ref: str,
    provider: Callable[..., list[str]],
) -> list[str]:
    """Call the normal provider and retain compatibility with test doubles."""

    try:
        return provider(workspace, base_ref, result_ref)
    except TypeError:
        # Compatibility with approval-module test doubles and its historical
        # ``(base, head, workspace=...)`` adapter.
        return provider(base_ref, result_ref, workspace=workspace)


def _call_file_sha256(
    workspace: Path | None,
    revision: str,
    relative: str,
    provider: Callable[..., str | None],
) -> str | None:
    try:
        return provider(workspace, revision, relative)
    except TypeError:
        return provider(revision, relative, workspace=workspace)


def validate_git_change_facts(
    workspace: Path | None,
    base_revision: object,
    result_revision: object,
    recorded_changed_files: object,
    before_hashes: object,
    after_hashes: object,
    *,
    errors: list[str] | None = None,
    require_result_at_head: bool = True,
    label: str = "Git change facts",
    changed_files_provider: Callable[..., list[str]] | None = None,
    file_sha256_provider: Callable[..., str | None] | None = None,
) -> list[str]:
    """Validate repository diff and per-file before/after content hashes.

    ``recorded_changed_files``, ``before_hashes`` and ``after_hashes`` are
    claims supplied by a record.  The returned errors are based on the actual
    repository facts.  Added files must have a null before hash; deleted files
    must have a null after hash.  Hash maps must cover exactly the actual diff,
    including no extra entries.

    The optional providers exist only so legacy approval tests can inject
    deterministic Git responses.  Production callers use the defaults.
    """

    result_errors = errors if errors is not None else []
    provider_changed = changed_files_provider or changed_files
    provider_hash = file_sha256_provider or file_sha256

    base = result = None
    if workspace is not None:
        base, result = validate_revision_pair(
            workspace,
            base_revision,
            result_revision,
            result_errors,
            require_result_at_head=require_result_at_head,
            label=label,
        )
    else:
        # A real validation always supplies a workspace.  This branch lets
        # callers that only exercise policy checks still use the same fact
        # validator with an injected provider.
        base = base_revision if isinstance(base_revision, str) else None
        result = result_revision if isinstance(result_revision, str) else None

    if not isinstance(recorded_changed_files, list):
        result_errors.append(f"{label} changed_files must be a list")
        recorded: list[str] = []
    else:
        recorded = []
        for raw in recorded_changed_files:
            normalized = _normalize_relative(raw)
            if normalized is None:
                result_errors.append(f"{label} changed_files contains an unsafe path: {raw}")
            else:
                recorded.append(normalized)
    if len(recorded) != len(set(recorded)):
        result_errors.append(f"{label} changed_files contains duplicates")

    if not isinstance(before_hashes, dict):
        result_errors.append(f"{label} before_hashes must be a mapping")
        before: dict[str, object] = {}
    else:
        before = dict(before_hashes)
    if not isinstance(after_hashes, dict):
        result_errors.append(f"{label} after_hashes must be a mapping")
        after: dict[str, object] = {}
    else:
        after = dict(after_hashes)

    try:
        actual = _call_changed_files(workspace, str(base_revision), str(result_revision), provider_changed)
    except Exception as exc:  # noqa: BLE001
        result_errors.append(f"{label} actual Git diff cannot be read: {exc}")
        actual = []
    actual = [_normalize_relative(item) for item in actual]
    actual = [item for item in actual if item is not None]
    if not actual and recorded:
        result_errors.append(f"{label} actual Git diff is empty but changed_files is non-empty")
    if set(actual) != set(recorded):
        result_errors.append(f"{label} actual and recorded changed files differ: actual={actual}, recorded={recorded}")
    if set(before) != set(actual):
        result_errors.append(f"{label} before_hashes must cover exactly the actual Git diff")
    if set(after) != set(actual):
        result_errors.append(f"{label} after_hashes must cover exactly the actual Git diff")

    for path in actual:
        actual_before = _call_file_sha256(workspace, str(base_revision), path, provider_hash)
        actual_after = _call_file_sha256(workspace, str(result_revision), path, provider_hash)
        recorded_before = before.get(path)
        recorded_after = after.get(path)
        if actual_before is None:
            if recorded_before is not None:
                result_errors.append(f"{label} before hash for added file must be null: {path}")
        elif not isinstance(recorded_before, str) or not FULL_FILE_SHA.fullmatch(recorded_before):
            result_errors.append(f"{label} before hash is invalid: {path}")
        elif recorded_before.lower() != actual_before.lower():
            result_errors.append(f"{label} before hash mismatch: {path}")
        if actual_after is None:
            if recorded_after is not None:
                result_errors.append(f"{label} after hash for deleted file must be null: {path}")
        elif not isinstance(recorded_after, str) or not FULL_FILE_SHA.fullmatch(recorded_after):
            result_errors.append(f"{label} after hash is invalid: {path}")
        elif recorded_after.lower() != actual_after.lower():
            result_errors.append(f"{label} after hash mismatch: {path}")
    return sorted(set(result_errors))


def validate_revision_pair(
    workspace: Path,
    base_revision: object,
    result_revision: object,
    errors: list[str],
    *,
    require_result_at_head: bool = True,
    label: str = "Git revision",
) -> tuple[str | None, str | None]:
    """Validate source/result commits, ancestry, and (by default) current HEAD."""

    base = resolve_commit(workspace, base_revision)
    result = resolve_commit(workspace, result_revision)
    if base is None:
        errors.append(f"{label} base revision is not a real full Git commit: {base_revision}")
    if result is None:
        errors.append(f"{label} result revision is not a real full Git commit: {result_revision}")
    head = resolve_head(workspace)
    if head is None:
        errors.append(f"{label} repository HEAD cannot be resolved")
    if result is not None and require_result_at_head and head is not None and result != head:
        errors.append(f"{label} result revision does not match repository HEAD")
    if result is not None and head is not None and not is_ancestor(workspace, result, head):
        errors.append(f"{label} result revision is not reachable from repository HEAD")
    if base is not None and result is not None and not is_ancestor(workspace, base, result):
        errors.append(f"{label} base revision is not an ancestor of the result revision")
    return base, result
