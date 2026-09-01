"""EXP-OPT-001 / EXP-OPT-002: SPEC-P1-M02 的实现（贪心 baseline + 精确枚举）。

演示三角色接力的编程手一侧：按规格实现、独立复算、按输出契约落盘。
运行：python cases/examples/optimization/q1/code/python/run_demo.py
"""

from __future__ import annotations

import csv
import itertools
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.model_checks import audit_optimization_result, write_check_report  # noqa: E402


CASE = Path(__file__).resolve().parents[3]
OUT = CASE / "q1/outputs"
EXP_ID = "EXP-OPT-002"
SPEC_ID = "SPEC-P1-M02"

DEMANDS = ("d1", "d2", "d3")
FACILITIES = ("A", "B")
COST = {
    "d1": {"A": 1, "B": 4},
    "d2": {"A": 2, "B": 1},
    "d3": {"A": 3, "B": 2},
}
# 规格第 3 段：基础实例与容量边界实例。
INSTANCES = {"base": {"A": 2, "B": 2}, "capacity_edge": {"A": 1, "B": 2}}


def objective(solution):
    return sum(COST[demand][solution[demand]] for demand in DEMANDS)


def constraints(capacity):
    """规格第 2 段的 C1/C2/C3，从规格文字重写，不复用求解过程。"""

    return [
        ("C1 每个需求点恰好分配一次", lambda values: set(values) == set(DEMANDS)),
        ("C2 容量 A", lambda values: sum(values[d] == "A" for d in DEMANDS) <= capacity["A"]),
        ("C2 容量 B", lambda values: sum(values[d] == "B" for d in DEMANDS) <= capacity["B"]),
        ("C3 变量域", lambda values: all(values[d] in FACILITIES for d in DEMANDS)),
    ]


def greedy(capacity):
    """M-01 构造式启发式，作为上界对照。"""

    solution = {}
    remaining = dict(capacity)
    for demand in DEMANDS:
        options = sorted(FACILITIES, key=lambda facility: COST[demand][facility])
        facility = next((item for item in options if remaining[item] > 0), None)
        if facility is None:
            return None
        solution[demand] = facility
        remaining[facility] -= 1
    return solution


def exact(capacity):
    """M-02 全枚举，给出真值。"""

    feasible = []
    for assignment in itertools.product(FACILITIES, repeat=len(DEMANDS)):
        solution = dict(zip(DEMANDS, assignment))
        report = audit_optimization_result(solution, objective, constraints(capacity))
        if report["passed"]:
            feasible.append((report["objective"], solution))
    return min(feasible, key=lambda item: item[0])[1] if feasible else None


def write_runtime_log(runtime_sec):
    """Record wall-clock time outside the tracked result files."""

    logs = OUT / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    (logs / f"{EXP_ID}_runtime.json").write_text(
        json.dumps({"exp_id": EXP_ID, "runtime_sec": runtime_sec}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")


def write_outputs(rows, metrics):
    (OUT / "data").mkdir(parents=True, exist_ok=True)
    with (OUT / f"data/{EXP_ID}_solution.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["instance", "demand_id", "facility_id", "cost_yuan"])
        writer.writerows(rows)
    (OUT / f"data/{EXP_ID}_metrics.json").write_text(
        json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main():
    started = time.perf_counter()
    rows = []
    checks = []
    metrics = {
        "exp_id": EXP_ID, "spec_id": SPEC_ID, "language": "python",
        "seed": None, "instances": {},
    }
    result = {"route": "optimization", "instances": {}}

    for name, capacity in INSTANCES.items():
        champion = exact(capacity)
        baseline = greedy(capacity)
        if champion is None:
            checks.append({"name": f"{name} 可行性", "kind": "infeasible", "passed": False,
                           "detail": "枚举未找到可行解"})
            continue

        # 复算：从最终分配重新验证约束并重算目标，不复用枚举中间值。
        audit = audit_optimization_result(
            champion, objective, constraints(capacity),
            reported_objective=objective(champion), tolerance=1e-9,
        )
        for violation in audit["violations"]:
            checks.append({"name": f"{name} {violation['name']}", "kind": "constraint",
                           "passed": False, "detail": violation["detail"]})
        if not audit["violations"]:
            checks.append({"name": f"{name} 全部约束", "kind": "constraint", "passed": True,
                           "detail": f"逐条检查 {len(constraints(capacity))} 条"})
        checks.append({
            "name": f"{name} 目标值独立重算", "kind": "objective_mismatch",
            "passed": audit["objective_matches"],
            "detail": f"recomputed={audit['objective']}, reported={audit['reported_objective']}",
        })

        rows.extend([name, demand, facility, COST[demand][facility]]
                    for demand, facility in sorted(champion.items()))
        metrics["instances"][name] = {
            "objective": audit["objective"],
            "feasible": audit["feasible"],
            "baseline_objective": objective(baseline) if baseline else None,
        }
        result["instances"][name] = {
            "champion": champion, "champion_objective": audit["objective"],
            "baseline": baseline, "baseline_objective": objective(baseline) if baseline else None,
            "audit_passed": audit["passed"],
        }

    # 运行时间每次都不同。把它写进已跟踪的结果文件，会让 `make test` / `make demos`
    # 每跑一次就弄脏工作树，逼人提交无意义的时序差异 —— 于是真正的结果变更也淹没在
    # 噪声里。时序进被忽略的日志，确定性结果留在 metrics.json。
    write_outputs(rows, metrics)
    write_runtime_log(round(time.perf_counter() - started, 6))
    write_check_report(OUT / "checks", EXP_ID, SPEC_ID, checks)

    result["candidate_routes"] = [
        {"id": "M-01", "method_family": "constructive heuristic"},
        {"id": "M-02", "method_family": "exact enumeration"},
        {"id": "M-03", "method_family": "mixed-integer programming", "status": "next"},
    ]
    result["challenger"] = "M-01"
    result["passed"] = all(item["passed"] for item in checks)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
