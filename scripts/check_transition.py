"""Fail-closed checks for the single competition state machine.

The main path is linear. A change after a passed gate enters the explicit
revision loop and can return only after the recorded targeted checks pass.
"""

from __future__ import annotations

import argparse

try:  # import works as a package and as ``python scripts/check_transition.py``
    from .gate_contract import (
        CHANGE_LEVELS,
        MAIN_TRANSITIONS,
        REVISION_TRANSITIONS,
        SAFE_CHECK_IDS,
        STATES,
        validate_revision_scope,
    )
except ImportError:  # pragma: no cover
    from gate_contract import (
        CHANGE_LEVELS,
        MAIN_TRANSITIONS,
        REVISION_TRANSITIONS,
        SAFE_CHECK_IDS,
        STATES,
        validate_revision_scope,
    )


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
    affected_gates: list[str] | tuple[str, ...] = (),
    required_checks: list[str] | tuple[str, ...] = (),
    validation_status: str | None = None,
) -> tuple[bool, str]:
    """Validate one state event; caller must persist the event separately."""

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
    if to_state == "human_frozen" and actor not in {"human", "human_owner"}:
        return False, "human_frozen requires human_owner"

    revision_edge = (from_state, to_state)
    if revision_edge == ("gate_passed", "revision_pending"):
        if not change_level and not any("revision" in item.lower() for item in evidence):
            return False, "revision_pending requires a revision record"
    elif revision_edge == ("revision_pending", "impact_classified"):
        if change_level not in CHANGE_LEVELS:
            return False, "impact_classified requires R0, R1, R2, or R3"
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
        if not affected_gates:
            return False, "restore_affected_gate requires affected gates"
        scope_ok, scope_message = validate_revision_scope(change_level, affected_gates)
        if not scope_ok:
            return False, scope_message
    elif revision_edge == ("restore_affected_gate", "gate_passed"):
        if not any("restore" in item.lower() or "regression" in item.lower() for item in evidence):
            return False, "restored gate requires restoration or regression evidence"
    return True, "ok"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("from_state", choices=STATES)
    parser.add_argument("to_state", choices=STATES)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--author")
    parser.add_argument("--change-level", choices=CHANGE_LEVELS)
    parser.add_argument("--affected-gate", action="append", default=[])
    parser.add_argument("--required-check", action="append", default=[])
    parser.add_argument("--validation-status", choices=["passed", "failed"])
    args = parser.parse_args()
    ok, message = validate_transition(
        args.from_state,
        args.to_state,
        actor=args.actor,
        evidence=args.evidence,
        author=args.author,
        change_level=args.change_level,
        affected_gates=args.affected_gate,
        required_checks=args.required_check,
        validation_status=args.validation_status,
    )
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
