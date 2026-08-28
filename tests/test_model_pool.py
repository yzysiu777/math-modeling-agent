import tempfile
import unittest
from pathlib import Path

from scripts.model_pool import normalize_method_family, validate_candidate_pool


def candidate_text(routes):
    sections = ["# 候选路线池"]
    for route_id, family, idea, falsifier, status in routes:
        sections.extend(
            [
                f"## {route_id}：路线",
                f"- 方法族：{family}",
                f"- 核心思想：{idea}",
                f"- 最便宜的证伪实验：{falsifier}",
                f"- 状态：`{status}`",
            ]
        )
    return "\n".join(sections) + "\n"


class ModelPoolTests(unittest.TestCase):
    def write_pool(self, directory, routes):
        path = Path(directory) / "candidates.md"
        path.write_text(candidate_text(routes), encoding="utf-8")
        return path

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


if __name__ == "__main__":
    unittest.main()
