import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReviewerCardPolicyTests(unittest.TestCase):
    def test_card_keeps_five_diagnostic_metadata_lines(self):
        text = (ROOT / "templates/independent_review_packet.md").read_text(encoding="utf-8")
        for marker in ("reviewer_provider", "reviewer_model", "review_session: fresh", "saw_main_conversation: false", "critical_node"):
            self.assertIn(marker, text)

    def test_five_findings_is_a_soft_expansion_limit(self):
        text = (ROOT / "REVIEWER.md").read_text(encoding="utf-8")
        self.assertIn("最多五条展开", text)
        self.assertIn("超过五条", text)
        self.assertIn("一行", text)

    def test_official_statement_data_conflict_routes_to_human(self):
        text = (ROOT / "REVIEWER.md").read_text(encoding="utf-8")
        self.assertIn("官方材料之间无法消除", text)
        self.assertIn("Human-only block", text)
        self.assertIn("硬约束", text)

    def test_card_has_room_for_three_concise_p0_findings(self):
        base = (ROOT / "templates/independent_review_packet.md").read_text(encoding="utf-8")
        findings = "\n".join(
            f"P0-{index}: 证据=官方材料；影响=路线；动作=核字段并重跑。"
            for index in range(1, 4)
        )
        filled = base.replace("Top findings:\n", f"Top findings:\n{findings}\n")
        self.assertLessEqual(len(filled.encode("utf-8")), 6144)


if __name__ == "__main__":
    unittest.main()
