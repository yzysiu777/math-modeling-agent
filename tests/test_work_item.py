import hashlib
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.check_work_item import validate_work_item, validate_work_item_set
from scripts.gate_contract import required_checks_for
from test_revision_contract import build_records


def valid_item(workspace: Path, **overrides):
    (workspace / "scripts").mkdir(parents=True, exist_ok=True)
    (workspace / "scripts/run_trusted_check.py").write_text("trusted runner\n", encoding="utf-8")
    manifest = workspace / "manifest.yaml"
    manifest.write_text(
        "record_type: project_manifest\ncase_id: CASE-1\n"
        "owner:\n  name: owner\n  owner_id: owner-1\n  role: human_owner\n"
        "identity_allowlist:\n  - id: owner-1\n    role: human_owner\n"
        "  - id: reviewer-1\n    role: independent_adversary\n",
        encoding="utf-8",
    )
    evidence = []
    item = {
        "record_type": "work_item", "work_item_id": "WI-1", "case_id": "CASE-1",
        "source_git_revision": "a" * 40, "objective": "update a note", "scope": ["update report"],
        "non_goals": ["do not change data"], "allowed_files": ["cases/CASE-1/coordination/report.md"],
        "affected_claims": [], "affected_experiments": [], "affected_gates": [],
        "required_checks": required_checks_for("R0", ["cases/CASE-1/coordination/report.md"], change_surfaces=["text_only"]),
        "change_level": "R0", "change_surfaces": ["text_only"], "required_review_nodes": [],
        "executor_id": "executor-1", "reviewer_id": "reviewer-1", "write_owner_id": "executor-1",
        "result_git_revision": "b" * 40, "test_evidence": [], "status": "accepted",
        "previous_status": "review_ready",
        "trusted_validation_record_path": "validation.yaml",
        "trusted_validation_record_sha256": None,
        "trusted_validation_record_id": "CLOSURE-1",
        "trusted_change_impact_path": None, "trusted_change_impact_sha256": None,
        "review_verdict_path": "review.yaml", "review_verdict_sha256": None,
        "review_id": "REV-C3-1", "reviewer_role": "independent_adversary",
        "unresolved_items": [], "revision_id": "REV-1", "report_path": "cases/CASE-1/coordination/report.md",
        "human_decisions_required": [],
    }
    for index, check_id in enumerate(item["required_checks"]):
        path = workspace / f"evidence/{index}-{check_id}.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("passed\n", encoding="utf-8")
        evidence.append({"check_id": check_id, "status": "passed", "evidence_path": str(path.relative_to(workspace)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    item["test_evidence"] = evidence
    validation_results = []
    for index, check_id in enumerate(item["required_checks"]):
        stderr_path = workspace / f"evidence/{index}-{check_id}.stderr.log"
        stderr_path.write_text("", encoding="utf-8")
        validation_results.append({
            "check_id": check_id, "status": "passed", "execution_kind": "trusted_runner", "executor": "trusted_check_runner", "exit_code": 0,
            "stdout_path": str(Path(evidence[index]["evidence_path"])), "stdout_sha256": evidence[index]["sha256"],
            "stderr_path": str(stderr_path.relative_to(workspace)), "stderr_sha256": hashlib.sha256(stderr_path.read_bytes()).hexdigest(),
        })
    validation = {
        "record_type": "revision_validation_record", "closure_id": "CLOSURE-1", "case_id": "CASE-1", "revision_id": "REV-1",
        "base_git_revision": "a" * 40, "new_git_revision": "b" * 40, "executor_id": "executor-1", "modifier_id": "modifier-1", "runner_id": "trusted_check_runner", "runner_version": "1.0.0",
        "change_level": "R0", "change_surfaces": ["text_only"], "execution_started_at": "2026-08-27T00:00:00+00:00", "execution_finished_at": "2026-08-27T00:00:01+00:00", "validation_status": "passed",
        "runner_script": "scripts/run_trusted_check.py", "runner_script_sha256": hashlib.sha256((workspace / "scripts/run_trusted_check.py").read_bytes()).hexdigest(),
        "project_manifest_path": "manifest.yaml", "project_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "evidence_root": "evidence", "check_results": validation_results,
    }
    validation_path = workspace / "validation.yaml"
    validation_path.write_text(yaml.safe_dump(validation, sort_keys=False), encoding="utf-8")
    review = {
        "record_type": "review_record", "review_id": "REV-C3-1", "case_id": "CASE-1", "target_revision": "REV-1",
        "reviewer_role": "independent_adversary", "reviewer_id": "reviewer-1", "critical_node": "C3", "review_mode": "results",
        "review_lens": ["evidence_claim_audit", "implementation_consistency", "invariant_counterexample"],
        "primary_method_family": "mixed_integer_programming", "alternative_method_family": "constraint_programming",
        "methodological_difference": {"axis": "feasibility", "primary_assumption": "primary", "alternative_assumption": "alternative", "discriminating_test": "small case"},
        "critical_decisions_reviewed": ["decision"],
        "disconfirming_tests": [{"test_id": "T-1", "target": "result", "input_or_case": "small", "expected_falsifier": "wrong", "actual_result": "none", "evidence": ["validation.yaml"], "status": "passed"}],
        "counterexamples": [], "what_was_checked": ["result"], "what_was_not_checked": ["scale"], "human_decisions_required": [],
        "target_artifacts": ["validation.yaml"], "input_hashes": ["0" * 64], "verdict": "PASS_WITH_LIMITATIONS", "findings": [],
        "unresolved_questions": [], "uncertainty": ["scale"], "reviewer_signature": "reviewer-1", "created_at": "2026-08-27T00:00:00+00:00",
    }
    review_path = workspace / "review.yaml"
    review_path.write_text(yaml.safe_dump(review, sort_keys=False), encoding="utf-8")
    item["trusted_validation_record_sha256"] = hashlib.sha256(validation_path.read_bytes()).hexdigest()
    item["review_verdict_sha256"] = hashlib.sha256(review_path.read_bytes()).hexdigest()
    item.update(overrides)
    return item


def trusted_item(workspace: Path):
    impact, validation = build_records(workspace)
    impact_path = workspace / "impact.yaml"
    validation_path = workspace / "validation-closure.yaml"
    impact_path.write_text(yaml.safe_dump(impact, sort_keys=False), encoding="utf-8")
    validation_path.write_text(yaml.safe_dump(validation, sort_keys=False), encoding="utf-8")
    input_path = workspace / "inputs/source-data.csv"
    review = {
        "record_type": "review_record", "review_id": "REV-C3-TRUSTED", "case_id": impact["case_id"],
        "target_revision": impact["revision_id"], "target_git_revision": impact["new_git_revision"],
        "reviewer_role": "independent_adversary", "reviewer_id": "reviewer-1", "critical_node": "C3", "review_mode": "results",
        "review_lens": ["evidence_claim_audit", "implementation_consistency", "invariant_counterexample"],
        "primary_method_family": "mixed_integer_programming", "alternative_method_family": "constraint_programming",
        "methodological_difference": {"axis": "feasibility", "primary_assumption": "primary", "alternative_assumption": "alternative", "discriminating_test": "small case"},
        "critical_decisions_reviewed": ["decision"],
        "disconfirming_tests": [{"test_id": "T-1", "target": "result", "input_or_case": "small", "expected_falsifier": "wrong", "actual_result": "none", "evidence": ["validation-closure.yaml"], "status": "passed"}],
        "counterexamples": [], "what_was_checked": ["result"], "what_was_not_checked": ["scale"],
        "human_decisions_required": [], "target_artifacts": ["validation-closure.yaml"],
        "input_bindings": [{"path": str(input_path.relative_to(workspace)), "sha256": hashlib.sha256(input_path.read_bytes()).hexdigest(), "artifact_kind": "source_data"}],
        "verdict": "PASS_WITH_LIMITATIONS", "findings": [], "unresolved_questions": [], "uncertainty": ["scale"],
        "reviewer_signature": "reviewer-1", "created_at": "2026-08-27T00:00:00+00:00",
    }
    review_path = workspace / "review-verdict.yaml"
    review_path.write_text(yaml.safe_dump(review, sort_keys=False), encoding="utf-8")
    return {
        "record_type": "work_item", "work_item_id": "WI-TRUSTED", "case_id": impact["case_id"],
        "source_git_revision": impact["base_git_revision"], "objective": "update a note", "scope": ["update report"],
        "non_goals": ["do not change data"], "allowed_files": ["notes.md"], "affected_claims": [],
        "affected_experiments": [], "affected_gates": impact["affected_gates"], "required_checks": impact["required_checks"],
        "change_level": impact["change_level"], "change_surfaces": impact["change_surfaces"],
        "required_review_nodes": impact["required_review_nodes"], "executor_id": "executor-1", "reviewer_id": "reviewer-1",
        "write_owner_id": "executor-1", "result_git_revision": impact["new_git_revision"], "test_evidence": [
            {"check_id": entry["check_id"], "status": "passed", "evidence_path": entry["stdout_path"], "sha256": entry["stdout_sha256"]}
            for entry in validation["check_results"]
        ],
        "status": "accepted", "previous_status": "review_ready", "unresolved_items": [], "revision_id": impact["revision_id"],
        "report_path": "report.md", "human_decisions_required": [],
        "trusted_validation_record_path": str(validation_path.relative_to(workspace)),
        "trusted_validation_record_sha256": hashlib.sha256(validation_path.read_bytes()).hexdigest(),
        "trusted_validation_record_id": validation["closure_id"],
        "trusted_change_impact_path": str(impact_path.relative_to(workspace)),
        "trusted_change_impact_sha256": hashlib.sha256(impact_path.read_bytes()).hexdigest(),
        "review_verdict_path": str(review_path.relative_to(workspace)),
        "review_verdict_sha256": hashlib.sha256(review_path.read_bytes()).hexdigest(),
        "review_id": review["review_id"], "reviewer_role": review["reviewer_role"],
    }


class WorkItemTests(unittest.TestCase):
    def test_structured_trusted_closure_can_accept(self):
        with tempfile.TemporaryDirectory() as temp:
            item = trusted_item(Path(temp))
            self.assertEqual(validate_work_item(item, workspace=Path(temp)), [])
            self.assertNotIn("human_frozen", item)

    def test_hand_assembled_validation_record_cannot_accept(self):
        with tempfile.TemporaryDirectory() as temp:
            item = valid_item(Path(temp), status="accepted")
            item["previous_status"] = "review_ready"
            errors = validate_work_item(item, workspace=Path(temp), source_ref="a" * 40, result_ref="b" * 40)
            self.assertTrue(any("trusted change impact record" in error or "revision closure" in error for error in errors))
            self.assertNotIn("human_frozen", item)

    def test_self_review_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            item = valid_item(Path(temp), reviewer_id="executor-1")
            self.assertTrue(any("self-review" in error for error in validate_work_item(item, workspace=Path(temp))))

    def test_source_or_result_revision_mismatch_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            item = valid_item(Path(temp))
            errors = validate_work_item(item, workspace=Path(temp), source_ref="c" * 40, result_ref="d" * 40)
            self.assertTrue(any("source_git_revision" in error for error in errors))
            self.assertTrue(any("result_git_revision" in error for error in errors))

    def test_missing_required_check_and_unresolved_p1_block_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            item = valid_item(Path(temp), test_evidence=[], unresolved_items=[{"id": "F-1", "severity": "P1", "statement": "open"}])
            errors = validate_work_item(item, workspace=Path(temp))
            self.assertTrue(any("cover every required check" in error for error in errors))
            self.assertTrue(any("unresolved P0/P1" in error for error in errors))

    def test_overlapping_active_scopes_are_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            left = valid_item(Path(temp), work_item_id="WI-1", status="executing", allowed_files=["cases/CASE-1/coordination/"])
            right = valid_item(Path(temp), work_item_id="WI-2", status="review_ready", allowed_files=["cases/CASE-1/coordination/report.md"])
            errors = validate_work_item_set([left, right], workspace=Path(temp))
            self.assertTrue(any("overlapping active" in error for error in errors))

    def test_proposed_cannot_jump_directly_to_accepted(self):
        with tempfile.TemporaryDirectory() as temp:
            item = valid_item(Path(temp), status="accepted", previous_status="proposed")
            errors = validate_work_item(item, workspace=Path(temp))
            self.assertTrue(any("review_ready" in error or "proposed" in error for error in errors))

    def test_fake_logs_and_reviewer_string_cannot_accept(self):
        with tempfile.TemporaryDirectory() as temp:
            item = valid_item(Path(temp), trusted_validation_record_path="self-made.log", review_verdict_path="reviewer.log")
            Path(temp, "self-made.log").write_text("passed", encoding="utf-8")
            Path(temp, "reviewer.log").write_text("reviewer_id: anyone", encoding="utf-8")
            item["trusted_validation_record_sha256"] = hashlib.sha256(Path(temp, "self-made.log").read_bytes()).hexdigest()
            item["review_verdict_sha256"] = hashlib.sha256(Path(temp, "reviewer.log").read_bytes()).hexdigest()
            errors = validate_work_item(item, workspace=Path(temp))
            self.assertTrue(any("record" in error or "verdict" in error or "cannot be parsed" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
