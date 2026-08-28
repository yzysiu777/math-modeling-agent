"""Fail-closed checks for the single competition state machine."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from pathlib import PurePosixPath

try:  # import works as a package and as ``python scripts/check_transition.py``
    from .check_evidence_graph import load_record
    from .check_human_signoff import validate_human_signoff
    from .check_revision_closure import load_yaml, validate_revision_closure
    from .git_contract import validate_revision_pair
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
    from check_revision_closure import load_yaml, validate_revision_closure
    from git_contract import validate_revision_pair
    from gate_contract import CHANGE_LEVELS, CHANGE_SURFACES, MAIN_TRANSITIONS, REVISION_TRANSITIONS, SAFE_CHECK_IDS, STATES, required_checks_for, validate_revision_scope


def _revision_transition_allowed(from_state: str, to_state: str) -> bool:
    expected = REVISION_TRANSITIONS.get(from_state)
    if isinstance(expected, tuple):
        return to_state in expected
    return expected == to_state


HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")


def _safe_relative(raw: object) -> str | None:
    if not isinstance(raw, str) or not raw.strip():
        return None
    path = PurePosixPath(raw.replace("\\", "/"))
    if path.is_absolute() or ".." in path.parts or str(path) in {"", "."}:
        return None
    return str(path)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validated_closure(
    *,
    closure_report: dict | None,
    closure_impact: dict | None,
    closure_id: str | None,
    closure_path: str | None,
    closure_sha256: str | None,
    workspace: Path | None,
    approval: dict | None = None,
) -> tuple[bool, str]:
    if not isinstance(closure_report, dict) or not isinstance(closure_impact, dict):
        return False, "transition requires a structured revision closure report and change impact record"
    if not closure_id or closure_report.get("closure_id") != closure_id:
        return False, "transition closure_id does not match the closure report"
    relative = _safe_relative(closure_path)
    if workspace is None or relative is None:
        return False, "transition requires a workspace-bound closure_path"
    if not isinstance(closure_sha256, str) or not HEX64.fullmatch(closure_sha256):
        return False, "transition requires a valid closure_sha256"
    path = (workspace / relative).resolve()
    try:
        path.relative_to(workspace.resolve())
    except ValueError:
        return False, "closure_path escapes workspace"
    if not path.is_file():
        return False, "closure report file does not exist"
    if _sha256(path).lower() != closure_sha256.lower():
        return False, "closure report file hash does not match the state event"
    try:
        file_report = load_record(path)
    except Exception as exc:  # noqa: BLE001
        return False, f"closure report file cannot be parsed: {exc}"
    if file_report != closure_report:
        return False, "closure report object does not match the hashed closure report file"
    closure_report = file_report
    if closure_report.get("validation_status") != "passed":
        return False, "closure report is not successful"
    git_errors: list[str] = []
    validate_revision_pair(
        workspace,
        closure_report.get("base_git_revision"),
        closure_report.get("new_git_revision"),
        git_errors,
        require_result_at_head=True,
        label="transition closure",
    )
    if git_errors:
        return False, "invalid closure Git revisions: " + "; ".join(git_errors)
    errors = validate_revision_closure(
        closure_impact,
        closure_report,
        approval,
        workspace=workspace,
        base_ref=closure_report.get("base_git_revision"),
        head_ref="HEAD",
        verify_git=True,
    )
    if errors:
        return False, "invalid revision closure: " + "; ".join(errors)
    return True, "ok"


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
    closure_report: dict | None = None,
    closure_impact: dict | None = None,
    approved_findings: dict | None = None,
    closure_id: str | None = None,
    closure_path: str | None = None,
    closure_sha256: str | None = None,
    project_manifest: dict | None = None,
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
            manifest=project_manifest,
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
        if to_state == "validation_passed":
            closure_ok, closure_message = _validated_closure(
                closure_report=closure_report,
                closure_impact=closure_impact,
                closure_id=closure_id,
                closure_path=closure_path,
                closure_sha256=closure_sha256,
                workspace=workspace,
                approval=approved_findings,
            )
            if not closure_ok:
                return False, closure_message
    elif revision_edge == ("validation_failed", "targeted_validation"):
        if not required_checks or set(required_checks).difference(SAFE_CHECK_IDS):
            return False, "retry requires a safe validation plan"
    elif revision_edge == ("validation_passed", "restore_affected_gate"):
        closure_ok, closure_message = _validated_closure(
            closure_report=closure_report,
            closure_impact=closure_impact,
            closure_id=closure_id,
            closure_path=closure_path,
            closure_sha256=closure_sha256,
            workspace=workspace,
            approval=approved_findings,
        )
        if not closure_ok:
            return False, closure_message
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
        closure_ok, closure_message = _validated_closure(
            closure_report=closure_report,
            closure_impact=closure_impact,
            closure_id=closure_id,
            closure_path=closure_path,
            closure_sha256=closure_sha256,
            workspace=workspace,
            approval=approved_findings,
        )
        if not closure_ok:
            return False, closure_message
        if not any("restore" in item.lower() or "regression" in item.lower() for item in evidence):
            return False, "restored gate requires restoration or regression evidence"
        if any(not isinstance(item, dict) or item.get("severity") in {"P0", "P1"} for item in unresolved_high_risk):
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
    parser.add_argument("--closure-report", type=Path)
    parser.add_argument("--closure-impact", type=Path)
    parser.add_argument("--approved-findings", type=Path)
    parser.add_argument("--closure-id")
    parser.add_argument("--closure-path")
    parser.add_argument("--closure-sha256")
    parser.add_argument("--project-manifest", type=Path)
    args = parser.parse_args()
    signoff = load_record(Path(args.signoff.name)) if args.signoff else None
    closure_report = load_record(args.closure_report) if args.closure_report else None
    closure_impact = load_record(args.closure_impact) if args.closure_impact else None
    approved_findings = load_record(args.approved_findings) if args.approved_findings else None
    project_manifest = load_record(args.project_manifest) if args.project_manifest else None
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
        closure_report=closure_report,
        closure_impact=closure_impact,
        approved_findings=approved_findings,
        closure_id=args.closure_id,
        closure_path=args.closure_path,
        closure_sha256=args.closure_sha256,
        project_manifest=project_manifest,
    )
    print(message)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
