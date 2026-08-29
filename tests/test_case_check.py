import json
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.check_case import _decision_covers_node, _valid_review, check_case
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

    @classmethod
    def set_claim_map(cls, case, exp_id="EXP-001", status="verified", create_evidence=True,
                      data_file=None, figure_id="FIG-001", report_file=None):
        """Write one claim row and, by default, the evidence files it points at."""

        data_file = data_file if data_file is not None else f"outputs/data/{exp_id}_solution.csv"
        report_file = report_file if report_file is not None else f"outputs/checks/{exp_id}.json"
        if create_evidence:
            cls.set_evidence(case, exp_id=exp_id, figure_id=figure_id)
        (case / "paper/claim_map.md").write_text(
            "# 论文数字溯源表\n\n"
            "| Claim ID | 论文位置 | 主张原文 | 强度 | 来源 EXP-ID | 数据文件 | 图/表 ID | 复算报告 | 状态 |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            f"| CLM-001 | 摘要 | 在 12 个算例上均得到可行解 | 可行解 | {exp_id} | "
            f"{data_file} | {figure_id} | {report_file} | {status} |\n",
            encoding="utf-8",
        )

    @staticmethod
    def set_evidence(case, exp_id="EXP-001", figure_id="FIG-001", check_passed=True):
        """Create the data file, recomputation report and figure entry a claim cites."""

        outputs = case / "experiments/outputs"
        (outputs / "data").mkdir(parents=True, exist_ok=True)
        (outputs / f"data/{exp_id}_solution.csv").write_text("a,b\n1,2\n", encoding="utf-8")
        (outputs / "checks").mkdir(parents=True, exist_ok=True)
        (outputs / f"checks/{exp_id}.json").write_text(
            json.dumps({"exp_id": exp_id, "spec_id": "SPEC-A1-M01", "passed": check_passed,
                        "checks": [{"name": "capacity", "kind": "constraint",
                                    "passed": check_passed, "detail": ""}]},
                       ensure_ascii=False),
            encoding="utf-8",
        )
        (outputs / "figures").mkdir(parents=True, exist_ok=True)
        (outputs / "figures/manifest.md").write_text(
            "# 图表清单\n\n"
            "| FIG-ID | 来源 EXP-ID | 生成脚本 | 数据文件 | 图题草稿 | 论文位置 | 状态 |\n"
            "|---|---|---|---|---|---|---|\n"
            f"| {figure_id} | {exp_id} | plot.py | data.csv | 图题 | 第 4 章 | final |\n",
            encoding="utf-8",
        )

    @staticmethod
    def set_board_experiment(case, exp_id="EXP-001"):
        (case / "experiments/board.md").write_text(
            "# 实验赛马板\n\n"
            "| 实验 ID | 候选路线 | 要回答的问题 | 最小配置 | 数据/实例范围 | 指标 | 预计成本 | status | 结果摘要 | 是否继续 | 下一项信息价值最高的实验 |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n"
            f"| {exp_id} | M-01 | baseline 是否可行 | toy | toy instance | 成本 | low | done | 判定：PASS；可行 | yes | 与枚举比较 |\n",
            encoding="utf-8",
        )

    @staticmethod
    def write_check_report(case, exp_id="EXP-001", kind="constraint", passed=False):
        target = case / "experiments/outputs/checks"
        target.mkdir(parents=True, exist_ok=True)
        (target / f"{exp_id}.json").write_text(
            json.dumps({
                "exp_id": exp_id, "spec_id": "SPEC-A1-M01", "passed": passed,
                "checks": [{"name": "capacity", "kind": kind, "passed": passed, "detail": "over capacity"}],
            }, ensure_ascii=False),
            encoding="utf-8",
        )

    @staticmethod
    def set_comparison(case):
        (case / "models/comparison.md").write_text(
            "# 路线比较\n\n当前 Champion：M-02\n当前 Challenger：M-01\n",
            encoding="utf-8",
        )

    @staticmethod
    def review_metadata(node):
        return (
            f"Review ID: review-{node.lower()}-001\n"
            "Case ID: case-check\n"
            "Reviewer provider: human_specialist\n"
            "Reviewer model: review-model\n"
            "Review session: fresh\n"
            "Saw main conversation: false\n"
            f"Critical node: {node}\n"
        )

    @classmethod
    def valid_review(cls, node, checked_label="What was checked", unchecked_label="What was not checked"):
        return (
            f"# {node} 审核\n\n"
            + cls.review_metadata(node)
            + "Verdict: PASS_WITH_LIMITATIONS\n"
            + f"{checked_label}: 题面、模型与关键结果。\n"
            + f"{unchecked_label}: 完整规模实验与最终提交。\n"
        )

    @staticmethod
    def add_review(case, node, content=None):
        content = content or CaseCheckTests.valid_review(node)
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

    def test_new_prompt_fixed_output_is_valid_for_each_review_node(self):
        for node in ("C1", "C2", "C3"):
            with self.subTest(node=node):
                with tempfile.TemporaryDirectory() as directory:
                    case = self.make_case(directory)
                    self.add_review(case, node)
                    valid, detail = _valid_review(case, node)
                self.assertTrue(valid, detail)

    def test_review_parser_accepts_underscore_scope_labels(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.add_review(
                case,
                "C3",
                self.valid_review("C3", "what_was_checked", "what_was_not_checked"),
            )
            valid, detail = _valid_review(case, "C3")
        self.assertTrue(valid, detail)

    def test_review_parser_accepts_underscore_metadata_labels(self):
        content = (
            "# C3\n"
            "review_id: review-c3-yaml\n"
            "case_id: case-check\n"
            "reviewer_provider: human_specialist\n"
            "reviewer_model: review-model\n"
            "review_session: fresh\n"
            "saw_main_conversation: false\n"
            "critical_node: C3\n"
            "verdict: PASS_WITH_LIMITATIONS\n"
            "what_was_checked: 题面、模型与关键结果\n"
            "what_was_not_checked: 完整规模实验与最终提交\n"
        )
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.add_review(case, "C3", content)
            valid, detail = _valid_review(case, "C3")
        self.assertTrue(valid, detail)

    def test_reviewer_metadata_is_required_and_bound_to_case_and_node(self):
        base = self.valid_review("C3")
        replacements = (
            ("Reviewer provider: human_specialist", "Reviewer provider: TODO"),
            ("Reviewer model: review-model", "Reviewer model: <实际模型>"),
            ("Review session: fresh", "Review session: reused"),
            ("Saw main conversation: false", "Saw main conversation: true"),
            ("Critical node: C3", "Critical node: C1"),
            ("Case ID: case-check", "Case ID: another-case"),
            ("Review ID: review-c3-001", "Review ID: TODO"),
            ("Review ID: review-c3-001", "Review ID: "),
            ("Reviewer provider: human_specialist\n", ""),
            ("Reviewer model: review-model\n", ""),
        )
        for current, replacement in replacements:
            with self.subTest(replacement=replacement):
                with tempfile.TemporaryDirectory() as directory:
                    case = self.make_case(directory)
                    self.add_review(case, "C3", base.replace(current, replacement))
                    valid, detail = _valid_review(case, "C3")
                self.assertFalse(valid, detail)

    def test_invalid_reviewer_metadata_blocks_c3_case_check(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.add_review(case, "C3", self.valid_review("C3").replace("Review session: fresh", "Review session: reused"))
            report = check_case(case, "paper_claims")
        self.assertTrue(any(f.code == "C3_REQUIRED" and f.blocks for f in report.findings))

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

    def test_review_headings_need_substantive_body(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.add_review(
                case,
                "C3",
                "# C3\n\n## 结论\n## 已检查范围\n## 未检查范围\n",
            )
            valid, detail = _valid_review(case, "C3")
        self.assertFalse(valid, detail)

    def test_review_headings_with_only_placeholders_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.add_review(
                case,
                "C3",
                "# C3\n\n## 结论\nTODO\n## 已检查范围\n待填写\n## 未检查范围\n待补充\n",
            )
            valid, detail = _valid_review(case, "C3")
        self.assertFalse(valid, detail)

    def test_review_punctuation_only_fields_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.add_review(
                case,
                "C3",
                "# C3\n结论：……\n已检查范围：!!!\n未检查范围：——\n",
            )
            valid, detail = _valid_review(case, "C3")
        self.assertFalse(valid, detail)

    def test_review_field_values_and_natural_markdown_sections_are_valid(self):
        cases = (
            self.valid_review("C3", "已检查范围", "未检查范围"),
            (
                "# C3\n\n"
                + self.review_metadata("C3")
                + "## 结论\n当前范围内可以继续。\n\n"
                "## 已检查范围\n题面、模型和关键结果。\n\n"
                "## 未检查范围\n完整规模实验和最终提交。\n"
            ),
        )
        for content in cases:
            with self.subTest(content=content):
                with tempfile.TemporaryDirectory() as directory:
                    case = self.make_case(directory)
                    self.add_review(case, "C3", content)
                    valid, detail = _valid_review(case, "C3")
                self.assertTrue(valid, detail)

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
            self.set_board_experiment(case)
            self.set_claim_map(case)
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

    def test_c1_not_needed_is_reminder_when_route_is_insufficient(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case, "insufficient_information")
            self.update_checkpoint(
                case,
                reviews={"C1": "not_needed"},
                review_notes={"C1": "暂不需要"},
            )
            report = check_case(case, "model_selection")
        self.assertTrue(any(f.code == "C1_RECOMMENDED" and not f.blocks for f in report.findings))

    def test_c1_not_needed_is_reminder_when_brief_has_route_changing_ambiguity(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.update_checkpoint(
                case,
                reviews={"C1": "not_needed"},
                review_notes={"C1": "暂不需要"},
            )
            (case / "case_brief.md").write_text(
                "# 案例简报\n\n- 会改变路线的歧义：目标函数可能应改为多目标\n",
                encoding="utf-8",
            )
            report = check_case(case, "model_selection")
        self.assertTrue(any(f.code == "C1_RECOMMENDED" and not f.blocks for f in report.findings))

    def test_valid_c1_report_resolves_route_changing_ambiguity_reminder(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.update_checkpoint(
                case,
                reviews={"C1": "not_needed"},
                review_notes={"C1": "已完成独立题意挑战"},
            )
            (case / "case_brief.md").write_text(
                "# 案例简报\n\n- 会改变路线的歧义：目标函数可能应改为多目标\n",
                encoding="utf-8",
            )
            self.add_review(case, "C1")
            report = check_case(case, "model_selection")
        self.assertNotIn("C1_RECOMMENDED", self.codes(report))

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

    def test_chinese_decision_options_do_not_count_as_one_choice(self):
        for choice in ("接受/拒绝", "采纳/不采纳", "延期/暂缓"):
            with self.subTest(choice=choice):
                with tempfile.TemporaryDirectory() as directory:
                    case = self.make_case(directory)
                    (case / "decisions.md").write_text(
                        "| 节点 | 决定 | 原因 |\n|---|---|---|\n"
                        f"| C3 | {choice} | 已有依据 |\n",
                        encoding="utf-8",
                    )
                    self.assertFalse(_decision_covers_node(case, "C3"))

    def test_decision_explanation_sentence_is_not_a_human_decision(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            (case / "decisions.md").write_text(
                "C3 报告需要决定接受或拒绝\n",
                encoding="utf-8",
            )
            self.assertFalse(_decision_covers_node(case, "C3"))

    def test_explicit_decision_with_reason_is_valid(self):
        decisions = (
            "| C3 | 接受 | 因为反例已补测并通过 |\n",
            "| 节点 | 决策 | 原因 |\n|---|---|---|\n| C3 | 接受 | 因为反例已补测并通过 |\n",
        )
        for content in decisions:
            with self.subTest(content=content):
                with tempfile.TemporaryDirectory() as directory:
                    case = self.make_case(directory)
                    (case / "decisions.md").write_text(content, encoding="utf-8")
                    self.assertTrue(_decision_covers_node(case, "C3"))

    def test_explicit_decision_without_reason_or_with_placeholder_is_invalid(self):
        for reason in ("", "TODO", "待填写"):
            with self.subTest(reason=reason):
                with tempfile.TemporaryDirectory() as directory:
                    case = self.make_case(directory)
                    (case / "decisions.md").write_text(
                        f"| C3 | 接受 | {reason} |\n",
                        encoding="utf-8",
                    )
                    self.assertFalse(_decision_covers_node(case, "C3"))

    def test_checkpoint_case_id_must_match_case_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.update_checkpoint(case, case_id="another-case")
            report = check_case(case, "exploration")
        self.assertTrue(any(f.code == "CASE_ID_MISMATCH" and f.blocks for f in report.findings))


    # --- 三角色重构新增的检查 ---

    def test_failed_recompute_report_raises_the_risk_without_touching_checkpoint(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.write_check_report(case, kind="objective_mismatch", passed=False)
            report = check_case(case, "model_selection")
        codes = [f.code for f in report.findings]
        self.assertIn("DETERMINISTIC_ERROR_BLOCK", codes)
        risk = next(f for f in report.findings if f.code == "DETERMINISTIC_ERROR_BLOCK")
        self.assertEqual(risk.owner, "ENGINEER")
        self.assertIn("EXP-001:capacity", risk.reason)
        self.assertFalse(risk.blocks)

    def test_failed_recompute_report_blocks_paper_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.add_review(case, "C3")
            self.write_check_report(case, kind="leakage", passed=False)
            report = check_case(case, "paper_claims")
        risk = next(f for f in report.findings if f.code == "DETERMINISTIC_ERROR_BLOCK")
        self.assertTrue(risk.blocks)

    def test_passing_recompute_report_raises_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.write_check_report(case, passed=True)
            report = check_case(case, "model_selection")
        self.assertNotIn("DETERMINISTIC_ERROR_BLOCK", [f.code for f in report.findings])

    def test_unreadable_recompute_report_is_not_treated_as_a_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            target = case / "experiments/outputs/checks"
            target.mkdir(parents=True, exist_ok=True)
            (target / "EXP-009.json").write_text("{not json", encoding="utf-8")
            report = check_case(case, "model_selection")
        self.assertIn("CHECK_REPORT_UNREADABLE", [f.code for f in report.findings])

    def test_selected_route_without_full_spec_is_reminded(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            (case / "models/candidates.md").write_text(
                "# 候选路线池\n\n## M-01：baseline\n\n- 状态：`champion`\n",
                encoding="utf-8",
            )
            report = check_case(case, "model_selection")
        finding = next(f for f in report.findings if f.code == "SPEC_MISSING")
        self.assertEqual(finding.owner, "MODELER")
        self.assertFalse(finding.blocks)

    def test_full_spec_without_probe_is_reminded(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            (case / "specs/SPEC-A1-M01.md").write_text(
                "---\nspec_id: SPEC-A1-M01\nroute_id: M-01\nstatus: full\nlanguage: python\n---\n",
                encoding="utf-8",
            )
            report = check_case(case, "model_selection")
        self.assertIn("PROBE_MISSING", [f.code for f in report.findings])

    def test_probe_then_full_spec_is_not_reminded(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            for status in ("probe", "full"):
                (case / f"specs/SPEC-A1-M01-{status}.md").write_text(
                    f"---\nspec_id: SPEC-A1-M01-{status}\nroute_id: M-01\nstatus: {status}\n"
                    "language: python\n---\n",
                    encoding="utf-8",
                )
            report = check_case(case, "model_selection")
        self.assertNotIn("PROBE_MISSING", [f.code for f in report.findings])

    def test_prose_after_the_last_route_card_is_not_attributed_to_it(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            (case / "models/candidates.md").write_text(
                "# 候选路线池\n\n"
                "## M-01：baseline\n\n- 状态：`candidate`\n\n"
                "## M-02：另一条\n\n- 状态：`candidate`\n\n"
                "## 为什么 Challenger 是 M-01\n\nChallenger 的作用是保险。\n",
                encoding="utf-8",
            )
            report = check_case(case, "model_selection")
        self.assertNotIn("SPEC_MISSING", [f.code for f in report.findings])

    def test_spec_reminders_do_not_fire_during_exploration(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            (case / "models/candidates.md").write_text(
                "# 候选路线池\n\n## M-01：baseline\n\n- 状态：`champion`\n", encoding="utf-8",
            )
            report = check_case(case, "exploration")
        self.assertNotIn("SPEC_MISSING", [f.code for f in report.findings])

    def test_unfilled_claim_map_blocks_final_but_only_reminds_at_paper_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.add_review(case, "C3")
            reminder = check_case(case, "paper_claims")
            self.add_review(case, "C1")
            self.add_review(case, "C2")
            for node in ("C1", "C2", "C3"):
                self.add_decision(case, node)
            blocked = check_case(case, "final")
        claim_reminders = [f for f in reminder.findings if "claim_map" in f.reason]
        self.assertTrue(claim_reminders)
        self.assertFalse(claim_reminders[0].blocks)
        self.assertTrue(any("claim_map" in f.reason and f.blocks for f in blocked.findings))

    def test_claim_referencing_an_unknown_experiment_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.add_review(case, "C3")
            self.set_board_experiment(case, "EXP-001")
            self.set_claim_map(case, exp_id="EXP-777")
            report = check_case(case, "paper_claims")
        self.assertTrue(any("无法追溯" in f.reason for f in report.findings))

    def test_stale_claim_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.add_review(case, "C3")
            self.set_board_experiment(case)
            self.set_claim_map(case, status="stale")
            report = check_case(case, "paper_claims")
        self.assertTrue(any("stale" in f.reason for f in report.findings))


    # --- MMAG-006：claim 证据存在性 ---

    def _paper_claims_ready(self, case):
        """Bring a case to the point where only claim-map issues remain."""

        self.confirm(case)
        self.set_comparison(case)
        self.add_review(case, "C3")
        self.set_board_experiment(case)

    def test_claim_pointing_at_a_missing_csv_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self._paper_claims_ready(case)
            self.set_claim_map(case, data_file="outputs/data/does_not_exist.csv")
            reminder = check_case(case, "paper_claims")
            self.add_review(case, "C1")
            self.add_review(case, "C2")
            for node in ("C1", "C2", "C3"):
                self.add_decision(case, node)
            blocked = check_case(case, "final")
        # P1-3：已写下的主张引用不存在的证据，paper_claims 与 final 都必须阻断
        self.assertTrue(any(f.code == "CLAIM_EVIDENCE_MISSING" and "数据文件" in f.reason
                            and f.blocks for f in reminder.findings))
        self.assertEqual(reminder.exit_code, 1)
        self.assertTrue(any(f.code == "CLAIM_EVIDENCE_MISSING" and f.blocks
                            for f in blocked.findings))
        self.assertEqual(blocked.exit_code, 1)

    def test_claim_pointing_at_a_missing_check_report_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self._paper_claims_ready(case)
            self.set_claim_map(case, report_file="outputs/checks/nope.json")
            report = check_case(case, "paper_claims")
        self.assertTrue(any(f.code == "CLAIM_EVIDENCE_MISSING" and "复算报告不可用" in f.reason
                            and f.blocks for f in report.findings))

    def test_claim_pointing_at_an_unparsable_check_report_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self._paper_claims_ready(case)
            self.set_claim_map(case)
            (case / "experiments/outputs/checks/EXP-001.json").write_text("{broken", encoding="utf-8")
            report = check_case(case, "paper_claims")
        self.assertTrue(any("无法解析" in f.reason for f in report.findings))

    def test_claim_pointing_at_an_unknown_figure_id_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self._paper_claims_ready(case)
            # manifest 里只有 FIG-001，claim 却引用 FIG-404
            self.set_evidence(case, figure_id="FIG-001")
            self.set_claim_map(case, create_evidence=False, figure_id="FIG-404")
            report = check_case(case, "paper_claims")
        self.assertTrue(any(f.code == "CLAIM_EVIDENCE_MISSING" and "FIG-404" in f.reason
                            for f in report.findings))

    def test_claim_pointing_at_a_stale_figure_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self._paper_claims_ready(case)
            self.set_claim_map(case)
            manifest = case / "experiments/outputs/figures/manifest.md"
            manifest.write_text(manifest.read_text(encoding="utf-8").replace("| final |", "| stale |"),
                                encoding="utf-8")
            report = check_case(case, "paper_claims")
        self.assertTrue(any("stale" in f.reason for f in report.findings))

    def test_verified_claim_bound_to_a_failed_check_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self._paper_claims_ready(case)
            self.set_claim_map(case, create_evidence=False, status="verified")
            self.set_evidence(case, check_passed=False)
            report = check_case(case, "paper_claims")
        self.assertTrue(any(f.code == "CLAIM_CONTRADICTS_CHECK" for f in report.findings))

    def test_claim_map_without_a_usable_header_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self._paper_claims_ready(case)
            (case / "paper/claim_map.md").write_text(
                "# 溯源\n\n| 甲 | 乙 |\n|---|---|\n| CLM-001 | 有内容 |\n", encoding="utf-8")
            report = check_case(case, "paper_claims")
        self.assertTrue(any(f.code == "CLAIM_MAP_HEADER_INVALID" for f in report.findings))

    def test_claim_with_placeholder_required_fields_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self._paper_claims_ready(case)
            self.set_evidence(case)
            (case / "paper/claim_map.md").write_text(
                "| Claim ID | 论文位置 | 主张原文 | 强度 | 来源 EXP-ID | 数据文件 | 图/表 ID | 复算报告 | 状态 |\n"
                "|---|---|---|---|---|---|---|---|---|\n"
                "| CLM-001 | 摘要 | 待填写 | 待填写 | EXP-001 | "
                "outputs/data/EXP-001_solution.csv | FIG-001 | outputs/checks/EXP-001.json | draft |\n",
                encoding="utf-8")
            report = check_case(case, "paper_claims")
        self.assertTrue(any(f.code == "CLAIM_MAP_INCOMPLETE" for f in report.findings))

    def test_fully_resolvable_claim_map_raises_nothing(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self._paper_claims_ready(case)
            self.set_claim_map(case)
            report = check_case(case, "paper_claims")
        self.assertFalse([f for f in report.findings if f.code.startswith("CLAIM_")])

    # --- MMAG-006：损坏的复算报告分阶段 ---

    def test_corrupt_check_report_reminds_early_and_blocks_at_paper_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self._paper_claims_ready(case)
            self.set_claim_map(case)
            target = case / "experiments/outputs/checks"
            target.mkdir(parents=True, exist_ok=True)
            (target / "EXP-777.json").write_text("{not json", encoding="utf-8")
            early = check_case(case, "exploration")
            selecting = check_case(case, "model_selection")
            claiming = check_case(case, "paper_claims")
        early_hit = [f for f in early.findings if f.code == "CHECK_REPORT_UNREADABLE"]
        self.assertTrue(early_hit)
        self.assertFalse(early_hit[0].blocks)
        self.assertEqual(early.exit_code, 0)
        self.assertFalse([f for f in selecting.findings
                          if f.code == "CHECK_REPORT_UNREADABLE" and f.blocks])
        self.assertTrue([f for f in claiming.findings
                         if f.code == "CHECK_REPORT_UNREADABLE" and f.blocks])
        self.assertEqual(claiming.exit_code, 1)

    # --- MMAG-006：probe -> full 闭环 ---

    @staticmethod
    def write_spec(case, name, route="M-01", status="full", probe_result="PASS",
                   probe_exp_id="EXP-001", waiver="", probe_spec_id=None,
                   write_probe=True, probe_route=None, subproblem="问题1",
                   probe_subproblem=None):
        """Write a full spec and, unless told otherwise, the probe spec it names."""

        (case / "specs").mkdir(parents=True, exist_ok=True)
        spec_id = name[:-3]
        probe_spec_id = probe_spec_id if probe_spec_id is not None else f"{spec_id}-probe"
        if write_probe:
            (case / f"specs/{probe_spec_id}.md").write_text(
                "---\n"
                f"spec_id: {probe_spec_id}\ncase_id: {case.name}\n"
                f"route_id: {probe_route or route}\n"
                f"subproblem: {probe_subproblem or subproblem}\n"
                "method_family: heuristic\nstatus: probe\nlanguage: python\n---\n",
                encoding="utf-8",
            )
        (case / f"specs/{name}").write_text(
            "---\n"
            f"spec_id: {spec_id}\ncase_id: {case.name}\nroute_id: {route}\n"
            f"subproblem: {subproblem}\nmethod_family: heuristic\n"
            f"status: {status}\nlanguage: python\n"
            f"probe_spec_id: {probe_spec_id}\nprobe_exp_id: {probe_exp_id}\n"
            f"probe_result: {probe_result}\nprobe_waiver_reason: {waiver}\n"
            "---\n",
            encoding="utf-8",
        )

    def test_full_spec_with_passed_probe_in_the_board_is_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.set_board_experiment(case, "EXP-001")
            self.write_spec(case, "SPEC-A1-M01.md")
            report = check_case(case, "model_selection")
        self.assertFalse([f for f in report.findings if f.code == "PROBE_NOT_CLOSED"])

    def test_pending_probe_reminds_early_and_blocks_before_paper_claims(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.set_board_experiment(case, "EXP-001")
            self.add_review(case, "C3")
            self.set_claim_map(case)
            self.write_spec(case, "SPEC-A1-M01.md", probe_result="PENDING")
            selecting = check_case(case, "model_selection")
            claiming = check_case(case, "paper_claims")
        selecting_hit = [f for f in selecting.findings if f.code == "PROBE_NOT_CLOSED"]
        self.assertTrue(selecting_hit)
        self.assertFalse(selecting_hit[0].blocks)
        self.assertTrue([f for f in claiming.findings
                         if f.code == "PROBE_NOT_CLOSED" and f.blocks])

    def test_probe_experiment_absent_from_the_board_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.set_board_experiment(case, "EXP-001")
            self.write_spec(case, "SPEC-A1-M01.md", probe_exp_id="EXP-999")  # 板上没有这一行
            report = check_case(case, "model_selection")
        self.assertTrue(any(f.code == "PROBE_NOT_CLOSED" and "EXP-999" in f.reason
                            for f in report.findings))

    def test_waiver_without_reason_is_reported_and_with_reason_passes(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            self.set_comparison(case)
            self.set_board_experiment(case, "EXP-001")
            self.write_spec(case, "SPEC-A1-M01.md", probe_result="WAIVED")
            bare = check_case(case, "model_selection")
            self.write_spec(case, "SPEC-A1-M01.md", probe_result="WAIVED",
                            waiver="题面第 3 问直接指定该调度算法，无替代方法族可比")
            stated = check_case(case, "model_selection")
        self.assertTrue([f for f in bare.findings if f.code == "PROBE_NOT_CLOSED"])
        self.assertFalse([f for f in stated.findings if f.code == "PROBE_NOT_CLOSED"])

    def test_selection_conflict_between_the_two_records_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.confirm(case)
            (case / "models/candidates.md").write_text(
                "# 候选路线池\n\n## M-02：枚举\n\n- 状态：`champion`\n\n"
                "## M-01：贪心\n\n- 状态：`challenger`\n", encoding="utf-8")
            (case / "models/comparison.md").write_text(
                "# 路线比较\n\n当前 Champion：M-03\n当前 Challenger：M-01\n", encoding="utf-8")
            conflicting = check_case(case, "model_selection")

            (case / "models/comparison.md").write_text(
                "# 路线比较\n\n当前 Champion：M-02\n当前 Challenger：M-01\n", encoding="utf-8")
            aligned = check_case(case, "model_selection")
        hit = [f for f in conflicting.findings if f.code == "SELECTION_CONFLICT"]
        self.assertTrue(hit)
        self.assertIn("M-03", hit[0].reason)
        self.assertIn("M-02", hit[0].reason)
        self.assertFalse(hit[0].blocks)
        self.assertFalse([f for f in aligned.findings if f.code == "SELECTION_CONFLICT"])

    def test_probe_closure_does_not_fire_during_exploration(self):
        with tempfile.TemporaryDirectory() as directory:
            case = self.make_case(directory)
            self.write_spec(case, "SPEC-A1-M01.md", probe_result="PENDING")
            report = check_case(case, "exploration")
        self.assertFalse([f for f in report.findings if f.code == "PROBE_NOT_CLOSED"])


if __name__ == "__main__":
    unittest.main()
