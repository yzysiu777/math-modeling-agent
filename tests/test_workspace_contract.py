import unittest
from pathlib import Path

from scripts.validate_workspace import validate_static_contract


ROOT = Path(__file__).resolve().parents[1]


class WorkspaceContractTests(unittest.TestCase):
    def test_lightweight_workspace_contract_is_clean(self):
        self.assertEqual(validate_static_contract(), [])

    def test_readme_is_a_runnable_usage_manual(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        for marker in ("快速启用", "create_case.py", "C1", "C2", "C3", "make paper", "make final-check"):
            self.assertIn(marker, text)

    def test_role_startup_prompts_are_small(self):
        modeler = (ROOT / "AGENTS.md").stat().st_size + (ROOT / "prompts/modeler.md").stat().st_size
        reviewer = (ROOT / "REVIEWER.md").stat().st_size + (ROOT / "prompts/reviewer/C1_problem_challenge.md").stat().st_size
        self.assertLess(modeler, 10 * 1024)
        self.assertLess(reviewer, 5 * 1024)

    def test_review_card_template_is_under_six_kib(self):
        self.assertLessEqual((ROOT / "templates/independent_review_packet.md").stat().st_size, 6144)

    def test_no_second_runtime_mode_or_old_packet_contract(self):
        workflow = (ROOT / "protocol/competition-workflow.md").read_text(encoding="utf-8")
        self.assertIn("只有这一套竞赛流程", workflow)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("reviews/packets", readme)

    def test_paper_uses_vendored_huawei_cup_style_and_split_sections(self):
        main = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
        self.assertIn("{gmcmthesis}", main)
        self.assertGreaterEqual(len(list((ROOT / "paper/sections").glob("*.tex"))), 5)
        self.assertIn("\\bibliographystyle{gmcm}", main)

    def test_current_official_rules_remain_a_frozen_snapshot_not_2026_claim(self):
        pending = (ROOT / "paper/official/2026/manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("active: false", pending)
        self.assertIn("pending_official_paper_standard", pending)


if __name__ == "__main__":
    unittest.main()
