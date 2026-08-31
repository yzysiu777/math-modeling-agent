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


@dataclass(frozen=True)
class ExtractedText:
    text: str
    tool: str
    source_bytes: int
    source_text_chars: int
    sources: tuple[Path, ...]


def _decode(data: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "big5", "latin-1"):
        try:
            return data.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace"


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


def _write_statement(case_dir: Path, extracted: ExtractedText) -> Path:
    problem = excerpt_problem(extracted.source_text_chars, len(extracted.text))
    if problem:
        raise RuntimeError(problem)
    sources = "；".join(str(path.resolve()) for path in extracted.sources)
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


def _write_docs(case_dir: Path, docs: Iterable[Path]) -> list[str]:
    directory = case_dir / "input/说明文档"
    directory.mkdir(parents=True, exist_ok=True)
    texts: list[str] = []
    used: set[str] = set()
    for source in docs:
        target = directory / _safe_doc_name(source, used)
        try:
            text, tool = _extract_file(source)
            body = (
                f"> 原路径：{source.resolve()}\n> 转写工具：{tool}\n"
                f"> 源字节数：{source.stat().st_size}\n\n{text.rstrip()}\n"
            )
            texts.append(text)
        except Exception as exc:  # noqa: BLE001
            body = (
                f"> 原路径：{source.resolve()}\n\n"
                f"**未转写，需人工打开**：{exc}\n"
            )
        target.write_text(body, encoding="utf-8")
    return texts


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
    return "[" + ", ".join(columns) + "]", encoding, ", ".join(missing) if missing else "未发现"


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
    missing = ", ".join(sorted(missing_values)) if missing_values else "未发现"
    return "; ".join(summaries), "; ".join(row_counts), "xlsx/xml", missing


def _markdown_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


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


def _write_inventory(case_dir: Path, sources: CaseSources, doc_texts: list[str]) -> Path:
    lines = [
        "# 数据清单",
        "",
        "数据保持原位只读；列名不截断。无内嵌表头的文本记录使用 `col_n`，并在下方列出说明文档中的字段声明。",
        "",
        "| 数据根 | 相对路径 | 字节数 | 行数 | 列名全量 | 编码 | 缺测标记候选值 |",
        "|---|---|---:|---:|---|---|---|",
    ]
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
        cells = (
            root.name, relative, path.stat().st_size, row_count, columns, encoding, missing
        )
        lines.append("| " + " | ".join(_markdown_cell(cell) for cell in cells) + " |")
    declarations = _field_declarations(doc_texts)
    lines.extend(["", "## 说明文档中的字段声明", ""])
    lines.extend(f"- {item}" for item in declarations)
    if not declarations:
        lines.append("- 未自动识别；请打开 `input/说明文档/` 核对无表头记录。")
    target = case_dir / "input/数据清单.md"
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
            *(f"- `{path}`" for path in allowed),
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
    doc_texts = _write_docs(case_dir, _auto_docs(sources))
    inventory = _write_inventory(case_dir, sources, doc_texts)
    return [statement, inventory, *_write_scopes(case_dir, sources)]


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
