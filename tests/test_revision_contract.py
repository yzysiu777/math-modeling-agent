import unittest

from scripts.check_revision_closure import validate_revision_closure
from scripts.classify_change import classify_change
from scripts.gate_contract import required_checks_for
from scripts.plan_targeted_validation import plan_validation


class RevisionContractTests(unittest.TestCase):
    def test_r0_tex_only_gets_fast_compile(self):
        result = classify_change(["paper/sections/01-problem.tex"], ["text"])
        self.assertEqual(result["change_level"], "R0")
        self.assertIn("latex_fast_compile", result["required_checks"])
        self.assertNotIn("affected_experiment_rerun", result["required_checks"])

    def test_r3_plan_has_model_checks(self):
        result = plan_validation("R3", ["data/labels.csv"])
        self.assertIn("feasibility_check", result["required_checks"])
        self.assertIn("objective_recompute", result["required_checks"])
        self.assertIn("robustness_check", result["required_checks"])

    def test_r1_numeric_change_requires_claim_binding(self):
        result = plan_validation("R1", ["paper/results.tex"])
        self.assertIn("claim_experiment_binding", result["required_checks"])
        self.assertIn("citation_crossref_check", result["required_checks"])

    def test_r2_code_change_requires_tests_and_experiment_rerun(self):
        result = plan_validation("R2", ["src/model.py"])
        self.assertIn("code_tests", result["required_checks"])
        self.assertIn("affected_experiment_rerun", result["required_checks"])
        self.assertIn("new_experiment_record", result["required_checks"])

    def test_r0_cannot_close_with_experiment(self):
        impact = {
            "record_type": "change_impact_record", "revision_id": "REV-R0", "case_id": "CASE-1",
            "base_git_revision": "base", "new_git_revision": "new", "change_level": "R0",
            "changed_files": ["notes.md"], "affected_gates": [], "affected_claims": [],
            "affected_experiments": ["EXP-OLD"],
            "required_checks": required_checks_for("R0", ["notes.md"]), "modified_by": "codex",
        }
        validation = {
            "record_type": "revision_validation_record", "revision_id": "REV-R0", "case_id": "CASE-1",
            "base_git_revision": "base", "new_git_revision": "new", "change_level": "R0",
            "changed_files": ["notes.md"], "executed_checks": impact["required_checks"],
            "check_exit_codes": {check: 0 for check in impact["required_checks"]},
            "check_outputs": {check: "pass" for check in impact["required_checks"]},
            "output_hashes": {}, "new_experiment_ids": ["EXP-NEW"], "claim_status_updates": [],
            "closed_findings": [], "unresolved_findings": [], "validator": "codex", "validation_status": "passed",
        }
        errors = validate_revision_closure(impact, validation)
        self.assertTrue(any("R0" in error and "experiment" in error for error in errors))

    def test_missing_required_execution_evidence_fails(self):
        impact = {
            "record_type": "change_impact_record",
            "revision_id": "REV-1",
            "case_id": "CASE-1",
            "base_git_revision": "base",
            "new_git_revision": "new",
            "change_level": "R1",
            "changed_files": ["paper/main.tex"],
            "affected_gates": ["G9", "G10", "G11"],
            "affected_claims": [],
            "affected_experiments": [],
            "required_checks": ["file_allowlist", "latex_compile"],
            "modified_by": "codex",
        }
        validation = {
            "record_type": "revision_validation_record",
            "revision_id": "REV-1",
            "case_id": "CASE-1",
            "base_git_revision": "base",
            "new_git_revision": "new",
            "change_level": "R1",
            "changed_files": ["paper/main.tex"],
            "executed_checks": ["file_allowlist"],
            "check_exit_codes": {"file_allowlist": 0},
            "check_outputs": {"file_allowlist": "pass"},
            "validation_status": "passed",
            "new_experiment_ids": [],
            "claim_status_updates": [],
            "closed_findings": [],
            "unresolved_findings": [],
        }
        errors = validate_revision_closure(impact, validation)
        self.assertTrue(any("lack execution" in error for error in errors))

    def test_failed_required_check_cannot_close(self):
        impact = {
            "record_type": "change_impact_record", "revision_id": "REV-FAIL", "case_id": "CASE-1",
            "base_git_revision": "base", "new_git_revision": "new", "change_level": "R1",
            "changed_files": ["paper/main.tex"], "affected_gates": ["G9", "G10", "G11"],
            "affected_claims": [], "affected_experiments": [],
            "required_checks": required_checks_for("R1", ["paper/main.tex"]), "modified_by": "codex",
        }
        validation = {
            "record_type": "revision_validation_record", "revision_id": "REV-FAIL", "case_id": "CASE-1",
            "base_git_revision": "base", "new_git_revision": "new", "change_level": "R1",
            "changed_files": ["paper/main.tex"], "executed_checks": impact["required_checks"],
            "check_exit_codes": {check: (1 if check == "latex_compile" else 0) for check in impact["required_checks"]},
            "check_outputs": {check: "failed" if check == "latex_compile" else "pass" for check in impact["required_checks"]},
            "output_hashes": {}, "new_experiment_ids": [], "claim_status_updates": [],
            "closed_findings": [], "unresolved_findings": [], "validator": "codex", "validation_status": "passed",
        }
        errors = validate_revision_closure(impact, validation)
        self.assertTrue(any("required check failed" in error for error in errors))

    def test_high_risk_finding_cannot_be_closed_by_modifier(self):
        impact = {
            "record_type": "change_impact_record", "revision_id": "REV-P1", "case_id": "CASE-1",
            "base_git_revision": "base", "new_git_revision": "new", "change_level": "R1",
            "changed_files": ["paper/main.tex"], "affected_gates": ["G9", "G10", "G11"],
            "affected_claims": [], "affected_experiments": [],
            "required_checks": required_checks_for("R1", ["paper/main.tex"]), "modified_by": "codex",
        }
        validation = {
            "record_type": "revision_validation_record", "revision_id": "REV-P1", "case_id": "CASE-1",
            "base_git_revision": "base", "new_git_revision": "new", "change_level": "R1",
            "changed_files": ["paper/main.tex"], "executed_checks": impact["required_checks"],
            "check_exit_codes": {check: 0 for check in impact["required_checks"]},
            "check_outputs": {check: "pass" for check in impact["required_checks"]},
            "output_hashes": {}, "new_experiment_ids": [], "claim_status_updates": [],
            "closed_findings": [{"finding_id": "F-1", "severity": "P1", "closed_by": "codex"}],
            "unresolved_findings": [], "validator": "codex", "validation_status": "passed",
        }
        errors = validate_revision_closure(impact, validation)
        self.assertTrue(any("modifier" in error for error in errors))

    def test_r3_omitting_feasibility_or_objective_check_cannot_close(self):
        required = ["file_allowlist"]
        impact = {
            "record_type": "change_impact_record", "revision_id": "REV-R3", "case_id": "CASE-1",
            "base_git_revision": "base", "new_git_revision": "new", "change_level": "R3",
            "changed_files": ["data/labels.csv"], "affected_gates": ["G1", "G2", "G4", "G5", "G6", "G7", "G8", "G9"],
            "affected_claims": [], "affected_experiments": [], "required_checks": required, "modified_by": "codex",
        }
        validation = {
            "record_type": "revision_validation_record", "revision_id": "REV-R3", "case_id": "CASE-1",
            "base_git_revision": "base", "new_git_revision": "new", "change_level": "R3",
            "changed_files": ["data/labels.csv"], "executed_checks": required,
            "check_exit_codes": {"file_allowlist": 0}, "check_outputs": {"file_allowlist": "pass"},
            "output_hashes": {}, "new_experiment_ids": [], "claim_status_updates": [],
            "closed_findings": [], "unresolved_findings": [], "validator": "codex", "validation_status": "passed",
        }
        errors = validate_revision_closure(impact, validation)
        self.assertTrue(any("feasibility_check" in error for error in errors))
        self.assertTrue(any("objective_recompute" in error for error in errors))

    def test_valid_r2_closure_requires_new_experiment_and_hash(self):
        required = required_checks_for("R2", ["src/model.py"])
        impact = {
            "record_type": "change_impact_record",
            "revision_id": "REV-2",
            "case_id": "CASE-1",
            "base_git_revision": "base",
            "new_git_revision": "new",
            "change_level": "R2",
            "changed_files": ["src/model.py"],
            "affected_gates": ["G4", "G5", "G6", "G7", "G8", "G9"],
            "affected_claims": ["CLM-1"],
            "affected_experiments": ["EXP-OLD"],
            "required_checks": required,
            "modified_by": "codex",
        }
        validation = {
            "record_type": "revision_validation_record",
            "revision_id": "REV-2",
            "case_id": "CASE-1",
            "base_git_revision": "base",
            "new_git_revision": "new",
            "change_level": "R2",
            "changed_files": ["src/model.py"],
            "executed_checks": required,
            "check_exit_codes": {check: 0 for check in required},
            "check_outputs": {check: "pass" for check in required},
            "output_hashes": {"results.json": "0" * 64},
            "new_experiment_ids": ["EXP-NEW"],
            "claim_status_updates": [{"claim_id": "CLM-1", "status": "revalidated"}],
            "closed_findings": [],
            "unresolved_findings": [],
            "validator": "reproducibility_engineer",
            "validation_status": "passed",
        }
        self.assertEqual(validate_revision_closure(impact, validation), [])


if __name__ == "__main__":
    unittest.main()
