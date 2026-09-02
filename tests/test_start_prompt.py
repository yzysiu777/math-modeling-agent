from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.create_case import create_case
from scripts.make_start_prompt import ROLES, build_prompt


class StartPromptTests(unittest.TestCase):
    """第三次实测的写作手提示词是手写的：144 行，复述了协议，还把四条题目结论抄了进去。

    手写就会抄，抄了就多一处会过期的副本。生成器只做填空和指路。
    """

    def _case(self, questions: int = 3, *, opened: tuple[int, ...] = ()) -> Path:
        root = Path(tempfile.mkdtemp())
        case = create_case("prompt-case", cases_root=root, questions=questions)
        for number in opened:
            card = case / f"q{number}/reviews/C1_done.md"
            card.write_text("Node decision: GO\n推荐路由：data_analysis\n", encoding="utf-8")
        return case

    def test_every_role_template_can_be_filled(self):
        case = self._case()
        for role in ROLES:
            with self.subTest(role=role):
                text = build_prompt(case, role, "q1")
                self.assertIn(str(case), text)
                self.assertNotIn("<案例目录>", text)
                self.assertNotIn("<项目根>", text)

    def test_slots_resolve_to_the_requested_question(self):
        case = self._case()
        text = build_prompt(case, "writer", "q2")
        self.assertIn("当前子问题：Q2", text)
        self.assertIn(f"{case}/q2", text)
        self.assertNotIn("q<k>", text)
        self.assertNotIn("Q<k>", text)

    def test_open_and_sealed_questions_come_from_the_case(self):
        case = self._case(opened=(1,))
        text = build_prompt(case, "writer", "q1")
        self.assertIn("已通过 C1 的子问题：Q1", text)
        self.assertIn("仍处封存状态、不得书写的子问题：Q2、Q3", text)

    def test_nothing_is_open_before_any_c1(self):
        text = build_prompt(self._case(), "modeler", "q1")
        self.assertIn("已通过 C1 的子问题：无", text)

    def test_conclusions_are_pointed_at_not_transcribed(self):
        """生成器只说「以 board 为准」，不把 PASS/FAIL 的具体结论抄进提示词。"""
        case = self._case(opened=(1,))
        board = case / "q1/board.md"
        board.write_text(
            board.read_text(encoding="utf-8")
            + "| EXP-002 | M-01 | probe | 方向一致性 | ρ≥0.30 | 全样本 | 1 min | failed | 判定：FAIL | no | 换路线 |\n",
            encoding="utf-8",
        )
        text = build_prompt(case, "writer", "q1")
        self.assertIn("以 q1/board.md 的预设判据和实测判定为准", text)
        self.assertIn("failed", text)          # 只给计数
        self.assertNotIn("方向一致性", text)    # 不抄具体结论
        self.assertNotIn("ρ≥0.30", text)

    def test_writer_is_told_the_state_of_the_literature_registry(self):
        case = self._case(opened=(1,))
        text = build_prompt(case, "writer", "q1")
        self.assertIn("文献清单当前为空", text)

        registry = case / "paper/文献清单.md"
        registry.write_text(
            registry.read_text(encoding="utf-8")
            + "| a2020 | 标题 | 作者 | 2020 | 出处 | - | 联网检索 | 背景第一段 | 待核对 |\n",
            encoding="utf-8",
        )
        self.assertIn("现有 1 条，其中 1 条待队员核对", build_prompt(case, "writer", "q1"))

    def test_unknown_role_is_rejected(self):
        with self.assertRaises(ValueError):
            build_prompt(self._case(), "reviewer-2", "q1")

    def test_missing_case_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            build_prompt(Path("/nonexistent/case"), "writer", "q1")


if __name__ == "__main__":
    unittest.main()


class ReviewerPromptTests(unittest.TestCase):
    """审核者提示词里留着 <C1/C2/C3> 和 <审核卡绝对路径>，等于让人再手填一次。"""

    def _case(self):
        from scripts.create_case import create_case

        root = Path(tempfile.mkdtemp())
        case = create_case("rev-case", cases_root=root, questions=2)
        (case / "q1/reviews/C1_done.md").write_text("Node decision: GO\n", encoding="utf-8")
        return case

    def test_node_and_card_path_are_filled(self):
        case = self._case()
        (case / "q1/reviews/C3_20260101-000000.md").write_text("卡", encoding="utf-8")
        text = build_prompt(case, "reviewer", "q1", "C3")
        self.assertIn("本会话只执行 C3", text)
        self.assertIn("critical_node: C3", text)
        self.assertIn("q1/reviews/C3_20260101-000000.md", text)
        self.assertNotIn("<C1/C2/C3>", text)
        self.assertNotIn("<审核卡绝对路径", text)

    def test_missing_card_says_how_to_make_one(self):
        text = build_prompt(self._case(), "reviewer", "q1", "C2")
        self.assertIn("make review-packet", text)

    def test_newest_card_wins(self):
        case = self._case()
        for stamp in ("20260101-000000", "20260202-000000"):
            (case / f"q1/reviews/C3_{stamp}.md").write_text("卡", encoding="utf-8")
        text = build_prompt(case, "reviewer", "q1", "C3")
        self.assertIn("C3_20260202-000000.md", text)
        self.assertNotIn("C3_20260101-000000.md", text)

    def test_unknown_node_is_rejected(self):
        with self.assertRaises(ValueError):
            build_prompt(self._case(), "reviewer", "q1", "C9")
