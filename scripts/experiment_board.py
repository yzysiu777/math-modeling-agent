"""Validate the lightweight Markdown experiment board."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, Iterable, List, Optional


REQUIRED_COLUMNS = (
    "实验 ID", "候选路线", "要回答的问题", "最小配置", "数据/实例范围", "指标",
    "预计成本", "status", "结果摘要", "是否继续", "下一项信息价值最高的实验",
)
VALID_STATUS = {"queued", "running", "done", "failed", "skipped"}


def parse_markdown_table(text: str) -> List[Dict[str, str]]:
    """Parse pipe tables, tolerating the separator row and surrounding prose."""

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


def validate_experiment_board(path: Path) -> List[str]:
    if not path.is_file():
        return [f"missing experiment board: {path}"]
    text = path.read_text(encoding="utf-8")
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    if len(lines) < 2:
        return ["experiment board has no Markdown table"]
    header = [cell.strip() for cell in lines[0].strip("|").split("|")]
    errors = [f"experiment board missing column: {column}" for column in REQUIRED_COLUMNS if column not in header]
    rows = parse_markdown_table(text)
    ids = [row.get("实验 ID", "") for row in rows]
    if any(not item or item.lower().startswith("exp-") is False for item in ids):
        errors.append("every experiment row needs an EXP-... identifier")
    if len(ids) != len(set(ids)):
        errors.append("experiment IDs must be unique")
    for row in rows:
        if row.get("status") not in VALID_STATUS:
            errors.append(f"invalid experiment status: {row.get('status')!r}")
        if not row.get("候选路线"):
            errors.append(f"experiment {row.get('实验 ID')} has no candidate route")
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
