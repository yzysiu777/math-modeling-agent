"""Small real-Git fixtures used by REV-06C acceptance tests."""

from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

from scripts.gate_contract import required_checks_for


SOURCE_ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _git(workspace: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=workspace, text=True).strip()


def _write_manifest(workspace: Path, case_id: str) -> Path:
    path = workspace / "manifest.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "record_type": "project_manifest",
                "case_id": case_id,
                "title": "REV-06C real runner fixture",
                "language_policy": "zh",
                "route": "optimization",
                "owner": {"name": "Test Owner", "owner_id": "owner-1", "role": "human_owner"},
                "identity_allowlist": [
                    {"id": "owner-1", "role": "human_owner"},
                    {"id": "reviewer-1", "role": "independent_adversary"},
                ],
                "objective": {
                    "user_goal": "exercise a real trusted closure",
                    "deliverables": ["validation record"],
                    "unacceptable_shortcuts": ["hand-written passed log"],
                },
                "sources": [],
                "acceptance": {
                    "required_gates": [f"G{index}" for index in range(13)],
                    "primary_metrics": ["closure integrity"],
                    "reproducibility_requirement": "re-run from the protected runner",
                },
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return path


def build_real_r0_case(workspace: Path) -> tuple[dict, dict, dict]:
    """Create a real base/result Git pair and run the fixed runner via CLI."""

    shutil.copytree(
        SOURCE_ROOT / "scripts",
        workspace / "scripts",
        ignore=shutil.ignore_patterns("__pycache__"),
    )
    (workspace / "notes.md").write_text("base note\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.invalid"], cwd=workspace, check=True)
    subprocess.run(["git", "config", "user.name", "MMAG REV-06C"], cwd=workspace, check=True)
    subprocess.run(["git", "add", "scripts", "notes.md"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-qm", "base fixture"], cwd=workspace, check=True)
    base_revision = _git(workspace, "rev-parse", "HEAD")
    (workspace / "notes.md").write_text("result note\n", encoding="utf-8")
    subprocess.run(["git", "add", "notes.md"], cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-qm", "result fixture"], cwd=workspace, check=True)
    result_revision = _git(workspace, "rev-parse", "HEAD")

    case_id = "CASE-REAL-06C"
    revision_id = "REV-REAL-06C"
    manifest_path = _write_manifest(workspace, case_id)
    checks = required_checks_for("R0", ["notes.md"], change_surfaces=["text_only"])
    before_hash = hashlib.sha256(b"base note\n").hexdigest()
    after_hash = hashlib.sha256(b"result note\n").hexdigest()
    impact = {
        "record_type": "change_impact_record",
        "revision_id": revision_id,
        "case_id": case_id,
        "base_git_revision": base_revision,
        "new_git_revision": result_revision,
        "executor_id": "executor-1",
        "approval_id": None,
        "source_review_id": None,
        "finding_ids": [],
        "change_level": "R0",
        "change_surfaces": ["text_only"],
        "changed_files": ["notes.md"],
        "before_hashes": {"notes.md": before_hash},
        "after_hashes": {"notes.md": after_hash},
        "affected_gates": [],
        "gate_impact": "no_gate_impact",
        "affected_claims": [],
        "affected_experiments": [],
        "affected_figures": [],
        "required_checks": checks,
        "required_review_nodes": [],
        "candidate_submission_pdf": False,
        "candidate_pdf_path": None,
        "candidate_pdf_sha256": None,
        "unresolved_findings": [],
        "modified_by": "modifier-1",
        "project_manifest_path": "manifest.yaml",
        "project_manifest_sha256": _sha256(manifest_path),
        "review_bindings": [],
        "validation_status": "pending",
    }
    impact_path = workspace / "impact.yaml"
    impact_path.write_text(yaml.safe_dump(impact, sort_keys=False), encoding="utf-8")

    command = [
        sys.executable,
        str(workspace / "scripts/run_trusted_check.py"),
        "--workspace", str(workspace),
        "--revision-id", revision_id,
        "--case-id", case_id,
        "--change-level", "R0",
        "--change-surface", "text_only",
        "--changed-file", "notes.md",
        "--output-record", "validation.yaml",
        "--evidence-root", "evidence/REV-REAL-06C",
        "--base-git-revision", base_revision,
        "--new-git-revision", result_revision,
        "--change-record", "impact.yaml",
        "--manifest", "manifest.yaml",
        "--base-ref", base_revision,
        "--head-ref", result_revision,
        "--closure-id", "CLOSURE-REAL-06C",
        "--executor-id", "executor-1",
        "--modifier-id", "modifier-1",
    ]
    process = subprocess.run(command, cwd=workspace, text=True, capture_output=True, check=False)
    if process.returncode != 0:
        raise AssertionError(f"real trusted runner failed: {process.stdout}\n{process.stderr}")
    validation_path = workspace / "validation.yaml"
    validation = yaml.safe_load(validation_path.read_text(encoding="utf-8"))

    review = {
        "record_type": "review_record",
        "review_id": "REV-INDEPENDENT-REAL-06C",
        "case_id": case_id,
        "target_revision": revision_id,
        "target_git_revision": result_revision,
        "reviewer_role": "independent_adversary",
        "reviewer_id": "reviewer-1",
        "critical_node": "C3",
        "review_mode": "results",
        "review_lens": ["evidence_claim_audit", "implementation_consistency", "invariant_counterexample"],
        "primary_method_family": "mixed_integer_programming",
        "alternative_method_family": "constraint_programming",
        "methodological_difference": {
            "axis": "evidence_audit",
            "primary_assumption": "recorded result is reproducible",
            "alternative_assumption": "recorded result may be stale",
            "discriminating_test": "rerun the protected runner",
        },
        "critical_decisions_reviewed": ["revision acceptance"],
        "disconfirming_tests": [{
            "test_id": "T-REAL-06C",
            "target": "Git change facts",
            "input_or_case": "notes.md revision",
            "expected_falsifier": "mismatched diff or hash",
            "actual_result": "recorded facts match the commits",
            "evidence": ["validation.yaml"],
            "status": "passed",
        }],
        "counterexamples": [],
        "what_was_checked": ["trusted validation record"],
        "what_was_not_checked": ["competition-specific modeling quality"],
        "human_decisions_required": [],
        "target_artifacts": ["validation.yaml"],
        "input_bindings": [{"path": "notes.md", "sha256": after_hash, "artifact_kind": "changed_text"}],
        "verdict": "PASS_WITH_LIMITATIONS",
        "findings": [],
        "unresolved_questions": [],
        "uncertainty": ["fixture is not a competition case"],
        "reviewer_signature": "reviewer-1",
        "created_at": "2026-08-28T00:00:00+00:00",
    }
    review_path = workspace / "review.yaml"
    review_path.write_text(yaml.safe_dump(review, sort_keys=False), encoding="utf-8")

    item = {
        "record_type": "work_item",
        "work_item_id": "WI-REAL-06C",
        "case_id": case_id,
        "source_git_revision": base_revision,
        "objective": "exercise an accepted item from a real closure",
        "scope": ["update notes"],
        "non_goals": ["do not change data or model"],
        "allowed_files": ["notes.md"],
        "affected_claims": [],
        "affected_experiments": [],
        "affected_gates": [],
        "required_checks": checks,
        "change_level": "R0",
        "change_surfaces": ["text_only"],
        "required_review_nodes": [],
        "executor_id": "executor-1",
        "reviewer_id": "reviewer-1",
        "reviewer_role": "independent_adversary",
        "write_owner_id": "executor-1",
        "result_git_revision": result_revision,
        "test_evidence": [
            {"check_id": entry["check_id"], "status": "passed", "evidence_path": entry["stdout_path"], "sha256": entry["stdout_sha256"]}
            for entry in validation["check_results"]
        ],
        "status": "accepted",
        "previous_status": "review_ready",
        "unresolved_items": [],
        "revision_id": revision_id,
        "report_path": "report.md",
        "human_decisions_required": [],
        "trusted_validation_record_path": "validation.yaml",
        "trusted_validation_record_sha256": _sha256(validation_path),
        "trusted_validation_record_id": validation["closure_id"],
        "trusted_change_impact_path": "impact.yaml",
        "trusted_change_impact_sha256": _sha256(impact_path),
        "review_verdict_path": "review.yaml",
        "review_verdict_sha256": _sha256(review_path),
        "review_id": review["review_id"],
        "reviewer_role": review["reviewer_role"],
    }
    return impact, validation, item
