"""Static and build-output QA for the reusable LaTeX template."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path


FORBIDDEN_PLACEHOLDERS = re.compile(r"\b(?:TODO|FIXME)\b|待补充|未验证")


def check_sources(paper_dir: Path) -> list[str]:
    errors: list[str] = []
    required = [
        paper_dir / "main.tex",
        paper_dir / "config/paper-profile.tex",
        paper_dir / "style/modeling-paper.sty",
        paper_dir / "bibliography/references.bib",
        # gmcmthesis 文档类与其书目样式随仓库分发；缺任何一个都编不出官方版式。
        paper_dir / "gmcmthesis.cls",
        paper_dir / "gmcm.bst",
        # 文档类硬编码 \includegraphics{logo} 与 {title}，缺图会直接编译失败。
        paper_dir / "figures/logo.pdf",
        paper_dir / "figures/title.pdf",
    ]
    for path in required:
        if not path.exists():
            errors.append(f"missing required LaTeX file: {path}")
    for path in sorted((paper_dir / "sections").glob("*.tex")):
        text = path.read_text(encoding="utf-8")
        if FORBIDDEN_PLACEHOLDERS.search(text):
            errors.append(f"placeholder found in paper source: {path}")
    main_text = (paper_dir / "main.tex").read_text(encoding="utf-8")
    for marker in ("{gmcmthesis}", "\\maketitle", "\\keywords",
                   "\\bibliographystyle{gmcm}", "\\bibliography{"):
        if marker not in main_text:
            errors.append(f"main.tex missing required marker: {marker}")
    # 分章结构是比赛期多人写作的前提，被合并回单文件就失去意义。
    if not sorted((paper_dir / "sections").glob("*.tex")):
        errors.append("no section files under sections/; the split structure is required")
    return errors


def check_build(build_dir: Path) -> list[str]:
    errors: list[str] = []
    pdf = build_dir / "main.pdf"
    if not pdf.exists() or pdf.stat().st_size < 1000:
        errors.append(f"missing or abnormally small PDF: {pdf}")
        return errors
    for suffix in (".log", ".aux"):
        path = build_dir / f"main{suffix}"
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            if "undefined references" in text.lower() or "undefined citations" in text.lower():
                errors.append(f"unresolved references or citations in {path}")
    if shutil.which("pdftotext"):
        result = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], text=True, capture_output=True, check=False)
        if result.returncode != 0:
            errors.append(f"pdftotext failed: {result.stderr.strip()}")
        else:
            for marker in ("摘要", "关键词", "参考文献"):
                if marker not in result.stdout:
                    errors.append(f"PDF text missing marker: {marker}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-dir", type=Path, default=Path("paper"))
    parser.add_argument("--build-dir", type=Path, default=Path("paper/build"))
    args = parser.parse_args()
    errors = check_sources(args.paper_dir) + check_build(args.build_dir)
    if errors:
        print("FAIL LaTeX QA")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS LaTeX QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
