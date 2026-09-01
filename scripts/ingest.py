"""Stage 0: ingest statement metadata, explanation docs and a data inventory."""

from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree

try:
    from .case_sources import CaseSources, SourceConfigError, load_sources
except ImportError:  # pragma: no cover
    from case_sources import CaseSources, SourceConfigError, load_sources


DOCUMENT_SUFFIXES = {".doc", ".docx", ".pdf"}
STATEMENT_SUFFIXES = DOCUMENT_SUFFIXES | {".md", ".txt"}
TEXT_DATA_SUFFIXES = {".csv", ".tsv", ".txt"}
DOC_TEXT_HINT = re.compile(r"说明|格式|字段|字典|指南|手册|readme|guide|manual|spec", re.IGNORECASE)
MISSING_TOKENS = {"", "na", "n/a", "nan", "null", "none", "-9999", "9999", "9999.0", "/"}
PROVENANCE_LINE = re.compile(r"^> (?P<label>[^：]+)：(?P<value>.*)$")
REQUIRED_PROVENANCE = ("来源绝对路径", "源文本层字符数", "抽取后字符数")


@dataclass(frozen=True)
class ExtractedText:
    text: str
    tool: str
    source_bytes: int
    source_text_chars: int
    sources: tuple[Path, ...]


@dataclass(frozen=True)
class DataObservation:
    root: Path
    path: Path
    relative: Path
    size: int
    row_count: int | str
    columns: str
    encoding: str
    missing: str


def _decode(data: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "big5", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


def _display_path(case_dir: Path, path: Path) -> str:
    candidate = path if path.is_absolute() else case_dir / path
    try:
        rel = candidate.resolve().relative_to(case_dir.resolve())
        return rel.as_posix()
    except (ValueError, RuntimeError):
        return str(candidate.resolve())


def _run_text_tool(command: list[str], tool: str) -> str:
    process = subprocess.run(command, text=False, capture_output=True, check=False)
    if process.returncode != 0:
        detail, _ = _decode(process.stderr)
        raise RuntimeError(f"{tool} 失败：{detail.strip() or 'unknown error'}")
    text, _ = _decode(process.stdout)
    return text


def _extract_file(path: Path) -> tuple[str, str]:
    suffix = path.suffix.casefold()
    if suffix in {".md", ".txt"}:
        text, encoding = _decode(path.read_bytes())
        return text, f"builtin-text/{encoding}"
    if suffix == ".pdf":
        executable = shutil.which("pdftotext")
        if not executable:
            raise RuntimeError("未找到 pdftotext")
        return _run_text_tool([executable, "-layout", str(path), "-"], "pdftotext"), "pdftotext -layout"
    if suffix in {".doc", ".docx"}:
        executable = shutil.which("textutil")
        if not executable:
            raise RuntimeError("未找到 textutil")
        return _run_text_tool([executable, "-convert", "txt", "-stdout", str(path)], "textutil"), "textutil"
    raise RuntimeError(f"不支持的文档格式：{path.suffix or '[无扩展名]'}")


def _statement_files(statement: Path) -> list[Path]:
    if statement.is_file():
        return [statement]
    candidates = sorted(
        path for path in statement.rglob("*")
        if path.is_file() and path.suffix.casefold() in STATEMENT_SUFFIXES
    )
    named = [
        path for path in candidates
        if re.search(r"题面|题目|原题|statement|problem", path.name, re.IGNORECASE)
    ]
    return named or candidates


def _extract_statement(statement: Path) -> ExtractedText:
    files = _statement_files(statement)
    if not files:
        raise RuntimeError(f"statement 目录中没有可抽取文档：{statement}")
    parts: list[str] = []
    tools: list[str] = []
    source_text_chars = 0
    for path in files:
        text, tool = _extract_file(path)
        if path.suffix.casefold() == ".pdf":
            executable = shutil.which("pdftotext")
            raw_text = _run_text_tool([executable, "-raw", str(path), "-"], "pdftotext") if executable else text
            source_text_chars += len(raw_text.strip())
        else:
            source_text_chars += len(text.strip())
        parts.append(text.strip())
        tools.append(tool)
    combined = "\n\n".join(part for part in parts if part).strip()
    return ExtractedText(
        combined,
        "+".join(dict.fromkeys(tools)),
        sum(path.stat().st_size for path in files),
        source_text_chars,
        tuple(files),
    )


def excerpt_problem(source_text_chars: int, extracted_chars: int) -> str:
    """Return an error when an extract is far shorter than the source text layer."""

    if source_text_chars >= 200 and extracted_chars < source_text_chars * 0.5:
        return (
            "题面疑似摘录："
            f"源文本层 {source_text_chars} 字符，抽取后仅 {extracted_chars} 字符"
        )
    return ""


def statement_provenance_problem(path: Path) -> str:
    """题面文件不可信时返回一句话原因，可信时返回空串。"""

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return "题面不是阶段 0 生成的，无法确认是全文而非摘录"

    lines = text.splitlines()
    provenance: dict[str, str] = {}
    body_start = 0
    for index, line in enumerate(lines):
        match = PROVENANCE_LINE.fullmatch(line)
        if match is None:
            body_start = index
            break
        provenance[match.group("label").strip()] = match.group("value").strip()
    else:
        body_start = len(lines)

    if any(not provenance.get(label) for label in REQUIRED_PROVENANCE):
        return "题面不是阶段 0 生成的，无法确认是全文而非摘录"
    try:
        source_chars = int(provenance["源文本层字符数"])
        declared_chars = int(provenance["抽取后字符数"])
    except ValueError:
        return "题面不是阶段 0 生成的，无法确认是全文而非摘录"

    body = "\n".join(lines[body_start:]).lstrip("\n").rstrip()
    actual_chars = len(body)
    if declared_chars != actual_chars:
        return "题面在阶段 0 之后被改写"
    return excerpt_problem(source_chars, actual_chars)


def _write_statement(case_dir: Path, extracted: ExtractedText) -> Path:
    problem = excerpt_problem(extracted.source_text_chars, len(extracted.text))
    if problem:
        raise RuntimeError(problem)
    sources = "；".join(_display_path(case_dir, path) for path in extracted.sources)
    header = (
        f"> 来源绝对路径：{sources}\n"
        f"> 源字节数：{extracted.source_bytes}\n"
        f"> 抽取工具：{extracted.tool}\n"
        f"> 源文本层字符数：{extracted.source_text_chars}\n"
        f"> 抽取后字符数：{len(extracted.text)}\n\n"
    )
    target = case_dir / "input/题面全文.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(header + extracted.text.rstrip() + "\n", encoding="utf-8")
    return target


def _auto_docs(sources: CaseSources) -> list[Path]:
    if sources.docs:
        return list(sources.docs)
    found: list[Path] = []
    for root in sources.data_roots:
        for directory in (root, root.parent):
            try:
                children = sorted(directory.iterdir())
            except OSError:
                continue
            for path in children:
                suffix = path.suffix.casefold()
                if not path.is_file():
                    continue
                if suffix in DOCUMENT_SUFFIXES or (suffix == ".txt" and DOC_TEXT_HINT.search(path.name)):
                    found.append(path.resolve())
    return list(dict.fromkeys(found))


def _safe_doc_name(path: Path, used: set[str]) -> str:
    stem = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff_-]+", "_", path.stem).strip("_") or "说明文档"
    name = f"{stem}.md"
    index = 2
    while name.casefold() in used:
        name = f"{stem}-{index}.md"
        index += 1
    used.add(name.casefold())
    return name


