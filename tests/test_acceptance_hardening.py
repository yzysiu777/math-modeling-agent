import hashlib
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import yaml

from scripts.check_revision_closure import validate_revision_closure
from scripts.classify_change import classify_change
from scripts.check_review_bindings import validate_review_bindings
from scripts.gate_contract import affected_gates_for_surfaces
from scripts.check_transition import validate_transition

from test_revision_contract import build_records


class AcceptanceHardeningTests(unittest.TestCase):
    def _review_binding_case(self, mutate_review):
        holder = tempfile.TemporaryDirectory()
        workspace = Path(holder.name)
        (workspace / "scripts").mkdir()
        (workspace / "scripts/run_trusted_check.py").write_text("trusted runner\n", encoding="utf-8")
        impact, validation = build_records(workspace, level="R3", surfaces=["data_contract"], changed_files=["data/labels.csv"])
        bindings = deepcopy(validation["review_bindings"])
        binding = bindings[0]
        review_path = workspace / binding["path"]
        review = yaml.safe_load(review_path.read_text(encoding="utf-8"))
        mutate_review(review)
        review_path.write_text(yaml.safe_dump(review, sort_keys=False), encoding="utf-8")
        binding["sha256"] = hashlib.sha256(review_path.read_bytes()).hexdigest()
        binding["input_bindings"] = review["input_bindings"]
        binding["target_git_revision"] = review["target_git_revision"]
        errors = validate_review_bindings(
            bindings,
            impact["required_review_nodes"],
            case_id=impact["case_id"],
            revision_id=impact["revision_id"],
            workspace=workspace,
            manifest=yaml.safe_load((workspace / "manifest.yaml").read_text(encoding="utf-8")),
            target_git_revision=impact["new_git_revision"],
        )
        return holder, errors

    def test_ten_plain_manual_attestation_files_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "scripts").mkdir()
            (workspace / "scripts/run_trusted_check.py").write_text("trusted runner\n", encoding="utf-8")
            impact, validation = build_records(workspace, level="R3", surfaces=["data_contract"], changed_files=["data/labels.csv"])
            plain_count = 0
            for result in validation["check_results"]:
                if result["execution_kind"] != "human_attestation":
                    continue
                path = workspace / result["attestation_path"]
                path.write_text("ordinary text pretending to be an attestation\n", encoding="utf-8")
                result["attestation_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
                plain_count += 1
            self.assertEqual(plain_count, 10)
            errors = validate_revision_closure(impact, validation, workspace=workspace)
            self.assertTrue(any("structured manual attestation" in error or "cannot be read" in error for error in errors))

    def test_executor_self_and_expired_approval_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "scripts").mkdir()
            (workspace / "scripts/run_trusted_check.py").write_text("trusted runner\n", encoding="utf-8")
            impact, validation = build_records(workspace)
            impact.update({"approval_id": "APR-EXPIRED", "source_review_id": "REV-APPROVAL", "finding_ids": ["F-1"]})
            validation.update({"approval_id": "APR-EXPIRED", "source_review_id": "REV-APPROVAL", "finding_ids": ["F-1"]})
            approval = {
                "record_type": "approved_findings", "status": "approved", "approval_id": "APR-EXPIRED",
                "case_id": impact["case_id"], "review_id": "REV-APPROVAL", "approver": "human_owner",
                "approver_id": impact["executor_id"], "approver_role": "human_owner",
                "approved_at": "2026-08-27T00:00:00+00:00", "expires_at": "2026-08-27T00:01:00+00:00",
                "finding_ids": ["F-1"], "revision_id": impact["revision_id"],
                "base_git_revision": impact["base_git_revision"], "new_git_revision": impact["new_git_revision"],
                "change_level": impact["change_level"], "change_surfaces": impact["change_surfaces"],
                "affected_gates": impact["affected_gates"], "gate_impact": impact["gate_impact"],
                "allowed_files": ["notes.md"], "forbidden_files": [], "validation_check_ids": impact["required_checks"],
                "required_review_nodes": [], "review_bindings": [], "candidate_submission_pdf": False,
                "candidate_pdf_path": None, "candidate_pdf_sha256": None, "executor_id": impact["executor_id"],
                "modified_by": impact["modified_by"], "project_manifest_path": impact["project_manifest_path"],
                "project_manifest_sha256": impact["project_manifest_sha256"],
            }
            errors = validate_revision_closure(impact, validation, approval, workspace=workspace)
            self.assertTrue(any("expired" in error for error in errors))
            self.assertTrue(any("cannot approve" in error for error in errors))

    def test_text_only_conflicts_with_data_and_code_paths(self):
        for path in ("data/labels.csv", "data/split.csv", "src/model.py"):
            result = classify_change([path], surfaces=["text_only"])
            self.assertIsNone(result["change_level"], path)
            self.assertTrue(result["requires_human_classification"], path)

    def test_model_and_objective_surfaces_do_not_freeze_inputs(self):
        self.assertIn("G1", affected_gates_for_surfaces(["data_contract"]))
        self.assertNotIn("G1", affected_gates_for_surfaces(["model_formula"]))
        self.assertNotIn("G1", affected_gates_for_surfaces(["objective_constraint"]))

    def test_review_binding_cannot_reuse_one_review_for_two_nodes(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "scripts").mkdir()
            (workspace / "scripts/run_trusted_check.py").write_text("trusted runner\n", encoding="utf-8")
            impact, validation = build_records(workspace, level="R3", surfaces=["data_contract"], changed_files=["data/labels.csv"])
            bindings = list(validation["review_bindings"])
            bindings[1] = dict(bindings[1], review_id=bindings[0]["review_id"], path=bindings[0]["path"], sha256=bindings[0]["sha256"])
            errors = validate_review_bindings(
                bindings, impact["required_review_nodes"], case_id=impact["case_id"], revision_id=impact["revision_id"], workspace=workspace,
                target_git_revision=impact["new_git_revision"],
            )
            self.assertTrue(any("reused" in error or "more than once" in error for error in errors))

    def test_review_all_zero_input_hash_fails_closed(self):
        holder, errors = self._review_binding_case(
            lambda review: review["input_bindings"][0].update({"sha256": "0" * 64})
        )
        try:
            self.assertTrue(any("all-zero" in error for error in errors))
        finally:
            holder.cleanup()

    def test_review_missing_input_file_fails_closed(self):
        holder, errors = self._review_binding_case(
            lambda review: review["input_bindings"][0].update({"path": "inputs/missing.csv"})
        )
        try:
            self.assertTrue(any("does not exist" in error for error in errors))
        finally:
            holder.cleanup()

    def test_review_wrong_input_hash_fails_closed(self):
        holder, errors = self._review_binding_case(
            lambda review: review["input_bindings"][0].update({"sha256": "f" * 64})
        )
        try:
            self.assertTrue(any("does not match" in error for error in errors))
        finally:
            holder.cleanup()

    def test_review_forged_target_git_revision_fails_closed(self):
        holder, errors = self._review_binding_case(
            lambda review: review.update({"target_git_revision": "b" * 40})
        )
        try:
            self.assertTrue(any("result Git revision" in error or "real full commit" in error for error in errors))
        finally:
            holder.cleanup()

    def test_transition_reads_the_hashed_closure_file(self):
        with tempfile.TemporaryDirectory() as temp:
            workspace = Path(temp)
            (workspace / "scripts").mkdir()
            (workspace / "scripts/run_trusted_check.py").write_text("trusted runner\n", encoding="utf-8")
            impact, validation = build_records(workspace)
            closure_path = workspace / "closure.yaml"
            closure_path.write_text(yaml.safe_dump(validation, sort_keys=False), encoding="utf-8")
            closure_hash = hashlib.sha256(closure_path.read_bytes()).hexdigest()
            altered = dict(validation, validation_status="failed")
            ok, _ = validate_transition(
                "targeted_validation", "validation_passed", actor="validator", evidence=["passed"],
                validation_status="passed", closure_report=altered, closure_impact=impact,
                closure_id=validation["closure_id"], closure_path="closure.yaml",
                closure_sha256=closure_hash, workspace=workspace,
            )
            self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()
