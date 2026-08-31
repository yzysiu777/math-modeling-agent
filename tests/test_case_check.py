from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_case import check_case


QUESTION_BOARD = """| 实验 ID | 路线 | 类型 | 要回答的问题/显式假设 | 预设判据 | 数据/实例范围 | 预算 | status | 结果与判定 | 是否继续 | 下一步 |
|---|---|---|---|---|---|---|---|---|---|---|
{rows}
"""


def question_spec(probe_result: str = "PASS") -> str:
    return f"""---
spec_id: SPEC-Q1-M01
case_id: case-a
route_id: M-01
subproblem: Q1
method_family: graph
status: full
language: python
probe_exp_id: EXP-001
probe_result: {probe_result}
probe_waiver_reason: 数据不可用
reviewer_probe_recheck_exp_id: ""
---
## 1. 目标与判据
目标。
## 2. 数学模型
模型。
## 3. 数据契约与显式假设
数据。
## 4. 算法与输出
算法。
## 5. 复算与遗留假设
复算。
"""


def make_question_case(root: Path, rows: str, probe_result: str = "PASS") -> Path:
    case = root / "case-a"
    for relative in (
        "input", "q1/reviews", "q1/specs", "q1/outputs/checks",
        "paper/reviews",
    ):
        (case / relative).mkdir(parents=True, exist_ok=True)
    (case / "input/题面全文.md").write_text("完整题面", encoding="utf-8")
    (case / "q1/数据范围.md").write_text("# 数据范围\n", encoding="utf-8")
    (case / "q1/brief.md").write_text(
        "# Q1 brief\n- 本题要回答什么：最小化成本\n- 数据范围：见数据范围.md\n"
        "- Champion：M-01\n",
        encoding="utf-8",
    )
    (case / "q1/board.md").write_text(QUESTION_BOARD.format(rows=rows), encoding="utf-8")
    (case / "q1/specs/SPEC-Q1-M01.md").write_text(
        question_spec(probe_result), encoding="utf-8"
    )
    (case / "checkpoint.yaml").write_text(
        """case_id: case-a
current_question: q1
questions:
  q1:
    step: B
    route:
      value: optimization
      decided_by: modeler
      confirmed_by_human: false
    reviews: {C1: pending, C2: optional}
    deterministic_risks:
      infeasible: false
      objective_mismatch: false
      leakage: false
      split_overlap: false
reviews: {C3: pending}
human_block: ""
""",
        encoding="utf-8",
    )
    return case


def question_review(case: Path, route: str | None = "optimization", body: str = "") -> None:
    route_line = f"推荐路由：{route}\n" if route else ""
    (case / "q1/reviews/C1_done.md").write_text(
        f"Node decision: GO\n{route_line}{body}\n", encoding="utf-8"
    )


def make_case(root: Path, case_id: str = "case-a", *, complete_startup: bool = True) -> Path:
    case = root / case_id
    for relative in ("input", "reviews", "models", "experiments/outputs/checks", "paper"):
        (case / relative).mkdir(parents=True, exist_ok=True)
    (case / "checkpoint.yaml").write_text(
        f"""case_id: {case_id}
stage: 1
route:
  value: optimization
  decided_by: modeler
  confirmed_by_human: {'true' if complete_startup else 'false'}
  note: test
reviews: {{C1: pending, C2: pending, C3: pending}}
human_block: ""
deterministic_risks:
  infeasible: false
  objective_mismatch: false
  leakage: false
  split_overlap: false
""", encoding="utf-8"
    )
    (case / "models/candidates.md").write_text("# candidates\n", encoding="utf-8")
    if complete_startup:
        (case / "input/problem.md").write_text("题面", encoding="utf-8")
        (case / "case_brief.md").write_text(
            "# brief\n- 用户真正要回答什么：最小化成本\n"
            "| Q1 | 分配 | 成本 | 方案 | 无 |\n- 数据文件和粒度：玩具实例\n",
            encoding="utf-8",
        )
    return case


def review(case: Path, node: str, decision: str = "GO", rejection: str = "", signback: str = "") -> None:
    (case / "reviews" / f"{node}_done.md").write_text(
        f"""# {node}
Node decision: {decision}
Rejected finding: {rejection}
Reviewer sign-back: {signback}
""", encoding="utf-8"
    )


