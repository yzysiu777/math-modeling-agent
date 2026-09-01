"""Tiny forecast-to-inventory example with explicit interface checks."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[6]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.model_checks import audit_optimization_result, validate_hybrid_interface  # noqa: E402


CAPACITY = 10
HOLDING_COST = 1
SHORTAGE_COST = 5


def cost(solution, demand):
    quantity = solution["quantity"]
    return quantity * HOLDING_COST + max(demand - quantity, 0) * SHORTAGE_COST


def choose_quantity(demand):
    options = []
    for quantity in range(CAPACITY + 1):
        solution = {"quantity": quantity}
        report = audit_optimization_result(
            solution,
            lambda values: cost(values, demand),
            [("capacity", lambda values: 0 <= values["quantity"] <= CAPACITY)],
        )
        options.append((report["objective"], solution))
    return min(options, key=lambda item: item[0])[1]


def main():
    forecast = {"demand": 8, "service_level": 0.9, "units": {"demand": "units"}}
    interface_errors = validate_hybrid_interface(
        forecast,
        {"demand": int, "service_level": float},
        {"demand": "units"},
    )
    decision = choose_quantity(forecast["demand"])
    decision_report = audit_optimization_result(
        decision,
        lambda values: cost(values, forecast["demand"]),
        [("capacity", lambda values: 0 <= values["quantity"] <= CAPACITY)],
    )
    stress = {
        str(demand): cost(choose_quantity(forecast["demand"]), demand)
        for demand in (6, 8, 10)
    }
    result = {
        "route": "hybrid",
        "interface_errors": interface_errors,
        "forecast": forecast,
        "decision": decision,
        "decision_audit": decision_report,
        "stress_costs": stress,
        "candidate_routes": ["forecast-then-optimize", "scenario/robust", "quantile/service-level"],
        "champion": "M-01",
        "challenger": "M-02",
        "passed": not interface_errors and decision_report["passed"],
    }
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
