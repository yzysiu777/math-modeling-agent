from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_case import check_case
from scripts.model_checks import check_information_cutoff, check_nonanticipativity
from tests.test_case_check import make_question_case, question_review


PASSED_ROW = "| EXP-001 | M-01 | probe | q | PASS | toy | 1 min | done | 判定：PASS | yes | Full |"


class UntriedRoutesAtCloseTests(unittest.TestCase):
    """一题做完，路线表里不该还留着没人碰过的行。

    原先这条提醒只在已有降级记录时触发，而一路 PASS 的题从不降级 —— 于是发散时写下的
    候选可以静静躺到交稿，没有任何环节问一句它们为什么没试。
    """

    HEADER = "\n## 候选路线与七维度\n\n| 路线 | 方法族 | 状态 |\n|---|---|---|\n"

    def _case(self, *statuses: str) -> Path:
        case = make_question_case(Path(tempfile.mkdtemp()), PASSED_ROW)
        question_review(case, nodes=("C1", "C2"))
        brief = case / "q1/brief.md"
        rows = "".join(
            f"| M-{index:02d} | 某方法族 | {status} |\n"
            for index, status in enumerate(statuses, start=1)
        )
        brief.write_text(brief.read_text(encoding="utf-8") + self.HEADER + rows, encoding="utf-8")
        return case

    def test_untried_routes_at_paper_stage_are_reminded(self):
        case = self._case("已实现", "待试")
        finding = next(
            f for f in check_case(case, "paper_claims").findings if f.code == "UNTRIED_ROUTES"
        )
        self.assertIn("M-02", finding.reason)
        self.assertFalse(finding.blocks)

    def test_resolved_routes_at_paper_stage_pass(self):
        case = self._case("已实现", "已排除（方法族在本题不成立）")
        codes = {f.code for f in check_case(case, "paper_claims").findings}
        self.assertNotIn("UNTRIED_ROUTES", codes)

    def test_exploration_stage_keeps_quiet(self):
        case = self._case("已实现", "待试")
        codes = {f.code for f in check_case(case, "exploration").findings}
        self.assertNotIn("UNTRIED_ROUTES", codes)


class TemplateWordingTests(unittest.TestCase):
    """本轮的规矩写在模板里，改回去会被这些断言挡住。"""

    ROOT = Path(__file__).resolve().parents[1]

    def _read(self, name: str) -> str:
        return (self.ROOT / name).read_text(encoding="utf-8")

    def test_idea_table_carries_a_disposal_column(self):
        text = self._read("templates/case_brief.md")
        self.assertIn("处置", text)
        for marker in ("已成路线", "已排除：方法族", "已排除：某实现", "保留待试"):
            self.assertIn(marker, text)

    def test_exclusion_must_name_its_layer(self):
        brief = self._read("templates/case_brief.md")
        self.assertIn("方法族", brief)
        self.assertIn("只排掉了一种实现的", brief)
        ideas = self._read(".agents/skills/competition-modeling/references/brainstorming.md")
        self.assertIn("淘汰要标层", ideas)
        self.assertIn("是**障碍**还是", ideas)

    def test_board_names_the_ablation_type(self):
        text = self._read("templates/experiment_board.md")
        self.assertIn("`ablation`", text)
        self.assertIn("增益分解", text)
        self.assertIn("固定上游", text)
        self.assertIn("各自端到端", text)
        self.assertIn("不得相加", text)

    def test_spec_asks_for_two_levels_and_two_periods(self):
        text = self._read("templates/spec.md")
        self.assertIn("两级指标", text)
        self.assertIn("选择期与评估期", text)

    def test_claim_map_covers_bound_attribution_and_leakage(self):
        text = self._read("templates/claim_map.md")
        for marker in ("`下界`", "`归因`", "`无泄漏`", "同一个术语在不同位置指不同对象"):
            self.assertIn(marker, text)

    def test_recipes_name_the_four_checks(self):
        text = self._read(".agents/skills/competition-engineering/references/recompute-recipes.md")
        for marker in ("独立复算", "变异注入", "异族互证", "参数敏感性", "信息可得性", "数字自洽"):
            self.assertIn(marker, text)


class InformationCutoffTests(unittest.TestCase):
    """按时刻比较，不按日期 —— 同一天的值可能属于决策之后的那一步。"""

    def test_a_value_revealed_after_the_decision_is_caught(self):
        errors = check_information_cutoff(
            [
                {"name": "past", "available_at": 3},
                {"name": "future", "available_at": 9},
            ],
            decision_time=5,
        )
        self.assertEqual(len(errors), 1)
        self.assertIn("future", errors[0])

    def test_per_item_decision_moments_pass(self):
        errors = check_information_cutoff(
            [
                {"name": "a", "available_at": 1, "used_for": 2},
                {"name": "b", "available_at": 2, "used_for": 2},
            ]
        )
        self.assertEqual(errors, [])

    def test_incomparable_stamps_are_reported_not_raised(self):
        errors = check_information_cutoff([{"name": "a", "available_at": "2026-01-01"}], decision_time=5)
        self.assertEqual(len(errors), 1)
        self.assertIn("not comparable", errors[0])


class NonanticipativityTests(unittest.TestCase):
    """共同前缀内的动作必须一致；差一格就是读了未来。"""

    PATH_A = [1, 2, 3, 4]
    PATH_B = [1, 2, 9, 9]

    def test_a_causal_procedure_passes(self):
        report = check_nonanticipativity(lambda path: [x * 2 for x in path], self.PATH_A, self.PATH_B, 2)
        self.assertTrue(report["passed"])
        self.assertTrue(report["prefix_shared"])
        self.assertTrue(report["paths_diverge"])

    def test_reading_the_future_is_caught(self):
        report = check_nonanticipativity(lambda path: [sum(path)] * 4, self.PATH_A, self.PATH_B, 2)
        self.assertFalse(report["passed"])
        self.assertEqual(report["first_mismatch"], 0)
        self.assertGreater(report["max_deviation"], 0)

    def test_a_vacuous_test_says_so(self):
        report = check_nonanticipativity(lambda path: list(path), self.PATH_A, self.PATH_A, 2)
        self.assertTrue(report["passed"])
        self.assertFalse(report["paths_diverge"])


if __name__ == "__main__":
    unittest.main()
