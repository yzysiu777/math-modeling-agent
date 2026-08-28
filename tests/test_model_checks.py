import unittest

from scripts.model_checks import (
    audit_optimization_result,
    check_data_split,
    compare_model_results,
    validate_hybrid_interface,
)


class ModelCheckTests(unittest.TestCase):
    def test_optimization_feasibility_and_objective_are_independent(self):
        solution = {"x": 2, "y": 3}
        result = audit_optimization_result(
            solution,
            lambda values: values["x"] + 2 * values["y"],
            [("nonnegative", lambda values: values["x"] >= 0 and values["y"] >= 0)],
            reported_objective=8,
        )
        self.assertTrue(result["passed"])
        self.assertEqual(result["objective"], 8.0)

        wrong = audit_optimization_result(
            solution,
            lambda values: values["x"] + 2 * values["y"],
            [("capacity", lambda values: values["x"] + values["y"] <= 4)],
            reported_objective=999,
        )
        self.assertFalse(wrong["passed"])
        self.assertFalse(wrong["objective_matches"])

    def test_split_check_catches_overlap_and_time_leakage(self):
        train = [{"id": "a", "time": 1}, {"id": "b", "time": 2}]
        validation = [{"id": "c", "time": 3}]
        test = [{"id": "d", "time": 4}]
        self.assertEqual(check_data_split(train, validation, test, "id", "time"), [])

        bad = check_data_split(train, [{"id": "b", "time": 2}], test, "id", "time")
        self.assertTrue(any("share id" in error for error in bad))
        future = check_data_split(train, [{"id": "c", "time": 1}], test, "id", "time")
        self.assertTrue(any("time order leakage" in error for error in future))

    def test_model_comparison_requires_methodological_difference(self):
        comparison = compare_model_results(
            [
                {"id": "M-01", "method_family": "mean", "score": 0.7, "status": "done"},
                {"id": "M-02", "method_family": "linear", "score": 0.9, "status": "done"},
            ],
            "score",
        )
        self.assertEqual(comparison["champion"]["id"], "M-02")
        self.assertEqual(comparison["challenger"]["id"], "M-01")
        with self.assertRaises(ValueError):
            compare_model_results(
                [
                    {"id": "M-01", "method_family": "same", "score": 0.7},
                    {"id": "M-02", "method_family": "same", "score": 0.9},
                ],
                "score",
            )

    def test_hybrid_interface_reports_missing_fields_and_units(self):
        self.assertEqual(
            validate_hybrid_interface(
                {"demand": 8, "units": {"demand": "units"}},
                {"demand": int},
                {"demand": "units"},
            ),
            [],
        )
        errors = validate_hybrid_interface(
            {"demand": "eight", "units": {"demand": "kg"}},
            {"demand": int, "service_level": float},
            {"demand": "units"},
        )
        self.assertTrue(any("missing interface field: service_level" in error for error in errors))
        self.assertTrue(any("unit mismatch" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