def _write_docs(case_dir: Path, docs: Iterable[Path]) -> tuple[list[str], list[Path]]:
    directory = case_dir / "input/说明文档"
    directory.mkdir(parents=True, exist_ok=True)
    texts: list[str] = []
    untranscribed: list[Path] = []
    used: set[str] = set()
    for source in docs:
        target = directory / _safe_doc_name(source, used)
        try:
            text, tool = _extract_file(source)
            body = (
                f"> 原路径：{_display_path(case_dir, source)}\n> 转写工具：{tool}\n"
                f"> 源字节数：{source.stat().st_size}\n\n{text.rstrip()}\n"
            )
            texts.append(text)
        except Exception as exc:  # noqa: BLE001
            untranscribed.append(source.resolve())
            body = (
                f"> 原路径：{_display_path(case_dir, source)}\n\n"
                f"**未转写，需人工打开**：{exc}\n"
            )
        target.write_text(body, encoding="utf-8")
    return texts, untranscribed


def _count_lines(path: Path) -> int:
    count = 0
    last = b""
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8 * 1024 * 1024)
            if not chunk:
                break
            count += chunk.count(b"\n")
            last = chunk[-1:]
    return count + (1 if path.stat().st_size and last not in {b"\n", b"\r"} else 0)


def _columns_and_missing(path: Path) -> tuple[str, str, str]:
    if path.suffix.casefold() not in TEXT_DATA_SUFFIXES:
        return "n/a（非文本表格）", "n/a", "n/a"
    with path.open("rb") as handle:
        sample = handle.read(256 * 1024)
    text, encoding = _decode(sample)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return "[]", encoding, "空文件"
    first = lines[0]
    delimiter: str | None = None
    try:
        delimiter = csv.Sniffer().sniff("\n".join(lines[:20]), delimiters=",;\t|").delimiter
    except csv.Error:
        delimiter = None
    if delimiter:
        columns = next(csv.reader([first], delimiter=delimiter))
    else:
        columns = re.split(r"\s+", first)
    if len(columns) <= 1 or all(re.fullmatch(r"[-+0-9.eE/]+", item or "") for item in columns):
        data_line = next((line for line in lines[1:] if len(re.split(r"\s+", line)) > 1), first)
        width = len(re.split(r"\s+", data_line))
        columns = [f"col_{index}" for index in range(1, width + 1)]
        marker = next((line for line in lines[:10] if re.fullmatch(r"[A-Z][A-Z0-9_ -]+", line)), "")
        if marker:
            columns.append(f"record_marker={marker}")
    values = re.split(r"[,;\t|\s]+", "\n".join(lines[:200]).casefold())
    missing = sorted({value for value in values if value in MISSING_TOKENS})
    rendered_missing = ["<空字符串>" if value == "" else value for value in missing]
    return (
        "[" + ", ".join(columns) + "]",
        encoding,
        ", ".join(rendered_missing) if rendered_missing else "未发现",
    )


