"""2025D 首次实测暴露的四个缺陷的回归测试。

每一条都对应一次真实发生的事，不是假想的边界情况 —— 归档在
`2025d实战测试/_归档_第一次尝试/` 里有当时的产物。
"""

import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.check_case import check_case
from scripts.create_case import create_case
from scripts.make_review_packet import build_packet


ROOT = Path(__file__).resolve().parents[1]


class CheckerAvailabilityTests(unittest.TestCase):
    """P1：工具跑不起来不等于检查通过。"""

    def test_unreadable_checkpoint_blocks_at_every_stage(self):
        with tempfile.TemporaryDirectory() as directory:
            case = create_case("degraded", "hybrid", Path(directory))
            # 模拟 PyYAML 缺失：解析失败与依赖缺失走同一条降级路径
            (case / "checkpoint.yaml").write_text("{ this is not: valid: yaml: [", encoding="utf-8")
            for stage in ("exploration", "model_selection", "paper_claims", "final"):
                with self.subTest(stage=stage):
                    report = check_case(case, stage)
                    self.assertTrue(report.blocked, stage)
                    self.assertEqual(report.exit_code, 1, stage)

    def test_degraded_run_says_the_other_checks_did_not_run(self):
        """最危险的不是报错，是让人以为查过了。"""

        with tempfile.TemporaryDirectory() as directory:
            case = create_case("degraded", "hybrid", Path(directory))
            (case / "checkpoint.yaml").write_text("[not a mapping]", encoding="utf-8")
            report = check_case(case, "exploration")
        reasons = " ".join(finding.reason for finding in report.findings)
        self.assertIn("未运行", reasons)
        self.assertIn("PYTHON=.venv/bin/python", reasons)

    def test_makefile_defaults_to_the_workbench_virtualenv(self):
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn(".venv/bin/python", makefile)
        self.assertNotIn("PYTHON ?= python3", makefile)


