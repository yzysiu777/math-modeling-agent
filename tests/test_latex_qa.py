import tempfile
import unittest
from pathlib import Path

from scripts.qa_latex import check_sources


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


if __name__ == "__main__":
    unittest.main()
