import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.check_revision_closure import validate_revision_closure
from scripts.classify_change import classify_change
from scripts.gate_contract import (
    CHECK_IMPLEMENTATION_STATUS,
    affected_gates_for_surfaces,
    required_checks_for,
    required_review_nodes_for,
)
from scripts.plan_targeted_validation import plan_validation


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_workspace() -> tuple[tempfile.TemporaryDirectory, Path]:
    holder = tempfile.TemporaryDirectory()
    workspace = Path(holder.name)
    runner = workspace / "scripts/run_trusted_check.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("trusted runner fixture\n", encoding="utf-8")
    return holder, workspace


def build_records(workspace: Path, *, level="R0", surfaces=None, changed_files=None, affected_experiments=None, affected_claims=None):
    surfaces = surfaces or ["text_only"]
    changed_files = changed_files or ["notes.md"]
    affected_experiments = affected_experiments or []
    affected_claims = affected_claims or []
    revision_id = "REV-TEST-001"
    case_id = "CASE-TEST-001"
    checks = required_checks_for(level, changed_files, change_surfaces=surfaces)
    evidence_root = workspace / "evidence" / revision_id
    evidence_root.mkdir(parents=True)
    check_results = []
    for index, check_id in enumerate(checks, start=1):
        stdout = evidence_root / f"{index:02d}-{check_id}.stdout"
        stderr = evidence_root / f"{index:02d}-{check_id}.stderr"
        stdout.write_text(f"{check_id} passed\n", encoding="utf-8")
        stderr.write_text("", encoding="utf-8")
        implementation = CHECK_IMPLEMENTATION_STATUS[check_id]
        entry = {
            "check_id": check_id,
            "status": "passed",
            "execution_kind": "trusted_runner" if implementation == "implemented" else "human_attestation",
            "executor": "trusted_check_runner" if implementation == "implemented" else "human-reviewer",
            "started_at": "2026-08-27T00:00:00+00:00",
            "finished_at": "2026-08-27T00:00:01+00:00",
            "exit_code": 0 if implementation == "implemented" else None,
            "stdout_path": str(stdout.relative_to(workspace)),
            "stdout_sha256": digest(stdout),
            "stderr_path": str(stderr.relative_to(workspace)),
            "stderr_sha256": digest(stderr),
            "artifact_hashes": {},
            "attestation_path": None,
            "attestation_sha256": None,
            "notes": "fixture",
        }
        if implementation == "manual_required":
            attestation = evidence_root / f"{index:02d}-{check_id}.attestation"
            attestation.write_text("human evidence\n", encoding="utf-8")
            entry["attestation_path"] = str(attestation.relative_to(workspace))
            entry["attestation_sha256"] = digest(attestation)
        check_results.append(entry)
    output_hashes = {}
    if affected_experiments:
        output = workspace / "results.json"
        output.write_text("{\"ok\": true}\n", encoding="utf-8")
        output_hashes[str(output.relative_to(workspace))] = digest(output)
    gates = affected_gates_for_surfaces(surfaces)
    impact = {
        "record_type": "change_impact_record",
        "revision_id": revision_id,
        "case_id": case_id,
        "base_git_revision": "a" * 40,
        "new_git_revision": "b" * 40,
        "approval_id": None,
        "source_review_id": None,
        "finding_ids": [],
        "change_level": level,
        "change_surfaces": surfaces,
        "changed_files": changed_files,
        "before_hashes": {},
        "after_hashes": {},
        "affected_gates": gates,
        "gate_impact": "no_gate_impact" if level == "R0" else "affected",
        "affected_claims": affected_claims,
        "affected_experiments": affected_experiments,
        "affected_figures": [],
        "required_checks": checks,
        "required_review_nodes": required_review_nodes_for(surfaces),
        "candidate_submission_pdf": False,
        "candidate_pdf_path": None,
        "candidate_pdf_sha256": None,
        "unresolved_findings": [],
        "modified_by": "executor-1",
        "validation_status": "pending",
    }
    validation = {
        "record_type": "revision_validation_record",
        "revision_id": revision_id,
        "case_id": case_id,
        "approval_id": None,
        "source_review_id": None,
        "finding_ids": [],
        "base_git_revision": impact["base_git_revision"],
        "new_git_revision": impact["new_git_revision"],
        "change_level": level,
        "change_surfaces": surfaces,
        "changed_files": changed_files,
        "evidence_root": str(evidence_root.relative_to(workspace)),
        "runner_id": "trusted_check_runner",
        "runner_version": "1.0.0",
        "runner_script": "scripts/run_trusted_check.py",
        "runner_script_sha256": digest(workspace / "scripts/run_trusted_check.py"),
        "execution_started_at": "2026-08-27T00:00:00+00:00",
        "execution_finished_at": "2026-08-27T00:01:00+00:00",
        "check_results": check_results,
        "output_hashes": output_hashes,
        "new_experiment_ids": ["EXP-NEW"] if affected_experiments else [],
        "claim_status_updates": [{"claim_id": item, "status": "revalidated"} for item in affected_claims],
        "closed_findings": [],
        "unresolved_findings": [],
        "validator": "trusted_check_runner",
        "validation_status": "passed",
    }
    return impact, validation


