"""EXP-HYB-003 的 Python 独立复算（主实现在 MATLAB）。

跨语言契约的下半段：读 MATLAB 导出的 CSV/JSON，按规格文字重新表达约束和目标，
独立重算一遍，再写 outputs/checks/<EXP-ID>.json。

为什么复算必须在 Python 侧：scripts/check_case.py、阶段检查和 CI 都只能运行 Python，
MATLAB 写的报告不会被自动读取。用另一种语言从落盘数据重算，同时也验证了导出格式
是否正确 —— 同一套代码算两遍证明不了任何事。

运行前先在 MATLAB 中执行 run_EXP_HYB_003。
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.model_checks import (  # noqa: E402
    audit_optimization_result, load_result, write_check_report,
)

CASE = Path(__file__).resolve().parents[3]
OUT = CASE / "experiments/outputs"
EXP_ID = "EXP-HYB-003"
SPEC_ID = "SPEC-P2-M01"


def main() -> int:
    metrics_path = OUT / f"data/{EXP_ID}_metrics.json"
    solution_path = OUT / f"data/{EXP_ID}_solution.csv"
    if not metrics_path.is_file() or not solution_path.is_file():
        print(f"SKIP {EXP_ID}: 未找到 MATLAB 导出的结果；请先在 MATLAB 中运行 run_EXP_HYB_003")
        return 0

    metrics = load_result(metrics_path)
    rows = load_result(solution_path)

    quantity = float(metrics["quantity"])
    capacity = float(metrics["capacity"])
    holding = float(metrics["holding_cost"])
    shortage = float(metrics["shortage_cost"])
    forecast = float(metrics["forecast"])

    # 目标函数按规格第 2 段重写，不读 MATLAB 算出的 objective 再回代
    def objective(values):
        q = values["quantity"]
        return q * holding + max(forecast - q, 0) * shortage

    constraints = [
        ("C1 备货量非负", lambda values: values["quantity"] >= 0),
        ("C2 不超过仓储容量", lambda values: values["quantity"] <= capacity),
    ]

    audit = audit_optimization_result(
        {"quantity": quantity}, objective, constraints,
        reported_objective=float(metrics["objective"]), tolerance=1e-9,
    )

    checks = [
        {"name": violation["name"], "kind": "constraint", "passed": False, "detail": violation["detail"]}
        for violation in audit["violations"]
    ]
    if not audit["violations"]:
        checks.append({"name": "全部约束", "kind": "constraint", "passed": True,
                       "detail": f"逐条检查 {len(constraints)} 条"})
    checks.append({
        "name": "目标值独立重算", "kind": "objective_mismatch",
        "passed": audit["objective_matches"],
        "detail": f'recomputed={audit["objective"]}, matlab_reported={audit["reported_objective"]}',
    })

    # 跨语言接口检查：CSV 的每一行成本能否由同一目标函数复现
    row_mismatch = []
    for row in rows:
        demand = float(row["demand_units"])
        q = float(row["quantity_units"])
        expected = q * holding + max(demand - q, 0) * shortage
        if abs(expected - float(row["cost_yuan"])) > 1e-9:
            row_mismatch.append(f'demand={demand}: csv={row["cost_yuan"]}, recomputed={expected}')
    checks.append({
        "name": "压力场景成本逐行复算", "kind": "objective_mismatch",
        "passed": not row_mismatch, "detail": "; ".join(row_mismatch) or f"{len(rows)} 行一致",
    })

    target = write_check_report(OUT / "checks", EXP_ID, SPEC_ID, checks)
    passed = all(item["passed"] for item in checks)
    print(f"{'PASS' if passed else 'FAIL'} {EXP_ID} 复算 -> {target}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
