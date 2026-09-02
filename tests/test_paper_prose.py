from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.claim_evidence import validate_check_report
from scripts.qa_latex import (
    check_citation_verification,
    check_citations,
    check_evidence_citations,
    check_figures,
    check_paper_prose,
    check_prose_style,
    check_sealed_questions,
)


def paper_with(body: str, *, registry: str | None = None) -> Path:
    root = Path(tempfile.mkdtemp())
    paper = root / "paper"
    (paper / "sections").mkdir(parents=True)
    (paper / "sections/q1.tex").write_text(body, encoding="utf-8")
    if registry is not None:
        (root / "队员工作区").mkdir(parents=True, exist_ok=True)
        (root / "队员工作区/待补图清单.md").write_text(registry, encoding="utf-8")
    return paper


class ProseBanTests(unittest.TestCase):
    """第三次实测的 q1.tex 里实验编号出现 23 次、六位小数 21 处，末尾整段是脚本路径。

    溯源机制漏进了交付物 —— 台账归台账，论文归论文。
    """

    def test_experiment_id_in_prose_is_reported(self):
        hits = check_paper_prose(paper_with("EXP-C01 仅由残差分支通过。"))
        self.assertEqual(len(hits), 1)
        self.assertIn("实验编号", hits[0])

    def test_script_name_in_prose_is_reported(self):
        hits = check_paper_prose(paper_with("正式计算入口为 run\\_demo.py。"))
        self.assertIn("文件名", hits[0])

    def test_workbench_directory_in_prose_is_reported(self):
        hits = check_paper_prose(paper_with("结果落在 q1/outputs/data 下。"))
        self.assertIn("工作台目录", hits[0])

    def test_command_line_flag_in_prose_is_reported(self):
        hits = check_paper_prose(paper_with("以 --case-dir 指定案例目录。"))
        self.assertIn("命令行参数", hits[0])

    def test_six_decimals_are_reported_but_four_significant_digits_pass(self):
        self.assertIn("有效数字", check_paper_prose(paper_with("秩相关为 0.981993。"))[0])
        self.assertEqual(check_paper_prose(paper_with("秩相关为 0.982。")), [])

    def test_clean_prose_passes(self):
        body = (
            "\\subsection{结果与分析}\n"
            "模型在五个独立时刻上的秩相关为 0.982，未超过纯剪切基线的 0.983，"
            "因此只能说残差分支达到预注册判据，不能说总体更优。\n"
        )
        self.assertEqual(check_paper_prose(paper_with(body)), [])

    def test_template_guidance_is_not_prose(self):
        body = "\\paperexample{不要在正文写 EXP-C01 或 run.py 这类东西。}\n模型结果稳定。\n"
        self.assertEqual(check_paper_prose(paper_with(body)), [])

    def test_figure_paths_and_labels_are_not_prose(self):
        body = "\\includegraphics{figures/EXP-C01_a.png}\n\\label{fig:EXP-C01}\n结果如图所示。\n"
        self.assertEqual(check_paper_prose(paper_with(body)), [])


class PlaceholderFigureTests(unittest.TestCase):
    FIGURE = (
        "\\begin{figure}[H]\n\\centering\n"
        "\\PlaceholderFigure{总体技术路线}\n"
        "\\caption{总体技术路线}\n\\label{fig:overall-roadmap}\n"
        "\\end{figure}\n"
    )

    def test_unregistered_placeholder_is_reported(self):
        problems = check_figures(paper_with(self.FIGURE, registry="# 待补图清单\n"))
        self.assertTrue(any("未登记" in item for item in problems))

    def test_registered_placeholder_passes(self):
        registry = "# 待补图清单\n\n| `fig:overall-roadmap` | 技术路线 | 需人工绘制 | 待认领 |\n"
        self.assertEqual(check_figures(paper_with(self.FIGURE, registry=registry)), [])

    def test_placeholder_is_rejected_in_the_submission(self):
        registry = "| `fig:overall-roadmap` | 技术路线 | 需人工绘制 | 待认领 |\n"
        problems = check_figures(paper_with(self.FIGURE, registry=registry), final=True)
        self.assertTrue(any("提交稿仍有占位图" in item for item in problems))

    def test_missing_registry_file_is_reported(self):
        problems = check_figures(paper_with(self.FIGURE))
        self.assertTrue(any("待补图清单" in item for item in problems))


