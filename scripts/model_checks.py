"""Small, model-neutral checks used during competition experiments.

These functions deliberately accept ordinary Python values and callables. A
team can use them inside a solver notebook or a short script without first
building a record system. They report facts and violations; interpretation of
the result remains part of the modeling work.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


Constraint = Callable[[Mapping[str, Any]], Any]
Objective = Callable[[Mapping[str, Any]], float]


@dataclass(frozen=True)
class ConstraintResult:
    name: str
    feasible: bool
    detail: str


def _evaluate_constraint(name: str, check: Any, solution: Mapping[str, Any]) -> ConstraintResult:
    try:
        outcome = check(solution) if callable(check) else bool(check)
    except Exception as exc:  # noqa: BLE001 - the report should identify a bad check
        return ConstraintResult(name, False, f"constraint raised {type(exc).__name__}: {exc}")
    if isinstance(outcome, tuple) and len(outcome) == 2:
        feasible, detail = bool(outcome[0]), str(outcome[1])
    else:
        feasible, detail = bool(outcome), "satisfied" if bool(outcome) else "violated"
    return ConstraintResult(name, feasible, detail)


def check_constraints(
    solution: Mapping[str, Any],
    constraints: Iterable[Tuple[str, Constraint]],
) -> Dict[str, Any]:
    """Evaluate named constraints and return a compact feasibility report."""

    results = [_evaluate_constraint(name, check, solution) for name, check in constraints]
    violations = [result.__dict__ for result in results if not result.feasible]
    return {
        "feasible": not violations,
        "checked": len(results),
        "violations": violations,
        "constraints": [result.__dict__ for result in results],
    }


def recompute_objective(solution: Mapping[str, Any], objective: Objective) -> float:
    """Compute an objective directly from the submitted decision values."""

    value = float(objective(solution))
    if value != value or value in (float("inf"), float("-inf")):
        raise ValueError("objective is not finite")
    return value


def audit_optimization_result(
    solution: Mapping[str, Any],
    objective: Objective,
    constraints: Iterable[Tuple[str, Constraint]],
    reported_objective: Optional[float] = None,
    tolerance: float = 1e-8,
) -> Dict[str, Any]:
    """Check feasibility and independently recompute the objective."""

    feasibility = check_constraints(solution, constraints)
    objective_value = recompute_objective(solution, objective)
    objective_matches = (
        reported_objective is None
        or isclose(objective_value, float(reported_objective), rel_tol=tolerance, abs_tol=tolerance)
    )
    return {
        "feasible": feasibility["feasible"],
        "objective": objective_value,
        "reported_objective": reported_objective,
        "objective_matches": objective_matches,
        "violations": feasibility["violations"],
        "passed": feasibility["feasible"] and objective_matches,
    }


def check_data_split(
    train: Sequence[Mapping[str, Any]],
    validation: Sequence[Mapping[str, Any]],
    test: Sequence[Mapping[str, Any]],
    key: str,
    time_key: Optional[str] = None,
) -> List[str]:
    """Find duplicate entities, cross-split overlap and time-order leakage."""

    errors: List[str] = []
    sets = {"train": [row.get(key) for row in train], "validation": [row.get(key) for row in validation], "test": [row.get(key) for row in test]}
    for name, values in sets.items():
        if any(value is None for value in values):
            errors.append(f"{name} contains a row without split key {key}")
        if len(values) != len(set(values)):
            errors.append(f"{name} contains duplicate {key} values")
    names = list(sets)
    for index, left in enumerate(names):
        for right in names[index + 1:]:
            overlap = set(sets[left]).intersection(sets[right])
            if overlap:
                errors.append(f"{left}/{right} share {key}: {sorted(overlap, key=str)}")

    if time_key:
        rows_by_name = {"train": train, "validation": validation, "test": test}
        times: Dict[str, List[Any]] = {}
        for name, rows in rows_by_name.items():
            values = [row.get(time_key) for row in rows]
            if any(value is None for value in values):
                errors.append(f"{name} contains a row without time key {time_key}")
            times[name] = values
        for left, right in (("train", "validation"), ("validation", "test"), ("train", "test")):
            if times[left] and times[right] and max(times[left]) >= min(times[right]):
                errors.append(f"time order leakage: {left} is not strictly before {right}")
    return errors


def compare_model_results(
    results: Sequence[Mapping[str, Any]],
    metric: str,
    higher_is_better: bool = True,
) -> Dict[str, Any]:
    """Rank completed candidates and retain a methodologically different challenger."""

    usable = [dict(item) for item in results if item.get("status", "done") == "done" and metric in item]
    if len(usable) < 2:
        raise ValueError("at least two completed model results are required")
    ranked = sorted(usable, key=lambda item: float(item[metric]), reverse=higher_is_better)
    champion = ranked[0]
    challenger = next(
        (item for item in ranked[1:] if item.get("method_family") != champion.get("method_family")),
        None,
    )
    if challenger is None:
        raise ValueError("no methodologically different challenger is available")
    return {
        "metric": metric,
        "higher_is_better": higher_is_better,
        "ranking": ranked,
        "champion": champion,
        "challenger": challenger,
    }


def validate_hybrid_interface(
    payload: Mapping[str, Any],
    required_fields: Mapping[str, type],
    expected_units: Optional[Mapping[str, str]] = None,
) -> List[str]:
    """Check a small upstream-to-decision payload without imposing a schema system."""

    errors: List[str] = []
    for field, expected_type in required_fields.items():
        if field not in payload:
            errors.append(f"missing interface field: {field}")
        elif not isinstance(payload[field], expected_type):
            errors.append(f"interface field {field} is not {expected_type.__name__}")
    if expected_units:
        units = payload.get("units", {})
        for field, unit in expected_units.items():
            if not isinstance(units, Mapping) or units.get(field) != unit:
                errors.append(f"interface unit mismatch for {field}: expected {unit}")
    return errors
