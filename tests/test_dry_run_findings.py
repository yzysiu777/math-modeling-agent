import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class LightweightProtocolTests(unittest.TestCase):
    def test_seven_stage_skeleton_and_removed_gate_table_remain(self):
        text = (ROOT / "protocol/competition-workflow.md").read_text(encoding="utf-8")
        for stage in range(1, 8):
            self.assertIn(f"## {stage}.", text)
        self.assertIn("被削门禁及替代办法", text)

    def test_only_one_competition_mode_exists(self):
        text = (ROOT / "protocol/competition-workflow.md").read_text(encoding="utf-8")
        self.assertIn("只有这一套竞赛流程", text)
        self.assertIn("不是另一种运行模式", text)

    def test_ai_accepts_findings_but_rejection_needs_signback(self):
        for relative in ("REVIEWER.md", "protocol/competition-workflow.md"):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("采纳", text)
            self.assertIn("回签", text)

    def test_modeler_may_run_probe_and_engineer_still_implements_full(self):
        text = (ROOT / "protocol/competition-workflow.md").read_text(encoding="utf-8")
        self.assertIn("Modeler 可以直接写和运行 Probe", text)
        self.assertIn("正式实现仍由 Engineer 独立完成", text)

    def test_semantic_assumptions_are_explicit_and_checked_at_c2(self):
        text = (ROOT / "protocol/competition-workflow.md").read_text(encoding="utf-8")
        for marker in ("单位", "坐标系", "时间基准", "网格对齐", "缺测语义", "C2"):
            self.assertIn(marker, text)

    def test_reviewer_probe_recheck_happens_before_full_freeze(self):
        text = (ROOT / "protocol/competition-workflow.md").read_text(encoding="utf-8")
        self.assertIn("冻结 Full SPEC", text)
        self.assertIn("Reviewer Probe", text)
        self.assertIn("复算", text)

    def test_known_official_conflict_is_counted_as_one_human_decision(self):
        text = (ROOT / "protocol/competition-workflow.md").read_text(encoding="utf-8")
        self.assertIn("应回人工 1 次", text)


if __name__ == "__main__":
    unittest.main()
