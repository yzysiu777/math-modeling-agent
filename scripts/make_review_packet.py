"""Generate one compact, round-trip review card for C1/C2/C3."""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path

import yaml

try:
    from .case_sources import SourceConfigError, load_sources
except ImportError:  # pragma: no cover
    from case_sources import SourceConfigError, load_sources


NODES = ("C1", "C2", "C3")
STATEMENT_NAME = re.compile(r"题面|题目|原题|statement|problem", re.IGNORECASE)
DATA_ROOT_FIELD = re.compile(r"data_root\s*[:：]\s*`?(?P<path>/[^`\n]+)`?", re.IGNORECASE)
PROSE_DATA_ROOT = re.compile(r"(?:数据根|原始数据)[^\n]*?`(?P<path>/[^`]+)`")
DOC_SUFFIXES = {".doc", ".docx", ".pdf", ".txt"}
TXT_DOC_HINT = re.compile(r"说明|格式|字段|字典|指南|手册|readme|guide|manual|spec", re.IGNORECASE)
# 只认填了唯一值的行。空白卡自带占位行 `GO | GO_WITH_FIXES | STOP`，
# 只匹配字段名的话，卡一生成就被当成已通过。
NODE_DECISION = re.compile(
    r"^[ \t]*Node\s+decision[ \t]*[:：][ \t]*(GO|GO_WITH_FIXES|STOP)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)


def node_decision(text: str) -> str | None:
    """The decision actually filled into a review card, or None."""

    match = NODE_DECISION.search(text)
    return match.group(1).upper() if match else None


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
    """Read ``sources.yaml`` first, then support legacy cases without it."""

    if (case_dir / "sources.yaml").is_file():
        try:
            return list(load_sources(case_dir).data_roots)
        except SourceConfigError:
            return []

    roots: list[Path] = []
    for source in (case_dir / "input/README.md", case_dir / "case_brief.md"):
        text = _read(source)
        for pattern in (DATA_ROOT_FIELD, PROSE_DATA_ROOT):
            for match in pattern.finditer(text):
                candidate = Path(match.group("path").strip().rstrip("/"))
                if candidate.is_absolute() and candidate.is_dir():
                    roots.append(candidate.resolve())
    return list(dict.fromkeys(roots))


def _active_question(case_dir: Path) -> str | None:
    try:
        payload = yaml.safe_load((case_dir / "checkpoint.yaml").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError):
        return None
    value = str(payload.get("current_question", "")).strip().casefold() if isinstance(payload, dict) else ""
    return value if re.fullmatch(r"q[1-9][0-9]*", value) else None


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


def _new_node_materials(
    case_dir: Path, node: str, question: str | None
) -> tuple[list[tuple[str, str]], list[str]]:
    """``question is None`` means the whole-case C3, which spans every question."""

    missing: list[str] = []
    materials: list[tuple[str, str]] = []
    try:
        sources = load_sources(case_dir)
    except SourceConfigError as exc:
        return [], [f"sources.yaml 无效：{exc}"]

    work_dir = (case_dir / question) if question else case_dir
    if node == "C1":
        materials.append(("原始题面（先读）", str(sources.statement.resolve())))
        for path, label in (
            (case_dir / "input/题面全文.md", "阶段 0 题面转写与来源行"),
            (work_dir / "brief.md", "待挑战的本题 brief（后读）"),
            (work_dir / "数据范围.md", "本题数据白名单"),
        ):
            if path.is_file():
                materials.append((label, _relative_or_absolute(path, case_dir)))
            else:
                missing.append(f"{_relative_or_absolute(path, case_dir)} 不存在；先运行 ingest")
        for path in _safe_files(case_dir / "input/说明文档"):
            materials.append(("阶段 0 转写的说明文档", _relative_or_absolute(path, case_dir)))
        for root in sources.data_roots:
            materials.append(("获准原始数据根（只读）", str(root)))
        for path in _explanation_docs(list(sources.data_roots)):
            materials.append(("原始说明文件", str(path)))
    elif node == "C2":
        for path, label in (
            (work_dir / "brief.md", "路线、七维度与 Champion"),
            (work_dir / "board.md", "Probe 与赛马结果"),
        ):
            if path.is_file():
                materials.append((label, _relative_or_absolute(path, case_dir)))
            else:
                missing.append(f"{_relative_or_absolute(path, case_dir)} 不存在")
        specs = sorted((work_dir / "specs").glob("SPEC-*.md"))
        if not specs:
            missing.append(f"{question}/specs/ 没有 Full SPEC")
        materials.extend(
            ("Full SPEC", _relative_or_absolute(path, case_dir))
            for path in specs if not path.name.endswith(".questions.md")
        )
        # 队员原话：「c2 审核是需要根据当时代码状态来调整审核或者思考方向的」。
        # 只给规格和实验板，审核者看不到实现与规格是否真的对得上。
        entries = [
            path for pattern in ("code/python/*.py", "code/matlab/*.m")
            for path in sorted(work_dir.glob(pattern))
        ]
        if not entries:
            missing.append(f"{question}/code/ 没有可审的实现")
        materials.extend(
            ("当前实现代码", _relative_or_absolute(path, case_dir)) for path in entries
        )
        materials.extend(
            ("已落盘复算报告", _relative_or_absolute(path, case_dir))
            for path in sorted((work_dir / "outputs/checks").glob("*.json"))
        )
    else:
        claim_map = case_dir / "paper/claim_map.md"
        if claim_map.is_file():
            materials.append(("全案例关键 Claim", "paper/claim_map.md"))
        else:
            missing.append("paper/claim_map.md 不存在")
        # C3 挑战的是论文里的强结论，没有正文就只能看着数字猜它被写成了什么。
        sections = sorted((case_dir / "paper/sections").glob("*.tex"))
        sections += sorted((case_dir / "paper/appendix").glob("*.tex"))
        if not sections:
            missing.append("paper/sections/ 没有正文")
        materials.extend(
            ("论文正文", _relative_or_absolute(path, case_dir)) for path in sections
        )
        registry = case_dir / "paper/文献清单.md"
        if registry.is_file():
            materials.append(("文献清单（核对引用是否可追）", "paper/文献清单.md"))
        # 给了题号就只看那一题；全案例收官那次才跨题。
        scope = [question] if question else list(sources.questions)
        for qname in scope:
            qdir = case_dir / qname
            board = qdir / "board.md"
            if board.is_file():
                materials.append((f"{qname.upper()} 实验板", _relative_or_absolute(board, case_dir)))
            for directory, label in (
                (qdir / "outputs/data", "结果数据"),
                (qdir / "outputs/checks", "复算报告"),
                (qdir / "outputs/figures", "图表"),
            ):
                materials.extend(
                    (f"{qname.upper()} {label}", _relative_or_absolute(path, case_dir))
                    for path in sorted(directory.glob("*")) if path.is_file()
                )
    return materials, missing


def _node_materials(
    case_dir: Path, node: str, question: str | None = None
) -> tuple[list[tuple[str, str]], list[str]]:
    if (case_dir / "sources.yaml").is_file():
        # 全案例收官的 C3 不属于任何一题，question 保持 None 让材料跨题；
        # 其余节点都必须落到具体一题。
        if node == "C3" and question is None:
            return _new_node_materials(case_dir, node, None)
        active = question or _active_question(case_dir)
        if not active:
            return [], ["checkpoint.yaml 缺少 current_question"]
        return _new_node_materials(case_dir, node, active)

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
            (case_dir / "outputs/figures/manifest.md", "图表清单"),
        ):
            if path.is_file():
                materials.append((label, _relative_or_absolute(path, case_dir)))
            else:
                missing.append(f"{_relative_or_absolute(path, case_dir)} 不存在")
        for directory, label in (
            (case_dir / "outputs/data", "结果数据"),
            (case_dir / "outputs/checks", "复算报告"),
        ):
            for path in sorted(directory.glob("*")):
                if path.is_file() and path.name != "README.md":
                    materials.append((label, _relative_or_absolute(path, case_dir)))

    return materials, missing


