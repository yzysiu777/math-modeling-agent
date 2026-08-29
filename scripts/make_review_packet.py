"""Assemble a compact Independent Reviewer packet draft for one critical node.

Building a packet by hand is the step most likely to be skipped under time
pressure, which turns C1/C2/C3 into paperwork nobody performs.  This script
gathers the visible case evidence a node actually needs to mount a
methodologically different challenge.

Three properties matter more than brevity:

* **C1 sees neutral evidence.**  A reviewer who only reads the Modeler's own
  ``case_brief.md`` can check internal consistency but cannot check fidelity to
  the problem, which is the entire point of C1.  The original statement and the
  input inventory go in.
* **C2 sees the real model.**  Front matter is not a model; the objective,
  formulation, algorithm and open questions of the Champion and Challenger are.
* **C3 sees the claim and its evidence.**  Claim text, the data rows behind it,
  the recomputation verdict and the figure entry, not a summary of them.

The output is a draft.  The main agent still states its real concerns and the
three to five questions it wants answered, and a teammate still runs the review
in a genuinely separate session.  When required evidence is absent the packet
says so at the top: an incomplete review must never be mistaken for a passed one.
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence

NODES = ("C1", "C2", "C3")

#: Per-file excerpt budget.  Large inputs are truncated and listed as
#: attachments rather than silently cut.
_MAX_CHARS = 8000
_INPUT_EXCERPT_CHARS = 4000
_DATA_EXCERPT_LINES = 12
#: Text extensions worth excerpting inline from ``input/``.
_TEXT_SUFFIXES = frozenset({".md", ".txt", ".csv", ".tsv", ".json", ".yaml", ".yml"})

_SPEC_FM_LINE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<value>.*?)\s*$")
_HEADING = re.compile(r"^\s*(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*$")
_SECTION_NUMBER = re.compile(r"^(\d+)[.、．]?\s")
_ROUTE_HEADING = re.compile(
    r"^\s*#{2,4}\s+(?P<route>M-[A-Za-z0-9][A-Za-z0-9_-]*)(?:\s*.*)?\s*$", re.IGNORECASE
)
_SELECTED_STATUS = re.compile(r"`?(?P<role>champion|challenger)`?", re.IGNORECASE)
_MARKDOWN_HEADING = re.compile(r"^\s*#{1,6}\s+\S")
_PLACEHOLDER = re.compile(r"^(?:<[^>]*>|[-—\s]|todo|tbd|n/?a|待填写|待填|待补充)*$", re.IGNORECASE)


class Packet:
    """Accumulate packet body, missing-evidence notes and an attachment list."""

    def __init__(self) -> None:
        self.parts: List[str] = []
        self.missing: List[str] = []
        self.attachments: List[str] = []

    def add(self, *lines: str) -> None:
        self.parts.extend(lines)

    def section(self, title: str, body: str, source: str) -> None:
        self.add(f"### {title}（`{source}`）", "", _fenced(body, source), "")

    def absent(self, what: str) -> None:
        self.missing.append(what)

    def attach(self, what: str) -> None:
        self.attachments.append(what)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeDecodeError):
        return ""


def _fenced(text: str, label: str, limit: int = _MAX_CHARS) -> str:
    if len(text) > limit:
        text = text[:limit].rstrip() + f"\n\n[... 已截断；完整内容见 {label}，见文末附件清单 ...]"
    return f"```\n{text}\n```"


def _has_value(text: str) -> bool:
    return bool(text.strip()) and not _PLACEHOLDER.fullmatch(text.strip())


def _split_sections(text: str) -> dict[str, str]:
    """Split a Markdown body into numbered level-2 sections."""

    sections: dict[str, str] = {}
    current = ""
    buffer: List[str] = []
    for line in text.splitlines():
        heading = _HEADING.match(line)
        if heading is not None and len(heading.group("hashes")) == 2:
            if current:
                sections[current] = "\n".join(buffer).strip()
            match = _SECTION_NUMBER.match(heading.group("title"))
            current = match.group(1) if match else ""
            buffer = []
            continue
        if current:
            buffer.append(line)
    if current:
        sections[current] = "\n".join(buffer).strip()
    return sections


def _spec_front_matter(text: str) -> dict[str, str]:
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = _SPEC_FM_LINE.match(line)
        if match is not None:
            fields[match.group("key").casefold()] = match.group("value").strip().strip("`'\"")
    return fields


def _specs(case_dir: Path) -> list[tuple[Path, dict[str, str], dict[str, str]]]:
    specs_dir = case_dir / "specs"
    if not specs_dir.is_dir():
        return []
    found = []
    for path in sorted(specs_dir.glob("SPEC-*.md")):
        if path.name.endswith(".questions.md"):
            continue
        text = _read(path)
        found.append((path, _spec_front_matter(text), _split_sections(text)))
    return found


def _selected_routes(case_dir: Path) -> dict[str, str]:
    """Map route ID -> champion/challenger, from the candidate pool."""

    path = case_dir / "models/candidates.md"
    if not path.is_file():
        return {}
    selected: dict[str, str] = {}
    current = ""
    for line in _read(path).splitlines():
        if _MARKDOWN_HEADING.match(line):
            heading = _ROUTE_HEADING.match(line)
            current = heading.group("route").strip().upper() if heading else ""
            continue
        if not current:
            continue
        match = _SELECTED_STATUS.search(line)
        if match is not None:
            selected[current] = match.group("role").casefold()
    return selected


def _pipe_rows(text: str) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        stripped = line.strip()
        if "|" not in stripped:
            continue
        cells = [cell.strip() for cell in stripped.strip("|").split("|")]
        if cells and all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells if cell):
            continue
        rows.append(cells)
    return rows


# --------------------------------------------------------------------------- C1


def _add_problem_evidence(packet: Packet, case_dir: Path) -> None:
    """Give C1 the original statement, not only the Modeler's reading of it."""

    input_dir = case_dir / "input"
    files = sorted(
        (path for path in input_dir.rglob("*") if path.is_file() and path.name != "README.md"),
        key=lambda path: path.name,
    ) if input_dir.is_dir() else []

    if not files:
        packet.absent(
            "`input/` 下没有题面或附件 —— C1 只能看到建模手转述的题意，"
            "**无法核对题意是否忠实于原题**"
        )
        return

    inventory = [
        f"- `{path.relative_to(case_dir)}`（{path.stat().st_size} 字节）" for path in files
    ]
    packet.add("### 原始输入清单（`input/`）", "", *inventory, "")

    excerpted = False
    for path in files:
        if path.suffix.casefold() not in _TEXT_SUFFIXES:
            packet.attach(f"`{path.relative_to(case_dir)}`（非文本，需随包一并提供）")
            continue
        text = _read(path)
        if not text:
            continue
        if len(text) > _INPUT_EXCERPT_CHARS:
            packet.attach(f"`{path.relative_to(case_dir)}`（已截断，审核前请提供完整文件）")
        packet.section(f"原题材料：{path.name}", text, str(path.relative_to(case_dir)))
        excerpted = True

    if not excerpted:
        packet.absent("`input/` 中没有可直接摘录的文本题面，审核者必须另行拿到原题")