def _xlsx_profile(path: Path) -> tuple[str, str, str, str]:
    """Read every worksheet's first non-empty row without third-party packages."""

    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    rel_ns = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}
    office_rel = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    with zipfile.ZipFile(path) as archive:
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            for item in root.findall("m:si", ns):
                shared.append("".join(node.text or "" for node in item.iterfind(".//m:t", ns)))

        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        targets = {
            node.attrib["Id"]: node.attrib["Target"]
            for node in relationships.findall("r:Relationship", rel_ns)
        }
        summaries: list[str] = []
        row_counts: list[str] = []
        missing_values: set[str] = set()
        for sheet in workbook.findall("m:sheets/m:sheet", ns):
            name = sheet.attrib.get("name", "sheet")
            target = targets.get(sheet.attrib.get(office_rel, ""), "")
            member = target.lstrip("/")
            if not member.startswith("xl/"):
                member = f"xl/{member}"
            root = ElementTree.fromstring(archive.read(member))
            rows = root.findall("m:sheetData/m:row", ns)
            max_row = max((int(row.attrib.get("r", "0")) for row in rows), default=0)
            row_counts.append(f"{name}={max_row}")
            header: list[str] = []
            sampled = 0
            for row in rows:
                values: list[str] = []
                for cell in row.findall("m:c", ns):
                    kind = cell.attrib.get("t", "")
                    value = cell.findtext("m:v", default="", namespaces=ns)
                    if kind == "s" and value.isdigit() and int(value) < len(shared):
                        value = shared[int(value)]
                    elif kind == "inlineStr":
                        value = "".join(node.text or "" for node in cell.iterfind(".//m:t", ns))
                    values.append(value)
                    if sampled < 200 and value.strip().casefold() in MISSING_TOKENS:
                        missing_values.add(value.strip())
                    sampled += 1
                if not header and any(value.strip() for value in values):
                    header = values
            summaries.append(f"{name}=[{', '.join(header)}]")
    missing = (
        ", ".join("<空字符串>" if value == "" else value for value in sorted(missing_values))
        if missing_values else "未发现"
    )
    return "; ".join(summaries), "; ".join(row_counts), "xlsx/xml", missing


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _human_size(size: int) -> str:
    """Render bytes for a human; 11043129126 tells nobody anything."""

    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{int(value)} B" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} GB"


def _row_span(counts: list[object]) -> str:
    numbers = [item for item in counts if isinstance(item, int)]
    if not numbers:
        return "、".join(dict.fromkeys(str(item) for item in counts)) or "n/a"
    low, high = min(numbers), max(numbers)
    return str(low) if low == high else f"{low}–{high}"


def _data_files(sources: CaseSources) -> Iterable[tuple[Path, Path]]:
    seen: set[Path] = set()
    for root in sources.data_roots:
        for path in sorted(root.rglob("*")):
            if not path.is_file() or path.name == ".DS_Store":
                continue
            resolved = path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield root, path


def _field_declarations(doc_texts: Iterable[str]) -> list[str]:
    found: list[str] = []
    declaration_hint = re.compile(r"字段|列名|各列|依次为|包括|包含")
    for text in doc_texts:
        for line in text.splitlines():
            compact = " ".join(line.split())
            if not compact:
                continue
            if declaration_hint.search(compact) and len(compact) <= 320:
                found.append(compact)
    return list(dict.fromkeys(found))