class FigureAssetTests(unittest.TestCase):
    def test_missing_figure_is_reported(self):
        problems = check_figures(paper_with("\\includegraphics{figures/missing.png}\n"))
        self.assertTrue(any("不存在的图" in item for item in problems))

    def test_final_requires_a_vector_sibling(self):
        paper = paper_with("\\includegraphics{figures/plot.png}\n")
        (paper / "figures").mkdir()
        (paper / "figures/plot.png").write_bytes(b"png")
        self.assertEqual(check_figures(paper), [])
        problems = check_figures(paper, final=True)
        self.assertTrue(any("缺少 plot.pdf" in item for item in problems))
        (paper / "figures/plot.pdf").write_bytes(b"pdf")
        self.assertEqual(check_figures(paper, final=True), [])


class CheckReportCoverageTests(unittest.TestCase):
    """一份复算脚本常常一次核完主实验和它的稳健性子实验。

    第三次实测里为了让每个 Claim 各有一份同 ID 报告，走了八次交接。
    """

    def _report(self, payload: dict) -> Path:
        path = Path(tempfile.mkdtemp()) / "report.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    BASE = {"exp_id": "EXP-C01", "checks": [{"name": "x", "passed": True}]}

    def test_covers_list_lets_one_report_serve_several_claims(self):
        report = self._report(dict(self.BASE, covers=["EXP-P02", "EXP-P03"]))
        self.assertTrue(validate_check_report(report, "EXP-P02").ok)
        self.assertTrue(validate_check_report(report, "EXP-C01").ok)

    def test_claim_outside_covers_is_still_rejected(self):
        report = self._report(dict(self.BASE, covers=["EXP-P02"]))
        self.assertIn("不含", validate_check_report(report, "EXP-P09").problem)

    def test_malformed_covers_entry_is_rejected(self):
        report = self._report(dict(self.BASE, covers=["not-an-id"]))
        self.assertIn("不是规范的 EXP-ID", validate_check_report(report, "EXP-C01").problem)


class SeededCaseTests(unittest.TestCase):
    """新建案例必须自洽：骨架自带的占位图都已登记，正文没有禁词。"""

    def test_fresh_case_paper_is_self_consistent(self):
        from scripts.create_case import create_case

        with tempfile.TemporaryDirectory() as tmp:
            case = create_case("fresh-case", cases_root=Path(tmp), questions=3)
            self.assertEqual(check_figures(case / "paper"), [])
            self.assertEqual(check_paper_prose(case / "paper"), [])
            main = (case / "paper/main.tex").read_text(encoding="utf-8")
            self.assertIn("{gmcmthesis}", main)
            self.assertNotIn("ctexart", main)
            registry = (case / "队员工作区/待补图清单.md").read_text(encoding="utf-8")
            for label in ("fig:overall-roadmap", "fig:q1-flow", "fig:q3-flow"):
                self.assertIn(label, registry)


if __name__ == "__main__":
    unittest.main()


