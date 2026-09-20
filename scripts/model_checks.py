"""Small, model-neutral checks used during competition experiments.

These functions deliberately accept ordinary Python values and callables. A
team can use them inside a solver notebook or a short script without first
building a record system. They report facts and violations; interpretation of
the result remains part of the modeling work.
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from math import isclose
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union


Constraint = Callable[[Mapping[str, Any]], Any]
Objective = Callable[[Mapping[str, Any]], float]

#: Risk kinds understood by ``scripts/check_case.py``.  ``constraint`` records an
#: ordinary per-constraint result; the other four map onto the deterministic risk
#: flags in ``checkpoint.yaml``.
CHECK_KINDS = frozenset(
    {"constraint", "infeasible", "objective_mismatch", "leakage", "split_overlap"}
)


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


def check_information_cutoff(
    items: Iterable[Mapping[str, Any]],
    decision_time: Any = None,
) -> List[str]:
    """Check that every input was already available when it was used.

    Each item carries ``name``, ``available_at`` -- the earliest moment the value
    could be known -- and optionally ``used_for``, the decision moment it feeds;
    ``decision_time`` is the fallback. Comparison is by moment, never by calendar
    day or batch label: a value stamped with the right day can still belong to the
    step after the decision, and a forecast issued at a given hour usually covers
    offsets in its own units rather than the model's.
    """

    errors: List[str] = []
    for index, item in enumerate(items):
        name = str(item.get("name", f"item[{index}]"))
        if "available_at" not in item:
            errors.append(f"{name} has no available_at")
            continue
        used_for = item.get("used_for", decision_time)
        if used_for is None:
            errors.append(f"{name} has no used_for and no decision_time was given")
            continue
        available_at = item["available_at"]
        try:
            late = available_at > used_for
        except TypeError:
            errors.append(
                f"{name}: available_at ({type(available_at).__name__}) and used_for "
                f"({type(used_for).__name__}) are not comparable"
            )
            continue
        if late:
            errors.append(f"{name} is available at {available_at}, used at {used_for}")
    return errors


def check_nonanticipativity(
    run: Callable[[Sequence[Any]], Sequence[Any]],
    path_a: Sequence[Any],
    path_b: Sequence[Any],
    split: int,
    tolerance: float = 0.0,
) -> Dict[str, Any]:
    """Run one procedure on two futures that share a prefix and must agree on it.

    ``path_a`` and ``path_b`` are identical up to ``split`` and differ afterwards.
    Anything the procedure decides inside the shared prefix must be identical in
    both runs; a difference there means the future was read. The report also says
    whether the two paths really share a prefix and really diverge -- a test where
    they do not is vacuous and passes for the wrong reason.
    """

    out_a = list(run(path_a))
    out_b = list(run(path_b))
    compared = min(split, len(out_a), len(out_b))
    max_deviation = 0.0
    first_mismatch: Optional[int] = None
    for index in range(compared):
        left, right = out_a[index], out_b[index]
        try:
            deviation = abs(float(left) - float(right))
        except (TypeError, ValueError):
            deviation = 0.0 if left == right else float("inf")
        max_deviation = max(max_deviation, deviation)
        if first_mismatch is None and deviation > tolerance:
            first_mismatch = index
    return {
        "passed": first_mismatch is None and compared == split,
        "compared": compared,
        "max_deviation": max_deviation,
        "first_mismatch": first_mismatch,
        "prefix_shared": list(path_a[:split]) == list(path_b[:split]),
        "paths_diverge": list(path_a[split:]) != list(path_b[split:]),
    }


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


def load_result(path: Union[str, Path]) -> Any:
    """Read a result file written by either the Python or the MATLAB side.

    ``.csv`` returns a list of row mappings and ``.json`` returns the decoded
    document, so a recomputation script does not care which language produced
    the file.  Empty CSV fields become ``None`` to match the shared convention
    that a missing value is written as an empty field.
    """

    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        return json.loads(file_path.read_text(encoding="utf-8"))
    if suffix != ".csv":
        raise ValueError(f"unsupported result format: {file_path.name}")
    with file_path.open(encoding="utf-8-sig", newline="") as handle:
        return [
            {key: (None if value == "" else value) for key, value in row.items()}
            for row in csv.DictReader(handle)
        ]


def write_check_report(
    checks_dir: Union[str, Path],
    exp_id: str,
    spec_id: str,
    checks: Sequence[Mapping[str, Any]],
) -> Path:
    """Write one recomputation report that ``check_case.py`` can read.

    Each check needs ``name``, ``kind`` and ``passed``; ``detail`` is optional.
    A failing check raises the matching deterministic risk flag during stage
    checks, so failures must be recorded honestly rather than omitted.
    """

    if not str(exp_id).strip():
        raise ValueError("exp_id is required")
    if not checks:
        raise ValueError("a report needs at least one check")

    normalized: List[Dict[str, Any]] = []
    for index, check in enumerate(checks):
        name = str(check.get("name", "")).strip()
        kind = str(check.get("kind", "")).strip()
        if not name:
            raise ValueError(f"check #{index} is missing a name")
        if kind not in CHECK_KINDS:
            raise ValueError(f"check {name!r} has unknown kind {kind!r}; use one of {sorted(CHECK_KINDS)}")
        if "passed" not in check:
            raise ValueError(f"check {name!r} is missing 'passed'")
        normalized.append(
            {
                "name": name,
                "kind": kind,
                "passed": bool(check["passed"]),
                "detail": str(check.get("detail", "")),
            }
        )

    target_dir = Path(checks_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "exp_id": str(exp_id).strip(),
        "spec_id": str(spec_id).strip(),
        "passed": all(item["passed"] for item in normalized),
        "checks": normalized,
    }
    target = target_dir / f"{report['exp_id']}.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return target


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
