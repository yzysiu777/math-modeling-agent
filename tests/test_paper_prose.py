from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.claim_evidence import validate_check_report
from scripts.qa_latex import check_figures, check_paper_prose


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
