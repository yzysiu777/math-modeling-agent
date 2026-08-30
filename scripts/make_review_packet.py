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

try:
    from .case_paths import clean_reference, contained_in, is_traversal, resolve_in_case
    from .claim_evidence import (board_experiment_ids, describe_missing_source,
                                 failed_checks, parse_source_experiment,
                                 validate_check_report)
except ImportError:  # pragma: no cover - direct script execution
    from case_paths import clean_reference, contained_in, is_traversal, resolve_in_case
    from claim_evidence import (board_experiment_ids, describe_missing_source,
                                failed_checks, parse_source_experiment,
                                validate_check_report)

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


#: 文件名里出现这些词，才认为它自称是题面。刻意不靠扩展名判断 ——
#: 一份 nodes.csv 是附件数据，不是题面。
_STATEMENT_NAME = re.compile(r"题面|题目|原题|statement|problem", re.IGNORECASE)
#: `input/README.md` 里同时出现文件名和这些词时，视为显式声明该文件是题面。
_STATEMENT_ROLE = re.compile(r"题面|题目|原题|statement|problem", re.IGNORECASE)
#: 自称是摘录的文件不能充当 C1 的题面依据 —— C1 要核的正是「主解有没有转述走样」，
#: 拿主解自己的摘录去核对，等于让它审自己。实测中真的发生过：1347 字符的
#: 「本次范围摘录」被当成题面，包还报 packet_complete: true。
_STATEMENT_IS_DIGEST = re.compile(
    r"摘录|摘要|节选|概要|本次范围|范围说明|summary|excerpt|abridged", re.IGNORECASE
)
#: 原件常见格式。存在原件却只提供文本转写时，无法确认转写是全文还是节选。
_SOURCE_DOCUMENT_SUFFIXES = frozenset({".pdf", ".doc", ".docx", ".rtf", ".odt"})


def _declared_statements(case_dir: Path) -> set[str]:
    """Read file roles declared in ``input/README.md``."""

    readme = case_dir / "input/README.md"
    if not readme.is_file():
        return set()
    declared: set[str] = set()
    for line in _read(readme).splitlines():
        if not _STATEMENT_ROLE.search(line):
            continue
        for token in re.findall(r"[\w.\u4e00-\u9fff-]+\.[A-Za-z0-9]{1,8}", line):
            declared.add(token.casefold())
    return declared


