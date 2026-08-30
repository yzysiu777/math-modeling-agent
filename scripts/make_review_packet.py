"""Generate one compact, round-trip review card for C1/C2/C3."""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path


NODES = ("C1", "C2", "C3")
STATEMENT_NAME = re.compile(r"题面|题目|原题|statement|problem", re.IGNORECASE)
DATA_ROOT_FIELD = re.compile(r"data_root\s*[:：]\s*`?(?P<path>/[^`\n]+)`?", re.IGNORECASE)
PROSE_DATA_ROOT = re.compile(r"(?:数据根|原始数据)[^\n]*?`(?P<path>/[^`]+)`")
DOC_SUFFIXES = {".doc", ".docx", ".pdf", ".txt"}
TXT_DOC_HINT = re.compile(r"说明|格式|字段|字典|指南|手册|readme|guide|manual|spec", re.IGNORECASE)


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _safe_files(root: Path) -> list[Path]:
    if not root.is_dir():
        return []
    base = root.resolve()
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if path.is_file() and (resolved == base or base in resolved.parents):
            found.append(path)
    return found


def _data_roots(case_dir: Path) -> list[Path]:
    """Read explicit data_root fields and the two historical prose forms."""

    roots: list[Path] = []
    for source in (case_dir / "input/README.md", case_dir / "case_brief.md"):
        text = _read(source)
        for pattern in (DATA_ROOT_FIELD, PROSE_DATA_ROOT):
            for match in pattern.finditer(text):
                candidate = Path(match.group("path").strip().rstrip("/"))
                if candidate.is_absolute() and candidate.is_dir():
                    roots.append(candidate.resolve())
    return list(dict.fromkeys(roots))


def _explanation_docs(roots: list[Path]) -> list[Path]:
    """Find direct explanation files beside an allowed data root.

    Direct-child scanning is intentional: it finds official format documents
    beside question folders without recursively walking every competition file.
    """

    found: list[Path] = []
    for root in roots:
        for directory in (root, root.parent):
            try:
                children = sorted(directory.iterdir())
            except OSError:
                continue
            for path in children:
                if not path.is_file() or path.suffix.casefold() not in DOC_SUFFIXES:
                    continue
                if path.suffix.casefold() == ".txt" and not TXT_DOC_HINT.search(path.name):
                    continue
                found.append(path.resolve())
    return list(dict.fromkeys(found))


def _relative_or_absolute(path: Path, case_dir: Path) -> str:
    try:
        return str(path.relative_to(case_dir))
    except ValueError:
        return str(path)


def _node_materials(case_dir: Path, node: str) -> tuple[list[tuple[str, str]], list[str]]:
    missing: list[str] = []
    materials: list[tuple[str, str]] = []

    if node == "C1":
        input_files = _safe_files(case_dir / "input")
        statements = [path for path in input_files if STATEMENT_NAME.search(path.name)]
        if not statements:
            missing.append("input/ 中没有可识别的原题全文")
        for path in statements:
            materials.append(("原题（先读）", _relative_or_absolute(path, case_dir)))
        brief = case_dir / "case_brief.md"
        if brief.is_file():
            materials.append(("待挑战的题意重构（后读）", "case_brief.md"))
        else:
            missing.append("case_brief.md 不存在")
        for path in input_files:
            if path not in statements and path.name != "README.md":
                materials.append(("案例内说明/字段材料", _relative_or_absolute(path, case_dir)))
        roots = _data_roots(case_dir)
        if not roots:
            missing.append("未找到获准数据根；请在 input/README.md 写 data_root: /absolute/path")
        for root in roots:
            materials.append(("获准原始数据根（只读）", str(root)))
        for path in _explanation_docs(roots):
            materials.append(("数据根或父目录的题目说明文件", str(path)))
    elif node == "C2":
        for path, label in (
            (case_dir / "models/candidates.md", "路线与七维度比较"),
            (case_dir / "experiments/board.md", "Probe 与赛马结果"),
        ):
            if path.is_file():
                materials.append((label, _relative_or_absolute(path, case_dir)))
            else:
                missing.append(f"{path.name} 不存在")
        specs = sorted((case_dir / "specs").glob("SPEC-*.md"))
        if not specs:
            missing.append("没有 Full SPEC")
        for path in specs:
            if not path.name.endswith(".questions.md"):
                materials.append(("Full SPEC", _relative_or_absolute(path, case_dir)))
    else:
        for path, label in (
            (case_dir / "paper/claim_map.md", "关键 Claim"),
            (case_dir / "experiments/board.md", "实验板"),
            (case_dir / "experiments/outputs/figures/manifest.md", "图表清单"),
        ):
            if path.is_file():
                materials.append((label, _relative_or_absolute(path, case_dir)))
            else:
                missing.append(f"{_relative_or_absolute(path, case_dir)} 不存在")
        for directory, label in (
            (case_dir / "experiments/outputs/data", "结果数据"),
            (case_dir / "experiments/outputs/checks", "复算报告"),
        ):
            for path in sorted(directory.glob("*")):
                if path.is_file() and path.name != "README.md":
                    materials.append((label, _relative_or_absolute(path, case_dir)))

    return materials, missing


