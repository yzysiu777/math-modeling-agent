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
        self.assertIn("只有这一套流程", workflow)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("reviews/packets", readme)

    def test_paper_uses_vendored_huawei_cup_style_and_split_sections(self):
        main = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
        self.assertIn("{gmcmthesis}", main)
        self.assertGreaterEqual(len(list((ROOT / "paper/sections").glob("*.tex"))), 5)
        self.assertIn("\\bibliographystyle{gmcm}", main)
        self.assertIn("\\pagestyle{plain}", main)

    def test_current_official_rules_remain_a_frozen_snapshot_not_2026_claim(self):
        pending = (ROOT / "paper/official/2026/manifest.yaml").read_text(encoding="utf-8")
        self.assertIn("active: false", pending)
        self.assertIn("pending_official_paper_standard", pending)

    def test_production_agents_are_locked_to_sol_high(self):
        for relative in (
            "prompts/startup/orchestrator.md", "prompts/startup/modeler.md",
            "prompts/startup/engineer.md", "prompts/startup/writer.md",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("gpt-5.6-sol", text, relative)
            self.assertIn("high", text, relative)
        orchestrator = (ROOT / "prompts/orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("不得自动降级", orchestrator)

    def test_all_production_agents_are_manually_started(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        orchestrator = (ROOT / "prompts/orchestrator.md").read_text(encoding="utf-8")
        collaboration = (ROOT / "protocol/team-collaboration.md").read_text(encoding="utf-8")
        for text in (agents, orchestrator, collaboration):
            self.assertIn("人工启动", text)
        self.assertIn("不调用任务工具", orchestrator)

    def test_teammate_notes_are_on_the_orchestrator_prohibited_write_list(self):
        orchestrator = (ROOT / "prompts/orchestrator.md").read_text(encoding="utf-8")
        collaboration = (ROOT / "protocol/team-collaboration.md").read_text(encoding="utf-8")
        for text in (orchestrator, collaboration):
            self.assertIn("我的笔记.md", text)
            self.assertIn("只读", text)
            self.assertIn("不得修改", text)

    def test_retired_probe_and_comparison_templates_are_absent(self):
        for relative in (
            "templates/spec_probe.md", "templates/model_comparison.md", "templates/model_candidate.md",
        ):
            self.assertFalse((ROOT / relative).exists(), relative)

    def test_reviewer_is_manually_started_and_vendor_neutral(self):
        startup = (ROOT / "prompts/startup/reviewer.md").read_text(encoding="utf-8")
        orchestrator = (ROOT / "prompts/orchestrator.md").read_text(encoding="utf-8")
        self.assertIn("人工启动 Independent Reviewer", startup)
        self.assertIn("reviewer_provider:", startup)
        self.assertNotIn("gpt-5.6-sol", startup)
        self.assertIn("Reviewer 同样由队员", orchestrator)
        self.assertNotIn("anthropic", startup.casefold())

    def test_six_line_agent_report_and_question_logs_are_documented(self):
        contract = (ROOT / "agent.md").read_text(encoding="utf-8")
        for marker in (
            "## Agent 回报卡", "[Q2 / 步骤B / DONE]", "产物：", "风险：",
            "需要人工：", "下一步：",
        ):
            self.assertIn(marker, contract)
        self.assertNotIn("reports/stage-", contract)

    def test_every_startup_template_has_question_and_directory_slots(self):
        for path in (ROOT / "prompts/startup").glob("*.md"):
            text = path.read_text(encoding="utf-8")
            self.assertIn("当前子问题：Q<k>", text, path.name)
            self.assertIn("本题目录：<案例目录>/q<k>", text, path.name)


if __name__ == "__main__":
    unittest.main()
