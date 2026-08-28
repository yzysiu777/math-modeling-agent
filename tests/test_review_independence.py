import unittest

from scripts.check_review_independence import validate_review_record


def valid_review(**overrides):
    record = {
        "record_type": "review_record",
        "review_id": "REV-TEST-001",
        "case_id": "CASE-TEST-001",
        "target_revision": "REVISION-TEST-001",
        "target_git_revision": "a" * 40,
        "reviewer_role": "independent_adversary",
        "reviewer_id": "claude-reviewer-1",
        "critical_node": "C2",
        "review_mode": "challenge",
        "review_lens": ["alternative_formulation", "implementation_consistency", "invariant_counterexample"],
        "primary_method_family": "mixed_integer_programming",
        "alternative_method_family": "constraint_programming",
        "methodological_difference": {
            "axis": "feasibility",
            "primary_assumption": "目标函数优先",
            "alternative_assumption": "先传播可行性",
            "discriminating_test": "两任务一资源的小实例",
        },
        "critical_decisions_reviewed": ["capacity constraint"],
        "disconfirming_tests": [{
            "test_id": "TEST-1",
            "target": "capacity constraint",
            "input_or_case": "two tasks one resource",
            "expected_falsifier": "over-capacity schedule",
            "actual_result": "no violation",
            "evidence": ["evidence/test-1.log"],
            "status": "passed",
        }],
        "counterexamples": [],
        "what_was_checked": ["formula-to-code mapping"],
        "what_was_not_checked": ["large-scale solver performance"],
        "uncertainty": ["large-scale solver performance was not independently rerun"],
        "human_decisions_required": ["choose the risk preference"],
        "target_artifacts": ["model.md"],
        "input_bindings": [{"path": "inputs/data.csv", "sha256": "1" * 64, "artifact_kind": "source_data"}],
        "verdict": "PASS_WITH_LIMITATIONS",
        "findings": [],
        "unresolved_questions": [],
        "reviewer_signature": "claude-reviewer-1",
        "created_at": "2026-08-27T00:00:00+00:00",
    }
    record.update(overrides)
    return record


class ReviewIndependenceTests(unittest.TestCase):
    def test_valid_methodological_challenge(self):
        ok, errors = validate_review_record(valid_review())
        self.assertTrue(ok, errors)

    def test_missing_lens_fails(self):
        ok, errors = validate_review_record(valid_review(review_lens=[]))
        self.assertFalse(ok)
        self.assertTrue(any("review_lens" in error for error in errors))

    def test_same_model_without_difference_fails(self):
        ok, errors = validate_review_record(
            valid_review(
                primary_method_family="mixed_integer_programming",
                alternative_method_family="mixed_integer_programming",
            )
        )
        self.assertFalse(ok)
        self.assertTrue(any("different alternative" in error for error in errors))

    def test_pass_without_counterexample_fails(self):
        ok, errors = validate_review_record(
            valid_review(disconfirming_tests=[], counterexamples=[], verdict="PASS")
        )
        self.assertFalse(ok)
        self.assertTrue(any("counterexample" in error or "disconfirming" in error for error in errors))

    def test_planned_only_falsification_cannot_claim_pass(self):
        review = valid_review()
        review["disconfirming_tests"][0]["status"] = "planned"
        ok, errors = validate_review_record(review)
        self.assertFalse(ok)
        self.assertTrue(any("actual result" in error for error in errors))

    def test_generic_review_without_binding_identity_fails(self):
        review = valid_review()
        review.pop("case_id")
        review.pop("target_revision")
        review["input_bindings"] = []
        ok, errors = validate_review_record(review)
        self.assertFalse(ok)
        self.assertTrue(any("case_id" in error or "target_revision" in error or "input_bindings" in error for error in errors))

    def test_all_zero_input_binding_hash_fails(self):
        ok, errors = validate_review_record(
            valid_review(input_bindings=[{"path": "inputs/data.csv", "sha256": "0" * 64, "artifact_kind": "source_data"}])
        )
        self.assertFalse(ok)
        self.assertTrue(any("all-zero" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
