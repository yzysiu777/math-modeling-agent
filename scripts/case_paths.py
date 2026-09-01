"""Resolve question-relative evidence without escaping the case directory.

Both the packet generator and the case checker turn a text reference written by
a human ("outputs/data/EXP-001_solution.csv") into a real file.  In the
per-question workbench that reference is relative to ``q<k>/``.  An explicit
``q<j>/outputs/...`` reference is allowed only when ``j <= k`` so a later
question may consume earlier results without letting an earlier question depend
on future work.

The rules are deliberately narrow:

* a reference containing ``..`` is rejected outright rather than normalized --
  silently rewriting it would hide the mistake that produced it;
* resolution happens on the real path (symlinks followed), and the result must
  still sit inside the resolved case directory;
* evidence of a given kind must sit in the directory that kind belongs to, so a
  claim cannot cite ``models/comparison.md`` as if it were a result file.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Optional


CROSS_QUESTION_BACKWARD_REFERENCE = "CROSS_QUESTION_BACKWARD_REFERENCE"
QUESTION_DIR = re.compile(r"^q(?P<number>[1-9][0-9]*)$", re.IGNORECASE)

#: Evidence kind -> its directory relative to the active question.
EVIDENCE_ROOTS = {
    "data": "outputs/data",
    "checks": "outputs/checks",
    "figures": "outputs/figures",
    "outputs": "outputs",
}

def clean_reference(reference: str) -> str:
    """Strip Markdown decoration from a reference cell."""

    cleaned = str(reference or "").strip().strip("`").strip()
    return cleaned[2:] if cleaned.startswith("./") else cleaned


def is_traversal(reference: str) -> bool:
    """Report whether a reference tries to walk out of its directory."""

    cleaned = clean_reference(reference)
    if not cleaned:
        return False
    return ".." in Path(cleaned).parts or Path(cleaned).is_absolute()


def normalize_question(question: str | int) -> str:
    """Return the canonical ``q<k>`` directory name."""

    value = f"q{question}" if isinstance(question, int) else str(question).strip().casefold()
    match = QUESTION_DIR.fullmatch(value)
    if match is None:
        raise ValueError("question must be a positive integer or q<positive integer>")
    return f"q{int(match.group('number'))}"


def referenced_question(reference: str) -> str | None:
    """Return an explicit leading question directory, if present."""

    cleaned = clean_reference(reference)
    if not cleaned:
        return None
    match = QUESTION_DIR.fullmatch(Path(cleaned).parts[0])
    return f"q{int(match.group('number'))}" if match else None


def reference_violation_code(reference: str, question: str | int) -> str | None:
    """Return the stable BLOCK code for a prohibited cross-question edge."""

    current = normalize_question(question)
    target = referenced_question(reference)
    if target is None:
        return None
    current_number = int(current[1:])
    target_number = int(target[1:])
    if target_number > current_number:
        return CROSS_QUESTION_BACKWARD_REFERENCE
    return None


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
    search_bases: Iterable[str] = ("",),
    question: str | int | None = None,
) -> Optional[Path]:
    """Return the real file a reference points at, or ``None`` if it is not allowed.

    ``kind`` restricts the answer to one of :data:`EVIDENCE_ROOTS` and therefore
    requires ``question``.  Unprefixed references are resolved below that
    question and an explicit later-question prefix is rejected.  Call
    :func:`reference_violation_code` when a caller needs the stable diagnostic
    code for a rejected dependency.
    """

    if kind is not None and question is None:
        raise ValueError("question is required for evidence resolution")

    cleaned = clean_reference(reference)
    if not cleaned or is_traversal(cleaned):
        return None

    try:
        case_root = case_dir.resolve(strict=True)
    except (OSError, RuntimeError):
        return None

    question_name = normalize_question(question) if question is not None else None
    if question_name is not None and reference_violation_code(cleaned, question_name):
        return None
    explicit_question = referenced_question(cleaned) if question_name is not None else None
    target_question = explicit_question or question_name
    relative_reference = Path(cleaned)
    if explicit_question is not None:
        relative_reference = Path(*relative_reference.parts[1:])

    scope_root = case_root / target_question if target_question else case_root
    allowed_root = case_root
    if kind is not None:
        relative = EVIDENCE_ROOTS.get(kind)
        if relative is None:
            return None
        try:
            allowed_root = (scope_root / relative).resolve(strict=True)
        except (OSError, RuntimeError):
            return None

    candidates = [scope_root / base / relative_reference if base else scope_root / relative_reference
                  for base in search_bases]
    if kind is not None:
        candidates.insert(0, scope_root / EVIDENCE_ROOTS[kind] / relative_reference.name)

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
