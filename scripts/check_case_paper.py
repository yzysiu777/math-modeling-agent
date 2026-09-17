"""Compile a throwaway case paper and require that its bibliography is its own.

``make paper CASE=...`` once put the recursive ``paper//`` on TEXINPUTS.  XeLaTeX
then found the repository's ``paper/build/main.bbl`` instead of the case's,
latexmk called that a foreign .bbl and skipped bibtex, and the case paper came
out with an empty reference list and no ``build/main.bbl``.  This check seeds a
case from ``templates/paper``, cites one entry, compiles one question and fails
unless the case build has its own non-empty ``main.bbl``.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO_BUILD = ROOT / "paper" / "build"
#: 仓库论文没有引用时不会生成 bbl，CI 的干净检出里就没有可被误读的文件。
#: 缺失时放一份空的诱饵，让回归在任何检出下都能复现；已有文件一律不动。
DECOY = "\\begin{thebibliography}{0}\n\\end{thebibliography}\n"


def check(fontset: str = "") -> list[str]:
    problems: list[str] = []
    decoy = REPO_BUILD / "main.bbl"
    placed_decoy = not decoy.exists()
    if placed_decoy:
        REPO_BUILD.mkdir(parents=True, exist_ok=True)
        decoy.write_text(DECOY, encoding="utf-8")
    try:
        with tempfile.TemporaryDirectory(prefix="case-paper-") as tmp:
            case = Path(tmp) / "case"
            shutil.copytree(ROOT / "templates" / "paper", case / "paper")
            q1 = case / "paper" / "sections" / "q1.tex"
            q1.write_text(
                q1.read_text(encoding="utf-8") + "\n回归检查引用\\cite{placeholder2026}。\n",
                encoding="utf-8",
            )
            command = ["make", "-C", str(ROOT), "paper", f"CASE={case}", "Q=q1"]
            if fontset:
                command.append(f"PAPER_FONTSET={fontset}")
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode != 0:
                tail = "\n".join((result.stdout + result.stderr).splitlines()[-30:])
                return [f"案例论文编译失败：\n{tail}"]
            build = case / "paper" / "build"
            bbl = build / "main.bbl"
            if not bbl.is_file():
                problems.append("案例 build/main.bbl 不存在：bibtex 没有在案例构建目录运行")
            elif "\\bibitem" not in bbl.read_text(encoding="utf-8"):
                problems.append("案例 build/main.bbl 没有任何 \\bibitem")
            fls = build / "main.fls"
            if fls.is_file():
                leaked = sorted(
                    {
                        line.split(" ", 1)[1]
                        for line in fls.read_text(encoding="utf-8").splitlines()
                        if line.startswith("INPUT ") and str(REPO_BUILD) in line
                    }
                )
                problems.extend(f"案例编译读取了仓库构建产物：{path}" for path in leaked)
    finally:
        if placed_decoy:
            decoy.unlink(missing_ok=True)
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fontset", default="", help="传给 make 的 PAPER_FONTSET")
    args = parser.parse_args()
    problems = check(args.fontset)
    for problem in problems:
        print(f"FAIL {problem}")
    if not problems:
        print("OK 案例论文使用自己的 build/main.bbl，参考文献非空")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
