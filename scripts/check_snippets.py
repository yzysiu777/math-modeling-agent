"""Compile every snippet in the LaTeX snippet library against the real paper setup.

A snippet library that is only eyeballed rots quietly: the document class gets
replaced, a package moves, and the examples people copy under competition time
pressure stop working -- at the worst possible moment.  So every block marked
``<!-- snippet: name -->`` is extracted, assembled into one document that uses
the repository's own class and style, and actually compiled.

The check verifies that the snippets *typeset*, not that they say anything true.
Whether a formula is the right formula remains a human and C2 question.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List, Tuple

SNIPPET = re.compile(
    r"<!--\s*snippet:\s*(?P<name>[A-Za-z0-9_-]+)\s*-->\s*\n```latex\n(?P<body>.*?)\n```",
    re.DOTALL,
)
#: 片段里引用的示意图。真实论文用 experiments/outputs/figures/ 下的产物，
#: 这里只需要让 \includegraphics 找得到东西，用 mwe 的占位图。
_PLACEHOLDER_FIGURES = ("example-image", "example-image-a", "example-image-b")


def extract(path: Path) -> List[Tuple[str, str]]:
    """Return (name, body) for every marked snippet, in document order."""

    text = path.read_text(encoding="utf-8")
    found = [(m.group("name"), m.group("body")) for m in SNIPPET.finditer(text)]
    names = [name for name, _ in found]
    duplicates = {name for name in names if names.count(name) > 1}
    if duplicates:
        raise ValueError(f"duplicate snippet names: {sorted(duplicates)}")
    return found


def _placeholder_figure(target: Path) -> None:
    """Write a minimal valid PDF so \\includegraphics has something to load."""

    target.write_bytes(
        b"%PDF-1.4\n"
        b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 120 90]>>endobj\n"
        b"trailer<</Root 1 0 R>>\n"
    )


def build_document(snippets: List[Tuple[str, str]]) -> str:
    """Assemble the snippets into one compilable document."""

    parts = [
        "% !TEX program = xelatex",
        "\\documentclass[bwprint]{gmcmthesis}",
        "\\input{config/paper-profile.tex}",
        "\\input{style/modeling-paper.sty}",
        "\\begin{document}",
        "\\maketitle",
        "\\begin{abstract}",
        "片段编译验证文档，不是论文。",
        "\\keywords{\\PaperKeywords}",
        "\\end{abstract}",
    ]
    for name, body in snippets:
        parts.append(f"\\section{{片段：{name}}}")
        parts.append(body)
    parts.append("\\bibliographystyle{gmcm}")
    parts.append("\\bibliography{bibliography/references}")
    parts.append("\\end{document}")
    return "\n\n".join(parts) + "\n"


def compile_document(paper_dir: Path, document: str, fontset: str | None) -> List[str]:
    """Compile the assembled document inside a copy of the paper engineering."""

    if shutil.which("latexmk") is None:
        return ["latexmk not found; cannot verify snippets"]

    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory) / "paper"
        shutil.copytree(paper_dir, work, ignore=shutil.ignore_patterns("build", "upstream"))
        for name in _PLACEHOLDER_FIGURES:
            _placeholder_figure(work / "figures" / f"{name}.pdf")
        (work / "snippets.tex").write_text(document, encoding="utf-8")

        command = ["latexmk", "-r", str((paper_dir / ".." / "latexmkrc").resolve()), "-xelatex"]
        if fontset:
            command.append(f"-usepretex=\\PassOptionsToClass{{fontset={fontset}}}{{ctexart}}")
        command += ["-interaction=nonstopmode", "-halt-on-error", "-outdir=build", "snippets.tex"]

        result = subprocess.run(command, cwd=work, capture_output=True, text=True, check=False)
        if result.returncode == 0 and (work / "build/snippets.pdf").exists():
            return []

        log = work / "build/snippets.log"
        detail = []
        if log.exists():
            text = log.read_text(encoding="utf-8", errors="replace")
            detail = [line for line in text.splitlines() if line.startswith("!")][:5]
        return ["snippet document failed to compile"] + [f"  {line}" for line in detail]


def main() -> int:
    parser = argparse.ArgumentParser(description="verify that every documented LaTeX snippet compiles")
    parser.add_argument("--library", type=Path, default=Path("writing/LATEX_SNIPPETS.md"))
    parser.add_argument("--paper-dir", type=Path, default=Path("paper"))
    parser.add_argument("--fontset", default=None, help="ctex fontset, e.g. fandol on Linux/CI")
    args = parser.parse_args()

    if not args.library.is_file():
        print(f"FAIL snippet check\n- missing library: {args.library}")
        return 1

    try:
        snippets = extract(args.library)
    except ValueError as exc:
        print(f"FAIL snippet check\n- {exc}")
        return 1

    if not snippets:
        print(f"FAIL snippet check\n- no snippets marked with <!-- snippet: name --> in {args.library}")
        return 1

    errors = compile_document(args.paper_dir, build_document(snippets), args.fontset)
    if errors:
        print("FAIL snippet check")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    print(f"PASS snippet check: {len(snippets)} snippets compiled "
          f"({', '.join(name for name, _ in snippets)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