class CaseCheckTests(unittest.TestCase):
    def test_exploration_moves_without_reviews(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = check_case(make_case(Path(tmp)), "exploration")
            self.assertFalse(report.blocked)

    def test_blank_startup_is_reminded_during_exploration(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = check_case(make_case(Path(tmp), complete_startup=False), "exploration")
            self.assertFalse(report.blocked)
            self.assertEqual(
                {finding.code for finding in report.findings},
                {"INPUT_MATERIAL_MISSING", "CASE_BRIEF_INCOMPLETE", "ROUTE_CONFIRMATION_REQUIRED"},
            )

    def test_historical_prose_data_root_counts_as_input_material(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = make_case(root)
            (case / "input/problem.md").unlink()
            data_root = root / "随题数据" / "第一题"
            data_root.mkdir(parents=True)
            (case / "input/README.md").write_text(
                f"数据根（只读）：`{data_root}/`\n", encoding="utf-8"
            )
            codes = {finding.code for finding in check_case(case, "exploration").findings}
            self.assertNotIn("INPUT_MATERIAL_MISSING", codes)

    def test_route_confirmation_blocks_model_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp), complete_startup=False)
            (case / "input/problem.md").write_text("题面", encoding="utf-8")
            (case / "case_brief.md").write_text(
                "- 用户真正要回答什么：最小化成本\n"
                "| Q1 | 分配 | 成本 | 方案 | 无 |\n- 数据文件和粒度：玩具实例\n",
                encoding="utf-8",
            )
            review(case, "C1")
            review(case, "C2")
            report = check_case(case, "model_selection")
            self.assertIn("ROUTE_CONFIRMATION_REQUIRED", {finding.code for finding in report.findings if finding.blocks})

    def test_model_selection_requires_c1_and_c2_cards(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            report = check_case(case, "model_selection")
            self.assertTrue(report.blocked)
            self.assertEqual({f.code for f in report.findings if f.blocks}, {"C1_REQUIRED", "C2_REQUIRED"})

    def test_go_cards_allow_model_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            review(case, "C1")
            review(case, "C2", "GO_WITH_FIXES")
            self.assertFalse(check_case(case, "model_selection").blocked)

    def test_stop_blocks_but_is_owned_by_ai_unless_human_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            review(case, "C1", "STOP")
            review(case, "C2")
            finding = next(f for f in check_case(case, "model_selection").findings if f.code == "C1_STOP")
            self.assertEqual(finding.owner, "ORCHESTRATOR")

    def test_rejecting_finding_requires_reviewer_signback(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            review(case, "C1", rejection="P1-1")
            review(case, "C2")
            self.assertTrue(check_case(case, "model_selection").blocked)
            review(case, "C1", rejection="P1-1", signback="ACCEPT_REJECTION")
            self.assertFalse(check_case(case, "model_selection").blocked)

    def test_reviewer_can_reject_producer_rejection(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            review(case, "C1", rejection="P1-1", signback="REJECT_REJECTION")
            review(case, "C2")
            self.assertTrue(check_case(case, "model_selection").blocked)

    def test_metadata_is_not_treated_as_identity_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            review(case, "C1")
            review(case, "C2")
            self.assertFalse(check_case(case, "model_selection").blocked)

    def test_human_block_is_the_only_early_human_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            text = (case / "checkpoint.yaml").read_text(encoding="utf-8")
            (case / "checkpoint.yaml").write_text(
                text.replace('human_block: ""', 'human_block: "官方文字与官方数据冲突，改变可用数据范围"'),
                encoding="utf-8",
            )
            finding = next(f for f in check_case(case, "exploration").findings if f.code == "HUMAN_ONLY_BLOCK")
            self.assertEqual(finding.owner, "HUMAN")

    def test_paper_claims_requires_c3(self):
        with tempfile.TemporaryDirectory() as tmp:
            case = make_case(Path(tmp))
            review(case, "C1")
            review(case, "C2")
            self.assertIn("C3_REQUIRED", {f.code for f in check_case(case, "paper_claims").findings})

    def test_c1_route_line_folds_route_confirmation(self):
        pass_row = "| EXP-001 | M-01 | probe | q | PASS | toy | 1 min | done | 判定：PASS | yes | Full |"
        with tempfile.TemporaryDirectory() as tmp:
            case = make_question_case(Path(tmp), pass_row)
            question_review(case)
            codes = {finding.code for finding in check_case(case, "model_selection").findings}
            self.assertNotIn("ROUTE_CONFIRMATION_REQUIRED", codes)

    def test_c1_without_route_does_not_fold_route_confirmation(self):
        pass_row = "| EXP-001 | M-01 | probe | q | PASS | toy | 1 min | done | 判定：PASS | yes | Full |"
        with tempfile.TemporaryDirectory() as tmp:
            case = make_question_case(Path(tmp), pass_row)
            question_review(case, route=None)
            codes = {finding.code for finding in check_case(case, "model_selection").findings if finding.blocks}
            self.assertIn("ROUTE_CONFIRMATION_REQUIRED", codes)

    def test_c2_trigger_1_requires_c2_without_champion_pass(self):
        queued = "| EXP-001 | M-01 | probe | q | PASS | toy | 1 min | queued |  |  | Probe |"
        with tempfile.TemporaryDirectory() as tmp:
            case = make_question_case(Path(tmp), queued)
            question_review(case)
            self.assertIn("C2_REQUIRED", {f.code for f in check_case(case, "model_selection").findings})

    def test_c2_trigger_1_negative_skips_c2_with_champion_pass(self):
        passed = "| EXP-001 | M-01 | probe | q | PASS | toy | 1 min | done | 判定：PASS | yes | Full |"
        with tempfile.TemporaryDirectory() as tmp:
            case = make_question_case(Path(tmp), passed)
            question_review(case)
            report = check_case(case, "model_selection")
            self.assertNotIn("C2_REQUIRED", {f.code for f in report.findings})
            self.assertIn("C2_SKIPPED", {f.code for f in report.findings})

    def test_c2_trigger_2_requires_c2_after_two_failures_on_same_route(self):
        rows = "\n".join((
            "| EXP-001 | M-01 | probe | q | PASS | toy | 1 min | done | 判定：PASS | yes | Full |",
            "| EXP-002 | M-01 | probe | q2 | PASS | toy | 1 min | failed | 判定：FAIL | no | 改进 |",
            "| EXP-003 | M-01 | probe | q3 | PASS | toy | 1 min | failed | 判定：FAIL | no | 改进 |",
        ))
        with tempfile.TemporaryDirectory() as tmp:
            case = make_question_case(Path(tmp), rows)
            question_review(case)
            self.assertIn("C2_REQUIRED", {f.code for f in check_case(case, "model_selection").findings})

    def test_c2_trigger_2_negative_allows_one_failure(self):
        rows = "\n".join((
            "| EXP-001 | M-01 | probe | q | PASS | toy | 1 min | done | 判定：PASS | yes | Full |",
            "| EXP-002 | M-01 | probe | q2 | PASS | toy | 1 min | failed | 判定：FAIL | no | 改进 |",
        ))
        with tempfile.TemporaryDirectory() as tmp:
            case = make_question_case(Path(tmp), rows)
            question_review(case)
            self.assertNotIn("C2_REQUIRED", {f.code for f in check_case(case, "model_selection").findings})

    def test_c2_trigger_3_requires_c2_for_waived_or_pending_spec(self):
        passed = "| EXP-001 | M-01 | probe | q | PASS | toy | 1 min | done | 判定：PASS | yes | Full |"
        for probe_result in ("WAIVED", "PENDING"):
            with self.subTest(probe_result=probe_result), tempfile.TemporaryDirectory() as tmp:
                case = make_question_case(Path(tmp), passed, probe_result)
                question_review(case)
                self.assertIn("C2_REQUIRED", {f.code for f in check_case(case, "model_selection").findings})

    def test_c2_trigger_3_negative_allows_pass_spec(self):
        passed = "| EXP-001 | M-01 | probe | q | PASS | toy | 1 min | done | 判定：PASS | yes | Full |"
        with tempfile.TemporaryDirectory() as tmp:
            case = make_question_case(Path(tmp), passed, "PASS")
            question_review(case)
            self.assertNotIn("C2_REQUIRED", {f.code for f in check_case(case, "model_selection").findings})

    def test_review_card_with_options_but_no_recommendation_is_reminded(self):
        passed = "| EXP-001 | M-01 | probe | q | PASS | toy | 1 min | done | 判定：PASS | yes | Full |"
        with tempfile.TemporaryDirectory() as tmp:
            case = make_question_case(Path(tmp), passed)
            question_review(case, body="选项 A：路线一\n选项 B：路线二")
            self.assertIn(
                "REVIEW_CARD_NO_RECOMMENDATION",
                {f.code for f in check_case(case, "model_selection").findings},
            )

    def test_final_checks_c1_for_every_question_not_only_current_question(self):
        passed = "| EXP-001 | M-01 | probe | q | PASS | toy | 1 min | done | 判定：PASS | yes | Full |"
        with tempfile.TemporaryDirectory() as tmp:
            case = make_question_case(Path(tmp), passed)
            question_review(case)
            for relative in ("q2/reviews", "q2/specs", "q2/outputs/checks"):
                (case / relative).mkdir(parents=True, exist_ok=True)
            (case / "q2/brief.md").write_text(
                "- 本题要回答什么：验证\n- 数据范围：见白名单\n- Champion：M-01\n",
                encoding="utf-8",
            )
            (case / "q2/board.md").write_text(QUESTION_BOARD.format(rows=passed), encoding="utf-8")
            checkpoint = (case / "checkpoint.yaml").read_text(encoding="utf-8")
            q2_state = """  q2:
    step: B
    route:
      value: optimization
      decided_by: modeler
      confirmed_by_human: true
    deterministic_risks: {infeasible: false, objective_mismatch: false, leakage: false, split_overlap: false}
"""
            (case / "checkpoint.yaml").write_text(
                checkpoint.replace("reviews: {C3: pending}", q2_state + "reviews: {C3: pending}"),
                encoding="utf-8",
            )
            findings = check_case(case, "final").findings
            self.assertTrue(any(f.code == "C1_REQUIRED" and "Q2" in f.reason for f in findings))


if __name__ == "__main__":
    unittest.main()