def build_packet(case_dir: Path, node: str, review_id: str | None = None) -> str:
    if node not in NODES:
        raise ValueError(f"node must be one of {list(NODES)}")
    if not case_dir.is_dir():
        raise FileNotFoundError(f"case directory does not exist: {case_dir}")

    materials, missing = _node_materials(case_dir, node)
    review_id = review_id or f"{node}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    ready = "true" if not missing else "false"
    lines = [
        f"# {node} 轻量审核卡：{review_id}",
        "",
        "本卡既是审核输入也是唯一详细记录。不要另建 packet、报告或交接副本。",
        "",
        "```yaml",
        f"case_id: {case_dir.name}",
        "reviewer_provider:",
        "reviewer_model:",
        "review_session: fresh",
        "saw_main_conversation: false",
        f"critical_node: {node}",
        f"card_ready: {ready}",
        "```",
        "",
        "## 允许读取或上传的材料",
        "",
    ]
    lines.extend(f"- {label}：`{path}`" for label, path in materials)
    if missing:
        lines += ["", "## 缺失材料", "", *(f"- {item}" for item in missing)]
    lines += [
        "",
        "## 当前最担心的问题",
        "",
        "- 待主 Agent 填写一条。",
        "",
        "## 希望回答的问题",
        "",
        "1. 待填写。",
        "2. 待填写。",
        "3. 待填写。",
        "",
        "## Reviewer 输出",
        "",
        "What was checked:",
        "",
        "Top findings: 最多五条展开；每条写严重度、证据、影响、最小动作。",
        "",
        "Supplementary observations: 超过五条的只在这里列一行清单。",
        "",
        "Node decision: GO | GO_WITH_FIXES | STOP",
        "",
        "Actions and owners:",
        "",
        "Human-only block: none",
        "",
        "What was not checked:",
        "",
        "Uncertainty:",
        "",
        "## 拒绝 finding 时的唯一往返",
        "",
        "Rejected finding:",
        "",
        "Reason and evidence:",
        "",
        "Requested reviewer sign-back:",
        "",
        "Reviewer sign-back: ACCEPT_REJECTION | REJECT_REJECTION",
        "",
    ]
    return "\n".join(lines)


def _unique_target(directory: Path, node: str) -> tuple[Path, str]:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    review_id = f"{node}-{stamp}"
    target = directory / f"{node}_{stamp}.md"
    suffix = 2
    while target.exists():
        target = directory / f"{node}_{stamp}-{suffix:02d}.md"
        review_id = f"{node}-{stamp}-{suffix:02d}"
        suffix += 1
    return target, review_id


def main() -> int:
    parser = argparse.ArgumentParser(description="generate one compact review card")
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--node", choices=NODES, required=True)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    if args.out is not None:
        if args.out.exists() and not args.force:
            print(f"FAIL 目标文件已存在：{args.out}")
            return 1
        target = args.out
        review_id = f"{args.node}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    else:
        target, review_id = _unique_target(args.case_dir / "reviews", args.node)
    target.parent.mkdir(parents=True, exist_ok=True)
    card = build_packet(args.case_dir, args.node, review_id)
    target.write_text(card, encoding="utf-8")
    print(f"WROTE {target}")
    print(f"SIZE {len(card.encode('utf-8'))} bytes")
    if "card_ready: false" in card:
        print("注意：材料不完整，先补齐再交给 Reviewer。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