def _add_problem_evidence(packet: Packet, case_dir: Path) -> None:
    """Give C1 the original statement, not only the Modeler's reading of it.

    C1 exists to check that the case brief is faithful to the problem, so the
    brief cannot be its own evidence.  Data attachments cannot stand in for the
    statement either: a table of coordinates says nothing about what is being
    asked, and deciding "is this CSV the statement?" from its extension would be
    guessing.  A file counts as statement evidence only when it says so -- by
    name, or by being declared in ``input/README.md``.
    """

    input_dir = case_dir / "input"
    files: list[Path] = []
    rejected: list[Path] = []
    if input_dir.is_dir():
        for path in sorted(input_dir.rglob("*"), key=lambda item: item.name):
            if path.name == "README.md":
                continue
            # 目录项是发现来的而不是填写的，符号链接同样不得把案例外内容带进包里
            if contained_in(input_dir, path) is None or not path.is_file():
                if path.is_symlink() or path.is_file():
                    rejected.append(path)
                continue
            files.append(path)

    for path in rejected:
        packet.absent(
            f"`input/{path.relative_to(input_dir)}` 指向案例目录之外（符号链接越界），"
            "已拒绝读取；请改为放入真实文件或在包外另行提供")

    if not files:
        packet.absent(
            "`input/` 下没有题面或附件 —— C1 只能看到建模手转述的题意，"
            "**无法核对题意是否忠实于原题**"
        )
        return

    declared = _declared_statements(case_dir)
    statements = [
        path for path in files
        if _STATEMENT_NAME.search(path.name) or path.name.casefold() in declared
    ]
    attachments = [path for path in files if path not in statements]

    packet.add("### 原始输入清单（`input/`）", "")
    for path in files:
        role = "题面依据" if path in statements else "数据附件"
        packet.add(f"- `{path.relative_to(case_dir)}`（{role}，{path.stat().st_size} 字节）")
    for path in rejected:
        packet.add(f"- `input/{path.relative_to(input_dir)}`（**已拒绝：指向案例目录之外**）")
    packet.add("")

    if not statements:
        packet.absent(
            "`input/` 下只有数据附件，没有可识别的题面 —— 数据表不能替代题面，"
            "C1 无法核对题意是否忠实于原题。请把题面文件放入 `input/`，"
            "文件名含「题面/题目/statement」，或在 `input/README.md` 中标注它的角色"
        )

    excerpted = False
    for path in statements:
        if path.suffix.casefold() not in _TEXT_SUFFIXES:
            packet.attach(f"`{path.relative_to(case_dir)}`（题面，非文本格式，需随包一并提供）")
            continue
        text = _read(path)
        if not text:
            continue
        # 自称摘录的文件不是题面依据。只查开头 —— 摘录通常在开头就声明范围。
        digest = _STATEMENT_IS_DIGEST.search(text[:400])
        if digest is not None:
            packet.absent(
                f"`{path.relative_to(case_dir)}` 自称「{digest.group(0)}」，是转述而非原题全文；"
                "C1 要核的正是转述有没有走样，拿转述当依据等于让主解审自己。"
                "请提供原题全文的完整转写"
            )
            continue
        if len(text) > _INPUT_EXCERPT_CHARS:
            packet.attach(f"`{path.relative_to(case_dir)}`（题面已截断，审核前请提供完整文件）")
        packet.section(f"原题材料：{path.name}", text, str(path.relative_to(case_dir)))
        excerpted = True

    if statements and not excerpted:
        packet.absent("题面文件不是可摘录的文本格式，审核者必须另行拿到原题")

    # 存在 PDF/DOC 原件却只给文本转写时，无法确认转写是全文还是节选。
    originals = [path for path in files
                 if path.suffix.casefold() in _SOURCE_DOCUMENT_SUFFIXES]
    text_statements = [path for path in statements
                       if path.suffix.casefold() in _TEXT_SUFFIXES]
    if originals and text_statements:
        packet.add(
            "> **注意**：`input/` 中同时存在原件（"
            + "、".join(f"`{path.name}`" for path in originals[:3])
            + "）与文本转写。审核者应确认转写覆盖了原题全文，而不是节选。",
            "",
        )

    for path in attachments[:5]:
        if path.suffix.casefold() not in _TEXT_SUFFIXES:
            packet.attach(f"`{path.relative_to(case_dir)}`（数据附件，需随包一并提供）")
            continue
        lines = _read(path).splitlines()
        excerpt = "\n".join(lines[:_DATA_EXCERPT_LINES])
        if len(lines) > _DATA_EXCERPT_LINES:
            excerpt += f"\n[... 共 {len(lines)} 行，已摘录前 {_DATA_EXCERPT_LINES} 行 ...]"
            packet.attach(f"`{path.relative_to(case_dir)}`（完整数据附件）")
        packet.section(f"数据附件片段：{path.name}", excerpt, str(path.relative_to(case_dir)))


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


#: claim_map 表头 -> 归一化字段名，与 check_case.py 保持一致。
_CLAIM_COLUMNS = (
    ("claim_id", ("claim id", "claim", "主张 id")),
    ("statement", ("主张原文", "主张", "statement")),
    ("exp_id", ("exp-id", "exp id", "来源 exp-id", "实验 id")),
    ("data_file", ("数据文件", "data file")),
    ("figure_id", ("图/表 id", "图表 id", "figure", "fig")),
    ("check_report", ("复算报告", "check report")),
)


