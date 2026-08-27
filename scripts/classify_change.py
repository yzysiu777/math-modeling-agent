"""Classify a revision as R0-R3 without executing any requested command."""

from __future__ import annotations

import argparse
import json
from pathlib import PurePosixPath

try:  # import works both as a package and as a direct script
    from .gate_contract import required_checks_for
except ImportError:  # pragma: no cover
    from gate_contract import required_checks_for


SIGNAL_LEVEL = {
    "text": "R0",
    "layout": "R0",
    "paper": "R1",
    "code": "R2",
    "experiment": "R2",
    "data": "R3",
    "model": "R3",
}
LEVEL_ORDER = {"R0": 0, "R1": 1, "R2": 2, "R3": 3}


def _level_for_path(path: str) -> tuple[str, str]:
    normalized = path.replace("\\", "/").lower()
    p = PurePosixPath(normalized)
    r3_terms = ("input/", "data/", "label", "split", "formula", "objective", "constraint", "model", "algorithm")
    r2_terms = ("src/", "code/", "experiment", "solver", "seed", "param", "requirements", ".py", ".ipynb")
    r1_terms = ("claim", "result", "figure", "table", "citation", ".bib", ".pdf")
    if any(term in normalized for term in r3_terms):
        return "R3", "path suggests data/model semantics"
    if any(term in normalized for term in r2_terms):
        return "R2", "path suggests executable code or experiment behavior"
    if any(term in normalized for term in r1_terms):
        return "R1", "path suggests paper evidence or published result"
    if p.suffix in {".tex", ".sty", ".cls", ".md", ".txt"}:
        return "R0", "path defaults to non-substantive text/layout pending human declaration"
    return "R0", "no higher-risk semantic signal was declared"


def classify_change(changed_files: list[str], signals: list[str] | None = None, *, candidate_submission_pdf: bool = False) -> dict:
    signals = signals or []
    levels = []
    reasons = []
    for signal in signals:
        if signal not in SIGNAL_LEVEL:
            raise ValueError(f"unknown change signal: {signal}")
        levels.append(SIGNAL_LEVEL[signal])
        reasons.append(f"declared signal: {signal}")
    for path in changed_files:
        level, reason = _level_for_path(path)
        levels.append(level)
        reasons.append(f"{path}: {reason}")
    level = max(levels, key=LEVEL_ORDER.get) if levels else "R0"
    return {
        "change_level": level,
        "changed_files": changed_files,
        "reasons": reasons,
        "required_checks": required_checks_for(level, changed_files, candidate_submission_pdf=candidate_submission_pdf),
        "candidate_submission_pdf": candidate_submission_pdf,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", action="append", dest="changed_files", required=True)
    parser.add_argument("--signal", action="append", default=[], choices=sorted(SIGNAL_LEVEL))
    parser.add_argument("--candidate-submission-pdf", action="store_true")
    args = parser.parse_args()
    print(json.dumps(classify_change(args.changed_files, args.signal, candidate_submission_pdf=args.candidate_submission_pdf), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
