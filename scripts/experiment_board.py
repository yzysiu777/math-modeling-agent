"""Validate the lightweight Markdown experiment board."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Dict, List


REQUIRED_COLUMNS = (
    "实验 ID", "候选路线", "要回答的问题", "最小配置", "数据/实例范围", "指标",
    "预计成本", "status", "结果摘要", "是否继续", "下一项信息价值最高的实验",
)
REQUIRED_CONTENT_COLUMNS = REQUIRED_COLUMNS[:8]
VALID_STATUS = {"queued", "running", "done", "failed", "skipped"}
EXPERIMENT_ID = re.compile(r"EXP-[A-Za-z0-9][A-Za-z0-9_-]*$", re.IGNORECASE)
PLACEHOLDERS = {"", "-", "—", "待填写", "待填", "待补充", "todo", "tbd", "n/a"}
FAILURE_HINTS = (
    "失败", "原因", "错误", "异常", "不可行", "超时", "中止", "缺失", "崩溃", "无法", "未能",
    "failed", "failure", "error", "exception", "infeasible", "timeout", "missing", "crash",
)
SKIP_HINTS = (
    "跳过", "原因", "不相关", "无需", "缺少", "重复", "资源", "暂不", "skip", "because",
)


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


def _has_value(value: str) -> bool:
    normalized = " ".join(value.casefold().split()).strip(" .。_")
    return bool(normalized) and normalized not in PLACEHOLDERS


def _has_failure_reason(value: str) -> bool:
    lowered = value.casefold()
    return _has_value(value) and any(hint.casefold() in lowered for hint in FAILURE_HINTS)


def _has_skip_reason(value: str) -> bool:
    lowered = value.casefold()
    return _has_value(value) and any(hint.casefold() in lowered for hint in SKIP_HINTS)


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
    if not rows:
        errors.append("experiment board has no experiment rows")
    ids = [row.get("实验 ID", "") for row in rows]
    if any(not EXPERIMENT_ID.fullmatch(item.strip()) for item in ids):
        errors.append("every experiment row needs an EXP-... identifier")
    normalized_ids = [item.strip().casefold() for item in ids]
    if len(normalized_ids) != len(set(normalized_ids)):
        errors.append("experiment IDs must be unique")
    for row in rows:
        experiment_id = row.get("实验 ID", "").strip() or "<unknown>"
        for column in REQUIRED_CONTENT_COLUMNS:
            if not _has_value(row.get(column, "")):
                errors.append(f"experiment {experiment_id} has empty required field: {column}")

        status = row.get("status", "").strip().casefold()
        if status not in VALID_STATUS:
            errors.append(f"invalid experiment status: {row.get('status')!r}")
            continue

        result = row.get("结果摘要", "")
        continuation = row.get("是否继续", "")
        next_experiment = row.get("下一项信息价值最高的实验", "")
        if status == "queued":
            if not _has_value(next_experiment):
                errors.append(f"queued experiment {experiment_id} needs a next experiment or 待当前实验后决定")
        elif status == "running":
            # A running experiment may not have a result yet; ``运行中`` is a useful explicit value.
            continue
        elif status == "done":
            if not _has_value(result):
                errors.append(f"done experiment {experiment_id} needs a result summary")
            if not _has_value(continuation):
                errors.append(f"done experiment {experiment_id} needs 是否继续")
            if not _has_value(next_experiment):
                errors.append(f"done experiment {experiment_id} needs a next experiment or 无/路线已确定")
        elif status == "failed":
            if not _has_failure_reason(result):
                errors.append(f"failed experiment {experiment_id} needs a failure reason in 结果摘要")
            if not _has_value(continuation):
                errors.append(f"failed experiment {experiment_id} needs 是否继续")
            if not _has_value(next_experiment):
                errors.append(f"failed experiment {experiment_id} needs a next step")
        elif status == "skipped" and not _has_skip_reason(result):
            errors.append(f"skipped experiment {experiment_id} needs a skip reason in 结果摘要")
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