# --------------------------------------------------------------------------- C2


def _add_model_evidence(packet: Packet, case_dir: Path) -> None:
    """Give C2 the actual formulation, not a list of spec file names."""

    selected = _selected_routes(case_dir)
    if not selected:
        packet.absent("`models/candidates.md` 中没有标记 champion/challenger，无法确定审核对象")
    specs = _specs(case_dir)
    if not specs:
        packet.absent("`specs/` 下没有实现规格 —— C2 无法审核尚未写下来的模型")
        return

    by_route: dict[str, list[tuple[Path, dict[str, str], dict[str, str]]]] = {}
    for path, front, sections in specs:
        by_route.setdefault(front.get("route_id", "").strip().upper(), []).append(
            (path, front, sections)
        )

    # full 规格的关键段：目标与判据 / 数学表述 / 算法 / 未决问题
    wanted = (("1", "目标与判据"), ("2", "数学表述"), ("4", "算法"), ("8", "未决问题"))
    covered: set[str] = set()

    for route, role in sorted(selected.items()):
        entries = by_route.get(route, [])
        full = [item for item in entries if item[1].get("status", "").casefold() == "full"]
        probe = [item for item in entries if item[1].get("status", "").casefold() == "probe"]
        packet.add(f"### {route}（{role}）", "")
        if not full:
            packet.absent(f"{route} 是 {role} 但没有 `status: full` 规格，C2 缺少它的正式模型")
            packet.add(f"> 没有 full 规格。", "")
        for path, front, sections in full:
            covered.add(route)
            packet.add(
                f"来源：`{path.relative_to(case_dir)}`，方法族 "
                f"`{front.get('method_family', '未填写')}`，语言 `{front.get('language', '未填写')}`",
                "",
            )
            for number, label in wanted:
                body = sections.get(number, "")
                if _has_value(body):
                    packet.add(f"**{number}. {label}**", "", _fenced(body, path.name, 4000), "")
                else:
                    packet.absent(f"{path.name} 的第 {number} 段（{label}）为空或仍是占位")
        for path, _front, sections in probe:
            body = sections.get("5", "")
            title = "probe 结果回填" if _has_value(body) else "probe 结果尚未回填"
            packet.add(f"**{title}**（`{path.relative_to(case_dir)}`）", "",
                       _fenced(body or "（未回填）", path.name, 2000), "")
        if not probe:
            packet.absent(f"{route} 没有 probe 规格，无法判断这条路线是否被便宜地证伪过")

    orphan = sorted(route for route in by_route if route and route not in covered and route in selected)
    if orphan:
        packet.add("> 以下被选中的路线没有可摘录的 full 规格：" + "、".join(orphan), "")

    questions = sorted((case_dir / "specs").glob("SPEC-*.questions.md")) if (case_dir / "specs").is_dir() else []
    for path in questions:
        packet.section(f"未解决的回问：{path.name}", _read(path), str(path.relative_to(case_dir)))


