"""Tiny time-aware data analysis example with a leakage counterexample."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.model_checks import check_data_split, compare_model_results  # noqa: E402


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
