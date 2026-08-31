"""Static, build-output and final-submission QA for the LaTeX paper."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


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


def check_sources(paper_dir: Path, *, final: bool = False) -> list[str]:
    errors: list[str] = []
    required = [
        paper_dir / "main.tex",
        paper_dir / "config/paper-profile.tex",
        paper_dir / "style/modeling-paper.sty",
        paper_dir / "bibliography/references.bib",
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
    if final:
        errors.extend(_official_freeze_errors(paper_dir))
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
    if errors:
        print("FAIL LaTeX QA")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print("PASS final LaTeX QA" if args.final else "PASS LaTeX QA")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
