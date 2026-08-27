"""Plan safe, targeted checks for an R0-R3 revision."""

from __future__ import annotations

import argparse
import json

try:
    from .gate_contract import MINIMUM_AFFECTED_GATES, affected_gates_for_surfaces, required_checks_for, required_review_nodes_for
except ImportError:  # pragma: no cover
    from gate_contract import MINIMUM_AFFECTED_GATES, affected_gates_for_surfaces, required_checks_for, required_review_nodes_for


def plan_validation(
    change_level: str,
    changed_files: list[str],
    *,
    candidate_submission_pdf: bool = False,
    change_surfaces: list[str] | None = None,
) -> dict:
    surfaces = list(change_surfaces or [])
    required = required_checks_for(
        change_level,
        changed_files,
        candidate_submission_pdf=candidate_submission_pdf,
        change_surfaces=surfaces,
    )
    not_run = []
    if change_level == "R0":
        not_run.extend(["affected_experiment_rerun", "independent_claude_review"])
    elif change_level == "R1":
        not_run.extend(["full_experiment_rerun", "model_rebuild"])
    return {
        "change_level": change_level,
        "change_surfaces": surfaces,
        "changed_files": changed_files,
        "affected_gates_minimum": sorted(MINIMUM_AFFECTED_GATES[change_level]),
        "affected_gates": affected_gates_for_surfaces(surfaces) if surfaces else [],
        "required_review_nodes": required_review_nodes_for(surfaces) if surfaces else [],
        "required_checks": required,
        "checks_not_automatically_triggered": not_run,
        "commands_executed": [],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--change-level", required=True, choices=["R0", "R1", "R2", "R3"])
    parser.add_argument("--file", action="append", dest="changed_files", default=[])
    parser.add_argument("--candidate-submission-pdf", action="store_true")
    parser.add_argument("--change-surface", action="append", default=[])
    args = parser.parse_args()
    print(json.dumps(plan_validation(args.change_level, args.changed_files, candidate_submission_pdf=args.candidate_submission_pdf, change_surfaces=args.change_surface), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
