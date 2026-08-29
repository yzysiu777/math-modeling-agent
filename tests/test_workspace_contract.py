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
            self.assertTrue((ROOT / "prompts/reviewer" / node).is_file())
        for card in (
            "optimization-method-cards.md",
            "data-analysis-method-cards.md",
            "hybrid-method-cards.md",
        ):
            self.assertTrue((ROOT / ".agents/skills/industrial-mathematical-modeling/references" / card).is_file())

    def test_reviewer_paths_are_vendor_neutral_and_old_paths_are_absent(self):
        self.assertTrue((ROOT / "REVIEWER.md").is_file())
        self.assertFalse((ROOT / "CLAUDE.md").exists())
        self.assertTrue((ROOT / "templates/independent_review_packet.md").is_file())
        self.assertFalse((ROOT / "templates/claude_review_packet.md").exists())
        self.assertTrue((ROOT / "prompts/reviewer").is_dir())
        self.assertFalse((ROOT / "prompts/claude").exists())

    def test_reviewer_protocol_has_extensible_metadata_and_distinct_lenses(self):
        packet = (ROOT / "templates/independent_review_packet.md").read_text(encoding="utf-8")
        for marker in (
            "reviewer_provider", "reviewer_model", "review_session", "saw_main_conversation",
            "critical_node", "fresh", "false",
        ):
            self.assertIn(marker, packet)
        prompt_paths = {
            "C1": ROOT / "prompts/reviewer/C1_problem_challenge.md",
            "C2": ROOT / "prompts/reviewer/C2_model_challenge.md",
            "C3": ROOT / "prompts/reviewer/C3_results_challenge.md",
        }
        prompts = {node: path.read_text(encoding="utf-8") for node, path in prompt_paths.items()}
        for node, prompt in prompts.items():
            self.assertIn(f"critical_node: {node}", prompt)
            self.assertIn("Alternative method family", prompt)
            self.assertIn("Disconfirming test or counterexample", prompt)
            self.assertIn("What was not checked", prompt)
            self.assertIn("Human decisions required", prompt)
        self.assertEqual(len(set(prompts.values())), 3)

    def test_active_reviewer_files_have_no_retired_vendor_or_path(self):
        active_files = [
            ROOT / "README.md", ROOT / "AGENTS.md", ROOT / "agent.md", ROOT / "REVIEWER.md",
            ROOT / "docs/README.md", ROOT / "docs/architecture.md",
            ROOT / "protocol/competition-workflow.md", ROOT / "protocol/team-collaboration.md",
            ROOT / "protocol/decision-log.md", ROOT / "prompts/codex-start.md", ROOT / "prompts/final-handoff.md",
            ROOT / "templates/independent_review_packet.md", ROOT / "templates/final_checklist.md",
            ROOT / ".agents/skills/industrial-mathematical-modeling/SKILL.md",
            ROOT / ".agents/skills/model-race/SKILL.md",
        ]
        active_files.extend(sorted((ROOT / "prompts/reviewer").glob("*.md")))
        active_files.extend(sorted((ROOT / "cases/examples").glob("*/reviews/README.md")))
        for path in active_files:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("Claude", text, path)
            self.assertNotIn("CLAUDE", text, path)
            self.assertNotIn("prompts/claude", text, path)
            self.assertNotIn("claude_review_packet", text, path)


if __name__ == "__main__":
    unittest.main()
