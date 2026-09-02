"""Fill a role startup template from the case, so no one hand-types case facts.

The third dry run's writer prompt was written by hand: 144 lines that restated
the protocol and baked in four problem-specific conclusions copied out of the
experiment board. Both are the same disease in different clothes -- a second
copy of something that already exists, which goes stale the moment the original
changes.

This generator keeps exactly one copy of each thing: the rules live in
``prompts/<role>.md``, the shape lives in ``prompts/startup/<role>.md``, and the
case facts stay in the case. What lands in ``队员工作区/启动提示词/`` is a filled
template plus pointers -- never a transcription of results.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

try:
    from .case_paths import normalize_question
    from .experiment_board import parse_markdown_table
except ImportError:  # pragma: no cover
    from case_paths import normalize_question
    from experiment_board import parse_markdown_table


ROOT = Path(__file__).resolve().parents[1]
ROLES = ("orchestrator", "modeler", "engineer", "writer", "reviewer")
STEP_BY_ROLE = {"modeler": "A", "engineer": "C", "writer": "D", "reviewer": "C1"}
NODE_DECISION = re.compile(r"^[ \t]*Node\s+decision[ \t]*[:：]", re.IGNORECASE | re.MULTILINE)
CODE_FENCE = re.compile(r"```text\n(?P<body>.*?)```", re.DOTALL)


def _questions(case_dir: Path) -> list[str]:
    found = [
        path.name for path in case_dir.iterdir()
        if path.is_dir() and re.fullmatch(r"q[1-9][0-9]*", path.name)
    ]
    return sorted(found, key=lambda name: int(name[1:]))


def _opened(case_dir: Path) -> list[str]:
    opened: list[str] = []
    for question in _questions(case_dir):
        cards = sorted((case_dir / question / "reviews").glob("C1*.md"))
        if any(NODE_DECISION.search(path.read_text(encoding="utf-8", errors="replace"))
               for path in cards):
            opened.append(question)
    return opened


def _board_summary(case_dir: Path, question: str) -> str:
    board = case_dir / question / "board.md"
    if not board.is_file():
        return "实验板尚不存在"
    rows = parse_markdown_table(board.read_text(encoding="utf-8"))
    done = [row for row in rows if str(row.get("status", "")).strip().casefold() == "done"]
    failed = [row for row in rows if str(row.get("status", "")).strip().casefold() == "failed"]
    return f"实验板共 {len(rows)} 行，其中 done {len(done)} 行、failed {len(failed)} 行"


def _literature_summary(case_dir: Path) -> str:
    path = case_dir / "paper/文献清单.md"
    if not path.is_file():
        return "文献清单尚不存在"
    rows = [
        row for row in parse_markdown_table(path.read_text(encoding="utf-8"))
        if str(row.get("key", "")).strip() and str(row.get("key", "")).strip() != "key"
    ]
    if not rows:
        return "文献清单当前为空 —— 本轮引用全靠你检索并登记"
    pending = sum(1 for row in rows if str(row.get("核对状态", "")).strip() != "已核对")
    return f"文献清单现有 {len(rows)} 条，其中 {pending} 条待队员核对"


def _spec_names(case_dir: Path, question: str) -> str:
    specs = [
        path.name for path in sorted((case_dir / question / "specs").glob("SPEC-*.md"))
        if not path.name.endswith(".questions.md")
    ]
    return "、".join(specs) if specs else "尚无 Full SPEC"


def build_prompt(case_dir: Path, role: str, question: str | None = None) -> str:
    if role not in ROLES:
        raise ValueError(f"role must be one of {list(ROLES)}")
    if not case_dir.is_dir():
        raise FileNotFoundError(f"case directory does not exist: {case_dir}")
    template = (ROOT / f"prompts/startup/{role}.md").read_text(encoding="utf-8")
    match = CODE_FENCE.search(template)
    if match is None:
        raise ValueError(f"startup template has no ```text block: {role}")

    body = match.group("body")
    name = normalize_question(question) if question else (_questions(case_dir) or ["q1"])[0]
    case = str(case_dir.resolve())
    body = (
        body.replace("<项目根>", str(ROOT))
        .replace("<案例目录>", case)
        .replace("Q<k>", name.upper())
        .replace("<案例目录>/q<k>", f"{case}/{name}")
        .replace("q<k>", name)
    )
    body = body.replace("<绝对路径>", f"{case}/{name}/specs/")

    opened = _opened(case_dir)
    sealed = [item for item in _questions(case_dir) if item not in opened]
    notes = [
        "",
        "本轮由 make start-prompt 生成，以下为案例现状，不要把它当成结论：",
        f"- 已通过 C1 的子问题：{'、'.join(item.upper() for item in opened) or '无'}",
        f"- 仍处封存状态、不得书写的子问题：{'、'.join(item.upper() for item in sealed) or '无'}",
    ]
    if role == "writer":
        notes.append(f"- {_literature_summary(case_dir)}")
    if role in {"engineer", "writer"}:
        notes.append(f"- 本题 Full SPEC：{_spec_names(case_dir, name)}")
        notes.append(f"- {_board_summary(case_dir, name)}")
        notes.append(
            f"- 结论强度以 {name}/board.md 的预设判据和实测判定为准，"
            "不得超出那里记录的结论；判定写 FAIL 的实验不许在论文里说成通过。"
        )
    return body.rstrip("\n") + "\n" + "\n".join(notes) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="fill a role startup template from the case")
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--role", choices=ROLES, required=True)
    parser.add_argument("--question")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    try:
        text = build_prompt(args.case_dir, args.role, args.question)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL start prompt: {exc}")
        return 1

    name = normalize_question(args.question) if args.question else "q1"
    step = STEP_BY_ROLE.get(args.role, "X")
    target = args.out or (
        args.case_dir / "队员工作区/启动提示词"
        / f"{name.upper()}-{step}-{args.role.capitalize()}.md"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# 启动 {args.role.capitalize()}（{name.upper()} 步骤 {step}）\n\n"
        "> 由 `make start-prompt` 从案例生成。**不要手工往里加题目结论** —— "
        "规则在 `prompts/`，事实在案例里，这里只做填空和指路。\n\n```text\n"
    )
    target.write_text(header + text + "```\n", encoding="utf-8")
    print(f"WROTE {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
