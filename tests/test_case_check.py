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

    @staticmethod
    def set_claim_map(case, exp_id="EXP-001", status="verified"):
        (case / "paper/claim_map.md").write_text(
            "# 论文数字溯源表\n\n"
            "| Claim ID | 论文位置 | 主张原文 | 强度 | 来源 EXP-ID | 数据文件 | 图/表 ID | 复算报告 | 状态 |\n"
            "|---|---|---|---|---|---|---|---|---|\n"
            f"| CLM-001 | 摘要 | 在 12 个算例上均得到可行解 | 可行解 | {exp_id} | "
            f"outputs/data/{exp_id}_solution.csv | FIG-001 | outputs/checks/{exp_id}.json | {status} |\n",
            encoding="utf-8",
        )

    @staticmethod
    def set_board_experiment(case, exp_id="EXP-001"):
        (case / "experiments/board.md").write_text(
            "# 实验赛马板\n\n"
            "| 实验 ID | 候选路线 | 要回答的问题 | 最小配置 | 数据/实例范围 | 指标 | 预计成本 | status | 结果摘要 | 是否继续 | 下一项信息价值最高的实验 |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n"
            f"| {exp_id} | M-01 | baseline 是否可行 | toy | toy instance | 成本 | low | done | 可行 | yes | 与枚举比较 |\n",
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


if __name__ == "__main__":
    unittest.main()
