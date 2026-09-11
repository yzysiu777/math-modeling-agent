"""Validate the compact five-section Full SPEC contract."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

try:
    from .case_paths import reference_violation_code
    from .experiment_board import parse_markdown_table
except ImportError:  # pragma: no cover
    from case_paths import reference_violation_code
    from experiment_board import parse_markdown_table


FM_LINE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<value>.*?)\s*$")
HEADING = re.compile(r"^##\s+(?P<number>[1-5])[.、．]?\s+")
PLACEHOLDER = re.compile(r"^(?:<[^>]+>|待填写|待填|待替换|todo|tbd|[-—\s])*$", re.IGNORECASE)
EXP_ID = re.compile(r"^EXP-[A-Za-z0-9][A-Za-z0-9_-]*$", re.IGNORECASE)
QUESTION_DIR = re.compile(r"^q[1-9][0-9]*$", re.IGNORECASE)
OUTPUT_REFERENCE = re.compile(r"(?<![A-Za-z0-9_-])(q[1-9][0-9]*/outputs/[A-Za-z0-9_./\-]+)", re.IGNORECASE)


@dataclass
class Spec:
    path: Path
    fields: dict[str, str]
    sections: dict[str, str]


def _has_value(value: str) -> bool:
    return bool(value.strip()) and not PLACEHOLDER.fullmatch(value.strip())


def parse_spec(path: Path) -> tuple[Spec | None, list[str]]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        return None, [f"{path.name}: 无法读取：{exc}"]
    if not lines or lines[0].strip() != "---":
        return None, [f"{path.name}: 缺少 YAML front matter"]
    fields: dict[str, str] = {}
    end = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = index
            break
        match = FM_LINE.match(line)
        if match:
            fields[match.group("key").casefold()] = match.group("value").strip().strip("`'\"")
    if end is None:
        return None, [f"{path.name}: front matter 未闭合"]

    sections: dict[str, list[str]] = {}
    current = ""
    for line in lines[end + 1:]:
        match = HEADING.match(line)
        if match:
            current = match.group("number")
            sections[current] = []
        elif current:
            sections[current].append(line)
    return Spec(path, fields, {key: "\n".join(value).strip() for key, value in sections.items()}), errors


def validate_spec(path: Path) -> list[str]:
    spec, errors = parse_spec(path)
    if spec is None:
        return errors
    required = (
        "spec_id", "case_id", "route_id", "subproblem", "method_family",
        "status", "language", "probe_result",
    )
    for field in required:
        if not _has_value(spec.fields.get(field, "")):
            errors.append(f"{path.name}: front matter 缺少 {field}")
    if spec.fields.get("status", "").casefold() != "full":
        errors.append(f"{path.name}: 只接受 status: full；Probe 直接写实验板")
    if spec.fields.get("language", "").casefold() not in {"python", "matlab"}:
        errors.append(f"{path.name}: language 必须是 python 或 matlab")
    result = spec.fields.get("probe_result", "").casefold()
    if result not in {"pass", "waived", "pending"}:
        errors.append(f"{path.name}: probe_result 必须是 PASS、WAIVED 或 PENDING")
    if result == "pass" and not EXP_ID.fullmatch(spec.fields.get("probe_exp_id", "")):
        errors.append(f"{path.name}: PASS 必须填写真实 probe_exp_id")
    if result == "waived" and not _has_value(spec.fields.get("probe_waiver_reason", "")):
        errors.append(f"{path.name}: WAIVED 必须写明理由")
    for number in ("1", "2", "3", "4", "5"):
        if not _has_value(spec.sections.get(number, "")):
            errors.append(f"{path.name}: 第 {number} 段为空或仍是占位")
    return errors


def spec_reminders(case_dir: Path, question: str | None = None) -> list[str]:
    """Criteria written purely as a relative increment pick the least bad, not a usable one.

    A threshold of the form "beats the control by delta" is legitimate, but on its own
    it lets a route whose absolute performance is worthless win a race and be carried
    into the paper as the chosen model. The absolute floor is a blank the modeller has
    to fill from what the problem is for; nothing here judges what it should say.
    """

    if question is not None:
        directories = [case_dir / question.strip().casefold()]
    else:
        directories = sorted(
            path for path in case_dir.iterdir()
            if path.is_dir() and QUESTION_DIR.fullmatch(path.name)
        ) or [case_dir]
    paths = [
        path for directory in directories
        for path in sorted((directory / "specs").glob("SPEC-*.md"))
        if not path.name.endswith(".questions.md")
    ]

    reminders: list[str] = []
    for path in paths:
        spec, errors = parse_spec(path)
        if spec is None or errors:
            continue
        goal = spec.sections.get("1", "")
        if "绝对底线" not in goal:
            reminders.append(f"{path.name}: 判据缺「绝对底线」一栏，只有相对增量会选出最不烂的那条")
        if "相对增量" not in goal:
            reminders.append(f"{path.name}: 判据缺「相对增量」一栏；没有对照时写 n/a 并说明")
    return reminders


def _board_rows(work_dir: Path) -> dict[str, dict[str, str]]:
    path = work_dir / "board.md" if (work_dir / "board.md").is_file() else work_dir / "experiments/board.md"
    if not path.is_file():
        return {}
    rows: dict[str, dict[str, str]] = {}
    for row in parse_markdown_table(path.read_text(encoding="utf-8")):
        exp_id = str(row.get("实验 ID", "")).strip().upper()
        if exp_id:
            rows[exp_id] = {str(key): str(value) for key, value in row.items()}
    return rows


def _row_value(row: dict[str, str], *names: str) -> str:
    for name in names:
        if name in row:
            return row[name].strip()
    return ""


def _pass_row(row: dict[str, str]) -> bool:
    status = _row_value(row, "status").casefold()
    result = _row_value(row, "结果与判定", "结果摘要")
    return status == "done" and re.search(r"\bPASS\b|判定\s*[:：]?\s*通过", result, re.IGNORECASE) is not None


def _validate_workbench_specs(case_dir: Path, work_dir: Path, question: str | None) -> list[str]:
    specs_dir = work_dir / "specs"
    if not specs_dir.is_dir():
        return [f"缺少 specs 目录：{specs_dir}"]
    paths = [
        path for path in sorted(specs_dir.glob("SPEC-*.md"))
        if not path.name.endswith(".questions.md")
    ]
    errors: list[str] = []
    seen: set[str] = set()
    board = _board_rows(work_dir)
    for path in paths:
        errors.extend(validate_spec(path))
        if question is not None:
            for reference in OUTPUT_REFERENCE.findall(path.read_text(encoding="utf-8", errors="replace")):
                code = reference_violation_code(reference, question)
                if code:
                    errors.append(f"{path.name}: {code}: {question} 不得引用后续子问题 {reference}")
        spec, parse_errors = parse_spec(path)
        errors.extend(parse_errors)
        if spec is None:
            continue
        spec_id = spec.fields.get("spec_id", "")
        if spec_id in seen:
            errors.append(f"{path.name}: spec_id 重复：{spec_id}")
        seen.add(spec_id)
        if spec.fields.get("probe_result", "").casefold() != "pass":
            continue
        exp_id = spec.fields.get("probe_exp_id", "").upper()
        row = board.get(exp_id)
        if row is None:
            errors.append(f"{path.name}: 实验板找不到 {exp_id}")
            continue
        if not _pass_row(row):
            errors.append(f"{path.name}: {exp_id} 未完成或没有 PASS 判定")
        route = _row_value(row, "路线", "候选路线").upper()
        if route and route != spec.fields.get("route_id", "").upper():
            errors.append(f"{path.name}: {exp_id} 路线不一致")
        kind = _row_value(row, "类型").casefold()
        if kind == "reviewer_probe":
            recheck_id = spec.fields.get("reviewer_probe_recheck_exp_id", "").upper()
            recheck = board.get(recheck_id)
            if not EXP_ID.fullmatch(recheck_id) or recheck is None or not _pass_row(recheck):
                errors.append(
                    f"{path.name}: {exp_id} 来自 Reviewer，冻结 Full 前必须填写并完成 "
                    "reviewer_probe_recheck_exp_id"
                )
    return errors


def validate_case_specs(case_dir: Path, question: str | None = None) -> list[str]:
    """Validate one active question or every question in a new-style case.

    Existing example cases without ``q<k>/`` remain readable while the runtime
    contract moves to the per-question layout.
    """

    if question is not None:
        normalized = question.strip().casefold()
        if not QUESTION_DIR.fullmatch(normalized):
            return [f"非法子问题：{question}"]
        return _validate_workbench_specs(case_dir, case_dir / normalized, normalized)

    questions = sorted(
        (path for path in case_dir.iterdir() if path.is_dir() and QUESTION_DIR.fullmatch(path.name)),
        key=lambda path: int(path.name[1:]),
    ) if case_dir.is_dir() else []
    if not questions:
        return _validate_workbench_specs(case_dir, case_dir, None)
    errors: list[str] = []
    for work_dir in questions:
        errors.extend(f"{work_dir.name}: {error}" for error in _validate_workbench_specs(
            case_dir, work_dir, work_dir.name.casefold()
        ))
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="validate compact Full SPEC files")
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--question")
    args = parser.parse_args()
    errors = validate_case_specs(args.case_dir, args.question)
    # 提醒不影响退出码：判据两栏是建模判断，脚本只负责提示那一栏还空着。
    for reminder in spec_reminders(args.case_dir, args.question):
        print(f"REMINDER {reminder}")
    if errors:
        for error in errors:
            print(f"FAIL {error}")
        return 1
    print("OK Full SPEC contract")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