def _claim_header(cells: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, cell in enumerate(cells):
        normalized = " ".join(cell.casefold().split()).strip("`*")
        for field, keywords in _CLAIM_COLUMNS:
            if field not in mapping and any(keyword in normalized for keyword in keywords):
                mapping[field] = index
                break
    return mapping


def _claim_cell(cells: list[str], header: dict[str, int], field: str) -> str:
    index = header.get(field)
    if index is None or index >= len(cells):
        return ""
    return cells[index].strip().strip("`")


def _add_claim_evidence(packet: Packet, case_dir: Path) -> None:
    """Give C3 each claim together with the evidence that claim itself names.

    Evidence is gathered per claim rather than per directory: an unrelated
    recomputation report sitting in ``checks/`` says nothing about the claim in
    front of the reviewer, so it must not make the packet look complete.
    """

    path = case_dir / "paper/claim_map.md"
    rows = _pipe_rows(_read(path)) if path.is_file() else []
    header: dict[str, int] = {}
    for cells in rows:
        candidate = _claim_header(cells)
        if "claim_id" in candidate and "exp_id" in candidate:
            header = candidate
            break
    claims = [
        cells for cells in rows
        if cells and re.fullmatch(r"`?CLM-[A-Za-z0-9_-]+`?", cells[0].strip(), re.IGNORECASE)
        and any(_has_value(cell) for cell in cells[1:])
    ] if header else []

    if not claims:
        packet.absent("`paper/claim_map.md` 没有已填写的强主张 —— C3 没有可抽查的对象")
        return

    packet.add("### 待审核的论文强主张（`paper/claim_map.md`）", "")
    header_row = next((cells for cells in rows if _claim_header(cells) == header), None)
    if header_row:
        packet.add("| " + " | ".join(header_row) + " |", "|" + "---|" * len(header_row))
    for cells in claims:
        packet.add("| " + " | ".join(cells) + " |")
    packet.add("", "审核者请从中挑 3–5 条风险最高的抽查，不要求逐条复核。", "")

    manifest_rows = _pipe_rows(_read(case_dir / "experiments/outputs/figures/manifest.md")) \
        if (case_dir / "experiments/outputs/figures/manifest.md").is_file() else []
    known_experiments = board_experiment_ids(case_dir)

    for cells in claims:
        claim_id = _claim_cell(cells, header, "claim_id") or cells[0].strip()
        source = parse_source_experiment(_claim_cell(cells, header, "exp_id"))
        exp_id = source.exp_id or ""
        if not source.ok:
            packet.absent(f"{claim_id} 的来源 EXP-ID 无法唯一解析：{source.problem}")
        elif exp_id.casefold() not in known_experiments:
            packet.absent(
                f"{claim_id} 的来源实验不在实验板上："
                f"{describe_missing_source(case_dir, exp_id)}；"
                "审核者无法确认这条主张背后的实验真的跑过")
        data_ref = _claim_cell(cells, header, "data_file")
        report_ref = _claim_cell(cells, header, "check_report")
        figure_ref = _claim_cell(cells, header, "figure_id")

        # --- 数据文件：必须由 claim 自己指名，且落在 outputs/data/ ---
        if not _has_value(data_ref):
            packet.absent(f"{claim_id} 没有填写数据文件，论文数字无处溯源")
        elif is_traversal(data_ref):
            packet.absent(f"{claim_id} 的数据文件引用非法（含 `..` 或绝对路径）：`{data_ref}`")
        else:
            resolved = resolve_in_case(case_dir, data_ref, kind="data")
            if resolved is None:
                packet.absent(
                    f"{claim_id} 的数据文件不存在或不在 `experiments/outputs/data/` 内："
                    f"`{data_ref}`")
            else:
                lines = _read(resolved).splitlines()
                excerpt = "\n".join(lines[:_DATA_EXCERPT_LINES])
                if len(lines) > _DATA_EXCERPT_LINES:
                    excerpt += f"\n[... 共 {len(lines)} 行，已摘录前 {_DATA_EXCERPT_LINES} 行 ...]"
                    packet.attach(f"`{data_ref}`（{claim_id} 的完整数据文件）")
                packet.section(f"{claim_id} 的结果数据片段：{resolved.name}", excerpt, data_ref)

        # --- 复算报告：必须存在、可解析、且 exp_id 与 claim 一致 ---
        if not _has_value(report_ref):
            packet.absent(f"{claim_id} 没有填写复算报告，无法判断该结论是否被独立复算")
        elif is_traversal(report_ref):
            packet.absent(f"{claim_id} 的复算报告引用非法（含 `..` 或绝对路径）：`{report_ref}`")
        else:
            resolved = resolve_in_case(case_dir, report_ref, kind="checks")
            if resolved is None:
                packet.absent(
                    f"{claim_id} 的复算报告不存在或不在 `experiments/outputs/checks/` 内："
                    f"`{report_ref}`")
            else:
                summary = _check_report_summary(resolved, claim_id, exp_id, packet)
                if summary:
                    packet.add(f"### {claim_id} 的复算报告（`{report_ref}`）", "", *summary, "")

        # --- 图：claim 填了才要求 ---
        if _has_value(figure_ref):
            matched = [row for row in manifest_rows
                       if row and figure_ref.casefold() in row[0].casefold()]
            if not matched:
                packet.absent(f"{claim_id} 引用的图 `{figure_ref}` 不在 `figures/manifest.md` 中")
            else:
                packet.add(f"### {claim_id} 的图表清单条目（`{figure_ref}`）", "")
                for row in matched:
                    packet.add("| " + " | ".join(row) + " |")
                packet.add("")
                for ext in ("pdf", "png"):
                    candidate = resolve_in_case(
                        case_dir, f"{clean_reference(figure_ref)}.{ext}", kind="figures")
                    if candidate is not None:
                        packet.attach(
                            f"`{candidate.relative_to(case_dir.resolve())}`（图，需随包一并提供）")


def _check_report_summary(path: Path, claim_id: str, exp_id: str, packet: Packet) -> List[str]:
    """Summarize one recomputation report, refusing it when it does not back this claim.

    Shares :func:`scripts.claim_evidence.validate_check_report` with the case
    checker so the two cannot drift apart again.
    """

    verdict = validate_check_report(path, exp_id or None)
    if not verdict.ok:
        packet.absent(
            f"{claim_id} 的复算报告不能作为证据：{verdict.problem}（`{path.name}`）"
            + ("；别的实验的复算结果不能替这条主张背书" if "不一致" in verdict.problem else ""))
        return []

    failed = failed_checks(path)
    lines = [f"- 共 {len(json.loads(path.read_text(encoding='utf-8'))['checks'])} 项检查，"
             + ("全部通过" if not failed else f"**{len(failed)} 项未通过**")]
    for item in failed:
        lines.append(f"- **未通过** {item.get('kind', '?')} / {item.get('name', '?')}："
                     f"{item.get('detail', '')}")
    return lines


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
        header += [
            "## 审核包完整性",
            "",
            "本节点所需的材料均已包含且与各条 Claim 对应。",
            "",
            "> `packet_complete: true` 只表示**该节点要求的文件存在且互相指得通**，"
            "不表示证据充分、模型正确或审核通过。判断证据够不够，是审核者的工作。",
            "",
        ]

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
    parser.add_argument(
        "--force", action="store_true",
        help="overwrite the file named by --out; without it an existing file is an error",
    )
    args = parser.parse_args()

    if args.out is not None:
        if args.out.exists() and not args.force:
            print(f"FAIL 目标文件已存在：{args.out}")
            print("审核包不静默覆盖。换一个 --out 路径，或明确加 --force。")
            return 1
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
