"""Validate the single lightweight experiment board used in competition."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List


CURRENT_COLUMNS = (
    "实验 ID", "路线", "类型", "要回答的问题/显式假设", "预设判据",
    "数据/实例范围", "预算", "status", "结果与判定", "是否继续", "下一步",
)
LEGACY_COLUMNS = (
    "实验 ID", "候选路线", "要回答的问题", "最小配置", "数据/实例范围", "指标",
    "预计成本", "status", "结果摘要", "是否继续", "下一项信息价值最高的实验",
)
VALID_STATUS = {"queued", "running", "done", "failed", "skipped"}
EXPERIMENT_ID = re.compile(r"EXP-[A-Za-z0-9][A-Za-z0-9_-]*$", re.IGNORECASE)
PLACEHOLDERS = {"", "-", "—", "待填写", "待填", "待替换", "待补充", "todo", "tbd", "n/a"}


def parse_markdown_table(text: str) -> List[Dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    rows: List[Dict[str, str]] = []
    for index in range(len(lines) - 1):
        header = [cell.strip() for cell in lines[index].strip("|").split("|")]
        separator = [cell.strip() for cell in lines[index + 1].strip("|").split("|")]
        if not header or len(header) != len(separator) or not all(set(cell) <= {"-", ":"} for cell in separator):
            continue
        for line in lines[index + 2:]:
            values = [cell.strip() for cell in line.strip("|").split("|")]
            if len(values) != len(header) or all(set(value) <= {"-", ":"} for value in values):
                break
            rows.append(dict(zip(header, values)))
        break
    return rows


def _has_value(value: str) -> bool:
    normalized = " ".join(value.casefold().split()).strip(" .。_`\"")
    return bool(normalized) and normalized not in PLACEHOLDERS


def _value(row: Dict[str, str], *names: str) -> str:
    return next((row[name].strip() for name in names if name in row), "")


def validate_experiment_board(path: Path) -> List[str]:
    if not path.is_file():
        return [f"missing experiment board: {path}"]
    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return ["experiment board has no Markdown table"]
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    current = all(column in header for column in CURRENT_COLUMNS)
    legacy = all(column in header for column in LEGACY_COLUMNS)
    errors: List[str] = []
    if not current and not legacy:
        errors.append("experiment board must use the compact current header")
    rows = parse_markdown_table(text)
    if not rows:
        errors.append("experiment board has no experiment rows")
        return errors

    ids = [_value(row, "实验 ID") for row in rows]
    if any(not EXPERIMENT_ID.fullmatch(item) for item in ids):
        errors.append("every experiment row needs an EXP-... identifier")
    if len({item.casefold() for item in ids}) != len(ids):
        errors.append("experiment IDs must be unique")

    for row in rows:
        exp_id = _value(row, "实验 ID") or "<unknown>"
        status = _value(row, "status").casefold()
        if status not in VALID_STATUS:
            errors.append(f"invalid experiment status: {row.get('status')!r}")
            continue
        if current:
            for label in CURRENT_COLUMNS[1:7]:
                if not _has_value(_value(row, label)):
                    errors.append(f"experiment {exp_id} has empty required field: {label}")
        else:
            for label in LEGACY_COLUMNS[:8]:
                if not _has_value(_value(row, label)):
                    errors.append(f"experiment {exp_id} has empty required field: {label}")

        result = _value(row, "结果与判定", "结果摘要")
        continuation = _value(row, "是否继续")
        next_step = _value(row, "下一步", "下一项信息价值最高的实验")
        kind = _value(row, "类型").casefold()
        if status == "done":
            if not _has_value(result):
                errors.append(f"done experiment {exp_id} needs a result and verdict")
            if current and kind in {"probe", "reviewer_probe"} and not re.search(
                r"\b(?:PASS|FAIL)\b|判定\s*[:：]?\s*(?:通过|失败|未通过)", result, re.IGNORECASE
            ):
                errors.append(f"completed probe {exp_id} needs an explicit PASS/FAIL verdict")
            if not _has_value(continuation):
                errors.append(f"done experiment {exp_id} needs 是否继续")
        elif status in {"failed", "skipped"} and not _has_value(result):
            errors.append(f"{status} experiment {exp_id} needs a result or failure summary")
        if status in {"done", "failed", "skipped"} and not _has_value(next_step):
            errors.append(f"{status} experiment {exp_id} needs 下一步")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="validate a modeling experiment board")
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    errors = validate_experiment_board(args.path)
    if errors:
        print("FAIL experiment board")
        print("\n".join(f"- {error}" for error in errors))
        return 1
    print(f"PASS experiment board: {args.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