def build_packet(
    case_dir: Path, node: str, review_id: str | None = None, question: str | None = None
) -> str:
    if node not in NODES:
        raise ValueError(f"node must be one of {list(NODES)}")
    if not case_dir.is_dir():
        raise FileNotFoundError(f"case directory does not exist: {case_dir}")

    # C3 分两层：不给题号就是全案例收官那次，必须跨题，不能被 checkpoint 的
    # current_question 悄悄收窄成一题 —— 那样「全案例 C3」永远只审了一道题。
    if question is None and node != "C3":
        question = _active_question(case_dir)
    materials, missing = _node_materials(case_dir, node, question)
    review_id = review_id or f"{node}-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    ready = "true" if not missing else "false"
    lines = [
        f"# Independent Reviewer {node} 轻量审核卡：{review_id}",
        "",
        "本卡由 Orchestrator 生成、队员人工交给新的独立审核会话，是唯一详细审核记录。",
        "",
        "```yaml",
        f"case_id: {case_dir.name}",
        "reviewer_provider: <实际 provider>",
        "reviewer_model: <实际 model 或 human>",
        "review_session: fresh",
        "saw_main_conversation: false",
        f"critical_node: {node}",
        f"question: {question or ('全案例' if node == 'C3' else 'legacy')}",
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
        "推荐动作：<唯一动作>",
        "推荐理由：",
        "次优项：",
        "默认执行",
        "",
        "Supplementary observations: 超过五条的只在这里列一行清单。",
        "",
        "Recommended route: <C1 必填；其他节点可 n/a>",
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


def _append_review_index(
    case_dir: Path, target: Path, node: str, question: str | None
) -> bool:
    """Append pointer metadata only; never copy review-card content."""

    index = case_dir / "队员工作区/审核卡索引.md"
    if not index.is_file():
        return False
    try:
        pointer = target.resolve().relative_to(case_dir.resolve()).as_posix()
    except ValueError:
        pointer = str(target.resolve())
    scope = "全案例" if node == "C3" else (question or "未指定").upper()
    row = (
        f"| {node} | {scope} | `{pointer}` | "
        "待 Reviewer 填写 | 待 Reviewer 填写 | 否 |\n"
    )
    with index.open("a", encoding="utf-8") as handle:
        handle.write(row)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="generate one compact review card")
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--node", choices=NODES, required=True)
    parser.add_argument("--question")
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
        question = args.question or _active_question(args.case_dir)
        if (args.case_dir / "sources.yaml").is_file():
            # C3 分两层：给了 --question 就是该题那次，落 q<k>/reviews/；
            # 不给才是全案例收官那次，落 paper/reviews/。检查器按同样的规则找卡，
            # 两边不一致会让人以为审过了而检查器仍说没有。
            directory = (
                args.case_dir / f"{question}/reviews" if question
                else args.case_dir / "paper/reviews"
            )
        else:
            directory = args.case_dir / "reviews"
        target, review_id = _unique_target(directory, args.node)
    target.parent.mkdir(parents=True, exist_ok=True)
    card = build_packet(args.case_dir, args.node, review_id, args.question)
    target.write_text(card, encoding="utf-8")
    question = args.question or _active_question(args.case_dir)
    indexed = _append_review_index(args.case_dir, target, args.node, question)
    print(f"WROTE {target}")
    if indexed:
        print(f"INDEXED {args.case_dir / '队员工作区/审核卡索引.md'}")
    print(f"SIZE {len(card.encode('utf-8'))} bytes")
    if "card_ready: false" in card:
        print("注意：材料不完整，先补齐再交给 Reviewer。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
