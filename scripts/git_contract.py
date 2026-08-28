"""Fail-closed Git commit identity and ancestry checks."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


FULL_GIT_SHA = re.compile(r"^[0-9a-fA-F]{40}$")


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
