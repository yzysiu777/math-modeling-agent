"""Create one case containing shared inputs and one workbench per question."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
ROUTES = {"optimization", "data_analysis", "hybrid", "insufficient_information"}
QUESTION_SECTION = re.compile(r"^q[1-9][0-9]*\.tex$")
CASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,63}$")


def _sources_seed(questions: int) -> str:
    mappings = "\n".join(f"  q{index}: 第{index}题" for index in range(1, questions + 1))
    return f"""# 人工只在这里声明原始来源；所有路径必须改成真实绝对路径。
statement: /absolute/path/to/statement.pdf
data_roots:
  - /absolute/path/to/data
docs: []
questions:
{mappings}
shared: []
"""


def _checkpoint_seed(case_id: str, route: str, questions: int) -> str:
    blocks: list[str] = []
    for index in range(1, questions + 1):
        blocks.append(f"""  q{index}:
    step: A
    status: not_started
    route:
      value: {route}
      decided_by: modeler
      confirmed_by_human: false
      note: ""
    reviews:
      C1: pending
      C2: optional
    deterministic_risks:
      infeasible: false
      objective_mismatch: false
      leakage: false
      split_overlap: false""")
    return f"""# 轻量进度提示，不是审批或身份认证。
case_id: {case_id}
current_question: q1
questions:
{chr(10).join(blocks)}
reviews:
  C3: pending
human_block: ""
"""


def _brief_seed(case_id: str, question: str, route: str) -> str:
    template = (TEMPLATES / "case_brief.md").read_text(encoding="utf-8")
    return (
        template.replace("<case_id>", case_id)
        .replace("<question>", question.upper())
        .replace("<route>", route)
    )


def _log_seed(question: str) -> str:
    return f"""# {question.upper()} 过程日志

每步结束只追加以下四行，不建立阶段报告副本：

```text
做了什么：
产物路径：
风险：none
下一步：
```
"""


def _seed_paper(case_dir: Path, questions: int) -> None:
    """Copy the paper skeleton so the Writer never has to invent a document class.

    The third dry run produced a hand-rolled ``ctexart`` main.tex because the case
    only offered an empty ``paper/sections/`` -- the gmcmthesis engineering that
    handles the cover page, the abstract layout and anonymity was never reached.
    Class, style and bst stay in the repository ``paper/`` and are found through
    TEXINPUTS; only case-specific content is copied here.
    """

    source = TEMPLATES / "paper"
    for relative in ("config", "sections", "bibliography", "figures", "tables", "appendix", "reviews"):
        (case_dir / "paper" / relative).mkdir(parents=True, exist_ok=True)
    for path in sorted(source.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if relative.parent.name == "sections" and QUESTION_SECTION.fullmatch(relative.name):
            if int(relative.stem[1:]) > questions:
                continue
        (case_dir / "paper" / relative).write_text(
            path.read_text(encoding="utf-8"), encoding="utf-8"
        )
    main = case_dir / "paper/main.tex"
    text = main.read_text(encoding="utf-8")
    # 用字面替换而不是 re.sub：替换串里的 \InputQuestion 会被当成正则转义。
    seeded = "\n".join(f"\\InputQuestion{{q{index}}}" for index in (1, 2, 3))
    wanted = "\n".join(
        f"\\InputQuestion{{q{index}}}" for index in range(1, questions + 1)
    )
    text = text.replace(seeded, wanted)
    main.write_text(text, encoding="utf-8")


def create_case(
    case_id: str,
    route: str = "insufficient_information",
    cases_root: Path = ROOT / "cases",
    questions: int = 1,
) -> Path:
    if not CASE_ID.fullmatch(case_id):
        raise ValueError("case-id must be 2-64 ASCII letters, digits, '-' or '_'")
    if route not in ROUTES:
        raise ValueError(f"route must be one of {sorted(ROUTES)}")
    if questions < 1 or questions > 20:
        raise ValueError("questions must be between 1 and 20")
    case_dir = cases_root / case_id
    if case_dir.exists():
        raise FileExistsError(f"case already exists: {case_dir}")

    for relative in (
        "input/说明文档",
        "队员工作区/待批准", "队员工作区/已批准", "队员工作区/启动提示词",
    ):
        (case_dir / relative).mkdir(parents=True, exist_ok=True)
    for index in range(1, questions + 1):
        question = f"q{index}"
        for relative in (
            "specs", "code/python", "code/matlab", "outputs/data",
            "outputs/checks", "outputs/figures", "reviews",
        ):
            (case_dir / question / relative).mkdir(parents=True, exist_ok=True)
        (case_dir / question / "brief.md").write_text(
            _brief_seed(case_id, question, route), encoding="utf-8"
        )
        (case_dir / question / "board.md").write_text(
            (TEMPLATES / "experiment_board.md").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (case_dir / question / "log.md").write_text(_log_seed(question), encoding="utf-8")

    (case_dir / "sources.yaml").write_text(_sources_seed(questions), encoding="utf-8")
    (case_dir / "checkpoint.yaml").write_text(
        _checkpoint_seed(case_id, route, questions), encoding="utf-8"
    )
    (case_dir / "decisions.md").write_text(
        (TEMPLATES / "decision_log.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (case_dir / "input/README.md").write_text(
        "# 阶段 0 生成目录\n\n运行 `make ingest CASE=cases/<case_id>` 后生成题面全文、数据清单、说明文档和每题数据范围。\n",
        encoding="utf-8",
    )
    _seed_paper(case_dir, questions)
    (case_dir / "paper/README.md").write_text(
        "# 全案例论文\n\n"
        "文档类、样式和 bst 来自仓库 `paper/`，本目录只放本案例内容。\n\n"
        "- 整本编译：`make paper CASE=<案例目录>`\n"
        "- 单题编译：`make paper CASE=<案例目录> Q=q1`\n\n"
        "每题正文写入 `sections/q<k>.tex`；每题 D 结束做一次 C3，全案例收官前再做一次。\n",
        encoding="utf-8",
    )
    (case_dir / "paper/claim_map.md").write_text(
        (TEMPLATES / "claim_map.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    for name in ("现在做什么.md", "审核卡索引.md", "我的笔记.md", "待补图清单.md"):
        text = (TEMPLATES / name).read_text(encoding="utf-8")
        if name == "现在做什么.md":
            text = text.replace("- 案例：/", f"- 案例：{case_id} /")
        (case_dir / "队员工作区" / name).write_text(text, encoding="utf-8")
    return case_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="create a per-question modeling case")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--questions", type=int, default=1)
    parser.add_argument("--route", choices=sorted(ROUTES), default="insufficient_information")
    parser.add_argument("--cases-root", type=Path, default=ROOT / "cases")
    args = parser.parse_args()
    try:
        path = create_case(args.case_id, args.route, args.cases_root, args.questions)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL create case: {exc}")
        return 1
    print(f"created case: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
