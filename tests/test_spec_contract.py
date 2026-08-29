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
probe_spec_id: SPEC-A1-M02-probe
probe_exp_id: EXP-001
probe_result: PASS
probe_waiver_reason: ""
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


class ProbeClosureTests(unittest.TestCase):
    """A probe file existing proves nothing; the probe has to have run."""

    def write(self, directory, text):
        path = Path(directory) / "SPEC-A.md"
        path.write_text(text, encoding="utf-8")
        return path

    def test_passed_probe_closes_the_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(validate_spec(self.write(directory, FULL_SPEC)), [])

    def test_missing_probe_result_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            text = FULL_SPEC.replace("probe_result: PASS\n", "")
            errors = validate_spec(self.write(directory, text))
        self.assertTrue(any("no probe_result" in error for error in errors))

    def test_failed_probe_cannot_be_promoted(self):
        with tempfile.TemporaryDirectory() as directory:
            text = FULL_SPEC.replace("probe_result: PASS", "probe_result: FAIL")
            errors = validate_spec(self.write(directory, text))
        self.assertTrue(any("probe_result is FAIL" in error for error in errors))

    def test_invalid_probe_result_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            text = FULL_SPEC.replace("probe_result: PASS", "probe_result: probably-fine")
            errors = validate_spec(self.write(directory, text))
        self.assertTrue(any("invalid probe_result" in error for error in errors))

    def test_waiver_requires_a_written_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            text = FULL_SPEC.replace("probe_result: PASS", "probe_result: WAIVED")
            errors = validate_spec(self.write(directory, text))
            self.assertTrue(any("probe_waiver_reason" in error for error in errors))

            stated = text.replace('probe_waiver_reason: ""',
                                  "probe_waiver_reason: 题面第 3 问直接指定使用该调度算法，无替代方法族可比")
            self.assertEqual(validate_spec(self.write(directory, stated)), [])

    def test_placeholder_waiver_reason_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            text = FULL_SPEC.replace("probe_result: PASS", "probe_result: WAIVED")
            text = text.replace('probe_waiver_reason: ""', "probe_waiver_reason: 待补充")
            errors = validate_spec(self.write(directory, text))
        self.assertTrue(any("probe_waiver_reason" in error for error in errors))

    def test_pass_requires_probe_spec_and_experiment_ids(self):
        with tempfile.TemporaryDirectory() as directory:
            text = FULL_SPEC.replace("probe_exp_id: EXP-001", "probe_exp_id: ")
            errors = validate_spec(self.write(directory, text))
        self.assertTrue(any("probe_exp_id" in error for error in errors))

    def test_probe_spec_itself_needs_no_closure_fields(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "SPEC-B.md"
            path.write_text(PROBE_SPEC, encoding="utf-8")
            self.assertEqual(validate_spec(path), [])


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
        self.assertIn("审核包不完整", packet)
        self.assertIn("packet_complete: false", packet)
        self.assertIn("specs/", packet)

    def test_each_node_pulls_its_own_material(self):
        with tempfile.TemporaryDirectory() as directory:
            case = create_case("packet-demo", "optimization", Path(directory))
            c1 = build_packet(case, "C1")
            c3 = build_packet(case, "C3")
        self.assertNotIn("候选路线池", c1)
        self.assertIn("input/", c1)
        self.assertIn("C3_results_challenge.md", c3)
        self.assertIn("claim_map.md", c3)

    def test_c1_without_original_statement_is_marked_incomplete(self):
        """C1 checks fidelity to the problem; the Modeler's brief is the object, not the evidence."""

        with tempfile.TemporaryDirectory() as directory:
            case = create_case("packet-demo", "optimization", Path(directory))
            blind = build_packet(case, "C1")
            self.assertIn("packet_complete: false", blind)
            self.assertIn("无法核对题意是否忠实于原题", blind)

            (case / "input/statement.md").write_text(
                "# 原题\n\n某公司有两个服务点与三个需求点，容量各为 2。\n", encoding="utf-8")
            with_statement = build_packet(case, "C1")
        self.assertIn("packet_complete: true", with_statement)
        self.assertIn("原始输入清单", with_statement)
        self.assertIn("某公司有两个服务点", with_statement)

    def test_c2_carries_full_spec_body_not_only_front_matter(self):
        with tempfile.TemporaryDirectory() as directory:
            case = create_case("packet-demo", "optimization", Path(directory))
            (case / "models/candidates.md").write_text(
                "# 候选路线池\n\n## M-02：枚举\n\n- 状态：`champion`\n", encoding="utf-8")
            (case / "specs/SPEC-A1-M02.md").write_text(FULL_SPEC, encoding="utf-8")
            packet = build_packet(case, "C2")
        self.assertIn("决策变量 x[i][j]", packet)          # 第 2 段数学表述
        self.assertIn("PuLP + CBC", packet)                # 第 4 段算法
        self.assertIn("容量不足时是否允许部分服务", packet)  # 第 8 段未决问题
        self.assertIn("mixed-integer programming", packet)

    def test_c3_carries_claim_text_and_its_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            case = create_case("packet-demo", "optimization", Path(directory))
            outputs = case / "experiments/outputs"
            (outputs / "data").mkdir(parents=True, exist_ok=True)
            (outputs / "data/EXP-001_solution.csv").write_text("a,b\n1,2\n", encoding="utf-8")
            (outputs / "checks").mkdir(parents=True, exist_ok=True)
            (outputs / "checks/EXP-001.json").write_text(
                json.dumps({"exp_id": "EXP-001", "checks": [
                    {"name": "capacity", "kind": "constraint", "passed": False, "detail": "超容量 2"}]}),
                encoding="utf-8")
            (case / "paper/claim_map.md").write_text(
                "| Claim ID | 论文位置 | 主张原文 | 强度 | 来源 EXP-ID | 数据文件 | 图/表 ID | 复算报告 | 状态 |\n"
                "|---|---|---|---|---|---|---|---|---|\n"
                "| CLM-001 | 摘要 | 全部算例均可行 | 可行解 | EXP-001 | "
                "outputs/data/EXP-001_solution.csv | — | outputs/checks/EXP-001.json | draft |\n",
                encoding="utf-8")
            packet = build_packet(case, "C3")
        self.assertIn("全部算例均可行", packet)              # 强结论原文
        self.assertIn("结果数据片段", packet)                # 实际数据摘录
        self.assertIn("CLM-001 的复算报告", packet)
        self.assertIn("**1 项未通过**", packet)              # 未通过项必须出现在包里
        self.assertIn("超容量 2", packet)

    def test_same_day_regeneration_does_not_overwrite(self):
        from scripts.make_review_packet import _unique_target

        with tempfile.TemporaryDirectory() as directory:
            packets = Path(directory)
            first, first_id = _unique_target(packets, "C2")
            first.write_text("first", encoding="utf-8")
            second, second_id = _unique_target(packets, "C2")
            second.write_text("second", encoding="utf-8")
            # 早先的包必须原样保留，不能被同日同节点的新包静默覆盖
            self.assertNotEqual(first, second)
            self.assertNotEqual(first_id, second_id)
            self.assertEqual(first.read_text(encoding="utf-8"), "first")
            self.assertEqual(len(list(packets.iterdir())), 2)

    def test_invalid_node_and_missing_case_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            case = create_case("packet-demo", "optimization", Path(directory))
            with self.assertRaises(ValueError):
                build_packet(case, "C9")
            with self.assertRaises(FileNotFoundError):
                build_packet(Path(directory) / "nope", "C1")


if __name__ == "__main__":
    unittest.main()