class StatementFidelityTests(unittest.TestCase):
    """P2：C1 的题面依据必须是原题，不能是主解的转述。"""

    def build(self, directory, statement_text, extra=()):
        case = create_case("fidelity", "hybrid", Path(directory))
        (case / "input/题面.md").write_text(statement_text, encoding="utf-8")
        for name in extra:
            (case / "input" / name).write_bytes(b"%PDF-1.4\n")
        return build_packet(case, "C1")

    def test_self_declared_digest_is_refused_as_statement_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = self.build(
                directory,
                "# 题面：本次范围摘录\n\n只摘录问题一相关内容。第二题不在范围内。\n")
        self.assertIn("packet_complete: false", packet)
        self.assertIn("转述而非原题全文", packet)

    def test_several_digest_words_are_recognised(self):
        for word in ("摘要", "节选", "概要", "summary"):
            with self.subTest(word=word):
                with tempfile.TemporaryDirectory() as directory:
                    packet = self.build(directory, f"# 题面{word}\n\n正文若干。\n")
                self.assertIn("packet_complete: false", packet)

    def test_full_statement_transcription_is_accepted(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = self.build(
                directory,
                "# 2025 年 D 题：低空湍流监测及最优航路规划\n\n"
                "根据题目提供的风廓线雷达和微波辐射计资料进行以下研究……\n")
        self.assertIn("packet_complete: true", packet)
        self.assertIn("低空湍流监测", packet)

    def test_presence_of_a_source_document_prompts_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            packet = self.build(
                directory,
                "# D 题全文\n\n正文若干。\n",
                extra=("D题原件.pdf",))
        self.assertIn("确认转写覆盖了原题全文", packet)


class ReviewerBoundaryTests(unittest.TestCase):
    """P4：过度自禁不是尽责——通用知识不构成污染。"""

    def test_reviewer_protocol_separates_the_three_source_classes(self):
        text = (ROOT / "REVIEWER.md").read_text(encoding="utf-8")
        for marker in ("禁止", "允许", "必读", "不必因此自判无效"):
            self.assertIn(marker, text, marker)
        self.assertIn("通用建模知识", text)

    def test_c1_prompt_fixes_the_reading_order(self):
        text = (ROOT / "prompts/reviewer/C1_problem_challenge.md").read_text(encoding="utf-8")
        self.assertIn("先只读原题", text)
        self.assertIn("再读", text)
        self.assertIn("摘录", text)


class OrchestratorBoundaryTests(unittest.TestCase):
    """P3：调度位置是唯一同时看到三方输出的地方，规则必须有方向。"""

    def test_orchestrator_prompt_exists_and_states_the_directional_rule(self):
        path = ROOT / "prompts/orchestrator.md"
        self.assertTrue(path.is_file())
        text = path.read_text(encoding="utf-8")
        self.assertIn("对人", text)
        self.assertIn("对下游", text)
        self.assertIn("只传路径", text)
        # 实测中真实发生的两次越界必须被点名
        self.assertIn("判据", text)
        self.assertIn("不是第四个生产角色", text)

    def test_orchestrator_is_not_a_production_role(self):
        text = (ROOT / "prompts/orchestrator.md").read_text(encoding="utf-8")
        for forbidden in ("不写生产代码", "不写规格", "不做路线取舍", "不写论文正文"):
            self.assertIn(forbidden, text, forbidden)

    def test_rules_and_contracts_reference_the_orchestrator(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("prompts/orchestrator.md", agents)
        self.assertIn("有方向的", agents)
        contracts = (ROOT / "prompts/contracts/README.md").read_text(encoding="utf-8")
        self.assertIn("只传路径", contracts)
        readme = (ROOT / "prompts/README.md").read_text(encoding="utf-8")
        self.assertIn("orchestrator.md", readme)


if __name__ == "__main__":
    unittest.main()


class StartupTemplateTests(unittest.TestCase):
    """启动模板必须存在、可填、且不复述协议内容。"""

    ROLES = ("orchestrator", "modeler", "engineer", "writer", "reviewer")

    def template(self, name):
        return (ROOT / "prompts/startup" / f"{name}.md").read_text(encoding="utf-8")

    def test_every_role_has_a_startup_template(self):
        for name in self.ROLES:
            path = ROOT / "prompts/startup" / f"{name}.md"
            self.assertTrue(path.is_file(), name)
        self.assertTrue((ROOT / "prompts/startup/README.md").is_file())

    def test_templates_carry_a_copyable_block_with_slots(self):
        for name in self.ROLES:
            with self.subTest(role=name):
                text = self.template(name)
                self.assertIn("## 提示词正文", text)
                self.assertIn("```text", text)
                self.assertTrue(re.search(r"<[^<>\n]{2,20}>", text), "模板必须有填空槽")
                self.assertIn("<项目根>", text)

    def test_production_templates_point_at_the_role_protocol(self):
        """模板只把 agent 指向协议，不复述协议——否则会有两份规则。"""

        for name in ("orchestrator", "modeler", "engineer", "writer"):
            with self.subTest(role=name):
                self.assertIn(f"prompts/{name}.md", self.template(name))

    def test_templates_require_a_scope_and_a_stopping_point(self):
        """不写边界的后果实测中出现过：一路冲到 probe。"""

        for name in ("orchestrator", "modeler", "engineer", "writer"):
            with self.subTest(role=name):
                text = self.template(name)
                self.assertIn("到此停止", text)
        self.assertIn("<硬范围>", self.template("modeler"))
        self.assertIn("<本轮阶段>", self.template("modeler"))

    def test_reviewer_template_encodes_both_dry_run_lessons(self):
        text = self.template("reviewer")
        # P4：按名单允许，不写绝对禁令
        self.assertIn("不构成污染", text)
        self.assertIn("不要因此判自己的报告无效", text)
        self.assertIn("绝对禁令", text)
        # P2：拿转述当题面
        self.assertIn("摘录", text)
        self.assertIn("原题全文", text)
        # C1 顺序约束
        self.assertIn("先只读题面原文", text)

    def test_startup_templates_are_indexed(self):
        # prompts/README.md 自己就在 prompts/ 下，用相对链接才是对的
        self.assertIn("startup/", (ROOT / "prompts/README.md").read_text(encoding="utf-8"))
        self.assertIn("prompts/startup/", (ROOT / "AGENTS.md").read_text(encoding="utf-8"))

    def test_startup_templates_are_not_mistaken_for_reviewer_protocols(self):
        """模板只是指路文本，审核元信息由 prompts/reviewer/ 下的协议定义。"""

        from scripts.validate_workspace import REVIEWER_ACTIVE_FILES

        self.assertFalse([path for path in REVIEWER_ACTIVE_FILES if "startup" in path])
