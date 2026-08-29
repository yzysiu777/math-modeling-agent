"""EXP-DA-001 / EXP-DA-002: SPEC-P1-M02 的实现（历史均值 baseline + 线性回归）。

演示数据类题目的编程手一侧：时间序切分、泄漏反例、独立复算并按输出契约落盘。
运行：python cases/examples/data-analysis/experiments/code/python/run_demo.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.model_checks import (  # noqa: E402
    check_data_split, compare_model_results, write_check_report,
)

CASE = Path(__file__).resolve().parents[3]
OUT = CASE / "experiments/outputs"
EXP_ID = "EXP-DA-002"
SPEC_ID = "SPEC-P1-M02"


ROWS = [
    {"id": f"e{i}", "time": i, "x": i, "y": 2 * i + (i % 2)}
    for i in range(1, 10)
]


def mae(actual, predicted):
    return sum(abs(left - right) for left, right in zip(actual, predicted)) / len(actual)


def main():
    train, validation, test = ROWS[:5], ROWS[5:7], ROWS[7:]
    split_errors = check_data_split(train, validation, test, "id", "time")
    train_mean = sum(row["y"] for row in train) / len(train)
    baseline_error = mae([row["y"] for row in test], [train_mean] * len(test))
    x_bar = sum(row["x"] for row in train) / len(train)
    y_bar = sum(row["y"] for row in train) / len(train)
    denominator = sum((row["x"] - x_bar) ** 2 for row in train)
    slope = sum((row["x"] - x_bar) * (row["y"] - y_bar) for row in train) / denominator
    intercept = y_bar - slope * x_bar
    linear_predictions = [intercept + slope * row["x"] for row in test]
    linear_error = mae([row["y"] for row in test], linear_predictions)
    comparison = compare_model_results(
        [
            {"id": "M-01", "method_family": "statistical baseline", "mae": -baseline_error, "status": "done"},
            {"id": "M-02", "method_family": "linear regression", "mae": -linear_error, "status": "done"},
        ],
        "mae",
        higher_is_better=True,
    )
    leakage_probe = check_data_split(train, validation, test + [test[0]], "id", "time")

    # 复算：切分与泄漏。反例分支刻意构造一个重复实体，确认检查器真的会报错 ——
    # 一个从不报错的检查器和没有检查器是一样的。
    checks = [
        {"name": "时间序切分无重叠且无泄漏", "kind": "split_overlap",
         "passed": not split_errors, "detail": "; ".join(split_errors)},
        {"name": "泄漏反例能被检出", "kind": "leakage",
         "passed": bool(leakage_probe), "detail": "; ".join(leakage_probe) or "反例未被检出"},
    ]
    write_check_report(OUT / "checks", EXP_ID, SPEC_ID, checks)

    (OUT / "data").mkdir(parents=True, exist_ok=True)
    with (OUT / f"data/{EXP_ID}_predictions.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["id", "time", "y_true", "y_pred_baseline", "y_pred_linear"])
        writer.writerows(
            [row["id"], row["time"], row["y"], round(train_mean, 6), round(prediction, 6)]
            for row, prediction in zip(test, linear_predictions)
        )
    (OUT / f"data/{EXP_ID}_metrics.json").write_text(
        json.dumps({
            "exp_id": EXP_ID, "spec_id": SPEC_ID, "language": "python", "seed": None,
            "split": {"train": len(train), "validation": len(validation), "test": len(test)},
            "baseline_test_mae": baseline_error, "linear_test_mae": linear_error,
            "feasible": not split_errors,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8",
    )

    result = {
        "route": "data_analysis",
        "split_errors": split_errors,
        "leakage_counterexample_detected": bool(leakage_probe),
        "baseline": {"method_family": "statistical baseline", "test_mae": baseline_error},
        "linear": {"method_family": "linear regression", "test_mae": linear_error, "slope": slope},
        "champion": comparison["champion"]["id"],
        "challenger": comparison["challenger"]["id"],
        "passed": not split_errors and bool(leakage_probe),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
