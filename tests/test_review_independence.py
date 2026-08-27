import unittest

from scripts.check_review_independence import validate_review_record


def valid_review(**overrides):
    record = {
        "critical_node": "C2",
        "review_mode": "challenge",
        "review_lens": ["alternative_formulation", "invariant_counterexample"],
        "primary_method_family": "mixed integer programming",
        "alternative_method_family": "constraint programming",
        "methodological_difference": "the alternative tests propagation and feasibility before objective quality",
        "critical_decisions_reviewed": ["capacity constraint"],
        "disconfirming_tests": ["enumerate a two-item instance"],
        "counterexamples": [],
        "what_was_checked": ["formula-to-code mapping"],
        "what_was_not_checked": ["large-scale solver performance"],
        "uncertainty": ["large-scale solver performance was not independently rerun"],
        "human_decisions_required": ["choose the risk preference"],
        "verdict": "PASS_WITH_LIMITATIONS",
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
                primary_method_family="same model",
                alternative_method_family="same model",
                methodological_difference="same",
            )
        )
        self.assertFalse(ok)
        self.assertTrue(any("methodological_difference" in error for error in errors))

    def test_pass_without_counterexample_fails(self):
        ok, errors = validate_review_record(
            valid_review(disconfirming_tests=[], counterexamples=[], verdict="PASS")
        )
        self.assertFalse(ok)
        self.assertTrue(any("counterexample" in error or "disconfirming" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
