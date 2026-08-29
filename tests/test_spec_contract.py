import json
import tempfile
import unittest
from pathlib import Path

from scripts.check_spec import validate_case_specs, validate_spec
from scripts.make_review_packet import build_packet
from scripts.create_case import create_case
from scripts.model_checks import load_result, write_check_report


ROOT = Path(__file__).resolve().parents[1]

FULL_SPEC = """---
spec_id: SPEC-A1-M02
case_id: demo
route_id: M-02
subproblem: 问题1
method_family: mixed-integer programming
status: full
language: python
---

## 1. 目标与判据

通过：12 个实例全部可行，目标值与枚举真值相对误差 ≤ 1e-6。

## 2. 数学表述

决策变量 x[i][j] ∈ {0,1}，目标 min 总成本，约束 C1 容量、C2 恰好分配一次。

## 3. 数据契约

输入 `input/cost.csv`，列 facility_id、demand_id、cost_yuan，缺失整行删除。

## 4. 算法

PuLP + CBC，时间上限 300 s，随机种子 42。

## 5. 输出契约

`outputs/data/EXP-001_solution.csv`，列 facility_id、demand_id、assigned、cost_yuan。

## 6. 复算要求

用 check_constraints 逐条验证容量与分配，recompute_objective 相对误差 ≤ 1e-6。

## 7. 明确不做

不做多目标扩展，不做鲁棒版本。

## 8. 未决问题

Q1：容量不足时是否允许部分服务，影响 C1，待队员确认。
"""

PROBE_SPEC = """---
spec_id: SPEC-A1-M02-probe
case_id: demo
route_id: M-02
subproblem: 问题1
method_family: mixed-integer programming
status: probe
language: python
---

## 1. 要证伪的假设

LP 松弛解四舍五入后仍可行。

## 2. 判据

通过：5 个玩具实例全部可行且间隙 ≤ 5%；失败：任一不可行或间隙 > 15%。

## 3. 最小实例 / 最小样本

手工构造 2 服务点 3 需求点，穷举可得真值。

## 4. 实现要点

读入成本矩阵，解 LP 松弛，四舍五入，检查容量。
"""


