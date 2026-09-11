from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.check_case import check_case
from scripts.check_spec import spec_reminders
from scripts.qa_latex import check_deliverable_sections
from tests.test_case_check import make_question_case, question_review


PASSED_ROW = "| EXP-001 | M-01 | probe | q | PASS | toy | 1 min | done | 判定：PASS | yes | Full |"


class DeliverableContractTests(unittest.TestCase):
    """工作台所有机制都朝一个方向：削弱结论、降级路线、拒绝无据之词。

    没有一处问「题目要的东西，最后拿什么交」，于是一串各自合规的降级可以把交付物
    带到离题面很远的地方，而没有任何环节亮红灯。契约是后面所有核对的参照物。
    """

    def _case(self, *, contract: str | None = None, board_extra: str = "") -> Path:
        case = make_question_case(Path(tempfile.mkdtemp()), PASSED_ROW + board_extra)
        question_review(case, nodes=("C1", "C2"))
        brief = case / "q1/brief.md"
        text = brief.read_text(encoding="utf-8")
        if contract is not None:
            text += "\n## 交付物契约\n\n" + contract + "\n"
        brief.write_text(text, encoding="utf-8")
        return case

    PLACEHOLDER = (
        "| 交付物 | 形态 | 量纲/单位 | 覆盖范围 | 验收方式 |\n|---|---|---|---|---|\n"
        "| D-01 | 场 / 序列 / 方案 / 分类 / 说明 | 有量纲（写明单位）或无量纲 | 时间、空间或样本范围 | 怎样算交付到位 |"
    )
    FILLED = (
        "| 交付物 | 形态 | 量纲/单位 | 覆盖范围 | 验收方式 |\n|---|---|---|---|---|\n"
        "| D-01 | 方案 | 无量纲 | 全部实例 | 每个实例给出可行方案且代价不高于基线 |"
    )

    def test_missing_contract_is_reminded(self):
        codes = {f.code for f in check_case(self._case(), "model_selection").findings}
        self.assertIn("DELIVERABLE_CONTRACT_EMPTY", codes)

    def test_placeholder_contract_is_reminded(self):
        case = self._case(contract=self.PLACEHOLDER)
        codes = {f.code for f in check_case(case, "model_selection").findings}
        self.assertIn("DELIVERABLE_CONTRACT_EMPTY", codes)

    def test_filled_contract_passes(self):
        case = self._case(contract=self.FILLED)
        codes = {f.code for f in check_case(case, "model_selection").findings}
        self.assertNotIn("DELIVERABLE_CONTRACT_EMPTY", codes)

    def test_the_reminder_never_blocks(self):
        report = check_case(self._case(), "model_selection")
        finding = next(f for f in report.findings if f.code == "DELIVERABLE_CONTRACT_EMPTY")
        self.assertFalse(finding.blocks)

    def test_exploration_does_not_nag_before_the_brief_is_written(self):
        codes = {f.code for f in check_case(self._case(), "exploration").findings}
        self.assertNotIn("DELIVERABLE_CONTRACT_EMPTY", codes)


class DowngradeAnsweredTests(unittest.TestCase):
    """降级各自都记录得很好，但没有一条回答「那题面要的东西由什么承担」。"""

    DOWNGRADE = "\n| EXP-002 | M-01 | probe | q | PASS | toy | 1 min | failed | 判定：FAIL，按预注册降级 M-02 | no | 降级 |"

    def _case(self, board_extra: str) -> Path:
        case = make_question_case(Path(tempfile.mkdtemp()), PASSED_ROW + board_extra)
        question_review(case, nodes=("C1", "C2"))
        return case

    def test_downgrade_without_an_answer_is_reminded(self):
        codes = {f.code for f in check_case(self._case(self.DOWNGRADE), "model_selection").findings}
        self.assertIn("DOWNGRADE_UNANSWERED", codes)

    def test_downgrade_with_an_answer_passes(self):
        extra = self.DOWNGRADE.replace("| 降级 |", "| 降级；交付物 D-01 改由 M-02 承担 |")
        codes = {f.code for f in check_case(self._case(extra), "model_selection").findings}
        self.assertNotIn("DOWNGRADE_UNANSWERED", codes)

    def test_no_downgrade_no_reminder(self):
        codes = {f.code for f in check_case(self._case(""), "model_selection").findings}
        self.assertNotIn("DOWNGRADE_UNANSWERED", codes)


class AbsoluteFloorTests(unittest.TestCase):
    """判据整条写成相对量时，绝对表现无价值的路线也能靠「比对照好一点」胜出。"""

    def _case_with_goal(self, goal: str) -> Path:
        case = make_question_case(Path(tempfile.mkdtemp()), PASSED_ROW)
        spec = sorted((case / "q1/specs").glob("SPEC-*.md"))[0]
        text = spec.read_text(encoding="utf-8")
        head, _, rest = text.partition("## 1. 目标与判据")
        _, _, tail = rest.partition("## 2.")
        spec.write_text(f"{head}## 1. 目标与判据\n\n{goal}\n\n## 2.{tail}", encoding="utf-8")
        return case

    def test_relative_only_criteria_are_reminded(self):
        case = self._case_with_goal("- 通过/失败判据：相对增量 ≥ 某值")
        self.assertTrue(any("绝对底线" in item for item in spec_reminders(case, "q1")))

    def test_both_rows_pass(self):
        case = self._case_with_goal(
            "- 通过/失败判据：\n  - 绝对底线：低于此值无实用价值\n  - 相对增量：相对对照的门槛"
        )
        self.assertEqual(spec_reminders(case, "q1"), [])

    def test_reminders_do_not_affect_spec_validation(self):
        from scripts.check_spec import validate_case_specs

        case = self._case_with_goal("- 通过/失败判据：相对增量 ≥ 某值")
        self.assertEqual(validate_case_specs(case, "q1"), [])


