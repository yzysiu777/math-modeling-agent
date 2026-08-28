import tempfile
import unittest
from pathlib import Path

from scripts.model_pool import normalize_method_family, validate_candidate_pool


def candidate_text(routes, levels=None):
    sections = ["# 候选路线池"]
    for index, (route_id, family, idea, falsifier, status) in enumerate(routes):
        level = 2 if levels is None else levels[index]
        sections.extend(
            [
                f"{'#' * level} {route_id}：路线",
                f"- 方法族：{family}",
                f"- 核心思想：{idea}",
                f"- 最便宜的证伪实验：{falsifier}",
                f"- 状态：`{status}`",
            ]
        )
    return "\n".join(sections) + "\n"


class ModelPoolTests(unittest.TestCase):
    def write_pool(self, directory, routes, levels=None):
        path = Path(directory) / "candidates.md"
        path.write_text(candidate_text(routes, levels), encoding="utf-8")
        return path

    def valid_routes(self):
        return [
            ("M-01", "constructive heuristic", "局部构造", "两步穷举", "candidate"),
            ("M-02", "exact enumeration", "枚举全部解", "手算小实例", "testing"),
            ("M-03", "mixed-integer programming", "显式约束", "复算线性约束", "challenger"),
        ]

    def test_three_different_method_families_pass(self):
        routes = [
            ("M-01", "constructive heuristic", "局部构造", "两步穷举", "candidate"),
            ("M-02", "exact enumeration", "枚举全部解", "手算小实例", "testing"),
            ("M-03", "mixed-integer programming", "显式约束", "复算线性约束", "challenger"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(validate_candidate_pool(self.write_pool(directory, routes)), [])

    def test_three_same_method_families_fail(self):
        routes = [
            ("M-01", "linear regression", "拟合关系", "时间外切分", "candidate"),
            ("M-02", "linear regression", "拟合关系", "时间外切分", "candidate"),
            ("M-03", "linear regression", "拟合关系", "时间外切分", "candidate"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_candidate_pool(self.write_pool(directory, routes))
        self.assertTrue(any("three distinct method families" in error for error in errors))

    def test_case_and_punctuation_only_differences_are_duplicates(self):
        self.assertEqual(normalize_method_family(" Linear-Regression "), "linearregression")
        routes = [
            ("M-01", "Linear Regression", "拟合关系", "时间外切分", "candidate"),
            ("M-02", "linear-regression", "拟合关系", "时间外切分", "candidate"),
            ("M-03", "LINEAR  REGRESSION", "拟合关系", "时间外切分", "candidate"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_candidate_pool(self.write_pool(directory, routes))
        self.assertTrue(any("three distinct method families" in error for error in errors))

    def test_empty_family_fails(self):
        routes = [
            ("M-01", "", "核心思路", "证伪实验", "candidate"),
            ("M-02", "linear", "核心思路", "证伪实验", "candidate"),
            ("M-03", "tree", "核心思路", "证伪实验", "candidate"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_candidate_pool(self.write_pool(directory, routes))
        self.assertTrue(any("M-01 has no method family" in error for error in errors))

    def test_empty_falsification_experiment_fails(self):
        routes = [
            ("M-01", "heuristic", "核心思路", "", "candidate"),
            ("M-02", "linear", "核心思路", "证伪实验", "candidate"),
            ("M-03", "tree", "核心思路", "证伪实验", "candidate"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_candidate_pool(self.write_pool(directory, routes))
        self.assertTrue(any("M-01 has no cheapest falsification experiment" in error for error in errors))

    def test_duplicate_route_id_fails(self):
        routes = [
            ("M-01", "heuristic", "核心思路", "证伪实验", "candidate"),
            ("M-01", "linear", "核心思路", "证伪实验", "candidate"),
            ("M-03", "tree", "核心思路", "证伪实验", "candidate"),
        ]
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_candidate_pool(self.write_pool(directory, routes))
        self.assertTrue(any("duplicate candidate route ID" in error for error in errors))

    def test_heading_levels_two_three_four_are_supported(self):
        for level in (2, 3, 4):
            with self.subTest(level=level), tempfile.TemporaryDirectory() as directory:
                errors = validate_candidate_pool(self.write_pool(directory, self.valid_routes(), [level] * 3))
            self.assertEqual(errors, [])

    def test_mixed_supported_heading_levels_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_candidate_pool(self.write_pool(directory, self.valid_routes(), [2, 3, 4]))
        self.assertEqual(errors, [])

    def test_level_one_and_five_headings_are_rejected_with_format_error(self):
        for level in (1, 5):
            with self.subTest(level=level), tempfile.TemporaryDirectory() as directory:
                errors = validate_candidate_pool(self.write_pool(directory, self.valid_routes(), [level] * 3))
            self.assertTrue(any("unsupported candidate heading level" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
