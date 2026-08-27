"""Classify revision risk from semantic declarations, not filename folklore."""

from __future__ import annotations

import argparse
import json
from pathlib import PurePosixPath

try:
    from .gate_contract import (
        CHANGE_SURFACES,
        affected_gates_for_surfaces,
        change_level_for_surfaces,
        required_checks_for,
        required_review_nodes_for,
    )
except ImportError:  # pragma: no cover
    from gate_contract import CHANGE_SURFACES, affected_gates_for_surfaces, change_level_for_surfaces, required_checks_for, required_review_nodes_for


SIGNAL_SURFACE = {
    "text": "text_only",
    "layout": "text_only",
    "paper": "paper_claim",
    "code": "code_only",
    "experiment": "experiment_logic",
    "data": "data_contract",
    "model": "model_formula",
    "objective": "objective_constraint",
    "constraint": "objective_constraint",
}


def _risk_hints_for_path(path: str) -> list[str]:
    normalized = path.replace("\\", "/").lower()
    p = PurePosixPath(normalized)
    hints: list[str] = []
    if any(term in normalized for term in ("input/", "data/", "label", "split")):
        hints.append("path suggests data-contract semantics")
    if any(term in normalized for term in ("src/", "code/", "experiment", "solver", "seed", "param", "requirements", ".py", ".ipynb")):
        hints.append("path suggests executable or experiment semantics")
    if any(term in normalized for term in ("claim", "result", "figure", "table", "citation", ".bib", ".pdf")):
        hints.append("path suggests paper-evidence semantics")
    if p.suffix in {".tex", ".sty", ".cls", ".md", ".txt"}:
        hints.append("text/layout extension is only a risk hint")
    return hints


def classify_change(
    changed_files: list[str],
    signals: list[str] | None = None,
    *,
    surfaces: list[str] | None = None,
    candidate_submission_pdf: bool = False,
    diff_text: str | None = None,
) -> dict:
    """Return a classification; path names never select the level by themselves."""

    declared = list(surfaces or [])
    for signal in signals or []:
        if signal not in SIGNAL_SURFACE:
            raise ValueError(f"unknown change signal: {signal}")
        declared.append(SIGNAL_SURFACE[signal])
    declared = list(dict.fromkeys(declared))
    invalid = set(declared).difference(CHANGE_SURFACES)
    if invalid:
        raise ValueError(f"unknown change surfaces: {sorted(invalid)}")
    if candidate_submission_pdf and "candidate_pdf" not in declared:
        declared.append("candidate_pdf")
    hints = {path: _risk_hints_for_path(path) for path in changed_files}
    reasons = [f"{path}: {hint}" for path, values in hints.items() for hint in values]
    if not declared:
        return {
            "change_level": None,
            "change_surfaces": [],
            "changed_files": changed_files,
            "risk_hints": hints,
            "reasons": reasons + ["no semantic declaration; human classification is required"],
            "requires_human_classification": True,
            "affected_gates": [],
            "required_review_nodes": [],
            "required_checks": [],
            "candidate_submission_pdf": candidate_submission_pdf,
        }
    level = change_level_for_surfaces(declared)
    return {
        "change_level": level,
        "change_surfaces": declared,
        "changed_files": changed_files,
        "risk_hints": hints,
        "reasons": reasons + [f"declared semantic surfaces: {', '.join(declared)}"],
        "requires_human_classification": False,
        "affected_gates": affected_gates_for_surfaces(declared),
        "required_review_nodes": required_review_nodes_for(declared),
        "required_checks": required_checks_for(
            level,
            changed_files,
            change_surfaces=declared,
            candidate_submission_pdf=candidate_submission_pdf,
        ),
        "candidate_submission_pdf": candidate_submission_pdf,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", action="append", dest="changed_files", required=True)
    parser.add_argument("--signal", action="append", default=[], choices=sorted(SIGNAL_SURFACE))
    parser.add_argument("--surface", action="append", default=[], choices=sorted(CHANGE_SURFACES))
    parser.add_argument("--candidate-submission-pdf", action="store_true")
    args = parser.parse_args()
    print(json.dumps(classify_change(args.changed_files, args.signal, surfaces=args.surface, candidate_submission_pdf=args.candidate_submission_pdf), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