class RevisionContractTests(unittest.TestCase):
    def test_r0_tex_only_gets_fast_compile_and_explicit_no_gate_impact(self):
        result = classify_change(["paper/sections/01-problem.tex"], ["text"])
        self.assertEqual(result["change_level"], "R0")
        self.assertIn("latex_fast_compile", result["required_checks"])
        self.assertEqual(result["affected_gates"], [])
        self.assertNotIn("affected_experiment_rerun", result["required_checks"])

    def test_filename_alone_requires_human_classification(self):
        result = classify_change(["paper/03-model.tex"])
        self.assertIsNone(result["change_level"])
        self.assertTrue(result["requires_human_classification"])
        self.assertEqual(result["required_checks"], [])

    def test_explicit_text_surface_overrides_model_like_filename(self):
        result = classify_change(["paper/03-model.tex"], surfaces=["text_only"])
        self.assertEqual(result["change_level"], "R0")
        self.assertFalse(result["requires_human_classification"])

    def test_r3_plan_has_model_checks(self):
        result = plan_validation("R3", ["data/labels.csv"], change_surfaces=["data_contract"])
        self.assertIn("feasibility_check", result["required_checks"])
        self.assertIn("objective_recompute", result["required_checks"])
        self.assertIn("robustness_check", result["required_checks"])

    def test_r1_numeric_change_requires_claim_binding(self):
        result = plan_validation("R1", ["paper/results.tex"], change_surfaces=["paper_claim"])
        self.assertIn("claim_experiment_binding", result["required_checks"])
        self.assertIn("citation_crossref_check", result["required_checks"])

    def test_r2_code_change_requires_tests_and_experiment_rerun(self):
        result = plan_validation("R2", ["src/model.py"], change_surfaces=["code_only"])
        self.assertIn("code_tests", result["required_checks"])
        self.assertIn("affected_experiment_rerun", result["required_checks"])
        self.assertIn("new_experiment_record", result["required_checks"])

    def test_r0_full_closure_accepts_empty_gate_impact(self):
        holder, workspace = make_workspace()
        try:
            impact, validation = build_records(workspace)
            self.assertEqual(validate_revision_closure(impact, validation, workspace=workspace), [])
        finally:
            holder.cleanup()

    def test_r0_cannot_close_with_experiment(self):
        holder, workspace = make_workspace()
        try:
            impact, validation = build_records(workspace, affected_experiments=["EXP-OLD"])
            errors = validate_revision_closure(impact, validation, workspace=workspace)
            self.assertTrue(any("R0" in error and "experiment" in error for error in errors))
        finally:
            holder.cleanup()

    def test_legacy_hand_filled_evidence_fails_closed(self):
        holder, workspace = make_workspace()
        try:
            impact, validation = build_records(workspace)
            validation["executed_checks"] = list(impact["required_checks"])
            validation["check_exit_codes"] = {check: 0 for check in impact["required_checks"]}
            validation["check_outputs"] = {check: "pass" for check in impact["required_checks"]}
            errors = validate_revision_closure(impact, validation, workspace=workspace)
            self.assertTrue(any("legacy" in error for error in errors))
        finally:
            holder.cleanup()

    def test_missing_log_or_hash_fails_closed(self):
        holder, workspace = make_workspace()
        try:
            impact, validation = build_records(workspace)
            check = validation["check_results"][0]
            (workspace / check["stdout_path"]).unlink()
            errors = validate_revision_closure(impact, validation, workspace=workspace)
            self.assertTrue(any("does not exist" in error for error in errors))
        finally:
            holder.cleanup()

    def test_failed_required_check_cannot_close(self):
        holder, workspace = make_workspace()
        try:
            impact, validation = build_records(workspace)
            validation["check_results"][0]["status"] = "failed"
            validation["check_results"][0]["exit_code"] = 1
            errors = validate_revision_closure(impact, validation, workspace=workspace)
            self.assertTrue(any("failed or is not proven" in error for error in errors))
        finally:
            holder.cleanup()

    def test_p1_same_reviewer_id_cannot_close(self):
        holder, workspace = make_workspace()
        try:
            impact, validation = build_records(workspace)
            impact["finding_ids"] = ["F-1"]
            impact["source_review_id"] = "REV-REVIEW-1"
            validation["finding_ids"] = ["F-1"]
            validation["source_review_id"] = "REV-REVIEW-1"
            validation["closed_findings"] = [{
                "finding_id": "F-1", "severity": "P1", "source_review_id": "REV-REVIEW-1",
                "raised_by": "claude", "raised_by_id": "same-reviewer", "modified_by": "executor",
                "modified_by_id": "executor-1", "closed_by": "independent_adversary",
                "closed_by_id": "same-reviewer", "closure_evidence": ["evidence/recheck.log"],
            }]
            errors = validate_revision_closure(impact, validation, workspace=workspace)
            self.assertTrue(any("third identity" in error for error in errors))
        finally:
            holder.cleanup()

    def test_approval_join_rejects_cross_revision_reuse(self):
        holder, workspace = make_workspace()
        try:
            impact, validation = build_records(workspace)
            impact.update({"approval_id": "APR-1", "source_review_id": "REV-REVIEW-1", "finding_ids": ["F-1"]})
            validation.update({"approval_id": "APR-1", "source_review_id": "REV-REVIEW-1", "finding_ids": ["F-1"]})
            approval = {
                "record_type": "approved_findings", "approval_id": "APR-1", "case_id": impact["case_id"],
                "review_id": "REV-REVIEW-1", "approver": "human_owner", "approved_at": "2026-08-27T00:00:00+00:00",
                "finding_ids": ["F-1"], "revision_id": impact["revision_id"],
                "base_git_revision": impact["base_git_revision"], "new_git_revision": impact["new_git_revision"],
                "change_level": impact["change_level"], "change_surfaces": impact["change_surfaces"],
                "affected_gates": impact["affected_gates"], "gate_impact": impact["gate_impact"],
                "allowed_files": ["notes.md"], "forbidden_files": [],
                "validation_check_ids": impact["required_checks"], "required_review_nodes": [],
                "candidate_submission_pdf": False, "candidate_pdf_path": None, "candidate_pdf_sha256": None,
                "status": "approved",
            }
            self.assertEqual(validate_revision_closure(impact, validation, approval, workspace=workspace), [])
            approval["base_git_revision"] = "c" * 40
            self.assertTrue(any("approval and impact disagree on base_git_revision" in error for error in validate_revision_closure(impact, validation, approval, workspace=workspace)))
        finally:
            holder.cleanup()

    def test_r3_omitting_feasibility_or_objective_check_cannot_close(self):
        holder, workspace = make_workspace()
        try:
            impact, validation = build_records(workspace, level="R3", surfaces=["data_contract"], changed_files=["data/labels.csv"])
            impact["required_checks"] = ["file_allowlist"]
            validation["check_results"] = [validation["check_results"][0]]
            errors = validate_revision_closure(impact, validation, workspace=workspace)
            self.assertTrue(any("feasibility_check" in error for error in errors))
            self.assertTrue(any("objective_recompute" in error for error in errors))
        finally:
            holder.cleanup()

    def test_valid_r2_closure_requires_new_experiment_and_hash(self):
        holder, workspace = make_workspace()
        try:
            impact, validation = build_records(
                workspace,
                level="R2",
                surfaces=["code_only"],
                changed_files=["src/model.py"],
                affected_experiments=["EXP-OLD"],
                affected_claims=["CLM-1"],
            )
            self.assertEqual(validate_revision_closure(impact, validation, workspace=workspace), [])
        finally:
            holder.cleanup()

    def test_candidate_pdf_requires_path_hash_and_pdf_checks(self):
        holder, workspace = make_workspace()
        try:
            pdf = workspace / "candidate.pdf"
            pdf.write_bytes(b"candidate pdf")
            impact, validation = build_records(
                workspace,
                level="R1",
                surfaces=["candidate_pdf"],
                changed_files=["candidate.pdf"],
            )
            impact["candidate_submission_pdf"] = True
            impact["candidate_pdf_path"] = "candidate.pdf"
            impact["candidate_pdf_sha256"] = digest(pdf)
            self.assertEqual(validate_revision_closure(impact, validation, workspace=workspace), [])
            impact["candidate_pdf_sha256"] = "0" * 64
            self.assertTrue(any("candidate PDF hash mismatch" in error for error in validate_revision_closure(impact, validation, workspace=workspace)))
        finally:
            holder.cleanup()


if __name__ == "__main__":
    unittest.main()