def _write_inventory(
    case_dir: Path, sources: CaseSources, doc_texts: list[str]
) -> tuple[Path, list[DataObservation]]:
    observations: list[DataObservation] = []
    for root, path in _data_files(sources):
        relative = path.relative_to(root)
        if path.suffix.casefold() == ".xlsx":
            try:
                columns, row_count, encoding, missing = _xlsx_profile(path)
            except (OSError, KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
                columns, row_count, encoding, missing = "无法读取工作表", "n/a", "xlsx", str(exc)
        else:
            columns, encoding, missing = _columns_and_missing(path)
            row_count = _count_lines(path) if path.suffix.casefold() in TEXT_DATA_SUFFIXES else "n/a"
        observations.append(DataObservation(
            root=root,
            path=path.resolve(),
            relative=relative,
            size=path.stat().st_size,
            row_count=row_count,
            columns=columns,
            encoding=encoding,
            missing=missing,
        ))

    # 一套列结构只完整打印一次。上千个雷达文件共用同一组一千多列的表头，逐文件
    # 重复会把清单撑到十几 MB —— 建模手读不进去的清单等于没有清单。分组保住了
    # 「每一种不同的列集合都完整出现」这条保证：漏掉某一列仍然不可能。
    signatures: dict[str, str] = {}
    groups: dict[tuple[str, str, str, str, str], list[DataObservation]] = {}
    for item in observations:
        if item.columns not in signatures:
            signatures[item.columns] = f"C{len(signatures) + 1:02d}"
        directory = item.relative.parent.as_posix()
        key = (item.root.name, "." if directory == "." else directory,
               signatures[item.columns], item.encoding, item.missing)
        groups.setdefault(key, []).append(item)

    lines = [
        "# 数据清单",
        "",
        "数据保持原位只读。按「目录 × 列结构」分组：同一目录下列结构相同的文件合并成一行，"
        "每一种列结构在下方 `## 列结构` 中完整列出一次，不截断。",
        "",
        "| 数据根 | 目录 | 文件数 | 合计大小 | 行数 | 列结构 | 编码 | 缺测标记候选值 |",
        "|---|---|---:|---:|---|---|---|---|",
    ]
    for (root_name, directory, signature, encoding, missing), items in groups.items():
        cells = (
            root_name, directory, len(items),
            _human_size(sum(entry.size for entry in items)),
            _row_span([entry.row_count for entry in items]),
            signature, encoding, missing,
        )
        lines.append("| " + " | ".join(_markdown_cell(cell) for cell in cells) + " |")

    lines.extend(["", "## 列结构", ""])
    counts: dict[str, list[DataObservation]] = {}
    for item in observations:
        counts.setdefault(signatures[item.columns], []).append(item)
    for columns, signature in signatures.items():
        members = counts[signature]
        example = members[0]
        lines.extend([
            f"### {signature} —— {len(members)} 个文件，例如 "
            f"`{example.root.name}/{example.relative.as_posix()}`",
            "",
            _markdown_cell(columns),
            "",
        ])

    declarations = _field_declarations(doc_texts)
    lines.extend(["## 说明文档中的字段声明", ""])
    lines.extend(f"- {item}" for item in declarations)
    if not declarations:
        lines.append("- 未自动识别；请打开 `input/说明文档/` 核对无表头记录。")
    target = case_dir / "input/数据清单.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target, observations


def _duplicate_columns(columns: str) -> bool:
    """Detect repeated header labels without copying those labels to the scout."""

    groups = re.findall(r"\[([^\]]*)\]", columns)
    for group in groups:
        names = [item.strip().casefold() for item in group.split(",")]
        names = [item for item in names if item and not item.startswith("record_marker=")]
        if len(names) != len(set(names)):
            return True
    return False


def _zero_rows(value: int | str) -> bool:
    if isinstance(value, int):
        return value == 0
    counts = [int(item) for item in re.findall(r"(?:^|=)([0-9]+)(?:$|;)", value)]
    return bool(counts) and any(item == 0 for item in counts)


def _scope_label(observation: DataObservation, sources: CaseSources) -> str:
    relative = observation.relative.as_posix().strip("/")
    for question, scope in sources.questions.items():
        normalized = scope.strip("/")
        if relative == normalized or relative.startswith(f"{normalized}/"):
            return question.upper()
    for scope in sources.shared:
        normalized = scope.strip("/")
        if relative == normalized or relative.startswith(f"{normalized}/"):
            return "共享"
    return "未映射"


def _write_scout(
    case_dir: Path,
    sources: CaseSources,
    observations: list[DataObservation],
    untranscribed: list[Path],
) -> Path:
    """Write human-decision anomalies only; never mirror the data inventory."""

    # 同一种异常逐文件列一行，在真实赛题数据上会变成几百行 —— 那就不是速览了。
    # 按异常种类聚合，给出计数和最多三个例子，队员一屏能读完。
    found: dict[str, list[str]] = {}
    def note(label: str, where: str) -> None:
        found.setdefault(label, []).append(where)

    for path in untranscribed:
        note("未能转写，需人工打开", _display_path(case_dir, path))
    for item in observations:
        location = f"{item.root.name}/{item.relative.as_posix()}"
        if item.encoding not in {"utf-8", "utf-8-sig", "xlsx/xml", "n/a"}:
            note(f"非 UTF-8 编码（{item.encoding}）", location)
        if item.size == 0 or _zero_rows(item.row_count):
            note("空文件或零行文件", location)
        if _duplicate_columns(item.columns):
            note("列名重复，需人工确认字段语义", location)
        if "col_" in item.columns:
            note("疑似无表头，需结合说明文档确认字段", location)
        if item.missing not in {"", "未发现", "n/a", "空文件"}:
            note(f"缺测标记候选值 {item.missing}", location)

    issues: list[str] = []
    for label, places in found.items():
        examples = "、".join(f"`{item}`" for item in places[:3])
        if len(places) <= 3:
            issues.append(f"- {label} —— {examples}")
        else:
            issues.append(
                f"- {label} —— {len(places)} 个文件，例如 {examples} 等"
                "（完整名单见 `input/数据清单.md` 同列结构分组）"
            )

    distribution: dict[str, int] = {}
    for item in observations:
        label = _scope_label(item, sources)
        distribution[label] = distribution.get(label, 0) + 1
    distribution_text = "、".join(
        f"{label} {count} 个" for label, count in sorted(distribution.items())
    ) or "无数据文件"
    total_size = sum(item.size for item in observations)
    lines = [
        "# 数据踏勘速览",
        "",
        "> 本文件由阶段 0 生成，只列需要队员判断的异常；完整清单见 `input/数据清单.md`。",
        "",
        "## 需要人工判断",
        "",
    ]
    if issues:
        lines.extend(issues)
    else:
        lines.append("未发现异常：未发现需要人工判断的异常。")
    lines.extend([
        "",
        "## 总计",
        "",
        f"- 文件数：{len(observations)}；总大小：{_human_size(total_size)}；按题分布：{distribution_text}。",
    ])
    target = case_dir / "队员工作区/数据踏勘速览.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return target


def _scope_paths(root: Path, values: Iterable[str]) -> list[Path]:
    return [candidate.resolve() for value in values if (candidate := root / value).exists()]


def _write_scopes(case_dir: Path, sources: CaseSources) -> list[Path]:
    written: list[Path] = []
    for question, relative in sources.questions.items():
        allowed: list[Path] = []
        for root in sources.data_roots:
            allowed.extend(_scope_paths(root, (relative, *sources.shared)))
        allowed = list(dict.fromkeys(allowed))
        lines = [
            f"# {question.upper()} 数据范围",
            "",
            "以下绝对路径是本题可读白名单；原始数据只读。后续题可引用前题 outputs，反向不允许。",
            "",
            *(f"- `{_display_path(case_dir, path)}`" for path in allowed),
        ]
        if not allowed:
            lines.append("- 未找到映射目录；需核对 sources.yaml。")
        target = case_dir / question / "数据范围.md"
        target.write_text("\n".join(lines) + "\n", encoding="utf-8")
        written.append(target)
    return written


def ingest_case(case_dir: Path) -> list[Path]:
    sources = load_sources(case_dir)
    statement = _write_statement(case_dir, _extract_statement(sources.statement))
    doc_texts, untranscribed = _write_docs(case_dir, _auto_docs(sources))
    inventory, observations = _write_inventory(case_dir, sources, doc_texts)
    scout = _write_scout(case_dir, sources, observations, untranscribed)
    return [statement, inventory, scout, *_write_scopes(case_dir, sources)]


def main() -> int:
    parser = argparse.ArgumentParser(description="run one-time Stage 0 ingestion")
    parser.add_argument("--case-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        written = ingest_case(args.case_dir)
    except (SourceConfigError, OSError, RuntimeError, ValueError) as exc:
        print(f"FAIL ingest: {exc}")
        return 1
    for path in written:
        print(f"WROTE {path}")
    print(f"PASS ingest: {args.case_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
