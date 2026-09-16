from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from scripts.check_case import _review_decision
from scripts.create_case import create_case
from scripts.make_review_packet import build_packet, node_decision
from scripts.make_start_prompt import ROOT, build_prompt
from scripts.qa_latex import check_sealed_questions


class NodeDecisionTests(unittest.TestCase):
    """空白审核卡自带占位行 `Node decision: GO | GO_WITH_FIXES | STOP`。

    启动提示词和论文封存检查原先只认字段名，卡一生成就把该题当成已通过 C1；
    check_case 只认填好的值，于是三处给出互相矛盾的结论。现在三处共用一个判定。
    """

    def _case(self) -> Path:
        case = create_case("decision-case", cases_root=Path(tempfile.mkdtemp()), questions=2)
        (case / "paper/sections").mkdir(parents=True, exist_ok=True)
        (case / "paper/sections/02-restate.tex").write_text(
            "\\subsection{问题一}\n% <<Q1-SEALED>>\n构建网格。\n", encoding="utf-8"
        )
        return case

    def _write_card(self, case: Path, decision: str | None) -> None:
        text = build_packet(case, "C1", "C1-test", "q1")
        if decision is not None:
            text = text.replace("Node decision: GO | GO_WITH_FIXES | STOP",
                                f"Node decision: {decision}")
        (case / "q1/reviews/C1_20260916-000000.md").write_text(text, encoding="utf-8")

    def test_only_a_single_filled_value_counts(self):
        self.assertIsNone(node_decision("Node decision: GO | GO_WITH_FIXES | STOP\n"))
        self.assertIsNone(node_decision("Node decision:\n"))
        self.assertEqual(node_decision("Node decision：go_with_fixes\n"), "GO_WITH_FIXES")

    def test_blank_card_does_not_open_the_question(self):
        case = self._case()
        self._write_card(case, None)
        text = build_prompt(case, "writer", "q1")
        self.assertIn("已通过 C1 的子问题：无", text)
        self.assertIn("仍处封存状态、不得书写的子问题：Q1、Q2", text)
        self.assertTrue(check_sealed_questions(case / "paper"))
        self.assertIsNone(_review_decision(case, "C1", "q1")[0])

    def test_filled_card_opens_the_question(self):
        case = self._case()
        self._write_card(case, "GO_WITH_FIXES")
        text = build_prompt(case, "writer", "q1")
        self.assertIn("已通过 C1 的子问题：Q1", text)
        self.assertEqual(check_sealed_questions(case / "paper"), [])
        self.assertEqual(_review_decision(case, "C1", "q1")[0], "GO_WITH_FIXES")


class ReviewerPromptPathTests(unittest.TestCase):
    def test_reviewer_is_given_the_project_root(self):
        case = create_case("root-case", cases_root=Path(tempfile.mkdtemp()), questions=1)
        self.assertIn(f"项目根：{ROOT}", build_prompt(case, "reviewer", "q1", "C1"))

    def test_relative_case_dir_yields_absolute_card_path(self):
        case = create_case("rel-case", cases_root=Path(tempfile.mkdtemp()), questions=1)
        (case / "q1/reviews/C1_20260916-000000.md").write_text("卡", encoding="utf-8")
        cwd = os.getcwd()
        os.chdir(case.parent)
        try:
            text = build_prompt(Path(case.name), "reviewer", "q1", "C1")
        finally:
            os.chdir(cwd)
        card = case.resolve() / "q1/reviews/C1_20260916-000000.md"
        self.assertIn(f"审核卡：{card}\n", text)


if __name__ == "__main__":
    unittest.main()
