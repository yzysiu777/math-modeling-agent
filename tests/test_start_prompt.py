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

    def test_unknown_role_is_rejected(self):
        with self.assertRaises(ValueError):
            build_prompt(self._case(), "reviewer-2", "q1")

    def test_missing_case_is_rejected(self):
        with self.assertRaises(FileNotFoundError):
            build_prompt(Path("/nonexistent/case"), "writer", "q1")


if __name__ == "__main__":
    unittest.main()
