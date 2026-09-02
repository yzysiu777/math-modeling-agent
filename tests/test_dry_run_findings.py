import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LightweightProtocolTests(unittest.TestCase):
    def test_four_question_steps_and_case_close_are_documented(self):
        text = (ROOT / "protocol/competition-workflow.md").read_text(encoding="utf-8")
        for marker in ("## A 定题", "## B 试跑", "## C 出结果", "## D 写本题", "## E 全案例收官"):
            self.assertIn(marker, text)

    def test_only_one_competition_mode_exists(self):
        text = (ROOT / "protocol/competition-workflow.md").read_text(encoding="utf-8")
        self.assertIn("只有这一套流程", text)
        self.assertIn("不切换模式", text)

    def test_timeboxes_and_stage_mapping_are_explicit(self):
        text = (ROOT / "protocol/competition-workflow.md").read_text(encoding="utf-8")
        for marker in ("不超过 2 小时", "不超过 4 小时", "exploration", "model_selection", "paper_claims", "final"):
            self.assertIn(marker, text)

    def test_review_recommendation_is_default_but_rejection_needs_signback(self):
        for relative in ("REVIEWER.md", "protocol/competition-workflow.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("推荐动作", text)
            self.assertIn("默认执行", text)
            self.assertIn("回签", text)

    def test_c1_c2_c3_frequency_is_documented(self):
        """MMAG-009 起 C2 每题必做，三条风险条件降级为审核卡的输入。"""
        text = (ROOT / "protocol/competition-workflow.md").read_text(encoding="utf-8")
        self.assertIn("C1 每题必做", text)
        self.assertIn("C2 每题必做", text)
        self.assertNotIn("C2 仅在", text)
        self.assertIn("全案例 C3", text)

    def test_stage_zero_and_shared_scope_are_documented(self):
        text = (ROOT / "protocol/competition-workflow.md").read_text(encoding="utf-8")
        self.assertIn("sources.yaml", text)
        self.assertIn("shared", text)
        self.assertIn("完整列名", text)

    def test_question_dependency_is_one_way(self):
        text = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("j < k", text)
        self.assertIn("CROSS_QUESTION_BACKWARD_REFERENCE", text)


if __name__ == "__main__":
    unittest.main()
