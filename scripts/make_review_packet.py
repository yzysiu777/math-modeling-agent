"""Assemble a compact Independent Reviewer packet draft for one critical node.

Building a packet by hand is the step most likely to be skipped under time
pressure, which turns C1/C2/C3 into paperwork nobody performs.  This script
gathers the visible case files a node needs so the human action shrinks to
"copy one file into a fresh session, paste the report back".

The output is a draft.  The main agent still has to state its real concerns and
the three to five questions it wants answered, and a teammate still has to run
the review in a genuinely separate session.
"""

from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
from typing import List, Sequence

NODES = ("C1", "C2", "C3")

#: Files pulled into the packet per node.  Anything absent is reported as
#: "not provided" rather than silently omitted, because a reviewer must know
#: what they could not see.
_NODE_SOURCES: dict[str, Sequence[tuple[str, str]]] = {
    "C1": (
        ("case_brief.md", "题意与数据理解"),
        ("checkpoint.yaml", "路由与状态"),
    ),
    "C2": (
        ("case_brief.md", "题意与数据理解"),
        ("models/candidates.md", "候选路线池"),
        ("models/comparison.md", "路线比较与取舍"),
        ("experiments/board.md", "已运行的实验"),
    ),
    "C3": (
        ("case_brief.md", "题意与数据理解"),
        ("models/comparison.md", "路线比较与取舍"),
        ("experiments/board.md", "已运行的实验"),
        ("paper/claim_map.md", "论文数字溯源"),
        ("decisions.md", "已记录的人工决定"),
    ),
}
_MAX_CHARS = 12000


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""


def _fenced(text: str, path_label: str) -> str:
    if len(text) > _MAX_CHARS:
        text = text[:_MAX_CHARS].rstrip() + f"\n\n[... 已截断，完整内容见 {path_label} ...]"
    return f"```markdown\n{text}\n```"


def _spec_summaries(case_dir: Path) -> List[str]:
    """List spec front matter so C2 sees which routes reached implementation."""

    specs_dir = case_dir / "specs"
    if not specs_dir.is_dir():
        return []
    lines: List[str] = []
    for path in sorted(specs_dir.glob("SPEC-*.md")):
        if path.name.endswith(".questions.md"):
            continue
        header: List[str] = []
        for line in _read(path).splitlines()[1:]:
            if line.strip() == "---":
                break
            if line.strip():
                header.append(line.strip())
        lines.append(f"- `{path.name}`：" + "；".join(header) if header else f"- `{path.name}`")
    return lines


def _checks_summary(case_dir: Path) -> List[str]:
    """Surface recomputation reports so C3 can see which checks actually ran."""

    checks_dir = case_dir / "experiments" / "outputs" / "checks"
    if not checks_dir.is_dir():
        return []
    return [f"- `{path.name}`\n{_fenced(_read(path), str(path))}" for path in sorted(checks_dir.glob("*.json"))]


def build_packet(case_dir: Path, node: str) -> str:
    """Render the packet draft for one case and one critical node."""

    if node not in NODES:
        raise ValueError(f"node must be one of {list(NODES)}")
    if not case_dir.is_dir():
        raise FileNotFoundError(f"case directory does not exist: {case_dir}")

    case_id = case_dir.name
    parts: List[str] = [
        f"# Independent Reviewer 审核包草稿：{node}",
        "",
        "> 这是脚本生成的草稿。复制到**全新会话**之前，主 Agent 必须补完「最担心的问题」",
        "> 和「希望回答的 3–5 个问题」，队员必须填入实际审核者信息。不要连同主解聊天",
        "> 记录一起交出去。",
        "",
        "## 包信息",
        "",
        "```yaml",
        f"case_id: {case_id}",
        f"review_id: {node}-{date.today().isoformat()}-01",
        "reviewer_provider: <gemini | grok | codex_fresh_task | other_model | human_specialist>",
        "reviewer_model: <实际模型或人工角色>",
        "review_session: fresh",
        "saw_main_conversation: false",
        f"critical_node: {node}",
        "```",
        "",
        "## 待补：主 Agent 填写",
        "",
        "- 当前最担心的问题：",
        "- 希望回答的 3–5 个问题：",
        "  1. ",
        "  2. ",
        "  3. ",
        "- 明确未提供、因此不能判断的内容：",
        "",
    ]

    parts.append("## 已提供的案例材料")
    parts.append("")
    missing: List[str] = []
    for relative, label in _NODE_SOURCES[node]:
        path = case_dir / relative
        content = _read(path)
        if not content:
            missing.append(f"- `{relative}`（{label}）")
            continue
        parts.extend([f"### {label}（`{relative}`）", "", _fenced(content, relative), ""])

    if node in {"C2", "C3"}:
        specs = _spec_summaries(case_dir)
        if specs:
            parts.extend(["### 实现规格清单（`specs/`）", "", *specs, ""])
        else:
            missing.append("- `specs/`（尚无实现规格）")

    if node == "C3":
        checks = _checks_summary(case_dir)
        if checks:
            parts.extend(["### 复算报告（`experiments/outputs/checks/`）", "", *checks, ""])
        else:
            missing.append("- `experiments/outputs/checks/`（尚无复算报告）")

    if missing:
        parts.extend([
            "## 未提供的材料",
            "",
            "审核者据此判断哪些结论无法验证，不要把「未提供」当成「已通过」：",
            "",
            *missing,
            "",
        ])

    parts.extend([
        "## 期望输出",
        "",
        f"按 `prompts/reviewer/{_prompt_name(node)}` 的固定输出格式回复。要点：",
        "",
        "1. 先独立重构审核对象，不把主解结论当默认前提；",
        "2. 找出 3–5 个最高风险问题，给出证据、影响和最小测试；",
        "3. 至少提出一个不同方法族、替代解释或反例/证伪测试；",
        "4. 给出路线保留、修改、暂停或拒绝建议；",
        "5. 明确 what was checked / what was not checked / uncertainty / human decisions required；",
        "6. 信息不足时输出 `BLOCKED`，不得补造题面、参数、数据、结果或引用；",
        "7. 不直接修改主文件、不决定最终路线、不批准自己的修订。",
        "",
        "报告回来后由队员把接受/拒绝/延期及原因写入 `decisions.md`，再由主 Agent 实施。",
    ])
    return "\n".join(parts) + "\n"


def _prompt_name(node: str) -> str:
    return {
        "C1": "C1_problem_challenge.md",
        "C2": "C2_model_challenge.md",
        "C3": "C3_results_challenge.md",
    }[node]


def main() -> int:
    parser = argparse.ArgumentParser(description="generate an Independent Reviewer packet draft")
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--node", choices=NODES, required=True)
    parser.add_argument("--out", type=Path, help="output file; defaults to <case>/reviews/packets/")
    args = parser.parse_args()

    packet = build_packet(args.case_dir, args.node)
    target = args.out or (
        args.case_dir / "reviews" / "packets" / f"{args.node}_{date.today().isoformat()}_packet.md"
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(packet, encoding="utf-8")
    print(f"WROTE {target}")
    print("下一步：补完「最担心的问题」和 3–5 个问题，再复制到全新会话交给独立审核者。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
