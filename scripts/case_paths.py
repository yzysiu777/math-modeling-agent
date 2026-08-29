"""Resolve case-relative evidence references without escaping the case directory.

Both the packet generator and the case checker turn a text reference written by
a human ("outputs/data/EXP-001_solution.csv") into a real file.  That step is the
one place where a typo, a copied absolute path or a stray ``..`` can make a tool
read something outside the case, so it lives here once rather than being
reimplemented per script.

The rules are deliberately narrow:

* a reference containing ``..`` is rejected outright rather than normalized --
  silently rewriting it would hide the mistake that produced it;
* resolution happens on the real path (symlinks followed), and the result must
  still sit inside the resolved case directory;
* evidence of a given kind must sit in the directory that kind belongs to, so a
  claim cannot cite ``models/comparison.md`` as if it were a result file.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

#: Evidence kind -> the only directory that kind may resolve into.
EVIDENCE_ROOTS = {
    "data": "experiments/outputs/data",
    "checks": "experiments/outputs/checks",
    "figures": "experiments/outputs/figures",
    "outputs": "experiments/outputs",
}


def clean_reference(reference: str) -> str:
    """Strip Markdown decoration from a reference cell."""

    return str(reference or "").strip().strip("`").strip().lstrip("./")


def is_traversal(reference: str) -> bool:
    """Report whether a reference tries to walk out of its directory."""

    cleaned = clean_reference(reference)
    if not cleaned:
        return False
    return ".." in Path(cleaned).parts or Path(cleaned).is_absolute()


def contained_in(root: Path, path: Path) -> Optional[Path]:
    """Return the real path of ``path`` when it stays inside ``root``.

    Used for walking a directory the team controls (``input/``) where the entries
    are discovered rather than typed: a symlink placed there still must not pull
    content from outside the case into a review packet.
    """

    try:
        real_root = root.resolve(strict=True)
        real_path = path.resolve(strict=True)
    except (OSError, RuntimeError):
        return None
    try:
        real_path.relative_to(real_root)
    except ValueError:
        return None
    return real_path


def resolve_in_case(
    case_dir: Path,
    reference: str,
    kind: Optional[str] = None,
    search_bases: Iterable[str] = ("", "experiments"),
) -> Optional[Path]:
    """Return the real file a reference points at, or ``None`` if it is not allowed.

    ``kind`` restricts the answer to one of :data:`EVIDENCE_ROOTS`.  A reference
    that escapes the case, points outside the allowed root, or does not name an
    existing regular file resolves to ``None`` -- callers report that as missing
    or illegal evidence rather than reading it.
    """

    cleaned = clean_reference(reference)
    if not cleaned or is_traversal(cleaned):
        return None

    try:
        case_root = case_dir.resolve(strict=True)
    except (OSError, RuntimeError):
        return None

    allowed_root = case_root
    if kind is not None:
        relative = EVIDENCE_ROOTS.get(kind)
        if relative is None:
            return None
        try:
            allowed_root = (case_root / relative).resolve(strict=True)
        except (OSError, RuntimeError):
            return None

    candidates = [case_dir / base / cleaned if base else case_dir / cleaned
                  for base in search_bases]
    if kind is not None:
        candidates.insert(0, case_dir / EVIDENCE_ROOTS[kind] / Path(cleaned).name)

    for candidate in candidates:
        try:
            # ``resolve`` follows symlinks, so a link pointing outside the case
            # lands outside ``allowed_root`` and is rejected below.
            real = candidate.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if not real.is_file():
            continue
        try:
            real.relative_to(allowed_root)
        except ValueError:
            continue
        return real
    return None
