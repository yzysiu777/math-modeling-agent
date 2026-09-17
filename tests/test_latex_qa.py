import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.qa_latex import check_build, check_sources

ROOT = Path(__file__).resolve().parents[1]


def make_minimal_paper(root: Path) -> Path:
    paper = root / "paper"
    for relative in ("config", "style", "bibliography", "figures", "sections", "official/2025"):
        (paper / relative).mkdir(parents=True, exist_ok=True)
    (paper / "main.tex").write_text(
        r"""\documentclass{gmcmthesis}
\begin{document}
\maketitle
\pagestyle{plain}
\keywords{测试}
\input{sections/body}
\bibliographystyle{gmcm}
\bibliography{bibliography/references}
\end{document}
""",
        encoding="utf-8",
    )
    (paper / "config/paper-profile.tex").write_text(
        r"""% 待填写只在注释里，不应阻断 final
\newcommand{\PaperOfficialYear}{2025}
\newcommand{\PaperOfficialFrozen}{true}
\baominghao{12345678}
\schoolname{测试大学}
\membera{甲}
\memberb{乙}
\memberc{丙}
""",
        encoding="utf-8",
    )
    (paper / "style/modeling-paper.sty").write_text("% style\n", encoding="utf-8")
    (paper / "bibliography/references.bib").write_text("% refs\n", encoding="utf-8")
    (paper / "gmcmthesis.cls").write_text("% class\n", encoding="utf-8")
    (paper / "gmcm.bst").write_text("% bst\n", encoding="utf-8")
    (paper / "figures/logo.pdf").write_bytes(b"pdf")
    (paper / "figures/title.pdf").write_bytes(b"pdf")
    (paper / "sections/body.tex").write_text("正文。\n", encoding="utf-8")
    (paper / "official/2025/manifest.yaml").write_text(
        "year: 2025\nactive: true\nstatus: frozen\n", encoding="utf-8"
    )
    return paper


class LatexQaTests(unittest.TestCase):
    def test_final_source_contract_accepts_filled_profile_and_ignores_comments(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(check_sources(make_minimal_paper(Path(tmp)), final=True), [])

    def test_final_source_contract_rejects_visible_placeholder_and_example(self):
        with tempfile.TemporaryDirectory() as tmp:
            paper = make_minimal_paper(Path(tmp))
            (paper / "sections/body.tex").write_text(
                "待填写。\\paperexample{示例}\n", encoding="utf-8"
            )
            errors = check_sources(paper, final=True)
            self.assertTrue(any("placeholder" in error for error in errors))
            self.assertTrue(any("paperexample" in error for error in errors))

    def test_final_source_contract_requires_frozen_official_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            paper = make_minimal_paper(Path(tmp))
            profile = paper / "config/paper-profile.tex"
            profile.write_text(
                profile.read_text(encoding="utf-8").replace(
                    r"\newcommand{\PaperOfficialFrozen}{true}",
                    r"\newcommand{\PaperOfficialFrozen}{false}",
                ),
                encoding="utf-8",
            )
            self.assertTrue(any("PaperOfficialFrozen" in error for error in check_sources(paper, final=True)))

    def test_keywords_may_live_in_an_input_section(self):
        # 案例模板把 \keywords 放在 sections/00-abstract.tex，不在 main.tex。
        with tempfile.TemporaryDirectory() as tmp:
            paper = make_minimal_paper(Path(tmp))
            main = paper / "main.tex"
            main.write_text(
                main.read_text(encoding="utf-8").replace(
                    "\\keywords{测试}", "\\input{sections/00-abstract}"
                ),
                encoding="utf-8",
            )
            (paper / "sections/00-abstract.tex").write_text(
                "\\begin{abstract}摘要。\\keywords{测试}\\end{abstract}\n", encoding="utf-8"
            )
            self.assertEqual(check_sources(paper), [])

    def test_keywords_missing_everywhere_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            paper = make_minimal_paper(Path(tmp))
            main = paper / "main.tex"
            main.write_text(
                main.read_text(encoding="utf-8").replace(
                    "\\keywords{测试}", "% \\input{sections/00-abstract}"
                ),
                encoding="utf-8",
            )
            # 被注释掉的 \input 不算纳入正文。
            (paper / "sections/00-abstract.tex").write_text(
                "\\keywords{测试}\n", encoding="utf-8"
            )
            errors = check_sources(paper)
            self.assertTrue(any("\\keywords" in error for error in errors), errors)


def _build_errors(pdf_text: str) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        build = Path(tmp)
        (build / "main.pdf").write_bytes(b"%PDF" + b"0" * 2000)
        done = subprocess.CompletedProcess([], 0, stdout=pdf_text, stderr="")
        with mock.patch("scripts.qa_latex.shutil.which", return_value="/usr/bin/pdftotext"), \
                mock.patch("scripts.qa_latex.subprocess.run", return_value=done):
            return check_build(build, build)


class PdfMarkerTests(unittest.TestCase):
    def test_gmcmthesis_spaced_abstract_heading_is_accepted(self):
        # gmcmthesis 印「摘\quad 要：」，pdftotext 得到「摘 要：」。
        text = "      摘 要：\n正文\n关键词： 甲 乙\n参考文献\n[1] 某文献\n"
        self.assertEqual(_build_errors(text), [])

    def test_missing_abstract_heading_is_reported(self):
        errors = _build_errors("正文\n关键词： 甲\n参考文献\n")
        self.assertEqual(errors, ["PDF text missing marker: 摘要"])


class CasePaperBuildTests(unittest.TestCase):
    def test_case_texinputs_do_not_expose_repository_build_dir(self):
        # 递归的 paper// 会让 xelatex 读到仓库 paper/build/main.bbl，latexmk 随即
        # 跳过 bibtex，案例参考文献为空。编译级回归在 make case-paper-check。
        makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
        match = re.search(r"^CASE_TEXINPUTS := (.*)$", makefile, re.MULTILINE)
        self.assertIsNotNone(match)
        self.assertNotIn("//", match.group(1))
        self.assertIn('TEXINPUTS="$(CASE_TEXINPUTS)"', makefile)
        self.assertIn("case-paper-check", makefile.split("paper-ci: paper", 1)[1].split("\n\n", 1)[0])


if __name__ == "__main__":
    unittest.main()
