"""Fail-closed checks for the project state machine."""

from __future__ import annotations

import argparse


STATES = (
    "intake", "routed", "frozen", "contracted", "baseline_ready", "model_ready",
    "validated", "reviewed", "revision_approved", "reproduced", "paper_ready",
    "pdf_qa_passed", "human_frozen",
)

NEXT = {state: STATES[index + 1] for index, state in enumerate(STATES[:-1])}


def validate_transition(
    from_state: str,
    to_state: str,
    *,
    actor: str,
    evidence: list[str] | tuple[str, ...] = (),
    author: str | None = None,
) -> tuple[bool, str]:
    if from_state not in STATES or to_state not in STATES:
        return False, "unknown state"
    if NEXT.get(from_state) != to_state:
        return False, f"illegal transition: {from_state} -> {to_state}"
    if not evidence:
        return False, "transition requires evidence"
    if to_state == "human_frozen" and actor not in {"human", "human_owner"}:
        return False, "human_frozen requires human_owner"
    if to_state == "revision_approved" and not any("approved" in item for item in evidence):
        return False, "revision_approved requires approved_findings evidence"
    if to_state == "reviewed" and author and actor == author:
        return False, "review author cannot approve its own review"
    return True, "ok"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("from_state", choices=STATES)
    parser.add_argument("to_state", choices=STATES)
    parser.add_argument("--actor", required=True)
    parser.add_argument("--evidence", action="append", default=[])
    parser.add_argument("--author")
    args = parser.parse_args()
    ok, message = validate_transition(
        args.from_state, args.to_state, actor=args.actor,
        evidence=args.evidence, author=args.author,
    )
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
