import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.check_case import check_case
from scripts.create_case import create_case


class CaseCheckTests(unittest.TestCase):
    @staticmethod
    def update_checkpoint(case, **updates):
        path = case / "checkpoint.yaml"
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        for key, value in updates.items():
            if isinstance(value, dict) and isinstance(payload.get(key), dict):
                payload[key].update(value)
            else:
                payload[key] = value
        path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")

    def make_case(self, directory, route="data_analysis"):
        return create_case("case-check", route, Path(directory))

    def confirm(self, case, route="data_analysis", note="依据题面完整核对输入与目标"):
        self.update_checkpoint(
            case,
            routing={
                "confirmed": True,
                "confirmed_route": route,
                "confirmed_by": "队长",
                "note": note,
            },
        )

    @staticmethod
    def set_comparison(case):
        (case / "models/comparison.md").write_text(
            "# 路线比较\n\n当前 Champion：M-02\n当前 Challenger：M-01\n",
            encoding="utf-8",
        )

    @staticmethod
    def add_review(case, node, content=None):
        content = content or (
            f"# {node} 审核\n\n"
            "结论：当前范围内可以继续。\n"
            "已检查：题面、模型与关键结果。\n"
            "未检查：完整规模实验与最终提交。\n"
        )
        (case / "reviews" / f"{node}_review.md").write_text(content, encoding="utf-8")

    @staticmethod
    def add_decision(case, node):
        with (case / "decisions.md").open("a", encoding="utf-8") as handle:
            handle.write(f"\n| DEC-{node}-001 | {node} | 接受 | 按报告继续 |\n")

    @staticmethod
    def codes(report):
        return {finding.code for finding in report.findings}

    def test_create_case_writes_checkpoint_consistent_with_route(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory, "hybrid")
            payload = yaml.safe_load((case / "checkpoint.yaml").read_text(encoding="utf-8"))
        self.assertEqual(payload["case_id"], "case-check")
        self.assertEqual(payload["routing"]["suggested"], "hybrid")
        self.assertFalse(payload["routing"]["confirmed"])
        self.assertEqual(payload["reviews"]["C1"], "pending")

    def test_unconfirmed_route_is_reminder_then_block(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            exploration = check_case(case, "exploration")
            selection = check_case(case, "model_selection")
        self.assertEqual(exploration.exit_code, 0)
        self.assertTrue(any(f.code == "ROUTE_CONFIRMATION_REQUIRED" and not f.blocks for f in exploration.findings))
        self.assertEqual(selection.exit_code, 1)
        self.assertTrue(any(f.code == "ROUTE_CONFIRMATION_REQUIRED" and f.blocks for f in selection.findings))

    def test_confirmed_route_can_override_suggestion_with_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory, "optimization")
            self.confirm(case, "hybrid", "题面同时要求预测和资源决策")
            report = check_case(case, "model_selection")
        self.assertNotIn("ROUTE_CONFIRMATION_REQUIRED", self.codes(report))

    def test_incomplete_confirmed_route_is_blocked(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.update_checkpoint(case, routing={"confirmed": True, "confirmed_route": "data_analysis"})
            report = check_case(case, "exploration")
        self.assertEqual(report.exit_code, 1)
        self.assertTrue(any(f.code == "ROUTE_CONFIRMATION_REQUIRED" and f.blocks for f in report.findings))

    def test_c3_requires_real_report_not_readme_or_placeholder(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            missing = check_case(case, "paper_claims")
            placeholder = None
            for content in (
                "# C3\n\nTODO\n",
                "# C3\n\n结论：TODO\n已检查范围：待填写\n未检查范围：TODO\n",
            ):
                self.add_review(case, "C3", content)
                placeholder = check_case(case, "paper_claims")
        self.assertTrue(any(f.code == "C3_REQUIRED" and f.blocks for f in missing.findings))
        self.assertIsNotNone(placeholder)
        self.assertTrue(any(f.code == "C3_REQUIRED" and f.blocks for f in placeholder.findings))

    def test_valid_c1_c2_c3_and_decisions_allow_final_case_check(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.add_review(case, "C1")
            self.add_review(case, "C2")
            self.add_review(case, "C3")
            self.add_decision(case, "C1")
            self.add_decision(case, "C2")
            self.add_decision(case, "C3")
            report = check_case(case, "final")
        self.assertEqual(report.findings, ())
        self.assertEqual(report.exit_code, 0)

    def test_c1_not_needed_requires_a_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.update_checkpoint(
                case,
                reviews={"C1": "not_needed"},
                review_notes={"C1": "题意清晰，不改变目标或硬约束"},
            )
            report = check_case(case, "model_selection")
        self.assertNotIn("C1_RECOMMENDED", self.codes(report))

    def test_c1_not_needed_without_reason_cannot_bypass(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.update_checkpoint(case, reviews={"C1": "not_needed"})
            report = check_case(case, "model_selection")
        self.assertTrue(any(f.code == "C1_RECOMMENDED" and f.blocks for f in report.findings))

    def test_failure_pattern_escalates_without_blocking_exploration(self):
        board = (
            "| 实验 ID | 候选路线 | 要回答的问题 | 最小配置 | 数据/实例范围 | 指标 | 预计成本 | status | 结果摘要 | 是否继续 | 下一项信息价值最高的实验 |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n"
            "| EXP-001 | M-01 | q | small | toy | score | low | failed | gap 未收敛 | yes | 检查参数 |\n"
            "| EXP-002 | M-01 | q | small | toy | score | low | failed | 数值震荡 | yes | 换 baseline |\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            (case / "experiments/board.md").write_text(board, encoding="utf-8")
            report = check_case(case, "exploration")
        self.assertEqual(report.exit_code, 0)
        pattern = [f for f in report.findings if f.code == "EXPERIMENT_FAILURE_PATTERN"]
        self.assertEqual(len(pattern), 1)
        self.assertEqual(pattern[0].node, "C2")
        self.assertFalse(pattern[0].blocks)

    def test_single_failure_is_only_a_non_blocking_reminder(self):
        board = (
            "| 实验 ID | 候选路线 | 要回答的问题 | 最小配置 | 数据/实例范围 | 指标 | 预计成本 | status | 结果摘要 | 是否继续 | 下一项信息价值最高的实验 |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n"
            "| EXP-001 | M-01 | q | small | toy | score | low | failed | gap 未收敛 | yes | 检查参数 |\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            (case / "experiments/board.md").write_text(board, encoding="utf-8")
            report = check_case(case, "exploration")
        self.assertTrue(any(f.code == "EXPERIMENT_FAILURE_RECORDED" and not f.blocks for f in report.findings))
        self.assertNotIn("EXPERIMENT_FAILURE_PATTERN", self.codes(report))

    def test_multiple_routes_failure_escalates(self):
        board = (
            "| 实验 ID | 候选路线 | 要回答的问题 | 最小配置 | 数据/实例范围 | 指标 | 预计成本 | status | 结果摘要 | 是否继续 | 下一项信息价值最高的实验 |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n"
            "| EXP-001 | M-01 | q | small | toy | score | low | failed | a | yes | b |\n"
            "| EXP-002 | M-02 | q | small | toy | score | low | failed | b | yes | c |\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            (case / "experiments/board.md").write_text(board, encoding="utf-8")
            report = check_case(case, "exploration")
        self.assertIn("EXPERIMENT_FAILURE_PATTERN", self.codes(report))

    def test_performance_concern_recommends_human_and_c2(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.update_checkpoint(case, performance_concern=True)
            report = check_case(case, "model_selection")
        findings = [f for f in report.findings if f.code == "HUMAN_DECISION_REQUIRED" and f.node == "C2"]
        self.assertTrue(findings)
        self.assertFalse(any(f.blocks for f in findings))

    def test_deterministic_risk_blocks_strong_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.update_checkpoint(case, deterministic_risks={"leakage": True})
            report = check_case(case, "paper_claims")
        self.assertTrue(any(f.code == "DETERMINISTIC_ERROR_BLOCK" and f.blocks for f in report.findings))

    def test_report_without_human_decision_blocks_final(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.add_review(case, "C3")
            report = check_case(case, "final")
        self.assertTrue(any(f.code == "HUMAN_DECISION_REQUIRED" and f.blocks for f in report.findings))

    def test_decision_placeholder_does_not_count_as_human_choice(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.add_review(case, "C3")
            (case / "decisions.md").write_text(
                "# 决策\n\n| C3 | accept/reject/pause/defer | 待填写 |\n",
                encoding="utf-8",
            )
            report = check_case(case, "final")
        self.assertTrue(any(f.code == "HUMAN_DECISION_REQUIRED" and f.blocks for f in report.findings))


if __name__ == "__main__":
    unittest.main()
