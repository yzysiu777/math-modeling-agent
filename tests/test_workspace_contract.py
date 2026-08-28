import unittest
from pathlib import Path

from scripts.validate_workspace import validate_static_contract


ROOT = Path(__file__).resolve().parents[1]


class WorkspaceContractTests(unittest.TestCase):
    def test_lightweight_workspace_contract_is_clean(self):
        self.assertEqual(validate_static_contract(), [])

    def test_readme_and_prompts_expose_core_loop(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for marker in ("五分钟", "候选模型池", "Champion", "Challenger", "C1/C2/C3"):
            self.assertIn(marker, readme)
        for node in ("C1_problem_challenge.md", "C2_model_challenge.md", "C3_results_challenge.md"):
            self.assertTrue((ROOT / "prompts/claude" / node).is_file())
        for card in (
            "optimization-method-cards.md",
            "data-analysis-method-cards.md",
            "hybrid-method-cards.md",
        ):
            self.assertTrue((ROOT / ".agents/skills/industrial-mathematical-modeling/references" / card).is_file())


if __name__ == "__main__":
    unittest.main()