class CitationTests(unittest.TestCase):
    """v2 论文 \\cite 为 0，references.bib 还是占位条目，而研究背景写满了外部事实。"""

    def _paper(self, body: str, *, bib: str = "", registry: str = "") -> Path:
        root = Path(tempfile.mkdtemp())
        paper = root / "paper"
        (paper / "sections").mkdir(parents=True)
        (paper / "bibliography").mkdir(parents=True)
        (paper / "sections/01-background.tex").write_text(body, encoding="utf-8")
        (paper / "bibliography/references.bib").write_text(bib, encoding="utf-8")
        if registry:
            (paper / "文献清单.md").write_text(registry, encoding="utf-8")
        return paper

    ROW = (
        "| key | 标题 | 作者 | 年份 | 出处 | DOI/URL | 获取方式 | 支撑论断 | 核对状态 |\n"
        "|---|---|---|---|---|---|---|---|---|\n"
    )
    BIB = "@article{kolmogorov1941, title={Local structure}, year={1941}}\n"

    def test_citation_outside_the_registry_is_flagged_as_fabricated(self):
        paper = self._paper("湍流服从 $-5/3$ 律\\cite{kolmogorov1941}。", bib=self.BIB)
        problems = check_citations(paper)
        self.assertTrue(any("疑似编造" in item for item in problems))

    def test_citation_without_a_bib_entry_is_flagged(self):
        registry = self.ROW + "| kolmogorov1941 | Local structure | K | 1941 | - | - | 人工放入 | 背景 | 已核对 |\n"
        paper = self._paper("湍流服从 $-5/3$ 律\\cite{kolmogorov1941}。", registry=registry)
        self.assertTrue(any("没有条目" in item for item in check_citations(paper)))

    def test_registered_and_bibbed_citation_passes(self):
        registry = self.ROW + "| kolmogorov1941 | Local structure | K | 1941 | - | - | 人工放入 | 背景 | 已核对 |\n"
        paper = self._paper("湍流服从 $-5/3$ 律\\cite{kolmogorov1941}。", bib=self.BIB, registry=registry)
        self.assertEqual(check_citations(paper), [])

    def test_pending_verification_is_reported_but_never_blocks(self):
        """核对是队员的判断，脚本不替他判，也不因此拦住流程 —— 不阻断项目优先。"""
        registry = self.ROW + "| kolmogorov1941 | Local structure | K | 1941 | - | - | 人工放入 | 背景 | 待核对 |\n"
        paper = self._paper("湍流服从 $-5/3$ 律\\cite{kolmogorov1941}。", bib=self.BIB, registry=registry)
        self.assertEqual(check_citations(paper), [])
        self.assertEqual(check_citations(paper, final=True), [])
        self.assertTrue(any("待你核对" in item for item in check_citation_verification(paper)))

    def test_unfilled_support_is_reported_but_never_blocks(self):
        registry = self.ROW + "| kolmogorov1941 | Local structure | K | 1941 | - | - | 联网检索 | 待填写 | 待核对 |\n"
        paper = self._paper("湍流服从 $-5/3$ 律\\cite{kolmogorov1941}。", bib=self.BIB, registry=registry)
        self.assertEqual(check_citations(paper, final=True), [])
        self.assertTrue(any("支撑正文哪一处论断" in item for item in check_citation_verification(paper)))

    def test_a_citation_with_no_registry_row_still_blocks(self):
        """机械错误照旧拦：连记录都没有的引用，无从核对。"""
        paper = self._paper("湍流服从 $-5/3$ 律\\cite{ghost2020}。", bib=self.BIB)
        self.assertTrue(any("疑似编造" in item for item in check_citations(paper, final=True)))

    def test_placeholder_bib_entry_blocks_the_submission(self):
        registry = self.ROW + "| kolmogorov1941 | Local structure | K | 1941 | - | - | 人工放入 | 背景 | 已核对 |\n"
        paper = self._paper(
            "湍流服从 $-5/3$ 律\\cite{kolmogorov1941}。",
            bib=self.BIB + "@misc{placeholder2026, title={待替换}}\n", registry=registry)
        self.assertTrue(any("占位条目" in item for item in check_citations(paper, final=True)))

    def test_background_without_any_citation_is_reminded(self):
        paper = self._paper("主流数值预报模式的分辨率通常在公里量级。")
        self.assertTrue(any("没有任何引用" in item for item in check_evidence_citations(paper)))


