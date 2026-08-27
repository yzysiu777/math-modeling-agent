"""Fail-closed checks for the single competition state machine."""

from __future__ import annotations

import argparse
from pathlib import Path

try:  # import works as a package and as ``python scripts/check_transition.py``
    from .check_evidence_graph import load_record
    from .check_human_signoff import validate_human_signoff
    from .gate_contract import (
        CHANGE_LEVELS,
        CHANGE_SURFACES,
        MAIN_TRANSITIONS,
        REVISION_TRANSITIONS,
        SAFE_CHECK_IDS,
        STATES,
        required_checks_for,
        validate_revision_scope,
    )
except ImportError:  # pragma: no cover
    from check_evidence_graph import load_record
    from check_human_signoff import validate_human_signoff
    from gate_contract import CHANGE_LEVELS, CHANGE_SURFACES, MAIN_TRANSITIONS, REVISION_TRANSITIONS, SAFE_CHECK_IDS, STATES, required_checks_for, validate_revision_scope


def _revision_transition_allowed(from_state: str, to_state: str) -> bool:
    expected = REVISION_TRANSITIONS.get(from_state)
    if isinstance(expected, tuple):
        return to_state in expected
    return expected == to_state


def validate_transition(
    from_state: str,
    to_state: str,
    *,
    actor: str,
    evidence: list[str] | tuple[str, ...] = (),
    author: str | None = None,
    change_level: str | None = None,
    change_surfaces: list[str] | tuple[str, ...] = (),
    affected_gates: list[str] | tuple[str, ...] = (),
    gate_impact: str | None = None,
    required_checks: list[str] | tuple[str, ...] = (),
    validation_status: str | None = None,
    signoff: dict | None = None,
    workspace=None,
    current_revision: str | None = None,
    unresolved_high_risk: list[str] | tuple[str, ...] = (),
) -> tuple[bool, str]:
    """Validate one state event; the caller persists the event separately."""

    if from_state not in STATES or to_state not in STATES:
        return False, "unknown state"
    main_ok = MAIN_TRANSITIONS.get(from_state) == to_state
    revision_ok = _revision_transition_allowed(from_state, to_state)
    if not (main_ok or revision_ok):
        return False, f"illegal transition: {from_state} -> {to_state}"
    if not evidence:
        return False, "transition requires evidence"
    if to_state == "reviewed" and author and actor == author:
        return False, "review author cannot approve its own review"
    if to_state == "human_frozen":
        signoff_role = signoff.get("signer_role") if isinstance(signoff, dict) else None
        actor_is_human = actor in {"human", "human_owner"} or (
            signoff is not None and signoff.get("actor") == actor and signoff_role in {"human", "human_owner"}
        )
        if not actor_is_human:
            return False, "human_frozen requires human_owner"
        if signoff is None:
            return False, "human_frozen requires a validated human_signoff record"
        signoff_errors = validate_human_signoff(
            signoff,
            actor=actor,
            current_revision=current_revision,
            workspace=workspace,
        )
        if signoff_errors:
            return False, "invalid human signoff: " + "; ".join(signoff_errors)

    revision_edge = (from_state, to_state)
    if revision_edge == ("gate_passed", "revision_pending"):
        if not change_level and not any("revision" in item.lower() for item in evidence):
            return False, "revision_pending requires a revision record"
    elif revision_edge == ("revision_pending", "impact_classified"):
        if change_level not in CHANGE_LEVELS:
            return False, "impact_classified requires R0, R1, R2, or R3"
        if change_surfaces and any(surface not in CHANGE_SURFACES for surface in change_surfaces):
            return False, "impact_classified contains an unknown change surface"
    elif revision_edge == ("impact_classified", "targeted_validation"):
        if change_level not in CHANGE_LEVELS:
            return False, "targeted_validation requires a change level"
        invalid_checks = set(required_checks).difference(SAFE_CHECK_IDS)
        if not required_checks:
            return False, "targeted_validation requires safe check IDs"
        if invalid_checks:
            return False, f"unknown or unsafe check IDs: {sorted(invalid_checks)}"
    elif revision_edge in {
        ("targeted_validation", "validation_passed"),
        ("targeted_validation", "validation_failed"),
    }:
        if validation_status not in {"passed", "failed"}:
            return False, "targeted validation requires validation_status"
        expected = "passed" if to_state == "validation_passed" else "failed"
        if validation_status != expected:
            return False, f"{to_state} requires validation_status={expected}"
    elif revision_edge == ("validation_failed", "targeted_validation"):
        if not required_checks or set(required_checks).difference(SAFE_CHECK_IDS):
            return False, "retry requires a safe validation plan"
    elif revision_edge == ("validation_passed", "restore_affected_gate"):
        if change_level not in CHANGE_LEVELS:
            return False, "restore_affected_gate requires a change level"
        if change_level == "R0":
            if affected_gates:
                return False, "R0 restore must keep affected_gates empty"
            if gate_impact != "no_gate_impact" or not any("no_gate_impact" in item for item in evidence):
                return False, "R0 restore requires explicit no_gate_impact evidence"
        else:
            if not affected_gates:
                return False, "non-R0 restore requires affected gates"
        scope_ok, scope_message = validate_revision_scope(
            change_level,
            affected_gates,
            change_surfaces=change_surfaces,
            gate_impact=gate_impact,
        )
        if not scope_ok:
            return False, scope_message
    elif revision_edge == ("restore_affected_gate", "gate_passed"):
        if not any("restore" in item.lower() or "regression" in item.lower() for item in evidence):
            return False, "restored gate requires restoration or regression evidence"
        if unresolved_high_risk:
            return False, "cannot restore a gate with unresolved P0/P1 findings"
    return True, "ok"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("from_state", choices=STATES)
    parser.add_argument("to_state", choices=STATES)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--author")
    parser.add_argument("--change-level", choices=CHANGE_LEVELS)
    parser.add_argument("--change-surface", action="append", default=[], choices=sorted(CHANGE_SURFACES))
    parser.add_argument("--affected-gate", action="append", default=[])
    parser.add_argument("--gate-impact", choices=["no_gate_impact", "affected"])
    parser.add_argument("--required-check", action="append", default=[])
    parser.add_argument("--validation-status", choices=["passed", "failed"])
    parser.add_argument("--signoff", type=argparse.FileType("r"))
    parser.add_argument("--workspace")
    parser.add_argument("--current-revision")
    parser.add_argument("--unresolved-high-risk", action="append", default=[])
    args = parser.parse_args()
    signoff = load_record(Path(args.signoff.name)) if args.signoff else None
    ok, message = validate_transition(
        args.from_state,
        args.to_state,
        actor=args.actor,
        evidence=args.evidence,
        author=args.author,
        change_level=args.change_level,
        change_surfaces=args.change_surface,
        affected_gates=args.affected_gate,
        gate_impact=args.gate_impact,
        required_checks=args.required_check,
        validation_status=args.validation_status,
        signoff=signoff,
        workspace=Path(args.workspace).resolve() if args.workspace else None,
        current_revision=args.current_revision,
        unresolved_high_risk=args.unresolved_high_risk,
    )
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
