"""Tiny allocation example: baseline, exact champion and independent checks."""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.model_checks import audit_optimization_result  # noqa: E402


DEMANDS = ("d1", "d2", "d3")
FACILITIES = ("A", "B")
COST = {
    "d1": {"A": 1, "B": 4},
    "d2": {"A": 2, "B": 1},
    "d3": {"A": 3, "B": 2},
}
CAPACITY = {"A": 2, "B": 2}


def objective(solution):
    return sum(COST[demand][solution[demand]] for demand in DEMANDS)


def constraints(solution):
    return [
        ("every demand assigned", lambda values: set(values) == set(DEMANDS)),
        ("capacity A", lambda values: sum(values[d] == "A" for d in DEMANDS) <= CAPACITY["A"]),
        ("capacity B", lambda values: sum(values[d] == "B" for d in DEMANDS) <= CAPACITY["B"]),
    ]


def greedy():
    solution = {}
    remaining = dict(CAPACITY)
    for demand in DEMANDS:
        options = sorted(FACILITIES, key=lambda facility: COST[demand][facility])
        facility = next(item for item in options if remaining[item] > 0)
        solution[demand] = facility
        remaining[facility] -= 1
    return solution


def exact():
    feasible = []
    for assignment in itertools.product(FACILITIES, repeat=len(DEMANDS)):
        solution = dict(zip(DEMANDS, assignment))
        report = audit_optimization_result(solution, objective, constraints(solution))
        if report["passed"]:
            feasible.append((report["objective"], solution))
    return min(feasible, key=lambda item: item[0])[1]


def main():
    baseline = greedy()
    champion = exact()
    baseline_report = audit_optimization_result(baseline, objective, constraints(baseline))
    champion_report = audit_optimization_result(champion, objective, constraints(champion))
    result = {
        "route": "optimization",
        "candidate_routes": [
            {"id": "M-01", "method_family": "constructive heuristic"},
            {"id": "M-02", "method_family": "exact enumeration"},
            {"id": "M-03", "method_family": "mixed-integer programming", "status": "next"},
        ],
        "baseline": {"solution": baseline, "audit": baseline_report},
        "champion": {"solution": champion, "audit": champion_report},
        "challenger": "M-01",
        "passed": baseline_report["passed"] and champion_report["passed"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