class SpecCheckTests(unittest.TestCase):
    def write(self, directory, name, text):
        path = Path(directory) / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_complete_full_and_probe_specs_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(validate_spec(self.write(directory, "SPEC-A.md", FULL_SPEC)), [])
            self.assertEqual(validate_spec(self.write(directory, "SPEC-B.md", PROBE_SPEC)), [])

    def test_missing_front_matter_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, "SPEC-A.md", "# 没有 front matter\n")
            errors = validate_spec(path)
        self.assertTrue(any("front matter" in error for error in errors))

    def test_placeholder_front_matter_field_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            text = FULL_SPEC.replace("method_family: mixed-integer programming", "method_family: <方法族>")
            errors = validate_spec(self.write(directory, "SPEC-A.md", text))
        self.assertTrue(any("method_family" in error for error in errors))

    def test_invalid_status_and_language_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            text = FULL_SPEC.replace("status: full", "status: draft").replace("language: python", "language: rust")
            errors = validate_spec(self.write(directory, "SPEC-A.md", text))
        self.assertTrue(any("invalid status" in error for error in errors))
        self.assertTrue(any("invalid language" in error for error in errors))

    def test_missing_and_placeholder_sections_are_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            text = FULL_SPEC.replace(
                "用 check_constraints 逐条验证容量与分配，recompute_objective 相对误差 ≤ 1e-6。", "待填写"
            )
            text = text.split("## 7. 明确不做")[0]
            errors = validate_spec(self.write(directory, "SPEC-A.md", text))
        self.assertTrue(any("section 6" in error for error in errors))
        self.assertTrue(any("missing section 7" in error for error in errors))
        self.assertTrue(any("missing section 8" in error for error in errors))

    def test_non_numeric_acceptance_criterion_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            text = FULL_SPEC.replace(
                "通过：12 个实例全部可行，目标值与枚举真值相对误差 ≤ 1e-6。", "通过：结果合理，收敛正常。"
            )
            errors = validate_spec(self.write(directory, "SPEC-A.md", text))
        self.assertTrue(any("numeric acceptance criterion" in error for error in errors))

    def test_probe_does_not_require_full_only_sections(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_spec(self.write(directory, "SPEC-B.md", PROBE_SPEC))
        self.assertEqual(errors, [])

    def test_duplicate_spec_id_across_files_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            case = create_case("spec-demo", "optimization", Path(directory))
            (case / "specs/SPEC-A.md").write_text(FULL_SPEC, encoding="utf-8")
            (case / "specs/SPEC-B.md").write_text(FULL_SPEC, encoding="utf-8")
            errors = validate_case_specs(case)
        self.assertTrue(any("duplicate spec_id" in error for error in errors))

    def test_question_files_are_not_validated_as_specs(self):
        with tempfile.TemporaryDirectory() as directory:
            case = create_case("spec-demo", "optimization", Path(directory))
            (case / "specs/SPEC-A.md").write_text(FULL_SPEC, encoding="utf-8")
            (case / "specs/SPEC-A.questions.md").write_text("# 回问\n\n没有 front matter。\n", encoding="utf-8")
            self.assertEqual(validate_case_specs(case), [])

    def test_case_without_specs_directory_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            errors = validate_case_specs(Path(directory) / "nothing")
        self.assertTrue(errors)


class CheckReportTests(unittest.TestCase):
    def test_report_round_trips_and_marks_overall_status(self):
        with tempfile.TemporaryDirectory() as directory:
            target = write_check_report(
                directory, "EXP-001", "SPEC-A1-M02",
                [
                    {"name": "capacity", "kind": "constraint", "passed": True},
                    {"name": "objective", "kind": "objective_mismatch", "passed": False, "detail": "rel_err=0.2"},
                ],
            )
            payload = json.loads(target.read_text(encoding="utf-8"))
        self.assertEqual(target.name, "EXP-001.json")
        self.assertFalse(payload["passed"])
        self.assertEqual(payload["checks"][1]["detail"], "rel_err=0.2")

    def test_unknown_kind_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                write_check_report(directory, "EXP-001", "SPEC-A", [{"name": "x", "kind": "vibes", "passed": True}])

    def test_missing_passed_and_empty_report_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                write_check_report(directory, "EXP-001", "SPEC-A", [{"name": "x", "kind": "constraint"}])
            with self.assertRaises(ValueError):
                write_check_report(directory, "EXP-001", "SPEC-A", [])

    def test_load_result_reads_both_formats_with_empty_as_none(self):
        with tempfile.TemporaryDirectory() as directory:
            csv_path = Path(directory) / "r.csv"
            csv_path.write_text("a,b\n1,\n", encoding="utf-8")
            json_path = Path(directory) / "r.json"
            json_path.write_text('{"objective": 12.5}', encoding="utf-8")
            self.assertEqual(load_result(csv_path), [{"a": "1", "b": None}])
            self.assertEqual(load_result(json_path)["objective"], 12.5)
            with self.assertRaises(ValueError):
                load_result(Path(directory) / "r.txt")


class ReviewPacketTests(unittest.TestCase):
    def test_packet_carries_metadata_and_names_missing_material(self):
        with tempfile.TemporaryDirectory() as directory:
            case = create_case("packet-demo", "optimization", Path(directory))
            packet = build_packet(case, "C2")
        for marker in (
            "reviewer_provider", "reviewer_model", "review_session: fresh",
            "saw_main_conversation: false", "critical_node: C2", "case_id: packet-demo",
        ):
            self.assertIn(marker, packet)
        self.assertIn("未提供的材料", packet)
        self.assertIn("specs/", packet)

    def test_each_node_pulls_its_own_material(self):
        with tempfile.TemporaryDirectory() as directory:
            case = create_case("packet-demo", "optimization", Path(directory))
            c1 = build_packet(case, "C1")
            c3 = build_packet(case, "C3")
        self.assertNotIn("候选路线池", c1)
        self.assertIn("论文数字溯源", c3)
        self.assertIn("C3_results_challenge.md", c3)

    def test_invalid_node_and_missing_case_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            case = create_case("packet-demo", "optimization", Path(directory))
            with self.assertRaises(ValueError):
                build_packet(case, "C9")
            with self.assertRaises(FileNotFoundError):
                build_packet(Path(directory) / "nope", "C1")


if __name__ == "__main__":
    unittest.main()
