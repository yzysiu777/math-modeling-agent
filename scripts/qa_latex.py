"""Static, build-output and final-submission QA for the LaTeX paper."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

try:
    from .experiment_board import parse_markdown_table
except ImportError:  # pragma: no cover
    from experiment_board import parse_markdown_table


DRAFT_PLACEHOLDERS = re.compile(r"\b(?:TODO|FIXME)\b|待补充|未验证")
FINAL_PLACEHOLDERS = re.compile(r"\b(?:TODO|FIXME)\b|待补充|未验证|待填写|待替换")
PAPER_EXAMPLE = re.compile(r"\\paperexample\s*\{")
OVERFULL = re.compile(r"Overfull \\[hv]box \(([0-9.]+)pt too (?:wide|high)\)")
INCOMPLETE_CONDITIONAL = re.compile(r"\\end occurred when \\if\w+ .* was incomplete")
PROFILE_VALUE = re.compile(
    r"\\newcommand\{\\(?P<name>PaperOfficialYear|PaperOfficialFrozen)\}\{(?P<value>[^{}]+)\}"
)
IDENTITY_VALUE = re.compile(
    r"\\(?:baominghao|schoolname|membera|memberb|memberc)\{(?P<value>[^{}]+)\}"
)


def _tex_sources(paper_dir: Path) -> list[Path]:
    paths = [paper_dir / "main.tex"]
    for directory in ("config", "sections", "appendix", "tables"):
        paths.extend(sorted((paper_dir / directory).glob("*.tex")))
    return paths


def _without_tex_comments(text: str) -> str:
    """Remove unescaped TeX comments before checking user-visible placeholders."""
    cleaned: list[str] = []
    for line in text.splitlines():
        match = re.search(r"(?<!\\)%", line)
        cleaned.append(line[:match.start()] if match else line)
    return "\n".join(cleaned)


def _profile_values(paper_dir: Path) -> dict[str, str]:
    path = paper_dir / "config/paper-profile.tex"
    if not path.is_file():
        return {}
    return {
        match.group("name"): match.group("value").strip()
        for match in PROFILE_VALUE.finditer(path.read_text(encoding="utf-8"))
    }


def _identity_values(paper_dir: Path) -> list[str]:
    path = paper_dir / "config/paper-profile.tex"
    if not path.is_file():
        return []
    values = [
        match.group("value").strip()
        for match in IDENTITY_VALUE.finditer(path.read_text(encoding="utf-8"))
    ]
    return [
        value for value in values
        if len(value) >= 2 and not FINAL_PLACEHOLDERS.search(value)
    ]


def _official_freeze_errors(paper_dir: Path) -> list[str]:
    values = _profile_values(paper_dir)
    year = values.get("PaperOfficialYear", "")
    frozen = values.get("PaperOfficialFrozen", "").casefold()
    errors: list[str] = []
    if not re.fullmatch(r"20\d{2}", year):
        errors.append("paper profile missing a valid PaperOfficialYear")
        return errors
    if frozen != "true":
        errors.append("PaperOfficialFrozen must be true for final submission")
    manifest = paper_dir / f"official/{year}/manifest.yaml"
    try:
        payload = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        errors.append(f"active official manifest is unavailable: {manifest} ({exc})")
        return errors
    if not isinstance(payload, dict) or payload.get("active") is not True:
        errors.append(f"official manifest is not active: {manifest}")
    if isinstance(payload, dict) and str(payload.get("year", "")) != year:
        errors.append(f"official manifest year does not match paper profile: {manifest}")
    status = str(payload.get("status", "")).casefold() if isinstance(payload, dict) else ""
    if "pending" in status:
        errors.append(f"official manifest is still pending: {manifest}")
    return errors


# 论文正文里不该出现的工作台内部符号。第三次实测的 q1.tex 里 `EXP-` 出现 23 次、
# 六位小数 21 处，末尾整整一段是脚本路径和命令行 —— 溯源机制漏进了交付物。
# 溯源留在案例的关键数字溯源表里，正文只写论文该有的东西。
PROSE_BANS = (
    (re.compile(r"EXP-[A-Za-z0-9][A-Za-z0-9_-]*"), "实验编号"),
    (re.compile(r"[\w\u4e00-\u9fff\-]+\.(?:py|csv|json|ya?ml|md|txt|log)\b"), "文件名"),
    (re.compile(r"\bq[1-9][0-9]*/|\boutputs/|\bcode/(?:python|matlab)|\bexperiments/"), "工作台目录"),
    (re.compile(r"\\path\s*\{"), r"\path 宏"),
    (re.compile(r"(?<![\w-])--[a-z][a-z-]{2,}"), "命令行参数"),
    (re.compile(r"\b(?:BLOCK|REMINDER|CLAIM_[A-Z_]+|SPEC-[A-Z0-9])"), "检查器或规格编号"),
    (re.compile(r"claim_map|checkpoint\.yaml|probe_result|board\.md|队员工作区"), "工作台词汇"),
    (re.compile(r"\d\.\d{5,}"), "超过四位有效数字"),
)
NON_PROSE_ARGUMENT = re.compile(
    r"\\(?:includegraphics(?:\[[^\]]*\])?|label|ref|eqref|cite|dataref)\{[^}]*\}"
)
INCLUDE_GRAPHICS = re.compile(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}")
PLACEHOLDER_FIGURE = re.compile(r"\\PlaceholderFigure(?:\[[^\]]*\])?\{")
FIGURE_LABEL = re.compile(r"\\label\{(fig:[^}]+)\}")


def _strip_paperexample(text: str) -> str:
    """Drop \\paperexample{...} blocks: template guidance is not prose."""

    out: list[str] = []
    index = 0
    while True:
        match = PAPER_EXAMPLE.search(text, index)
        if match is None:
            out.append(text[index:])
            return "".join(out)
        out.append(text[index:match.start()])
        depth, cursor = 1, match.end()
        while cursor < len(text) and depth:
            char = text[cursor]
            if char == "{" and text[cursor - 1] != "\\":
                depth += 1
            elif char == "}" and text[cursor - 1] != "\\":
                depth -= 1
            cursor += 1
        index = cursor


CITE = re.compile(r"\\cite[tp]?(?:\[[^\]]*\])?\{([^}]+)\}")
BIB_ENTRY = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,")
BIB_PLACEHOLDER = re.compile(r"待替换|待填写|placeholder")
EVIDENCE_SECTIONS = ("01-background.tex", "04-analysis.tex")


def _cited_keys(paper_dir: Path) -> dict[str, list[str]]:
    """Map citation key -> the section files that use it."""

    found: dict[str, list[str]] = {}
    for path in sorted((paper_dir / "sections").glob("*.tex")) + sorted(
        (paper_dir / "appendix").glob("*.tex")
    ):
        text = _strip_paperexample(_without_tex_comments(path.read_text(encoding="utf-8")))
        for group in CITE.findall(text):
            for key in (item.strip() for item in group.split(",")):
                if key:
                    found.setdefault(key, []).append(path.name)
    return found


def _registry_rows(paper_dir: Path) -> list[dict[str, str]]:
    path = paper_dir / "文献清单.md"
    if not path.is_file():
        return []
    return [
        row for row in parse_markdown_table(path.read_text(encoding="utf-8"))
        if str(row.get("key", "")).strip() and str(row.get("key", "")).strip() != "key"
    ]


def check_citations(paper_dir: Path, *, final: bool = False) -> list[str]:
    """Every citation must be traceable to the registry the team verifies.

    The v2 paper cited nothing at all while asserting a page of external facts.
    The fix is not to judge whether a reference is good -- that is the team's
    call -- but to make an unverifiable citation impossible to leave in place.
    """

    problems: list[str] = []
    cited = _cited_keys(paper_dir)
    rows = _registry_rows(paper_dir)
    registered = {str(row.get("key", "")).strip(): row for row in rows}

    bib = paper_dir / "bibliography/references.bib"
    bib_text = bib.read_text(encoding="utf-8") if bib.is_file() else ""
    bib_keys = set(BIB_ENTRY.findall(bib_text))

    for key, where in cited.items():
        places = "、".join(dict.fromkeys(where))
        if key not in registered:
            problems.append(f"{places}: 引用 {key} 不在 文献清单.md 中，疑似编造")
        if key not in bib_keys:
            problems.append(f"{places}: 引用 {key} 在 references.bib 中没有条目")

    if final and BIB_PLACEHOLDER.search(bib_text):
        problems.append("references.bib 仍含占位条目")
    return problems


def check_citation_verification(paper_dir: Path) -> list[str]:
    """The team's own reading list -- reported, never blocking.

    Whether a reference is real and whether it actually supports the sentence it
    is attached to are judgements only a person can make. Holding the build
    hostage to that judgement stops the work without improving it, so this comes
    back as a reminder at every stage; the mechanical half (a citation with no
    registry row, no bib entry, or a placeholder entry) stays strict.
    """

    reminders: list[str] = []
    for row in _registry_rows(paper_dir):
        key = str(row.get("key", "")).strip()
        status = str(row.get("核对状态", "")).strip()
        if status != "已核对":
            reminders.append(f"文献清单.md: {key} 待你核对（状态「{status or '空'}」）")
        support = str(row.get("支撑论断", "")).strip().strip("-")
        if not support or "待填写" in support:
            reminders.append(f"文献清单.md: {key} 没有写清它支撑正文哪一处论断")
    return reminders


def check_evidence_citations(paper_dir: Path) -> list[str]:
    """Sections that assert external facts should carry sources."""

    reminders: list[str] = []
    for name in EVIDENCE_SECTIONS:
        path = paper_dir / "sections" / name
        if not path.is_file():
            continue
        text = _strip_paperexample(_without_tex_comments(path.read_text(encoding="utf-8")))
        if PAPER_EXAMPLE.search(path.read_text(encoding="utf-8")):
            continue  # 尚未开写的模板章节不提醒
        if not CITE.search(text):
            reminders.append(f"{name}: 陈述了外部事实却没有任何引用")
    unused = {
        str(row.get("key", "")).strip() for row in _registry_rows(paper_dir)
    } - set(_cited_keys(paper_dir))
    reminders.extend(f"文献清单.md: {key} 登记了但正文没引用" for key in sorted(unused))
    return reminders


SEALED = re.compile(r"%\s*<<Q([1-9][0-9]*)(?:-OUTLOOK)?-SEALED>>")
NODE_DECISION = re.compile(r"^[ \t]*Node\s+decision[ \t]*[:：]", re.IGNORECASE | re.MULTILINE)
LIST_ENVIRONMENT = re.compile(r"\\begin\{(itemize|enumerate|description)\}")
#: 列表只在这三处天然合理：假设逐条、符号成表、程序清单成表。
LIST_ALLOWED = {"05-assumptions.tex", "03-symbols.tex", "99-programs.tex"}
#: 每题正文留一个额度，其余章节一律叙述式。
LIST_BUDGET_PER_QUESTION = 1
CLICHE = re.compile(r"如图所示|如表所示|如下所示|如下图|见下表|如上图|如上表")


def _opened_questions(case_dir: Path) -> set[int]:
    """A question is open once its C1 card carries a node decision."""

    opened: set[int] = set()
    for directory in sorted(case_dir.glob("q[0-9]*")):
        match = re.fullmatch(r"q([1-9][0-9]*)", directory.name)
        reviews = directory / "reviews"
        if match is None or not reviews.is_dir():
            continue
        for path in reviews.glob("C1*.md"):
            if NODE_DECISION.search(path.read_text(encoding="utf-8", errors="replace")):
                opened.add(int(match.group(1)))
                break
    return opened


def _block_is_substantive(text: str) -> bool:
    """Template guidance and placeholder figures are not content."""

    body = _strip_paperexample(text)
    body = re.sub(r"\\begin\{figure\}.*?\\end\{figure\}", "", body, flags=re.DOTALL)
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%"):
            continue
        if stripped.startswith("\\subsection") or stripped.startswith("\\section"):
            continue
        return True
    return False


def check_sealed_questions(paper_dir: Path) -> list[str]:
    """A question's sections stay sealed until that question has passed C1.

    The v2 paper wrote the full technical route for questions two and three --
    grid resolutions, model names, a search algorithm -- while neither question
    had a brief, a route comparison or a review. Routes have to come out of a
    question's own A step, not be guessed in another question's D step.
    """

    problems: list[str] = []
    opened = _opened_questions(paper_dir.parent)
    for path in sorted((paper_dir / "sections").glob("*.tex")):
        text = path.read_text(encoding="utf-8")
        marks = list(SEALED.finditer(text))
        sealed_here = {int(match.group(1)) for match in marks}
        for match in marks:
            number = int(match.group(1))
            if number in opened:
                continue
            # 从哨兵所在行的行尾开始，否则该行 `>>` 之后的说明文字会被当成正文。
            line_end = text.find("\n", match.end())
            tail = text[line_end + 1:] if line_end != -1 else ""
            stop = re.search(r"\n\\(?:sub)*section\{|\n%\s*<<Q", tail)
            block = tail[:stop.start()] if stop else tail
            if _block_is_substantive(block):
                problems.append(
                    f"{path.name}: 问题 {number} 尚未通过 C1，本小节不得写入实质内容")
        # 哨兵被整段删掉同样要抓：该题没开工，章节里却出现了它的小节。
        for number in range(1, 10):
            if number in opened or number in sealed_here:
                continue
            heading = re.search(rf"\\subsection\{{问题{'一二三四五六七八九'[number - 1]}[^}}]*\}}", text)
            if heading is not None:
                problems.append(
                    f"{path.name}: 问题 {number} 的封存标记被删除，但该题尚未通过 C1")
    return problems


def check_prose_style(paper_dir: Path) -> list[str]:
    """Lists and stock phrases are how a paper turns into a slide deck.

    The reference award paper carries 8 bullet lines across 110 pages; v2 carried
    32 across 23 -- a 21x density. Lists are allowed only where enumeration is
    the natural form.
    """

    problems: list[str] = []
    for path in sorted((paper_dir / "sections").glob("*.tex")) + sorted(
        (paper_dir / "appendix").glob("*.tex")
    ):
        text = _strip_paperexample(_without_tex_comments(path.read_text(encoding="utf-8")))
        lists = LIST_ENVIRONMENT.findall(text)
        if path.name not in LIST_ALLOWED:
            budget = LIST_BUDGET_PER_QUESTION if re.fullmatch(r"q[0-9]+\.tex", path.name) else 0
            if len(lists) > budget:
                problems.append(
                    f"{path.name}: 用了 {len(lists)} 个列表环境，上限 {budget} —— "
                    "本章应当叙述式行文")
        for number, line in enumerate(text.splitlines(), start=1):
            hit = CLICHE.search(line)
            if hit:
                problems.append(
                    f"{path.name}:{number} 套话「{hit.group(0)}」—— "
                    "要写清这张图或这张表说明了什么")
    return problems


def check_paper_prose(paper_dir: Path) -> list[str]:
    """Report workbench artefacts that leaked into the paper body."""

    problems: list[str] = []
    for path in sorted((paper_dir / "sections").glob("*.tex")):
        text = _strip_paperexample(_without_tex_comments(path.read_text(encoding="utf-8")))
        # 只查读者看得见的文字。图片路径、标签和引用键不会印进 PDF，
        # 用工作台命名不影响论文可读性。
        text = NON_PROSE_ARGUMENT.sub("", text)
        for number, line in enumerate(text.splitlines(), start=1):
            for pattern, label in PROSE_BANS:
                found = pattern.search(line)
                if found:
                    problems.append(
                        f"{path.name}:{number} 正文出现{label}「{found.group(0)}」："
                        f"{line.strip()[:60]}"
                    )
                    break
    return problems


def check_figures(paper_dir: Path, *, final: bool = False) -> list[str]:
    """Placeholder figures must be registered, and final figures must be vector."""

    problems: list[str] = []
    registry = paper_dir.parent / "队员工作区/待补图清单.md"
    registered = registry.read_text(encoding="utf-8") if registry.is_file() else ""
    for path in sorted((paper_dir / "sections").glob("*.tex")):
        text = _without_tex_comments(path.read_text(encoding="utf-8"))
        for block in re.split(r"\\begin\{figure\}", text)[1:]:
            body = block.split("\\end{figure}")[0]
            if not PLACEHOLDER_FIGURE.search(body):
                continue
            label = FIGURE_LABEL.search(body)
            name = label.group(1) if label else path.name
            if final:
                problems.append(f"{path.name}: 提交稿仍有占位图 {name}")
            elif not registry.is_file():
                problems.append(f"{path.name}: 有占位图 {name}，但缺少 队员工作区/待补图清单.md")
            elif label and label.group(1) not in registered:
                problems.append(f"{path.name}: 占位图 {name} 未登记在待补图清单中")
        for reference in INCLUDE_GRAPHICS.findall(_strip_paperexample(text)):
            target = paper_dir / reference
            if target.suffix:
                candidates = [target]
            else:
                candidates = [target.with_suffix(item) for item in (".pdf", ".png", ".jpg", ".eps")]
            if not any(item.is_file() for item in candidates):
                problems.append(f"{path.name}: 引用了不存在的图 {reference}")
                continue
            if final and not target.with_suffix(".pdf").is_file():
                problems.append(f"{path.name}: 提交稿要求矢量图，缺少 {target.with_suffix('.pdf').name}")
    return problems


def check_sources(paper_dir: Path, *, final: bool = False) -> list[str]:
    errors: list[str] = []
    # 案例论文只放自己的内容，文档类、样式、bst 和封面图经 TEXINPUTS 从仓库
    # paper/ 解析。缺少 gmcmthesis.cls 即判定为案例工程，不再强求那几份共享文件。
    inherited = not (paper_dir / "gmcmthesis.cls").is_file()
    required = [
        paper_dir / "main.tex",
        paper_dir / "config/paper-profile.tex",
        paper_dir / "bibliography/references.bib",
    ]
    if not inherited:
        required += [
            paper_dir / "style/modeling-paper.sty",
            paper_dir / "gmcmthesis.cls",
            paper_dir / "gmcm.bst",
            paper_dir / "figures/logo.pdf",
            paper_dir / "figures/title.pdf",
        ]
    for path in required:
        if not path.exists():
            errors.append(f"missing required LaTeX file: {path}")
    placeholder_pattern = FINAL_PLACEHOLDERS if final else DRAFT_PLACEHOLDERS
    for path in _tex_sources(paper_dir):
        if not path.is_file():
            continue
        text = _without_tex_comments(path.read_text(encoding="utf-8"))
        if placeholder_pattern.search(text):
            errors.append(f"placeholder found in paper source: {path}")
        if final and PAPER_EXAMPLE.search(text):
            errors.append(f"paperexample found in final paper source: {path}")
    main_path = paper_dir / "main.tex"
    main_text = main_path.read_text(encoding="utf-8") if main_path.is_file() else ""
    for marker in (
        "{gmcmthesis}", "\\maketitle", "\\pagestyle{plain}", "\\keywords",
        "\\bibliographystyle{gmcm}", "\\bibliography{",
    ):
        if marker not in main_text:
            errors.append(f"main.tex missing required marker: {marker}")
    if not sorted((paper_dir / "sections").glob("*.tex")):
        errors.append("no section files under sections/; the split structure is required")
    errors.extend(check_figures(paper_dir, final=final))
    errors.extend(check_citations(paper_dir, final=final))
    errors.extend(check_sealed_questions(paper_dir))
    if final:
        errors.extend(check_prose_style(paper_dir))
        errors.extend(_official_freeze_errors(paper_dir))
        errors.extend(check_paper_prose(paper_dir))
    return errors


def _pdf_layout_errors(pdf: Path, paper_dir: Path) -> list[str]:
    result = subprocess.run(
        ["pdftotext", "-bbox-layout", str(pdf), "-"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return [f"pdftotext -bbox-layout failed: {result.stderr.strip()}"]
    try:
        root = ET.fromstring(result.stdout)
    except ET.ParseError as exc:
        return [f"unable to parse PDF layout: {exc}"]
    pages = [item for item in root.iter() if item.tag.endswith("page")]
    errors: list[str] = []
    for index, page in enumerate(pages):
        width = float(page.attrib.get("width", "0"))
        height = float(page.attrib.get("height", "0"))
        words = [item for item in page.iter() if item.tag.endswith("word")]
        if index >= 2:
            header_words = [
                (word.text or "").strip() for word in words
                if float(word.attrib.get("yMin", "999")) < 70 and (word.text or "").strip()
            ]
            if header_words:
                errors.append(
                    f"header-like text found on PDF page {index + 1}: {''.join(header_words[:12])}"
                )
        if index >= 1:
            expected = str(index)
            footer_number = any(
                (word.text or "").strip() == expected
                and float(word.attrib.get("yMin", "0")) > height - 65
                and abs(
                    (float(word.attrib.get("xMin", "0")) + float(word.attrib.get("xMax", "0"))) / 2
                    - width / 2
                ) < 40
                for word in words
            )
            if not footer_number:
                errors.append(
                    f"PDF page {index + 1} is missing centered footer page number {expected}"
                )

    text_result = subprocess.run(
        ["pdftotext", "-layout", str(pdf), "-"],
        text=True,
        capture_output=True,
        check=False,
    )
    if text_result.returncode == 0:
        body = "\n".join(text_result.stdout.split("\f")[1:])
        for token in _identity_values(paper_dir):
            if token in body:
                errors.append(f"identity token appears after cover: {token}")
    return errors


def check_build(build_dir: Path, paper_dir: Path, *, final: bool = False) -> list[str]:
    errors: list[str] = []
    pdf = build_dir / "main.pdf"
    if not pdf.exists() or pdf.stat().st_size < 1000:
        return [f"missing or abnormally small PDF: {pdf}"]
    log_path = build_dir / "main.log"
    for suffix in (".log", ".aux"):
        path = build_dir / f"main{suffix}"
        if path.exists():
            text = path.read_text(encoding="utf-8", errors="replace")
            if "undefined references" in text.lower() or "undefined citations" in text.lower():
                errors.append(f"unresolved references or citations in {path}")
    if log_path.is_file():
        log = log_path.read_text(encoding="utf-8", errors="replace")
        if INCOMPLETE_CONDITIONAL.search(log):
            errors.append(f"incomplete TeX conditional in {log_path}")
        if final:
            widths = [float(value) for value in OVERFULL.findall(log) if float(value) > 2.0]
            if widths:
                errors.append(
                    f"overfull box exceeds 2pt in {log_path}: max={max(widths):.2f}pt"
                )
    if shutil.which("pdftotext"):
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf), "-"],
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"pdftotext failed: {result.stderr.strip()}")
        else:
            for marker in ("摘要", "关键词", "参考文献"):
                if marker not in result.stdout:
                    errors.append(f"PDF text missing marker: {marker}")
        if final:
            errors.extend(_pdf_layout_errors(pdf, paper_dir))
    elif final:
        errors.append("pdftotext is required for final PDF layout checks")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--paper-dir", type=Path, default=Path("paper"))
    parser.add_argument("--build-dir", type=Path, default=Path("paper/build"))
    parser.add_argument("--final", action="store_true", help="enforce submission-only checks")
    args = parser.parse_args()
    errors = check_sources(args.paper_dir, final=args.final) + check_build(
        args.build_dir, args.paper_dir, final=args.final
    )
    if not args.final:
        # 草稿阶段只提醒：正文还在改，不该因为一处遗留的实验编号挡住编译流程。
        reminders = (
            check_paper_prose(args.paper_dir)
            + check_evidence_citations(args.paper_dir)
            + check_prose_style(args.paper_dir)
            + check_citation_verification(args.paper_dir)
        )
        if reminders:
            print("REMINDER 正文问题（提交前必须清干净）")
            print("\n".join(f"- {item}" for item in reminders))
    if args.final:
        # 提交前也只提醒：核对是队员的事，脚本不替他判断，也不因此拦住流程。
        pending = check_citation_verification(args.paper_dir)
        if pending:
            print("REMINDER 文献待人工核对（不阻断）")
            print("\n".join(f"- {item}" for item in pending))
    if errors:
        print("FAIL LaTeX QA")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS final LaTeX QA" if args.final else "PASS LaTeX QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