# --------------------------------------------------------------------------- C3


def _claim_rows(case_dir: Path) -> tuple[list[str], list[list[str]]]:
    path = case_dir / "paper/claim_map.md"
    if not path.is_file():
        return [], []
    rows = _pipe_rows(_read(path))
    header: list[str] = []
    claims: list[list[str]] = []
    for cells in rows:
        if not header and cells and cells[0].strip().casefold().startswith("claim"):
            header = cells
            continue
        if cells and re.fullmatch(r"`?CLM-[A-Za-z0-9_-]+`?", cells[0].strip(), re.IGNORECASE):
            if any(_has_value(cell) for cell in cells[1:]):
                claims.append(cells)
    return header, claims


def _add_claim_evidence(packet: Packet, case_dir: Path) -> None:
    """Give C3 the claim text plus the rows, verdicts and figures behind it."""

    header, claims = _claim_rows(case_dir)
    if not claims:
        packet.absent("`paper/claim_map.md` 没有已填写的强主张 —— C3 没有可抽查的对象")
        return

    packet.add("### 待审核的论文强主张（`paper/claim_map.md`）", "")
    if header:
        packet.add("| " + " | ".join(header) + " |", "|" + "---|" * len(header))
    for cells in claims:
        packet.add("| " + " | ".join(cells) + " |")
    packet.add("", "审核者请从中挑 3–5 条风险最高的抽查，不要求逐条复核。", "")

    joined = " ".join(" ".join(cells) for cells in claims)
    outputs = case_dir / "experiments/outputs"

    # 数据片段：claim 引用到的结果文件，各摘录前若干行
    referenced = sorted({
        match.group(0) for match in re.finditer(r"[\w./-]+\.(?:csv|json)", joined)
    })
    shown = 0
    for reference in referenced:
        candidate = _resolve(case_dir, reference)
        if candidate is None or not candidate.is_file():
            packet.absent(f"claim 引用的结果文件不存在：`{reference}`")
            continue
        if "checks" in candidate.parts:
            continue  # 复算报告单独成节
        lines = _read(candidate).splitlines()
        excerpt = "\n".join(lines[:_DATA_EXCERPT_LINES])
        if len(lines) > _DATA_EXCERPT_LINES:
            excerpt += f"\n[... 共 {len(lines)} 行，已摘录前 {_DATA_EXCERPT_LINES} 行 ...]"
            packet.attach(f"`{reference}`（完整数据文件）")
        packet.section(f"结果数据片段：{candidate.name}", excerpt, reference)
        shown += 1
    if referenced and not shown:
        packet.absent("claim 引用的结果数据文件都无法读取，C3 只能看到主模型的转述")

    # 复算报告摘要
    checks_dir = outputs / "checks"
    reports = sorted(checks_dir.glob("*.json")) if checks_dir.is_dir() else []
    if not reports:
        packet.absent("`experiments/outputs/checks/` 下没有复算报告，无法判断结论是否已被独立复算")
    else:
        summary: List[str] = []
        for path in reports:
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                summary.append(f"- `{path.name}`：**无法解析**，不能当作已通过")
                packet.absent(f"复算报告无法解析：`{path.name}`")
                continue
            checks = payload.get("checks") if isinstance(payload, dict) else None
            if not isinstance(checks, list):
                summary.append(f"- `{path.name}`：格式不符合约定，不能当作已通过")
                packet.absent(f"复算报告格式不符合约定：`{path.name}`")
                continue
            failed = [item for item in checks if isinstance(item, dict) and not item.get("passed", True)]
            verdict = "全部通过" if not failed else f"**{len(failed)} 项未通过**"
            summary.append(f"- `{path.name}`（{payload.get('exp_id', '?')}）：{len(checks)} 项检查，{verdict}")
            for item in failed:
                summary.append(f"  - {item.get('kind', '?')} / {item.get('name', '?')}：{item.get('detail', '')}")
        packet.add("### 复算报告摘要（`experiments/outputs/checks/`）", "", *summary, "")

    # 图表清单条目
    manifest = outputs / "figures/manifest.md"
    if not manifest.is_file():
        packet.absent("没有 `figures/manifest.md`，无法核对论文引用的图来自哪个实验")
    else:
        figure_ids = sorted({match.group(0) for match in re.finditer(r"FIG-[A-Za-z0-9_-]+", joined)})
        rows = [cells for cells in _pipe_rows(_read(manifest))
                if cells and any(fid.casefold() in cells[0].casefold() for fid in figure_ids)]
        if figure_ids and not rows:
            packet.absent("claim 引用的 Figure ID 在 `figures/manifest.md` 中找不到对应条目")
        elif rows:
            packet.add("### 图表清单条目（`experiments/outputs/figures/manifest.md`）", "")
            for cells in rows:
                packet.add("| " + " | ".join(cells) + " |")
            packet.add("")
            for fid in figure_ids:
                for ext in ("pdf", "png"):
                    candidate = outputs / f"figures/{fid}.{ext}"
                    if candidate.is_file():
                        packet.attach(f"`{candidate.relative_to(case_dir)}`（图，需随包一并提供）")


