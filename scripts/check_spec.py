"""Validate lightweight implementation specs handed from the Modeler to the Engineer.

The checker is intentionally syntactic.  It catches missing front-matter, empty
or placeholder sections and invalid enum values, but it cannot decide whether a
model is correct or whether an acceptance criterion is reasonable; that remains
a C2 and human judgment.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

VALID_STATUS = frozenset({"probe", "full"})
VALID_LANGUAGE = frozenset({"python", "matlab"})
#: probe -> full 闭环的判定值。``PENDING`` 表示规格已写但探针尚未跑完 ——
#: 这是合法的中间状态，早期不阻断，但不能带着它进入路线结论或论文强结论。
#: ``WAIVED`` 是人工豁免，必须写明理由。
VALID_PROBE_RESULT = frozenset({"pass", "fail", "pending", "waived"})
#: 闭环已成立的取值；其余取值在强结论阶段会被 check_case.py 阻断。
CLOSED_PROBE_RESULT = frozenset({"pass", "waived"})

_PLACEHOLDERS = frozenset(
    {"", "-", "—", "待填写", "待填", "待补充", "todo", "tbd", "n/a", "n/a。", "无"}
)
_TEMPLATE_TOKEN = re.compile(r"<[^<>]{1,80}>")
_FRONT_MATTER = re.compile(r"^---\s*\n(?P<body>.*?)\n---\s*(?:\n|$)", re.DOTALL)
_FM_LINE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<value>.*?)\s*$")
_HEADING = re.compile(r"^\s*(?P<hashes>#{1,6})\s+(?P<title>.+?)\s*$")

#: Section number -> (identifying keywords, human label).  Matching is by the
#: leading number so a team can rename a heading without breaking the check.
_FULL_SECTIONS: Sequence[tuple[str, str]] = (
    ("1", "目标与判据"),
    ("2", "数学表述"),
    ("3", "数据契约"),
    ("4", "算法"),
    ("5", "输出契约"),
    ("6", "复算要求"),
    ("7", "明确不做"),
    ("8", "未决问题"),
)
_PROBE_SECTIONS: Sequence[tuple[str, str]] = (
    ("1", "要证伪的假设"),
    ("2", "判据"),
    ("3", "最小实例"),
    ("4", "实现要点"),
)
_REQUIRED_FM = ("spec_id", "case_id", "route_id", "subproblem", "method_family", "status", "language")
#: full 规格额外要求的 probe 闭环字段。probe 规格不需要它们。
_PROBE_CLOSURE_FM = ("probe_spec_id", "probe_exp_id", "probe_result")
#: Sections whose emptiness defeats the purpose of the contract.  Section 7 and 8
#: may legitimately be short, and section 8 may say "none" explicitly.
_MUST_HAVE_CONTENT = {"1", "2", "3", "4", "5", "6"}
_PROBE_MUST_HAVE_CONTENT = {"1", "2", "3", "4"}
_NUMERIC = re.compile(r"\d")


@dataclass(frozen=True)
class Spec:
    path: Path
    front_matter: Dict[str, str]
    sections: Dict[str, str]

    @property
    def status(self) -> str:
        return self.front_matter.get("status", "").strip().strip("`'\"").casefold()

    @property
    def language(self) -> str:
        return self.front_matter.get("language", "").strip().strip("`'\"").casefold()


def _has_value(value: str) -> bool:
    """Report whether a field carries content rather than a template placeholder."""

    stripped = _TEMPLATE_TOKEN.sub("", value)
    normalized = " ".join(stripped.casefold().split()).strip(" .。_`'\"[]|-")
    return bool(normalized) and normalized not in _PLACEHOLDERS


def _section_number(title: str) -> str:
    match = re.match(r"^(\d+)[.、．]?\s", title)
    return match.group(1) if match else ""


def parse_spec(path: Path) -> tuple[Spec | None, List[str]]:
    """Split one spec file into front matter and numbered sections."""

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, [f"{path}: file not found"]
    except OSError as exc:  # pragma: no cover - unreadable file
        return None, [f"{path}: cannot read ({exc})"]

    match = _FRONT_MATTER.match(text)
    if match is None:
        return None, [f"{path.name}: missing YAML front matter delimited by ---"]

    front_matter: Dict[str, str] = {}
    for line in match.group("body").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        field = _FM_LINE.match(line)
        if field is not None:
            front_matter[field.group("key").casefold()] = field.group("value")

    sections: Dict[str, str] = {}
    current = ""
    buffer: List[str] = []
    for line in text[match.end():].splitlines():
        heading = _HEADING.match(line)
        if heading is not None and len(heading.group("hashes")) == 2:
            if current:
                sections[current] = "\n".join(buffer).strip()
            current = _section_number(heading.group("title"))
            buffer = []
            continue
        if current:
            buffer.append(line)
    if current:
        sections[current] = "\n".join(buffer).strip()
    return Spec(path, front_matter, sections), []


def _probe_closure_errors(name: str, spec: Spec) -> List[str]:
    """Check that a full spec traces back to a probe that actually ran.

    A probe file merely existing proves nothing; the point of the cheap test is
    that it was executed and produced a verdict.  The waiver path stays open for
    the legitimate case where the statement itself dictates the algorithm, but a
    waiver has to say why.
    """

    errors: List[str] = []
    result = spec.front_matter.get("probe_result", "").strip().strip("`'\"").casefold()
    if not result:
        return [
            f"{name}: full spec has no probe_result; a full spec must trace back to a probe "
            "that ran (PASS) or to a written waiver (WAIVED)"
        ]
    if result not in VALID_PROBE_RESULT:
        return [f"{name}: invalid probe_result {result!r}; use one of {sorted(VALID_PROBE_RESULT)}"]

    if result == "fail":
        errors.append(
            f"{name}: probe_result is FAIL; a route whose probe was falsified must not be "
            "promoted to a full spec without re-running the probe"
        )
    if result == "waived":
        if not _has_value(spec.front_matter.get("probe_waiver_reason", "")):
            errors.append(
                f"{name}: probe_result is WAIVED but probe_waiver_reason is empty or a placeholder; "
                "state why the cheap falsification step was skipped"
            )
    else:
        for field in ("probe_spec_id", "probe_exp_id"):
            if not _has_value(spec.front_matter.get(field, "")):
                errors.append(
                    f"{name}: front matter field {field!r} is missing or a placeholder; "
                    "it is required unless probe_result is WAIVED"
                )
    return errors


def validate_spec(path: Path) -> List[str]:
    """Return every syntactic problem found in one spec file."""

    spec, errors = parse_spec(path)
    if spec is None:
        return errors

    name = path.name
    for field in _REQUIRED_FM:
        if not _has_value(spec.front_matter.get(field, "")):
            errors.append(f"{name}: front matter field {field!r} is missing or a placeholder")

    status = spec.status
    if status and status not in VALID_STATUS:
        errors.append(f"{name}: invalid status {status!r}; use one of {sorted(VALID_STATUS)}")
    language = spec.language
    if language and language not in VALID_LANGUAGE:
        errors.append(f"{name}: invalid language {language!r}; use one of {sorted(VALID_LANGUAGE)}")

    if status == "full":
        errors.extend(_probe_closure_errors(name, spec))

    expected = _PROBE_SECTIONS if status == "probe" else _FULL_SECTIONS
    required = _PROBE_MUST_HAVE_CONTENT if status == "probe" else _MUST_HAVE_CONTENT
    for number, label in expected:
        if number not in spec.sections:
            errors.append(f"{name}: missing section {number} ({label})")
        elif number in required and not _has_value(spec.sections[number]):
            errors.append(f"{name}: section {number} ({label}) is empty or still a placeholder")

    criteria_section = "2" if status == "probe" else "1"
    criteria = spec.sections.get(criteria_section, "")
    if _has_value(criteria) and not _NUMERIC.search(_TEMPLATE_TOKEN.sub("", criteria)):
        errors.append(
            f"{name}: section {criteria_section} states no numeric acceptance criterion; "
            "'效果好' or '收敛正常' cannot be judged by the engineer"
        )
    return errors


def validate_case_specs(case_dir: Path) -> List[str]:
    """Validate every spec in one case directory."""

    specs_dir = case_dir / "specs"
    if not specs_dir.is_dir():
        return [f"{case_dir}: no specs/ directory; the modeler has not handed anything over yet"]

    files = sorted(
        path
        for path in specs_dir.glob("SPEC-*.md")
        if not path.name.endswith(".questions.md")
    )
    if not files:
        return [f"{specs_dir}: contains no SPEC-*.md file"]

    errors: List[str] = []
    seen: Dict[str, Path] = {}
    for path in files:
        errors.extend(validate_spec(path))
        spec, _ = parse_spec(path)
        if spec is None:
            continue
        spec_id = spec.front_matter.get("spec_id", "").strip()
        if _has_value(spec_id):
            if spec_id in seen:
                errors.append(f"{path.name}: duplicate spec_id {spec_id!r}, also in {seen[spec_id].name}")
            else:
                seen[spec_id] = path
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="validate implementation specs for one case")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--case-dir", type=Path)
    source.add_argument("path", type=Path, nargs="?")
    args = parser.parse_args()

    if args.case_dir is not None:
        errors = validate_case_specs(args.case_dir)
        target = args.case_dir
    else:
        errors = validate_spec(args.path)
        target = args.path

    if errors:
        print("FAIL spec check")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"PASS spec check: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
