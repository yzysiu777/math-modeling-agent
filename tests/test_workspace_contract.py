import unittest
from pathlib import Path

from scripts.validate_workspace import validate_static_contract


ROOT = Path(__file__).resolve().parents[1]


class WorkspaceContractTests(unittest.TestCase):
    def test_lightweight_workspace_contract_is_clean(self):
        self.assertEqual(validate_static_contract(), [])

    def test_old_heavy_runtime_paths_are_not_current_entries(self):
        for relative in (
            "protocol/workflow.md", "protocol/gates.md", "protocol/state-machine.md",
            "scripts/gate_contract.py", "scripts/check_revision_closure.py",
            "scripts/run_trusted_check.py", "templates/case_manifest.yaml",
        ):
            self.assertFalse((ROOT / relative).exists(), relative)

    def test_readme_and_prompts_expose_core_loop(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for marker in ("十分钟", "候选模型池", "Champion", "Challenger", "C1/C2/C3"):
            self.assertIn(marker, readme)
        for node in ("C1_problem_challenge.md", "C2_model_challenge.md", "C3_results_challenge.md"):
            self.assertTrue((ROOT / "prompts/claude" / node).is_file())


if __name__ == "__main__":
    unittest.main()