def _resolve(case_dir: Path, reference: str) -> Path | None:
    """Map a claim-map path reference onto a real file inside the case."""

    reference = reference.strip("`").lstrip("./")
    for base in (case_dir, case_dir / "experiments"):
        candidate = base / reference
        try:
            candidate.relative_to(case_dir)
        except ValueError:
            continue
        if candidate.is_file():
            return candidate
    matches = list((case_dir / "experiments/outputs").rglob(Path(reference).name))
    return matches[0] if len(matches) == 1 else None


# --------------------------------------------------------------------------- 组装


_NODE_COMMON: dict[str, Sequence[tuple[str, str]]] = {
    "C1": (("case_brief.md", "建模手对题意的理解（**待核对的对象，不是依据**）"),
           ("checkpoint.yaml", "路由与状态")),
    "C2": (("case_brief.md", "题意与数据理解"),
           ("models/comparison.md", "路线比较与取舍")),
    "C3": (("models/comparison.md", "路线比较与取舍"),
           ("experiments/board.md", "已运行的实验"),
           ("decisions.md", "已记录的人工决定")),
}
_PROMPTS = {
    "C1": "C1_problem_challenge.md",
    "C2": "C2_model_challenge.md",
    "C3": "C3_results_challenge.md",
}


def build_packet(case_dir: Path, node: str, review_id: str | None = None) -> str:
    """Render the packet draft for one case and one critical node."""

    if node not in NODES:
        raise ValueError(f"node must be one of {list(NODES)}")
    if not case_dir.is_dir():
        raise FileNotFoundError(f"case directory does not exist: {case_dir}")

    case_id = case_dir.name
    packet = Packet()

    for relative, label in _NODE_COMMON[node]:
        content = _read(case_dir / relative)
        if content:
            packet.section(label, content, relative)
        else:
            packet.absent(f"`{relative}`（{label}）不存在或为空")

    if node == "C1":
        _add_problem_evidence(packet, case_dir)
    elif node == "C2":
        _add_model_evidence(packet, case_dir)
    else:
        _add_claim_evidence(packet, case_dir)

    header: List[str] = [
        f"# Independent Reviewer 审核包草稿：{node}",
        "",
        "> 这是脚本生成的草稿。交给审核者之前，主 Agent 必须补完「最担心的问题」和",
        "> 「希望回答的 3–5 个问题」，队员必须填入实际审核者信息，并在**全新会话**中进行。",
        "> 不要连同主解聊天记录一起交出去。",
        "",
    ]

    if packet.missing:
        header += [
            f"## ⚠ 审核包不完整（缺 {len(packet.missing)} 项关键证据）",
            "",
            "以下证据缺失，审核者据此判断哪些结论**无法验证**。"
            "「未提供」不等于「已通过」，缺证据时正确的结论是 `BLOCKED` 而不是 `PASS`：",
            "",
            *(f"- {item}" for item in packet.missing),
            "",
        ]
    else:
        header += ["## 审核包完整性", "", "本节点所需的关键证据均已包含。", ""]

    header += [
        "## 包信息",
        "",
        "```yaml",
        f"case_id: {case_id}",
        f"review_id: {review_id or _review_id(node)}",
        "reviewer_provider: <gemini | grok | codex_fresh_task | other_model | human_specialist>",
        "reviewer_model: <实际模型或人工角色>",
        "review_session: fresh",
        "saw_main_conversation: false",
        f"critical_node: {node}",
        f"packet_complete: {'true' if not packet.missing else 'false'}",
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
        "## 已提供的案例材料",
        "",
    ]

    body = header + packet.parts

    if packet.attachments:
        body += [
            "## 附件清单",
            "",
            "本包**不是单文件自包含**。下列材料未完整内嵌，需与本文件一并提供给审核者；",
            "缺少它们时，相关结论只能标为未验证：",
            "",
            *(f"- {item}" for item in dict.fromkeys(packet.attachments)),
            "",
        ]

    body += [
        "## 期望输出",
        "",
        f"按 `prompts/reviewer/{_PROMPTS[node]}` 的固定输出格式回复。要点：",
        "",
        "1. 先独立重构审核对象，不把主解结论当默认前提；",
        "2. 找出 3–5 个最高风险问题，给出证据、影响和最小测试；",
        "3. 至少提出一个不同方法族、替代解释或反例/证伪测试，并写明方法论差异；",
        "4. 给出路线保留、修改、暂停或拒绝建议；",
        "5. 明确 what was checked / what was not checked / uncertainty / human decisions required；",
        "6. 信息不足时输出 `BLOCKED`，不得补造题面、参数、数据、结果或引用；",
        "7. 不直接修改主文件、不决定最终路线、不批准自己的修订。",
        "",
        "报告回来后由队员把接受/拒绝/延期及原因写入 `decisions.md`，再由主 Agent 实施。",
    ]
    return "\n".join(body) + "\n"


