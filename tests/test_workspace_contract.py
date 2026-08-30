import re
import unittest
from pathlib import Path

from scripts.validate_workspace import validate_static_contract


ROOT = Path(__file__).resolve().parents[1]


class WorkspaceContractTests(unittest.TestCase):
    def test_lightweight_workspace_contract_is_clean(self):
        self.assertEqual(validate_static_contract(), [])

    def test_readme_and_prompts_expose_core_loop(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for marker in (
            "五分钟", "候选路线池", "Champion", "Challenger", "C1 / C2 / C3",
            "建模手", "编程手", "写作手", "probe", "claim_map.md",
        ):
            self.assertIn(marker, readme)
        for node in ("C1_problem_challenge.md", "C2_model_challenge.md", "C3_results_challenge.md"):
            self.assertTrue((ROOT / "prompts/reviewer" / node).is_file())
        for card in (
            "optimization-method-cards.md",
            "data-analysis-method-cards.md",
            "hybrid-method-cards.md",
        ):
            self.assertTrue((ROOT / ".agents/skills/competition-modeling/references" / card).is_file())

    def test_three_roles_have_prompt_skill_and_contract(self):
        for role in ("modeler", "engineer", "writer"):
            self.assertTrue((ROOT / f"prompts/{role}.md").is_file(), role)
        for skill in ("competition-modeling", "competition-engineering", "competition-paper-writing"):
            self.assertTrue((ROOT / ".agents/skills" / skill / "SKILL.md").is_file(), skill)
        for contract in ("README.md", "spec.md", "results.md", "questions.md"):
            self.assertTrue((ROOT / "prompts/contracts" / contract).is_file(), contract)
        for retired in (
            "prompts/codex-start.md", "roles",
            ".agents/skills/industrial-mathematical-modeling", ".agents/skills/model-race",
        ):
            self.assertFalse((ROOT / retired).exists(), retired)

    def test_paper_engine_uses_the_vendored_official_class(self):
        """论文版式由 gmcmthesis 负责，不得回退成自建 ctexart 版式。"""

        main = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
        self.assertIn("{gmcmthesis}", main)
        self.assertNotIn("{ctexart}", main)
        # 承诺书页/摘要页由文档类生成，自建封面宏不得复活
        self.assertNotIn("\\PaperCover", main)
        for name in ("gmcmthesis.cls", "gmcm.bst",
                     "figures/logo.pdf", "figures/title.pdf"):
            self.assertTrue((ROOT / "paper" / name).is_file(), name)

    def test_paper_keeps_the_split_section_structure(self):
        """比赛期多人并行写作的前提；合并回单文件就会制造冲突。"""

        sections = sorted((ROOT / "paper/sections").glob("*.tex"))
        self.assertGreaterEqual(len(sections), 5)
        main = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
        for path in sections:
            self.assertIn(f"sections/{path.stem}", main, path.name)

    def test_paper_bibliography_uses_bibtex_not_biber(self):
        """gmcm.bst 是经典 BibTeX 样式；latexmkrc 与文档必须一致。"""

        main = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
        self.assertIn("\\bibliographystyle{gmcm}", main)
        self.assertNotIn("addbibresource", main)
        latexmkrc = (ROOT / "latexmkrc").read_text(encoding="utf-8")
        self.assertIn("bibtex", latexmkrc)
        self.assertNotIn("$biber", latexmkrc)

    def test_snippet_library_is_extractable_and_non_trivial(self):
        """片段库必须能被抽取器解析；解析不出来就等于没有验证。"""

        from scripts.check_snippets import build_document, extract

        library = ROOT / "writing/LATEX_SNIPPETS.md"
        self.assertTrue(library.is_file())
        snippets = extract(library)
        self.assertGreaterEqual(len(snippets), 6, "片段库过于单薄")
        for name, body in snippets:
            self.assertTrue(body.strip(), name)
        # 建模论文最常用的几类必须在库里
        names = {name for name, _ in snippets}
        for required in ("booktabs", "algorithm", "figures", "equations", "listings"):
            self.assertIn(required, names, required)
        document = build_document(snippets)
        self.assertIn("{gmcmthesis}", document)
        self.assertIn("\\end{document}", document)

    def test_snippet_library_warns_about_the_class_code_environments(self):
        """文档类的 Matlab/Python 环境写死了 Windows/macOS 字体，换机器会炸。"""

        library = (ROOT / "writing/LATEX_SNIPPETS.md").read_text(encoding="utf-8")
        self.assertIn("Courier New", library)
        self.assertIn("不要用文档类自带的", library)
        # 我们自己的样式必须覆盖 basicstyle，否则本队论文也会踩同一个坑
        style = (ROOT / "paper/style/modeling-paper.sty").read_text(encoding="utf-8")
        self.assertIn("basicstyle", style)
        self.assertIn("ttfamily", style)
        main = (ROOT / "paper/main.tex").read_text(encoding="utf-8")
        for env in ("\\begin{Matlab}", "\\begin{Python}"):
            self.assertNotIn(env, main)

    def test_upstream_example_is_compilable_in_place(self):
        """make paper-example 的前提：源、图和书目都在仓库里。"""

        upstream = ROOT / "paper/upstream"
        self.assertTrue((upstream / "example.tex").is_file())
        self.assertTrue((upstream / "reference.bib").is_file())
        text = (upstream / "example.tex").read_text(encoding="utf-8", errors="replace")
        referenced = set(re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", text))
        available = {path.stem for path in (upstream / "figures").glob("*")}
        available |= {path.stem for path in (ROOT / "paper/figures").glob("*")}
        missing = {name for name in referenced
                   if Path(name).stem not in available and name not in available}
        self.assertFalse(missing, f"上游示例引用了仓库里没有的图：{sorted(missing)}")
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        self.assertIn("paper-example:", makefile)

    def test_working_paper_figures_stay_free_of_demo_material(self):
        """论文工程的图目录只放它自己要用的，示例图归 upstream。"""

        working = {path.name for path in (ROOT / "paper/figures").glob("*")}
        self.assertEqual(working, {"logo.pdf", "title.pdf"},
                         "paper/figures/ 只应包含文档类硬编码依赖的两张图")
        self.assertFalse(list((ROOT / "paper/figures").glob("gongzhonghao*")))

    def test_upstream_checksums_match_the_vendored_files(self):
        """记录的校验和必须在当前仓库内容上成立，否则它比没有更糟。"""

        import hashlib
        import re

        readme = (ROOT / "paper/upstream/README.md").read_text(encoding="utf-8")
        block = re.search(r"## 校验和\n\n```text\n(.*?)```", readme, re.S)
        self.assertIsNotNone(block, "upstream/README.md 缺少校验和块")
        rows = [line.split(None, 1) for line in block.group(1).strip().splitlines() if line.strip()]
        self.assertGreaterEqual(len(rows), 4)
        for digest, name in rows:
            path = ROOT / "paper" / name.strip()
            self.assertTrue(path.is_file(), name)
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            self.assertEqual(actual, digest, f"{name} 与记录的校验和不一致")

    def test_upstream_template_provenance_is_recorded(self):
        readme = (ROOT / "paper/upstream/README.md").read_text(encoding="utf-8")
        for marker in ("gmcmthesis", "校验和", "不是官方来源", "2026"):
            self.assertIn(marker, readme, marker)
        # 上游的推广物料不得进入比赛工程
        self.assertFalse(list((ROOT / "paper/figures").glob("gongzhonghao*")))

    def test_writer_input_contract_is_not_self_contradictory(self):
        """The Writer must write model assumptions, so it needs read access to specs."""

        writer = (ROOT / "prompts/writer.md").read_text(encoding="utf-8")
        results = (ROOT / "prompts/contracts/results.md").read_text(encoding="utf-8")
        skill = (ROOT / ".agents/skills/competition-paper-writing/SKILL.md").read_text(encoding="utf-8")

        for text, label in ((writer, "writer.md"), (results, "results.md"), (skill, "SKILL.md")):
            # 旧表述把材料限制为结果三件套，却又要求写模型假设和公式
            self.assertNotIn("只从三个入口", text, label)
            self.assertNotIn("three entry points only", text, label)

        # 模型真值必须是写作手的合法只读来源
        for marker in ("模型真值", "结果真值", "写作规范"):
            self.assertIn(marker, writer, marker)
        self.assertIn("specs/SPEC-*.md", writer)
        self.assertIn("Model truth", skill)
        self.assertIn("read-only", skill)
        # 只读边界不得被削弱
        self.assertIn("不修改", results)
        self.assertIn("不改规格", (ROOT / "README.md").read_text(encoding="utf-8"))

    def test_independent_reviewer_is_a_cross_cutting_mechanism(self):
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("不是第四个生产角色", agents)
        self.assertNotIn("第四个角色 Independent Reviewer", agents)

    def test_brainstorming_term_is_spelled_correctly(self):
        for path in ROOT.rglob("*.md"):
            if ".venv" in path.parts or ".git" in path.parts:
                continue
            self.assertNotIn("头脑砖暴", path.read_text(encoding="utf-8"), str(path))

    def test_role_prompts_state_their_handoff_boundary(self):
        engineer = (ROOT / "prompts/engineer.md").read_text(encoding="utf-8")
        self.assertIn("不得修改模型", engineer)
        self.assertIn("questions.md", engineer)
        self.assertIn("MATLAB", engineer)
        writer = (ROOT / "prompts/writer.md").read_text(encoding="utf-8")
        self.assertIn("claim_map.md", writer)
        self.assertIn("不得就地", writer)
        modeler = (ROOT / "prompts/modeler.md").read_text(encoding="utf-8")
        self.assertIn("probe", modeler)
        self.assertIn("未决问题", modeler)

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
            ROOT / "protocol/decision-log.md", ROOT / "prompts/README.md", ROOT / "prompts/final-handoff.md",
            ROOT / "prompts/modeler.md", ROOT / "prompts/engineer.md", ROOT / "prompts/writer.md",
            ROOT / "templates/independent_review_packet.md", ROOT / "templates/final_checklist.md",
            ROOT / ".agents/skills/competition-modeling/SKILL.md",
            ROOT / ".agents/skills/competition-engineering/SKILL.md",
        ]
        active_files.extend(sorted((ROOT / "prompts/contracts").glob("*.md")))
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