class SealedQuestionTests(unittest.TestCase):
    """v2 把还没做 A 步的问题二、问题三的技术路线整段写死了。"""

    def _case(self, body: str, *, opened: tuple[int, ...] = ()) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "paper/sections").mkdir(parents=True)
        (root / "paper/sections/02-restate.tex").write_text(body, encoding="utf-8")
        for number in opened:
            reviews = root / f"q{number}/reviews"
            reviews.mkdir(parents=True)
            (reviews / "C1_done.md").write_text("Node decision: GO\n", encoding="utf-8")
        return root / "paper"

    SEALED = (
        "\\subsection{问题二}\n"
        "% <<Q2-SEALED>> 问题二通过 C1 之前保持原样。\n"
    )

    def test_writing_into_a_sealed_question_is_flagged(self):
        paper = self._case(self.SEALED + "构建 100 m 网格的三维湍流场。\n")
        self.assertTrue(any("不得写入实质内容" in item for item in check_sealed_questions(paper)))

    def test_sealed_and_empty_passes(self):
        self.assertEqual(check_sealed_questions(self._case(self.SEALED)), [])

    def test_opened_question_may_be_written(self):
        paper = self._case(self.SEALED + "构建 100 m 网格的三维湍流场。\n", opened=(2,))
        self.assertEqual(check_sealed_questions(paper), [])

    def test_deleting_the_sentinel_does_not_bypass_the_gate(self):
        paper = self._case("\\subsection{问题二}\n构建 100 m 网格的三维湍流场。\n")
        self.assertTrue(any("封存标记被删除" in item for item in check_sealed_questions(paper)))


class ProseStyleTests(unittest.TestCase):
    """获奖论文 110 页 8 个项目符号行；v2 论文 23 页 32 个 —— 密度差 21 倍。"""

    def _paper(self, name: str, body: str) -> Path:
        root = Path(tempfile.mkdtemp())
        (root / "paper/sections").mkdir(parents=True)
        (root / "paper/sections" / name).write_text(body, encoding="utf-8")
        return root / "paper"

    LIST = "\\begin{itemize}\n  \\item 甲\n  \\item 乙\n\\end{itemize}\n"

    def test_list_in_a_narrative_chapter_is_flagged(self):
        problems = check_prose_style(self._paper("01-background.tex", self.LIST))
        self.assertTrue(any("叙述式行文" in item for item in problems))

    def test_list_in_assumptions_is_allowed(self):
        self.assertEqual(check_prose_style(self._paper("05-assumptions.tex", self.LIST * 3)), [])

    def test_question_chapter_gets_one_list_of_budget(self):
        self.assertEqual(check_prose_style(self._paper("q1.tex", self.LIST)), [])
        self.assertTrue(check_prose_style(self._paper("q1.tex", self.LIST * 2)))

    def test_stock_phrases_are_flagged(self):
        problems = check_prose_style(self._paper("q1.tex", "结果如图所示。\n"))
        self.assertTrue(any("套话" in item for item in problems))

    def test_a_sentence_that_says_what_the_figure_shows_passes(self):
        body = "图~\\ref{fig:a} 给出五个时刻的耗散率廓线，低层量级差异主要来自切变。\n"
        self.assertEqual(check_prose_style(self._paper("q1.tex", body)), [])


class C3CardTests(unittest.TestCase):
    """C3 卡曾经落在 paper/reviews/ 而检查器去 q<k>/reviews/ 找 —— 审了也等于没审。"""

    def _case(self) -> Path:
        from scripts.create_case import create_case

        root = Path(tempfile.mkdtemp())
        case = create_case("c3-case", cases_root=root, questions=2)
        (case / "sources.yaml").write_text(
            "statement: input/README.md\ndata_roots:\n  - input\ndocs: []\n"
            "questions:\n  q1: a\n  q2: b\nshared: []\n", encoding="utf-8")
        for name in ("a", "b"):
            (case / "input" / name).mkdir(parents=True, exist_ok=True)
        (case / "paper/sections/q1.tex").write_text("本题结论。\n", encoding="utf-8")
        return case

    def test_per_question_c3_materials_include_the_paper_and_registry(self):
        from scripts.make_review_packet import build_packet

        card = build_packet(self._case(), "C3", question="q1")
        self.assertIn("paper/sections/q1.tex", card)
        self.assertIn("paper/文献清单.md", card)
        self.assertIn("paper/claim_map.md", card)

    def test_per_question_c3_does_not_drag_in_other_questions(self):
        from scripts.make_review_packet import build_packet

        card = build_packet(self._case(), "C3", question="q1")
        self.assertIn("Q1 实验板", card)
        self.assertNotIn("Q2 实验板", card)

    def test_case_level_c3_spans_every_question(self):
        from scripts.make_review_packet import build_packet

        card = build_packet(self._case(), "C3")
        self.assertIn("Q1 实验板", card)
        self.assertIn("Q2 实验板", card)