def _review_id(node: str, moment: datetime | None = None) -> str:
    stamp = (moment or datetime.now()).strftime("%Y%m%d-%H%M%S")
    return f"{node}-{stamp}"


def _unique_target(directory: Path, node: str, moment: datetime | None = None) -> tuple[Path, str]:
    """Never silently overwrite an earlier packet for the same node and day."""

    stamp = (moment or datetime.now()).strftime("%Y%m%d-%H%M%S")
    base = f"{node}_{stamp}_packet"
    target = directory / f"{base}.md"
    suffix = 2
    while target.exists():
        target = directory / f"{base}-{suffix:02d}.md"
        suffix += 1
    return target, f"{node}-{stamp}" + ("" if suffix == 2 else f"-{suffix - 1:02d}")


def main() -> int:
    parser = argparse.ArgumentParser(description="generate an Independent Reviewer packet draft")
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--node", choices=NODES, required=True)
    parser.add_argument("--out", type=Path, help="output file; defaults to <case>/reviews/packets/")
    args = parser.parse_args()

    if args.out is not None:
        target, review_id = args.out, _review_id(args.node)
    else:
        directory = args.case_dir / "reviews" / "packets"
        directory.mkdir(parents=True, exist_ok=True)
        target, review_id = _unique_target(directory, args.node)

    packet = build_packet(args.case_dir, args.node, review_id=review_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(packet, encoding="utf-8")

    incomplete = "packet_complete: false" in packet
    print(f"WROTE {target}")
    if incomplete:
        print("注意：审核包标记为不完整，缺失证据已列在文件开头；不要把「未提供」当成「已通过」。")
    if "## 附件清单" in packet:
        print("注意：本包不是单文件自包含，请按文末附件清单一并提供材料。")
    print("下一步：补完「最担心的问题」和 3–5 个问题，再在全新会话中交给独立审核者。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