class DeliverableSectionTests(unittest.TestCase):
    def _paper(self, body: str) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "paper/sections").mkdir(parents=True)
        (root / "paper/sections/q1.tex").write_text(body, encoding="utf-8")
        return root / "paper"

    def test_missing_section_is_reminded(self):
        problems = check_deliverable_sections(self._paper("\\section{问题一}\n正文。\n"))
        self.assertTrue(any("交付物对照" in item for item in problems))

    def test_present_section_passes(self):
        body = "\\section{问题一}\n正文。\n\\subsection{交付物对照}\n对照表。\n"
        self.assertEqual(check_deliverable_sections(self._paper(body)), [])

    def test_untouched_template_is_not_nagged(self):
        body = "\\section{问题一}\n\\paperexample{说明}\n待填写\n"
        self.assertEqual(check_deliverable_sections(self._paper(body)), [])


if __name__ == "__main__":
    unittest.main()


class RouteSwitchBeforeDowngradeTests(unittest.TestCase):
    """一条路不通不等于所有路不通。

    实测里某题的候选池有四条，第一条判据不过之后直接落到预注册的降级路线，
    另外两条从头到尾没被碰过 —— 而其中一条明确写着可能保住题面要求的交付形态。
    """

    DOWNGRADE = (
        "\n| EXP-002 | M-01 | probe | q | PASS | toy | 1 min | failed | "
        "判定：FAIL，按预注册降级 M-02；交付物 D-01 改由 M-02 承担 | no | 降级 |"
    )
    HEADER = (
        "\n## 候选路线与七维度\n\n"
        "| 路线 | 方法族 | 状态 |\n|---|---|---|\n"
    )

    def _case(self, *, board_extra: str, statuses: tuple[str, ...]) -> Path:
        case = make_question_case(Path(tempfile.mkdtemp()), PASSED_ROW + board_extra)
        question_review(case, nodes=("C1", "C2"))
        brief = case / "q1/brief.md"
        rows = "".join(
            f"| M-{index:02d} | 某方法族 | {status} |\n"
            for index, status in enumerate(statuses, start=1)
        )
        brief.write_text(
            brief.read_text(encoding="utf-8") + self.HEADER + rows, encoding="utf-8"
        )
        return case

    def test_downgrade_with_untried_routes_is_reminded(self):
        case = self._case(board_extra=self.DOWNGRADE, statuses=("已实现", "待试", "待试"))
        finding = next(
            f for f in check_case(case, "model_selection").findings
            if f.code == "UNTRIED_ROUTES"
        )
        self.assertIn("M-02", finding.reason)
        self.assertIn("M-03", finding.reason)
        self.assertFalse(finding.blocks)

    def test_all_routes_resolved_passes(self):
        case = self._case(board_extra=self.DOWNGRADE, statuses=("已实现", "已排除（数据不足）"))
        codes = {f.code for f in check_case(case, "model_selection").findings}
        self.assertNotIn("UNTRIED_ROUTES", codes)

    def test_no_downgrade_no_reminder(self):
        case = self._case(board_extra="", statuses=("已实现", "待试"))
        codes = {f.code for f in check_case(case, "model_selection").findings}
        self.assertNotIn("UNTRIED_ROUTES", codes)


class FailureOrderTests(unittest.TestCase):
    """降级是最后一步。把顺序写死在模板里，防止有人改回「失败即降级」。"""

    ROOT = Path(__file__).resolve().parents[1]

    def test_route_switch_comes_before_downgrade(self):
        text = (self.ROOT / "templates/experiment_board.md").read_text(encoding="utf-8")
        switch = text.index("回到路线池")
        downgrade = text.index("一条都没有，才降级")
        self.assertLess(switch, downgrade)

    def test_the_board_says_downgrade_is_last(self):
        text = (self.ROOT / "templates/experiment_board.md").read_text(encoding="utf-8")
        self.assertIn("降级是最后一步", text)
        self.assertIn("逐条写明", text)

    def test_route_table_carries_a_status_column(self):
        text = (self.ROOT / "templates/case_brief.md").read_text(encoding="utf-8")
        for marker in ("状态", "待试", "进行中", "已实现", "已排除"):
            self.assertIn(marker, text)

    def test_form_outranks_coverage_is_stated(self):
        text = (self.ROOT / "prompts/modeler.md").read_text(encoding="utf-8")
        self.assertIn("形态优先于范围", text)
        self.assertIn("保形态、缩范围", text)
