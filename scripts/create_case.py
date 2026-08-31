"""Create one case containing shared inputs and one workbench per question."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
ROUTES = {"optimization", "data_analysis", "hybrid", "insufficient_information"}
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

    for relative in ("input/说明文档", "paper/reviews", "paper/sections"):
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
    (case_dir / "paper/README.md").write_text(
        "# 全案例论文\n\n每题正文写入 `sections/q<k>.tex`；C3 在全案例收官前只做一次。\n",
        encoding="utf-8",
    )
    (case_dir / "paper/claim_map.md").write_text(
        (TEMPLATES / "claim_map.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
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
