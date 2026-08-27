"""Canonical gate, state, change-impact, and safe-check contract.

This module is the single machine-readable source for the competition
workflow.  Markdown protocol documents mirror it for human use; they must not
invent a second numbering scheme.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable


@dataclass(frozen=True)
class Gate:
    gate_id: str
    name: str
    state: str
    exit_evidence: str


GATES = (
    Gate("G0", "目标、题意与权限", "routed", "人工确认目标、交付物和权限边界"),
    Gate("G1", "输入和数据冻结", "frozen", "输入清单、来源、只读状态和哈希"),
    Gate("G2", "数据契约、假设、符号和指标", "contracted", "数据/模型契约、假设表和指标定义"),
    Gate("G3", "Baseline", "baseline_ready", "可解释 baseline、小案例和运行记录"),
    Gate("G4", "正式模型和算法", "model_ready", "公式、算法、代码版本和参数记录"),
    Gate("G5", "正确性、可行性与边界", "validated", "手算/穷举、维度、约束和边界检查"),
    Gate("G6", "结果可信度与稳健性", "results_verified", "对照、复算、敏感性和稳健性证据"),
    Gate("G7", "独立审核", "reviewed", "C1/C2/C3 审核记录和未解决问题"),
    Gate("G8", "修订与回归", "gate_passed", "变更影响、定向验证和关闭记录"),
    Gate("G9", "论文证据绑定", "paper_ready", "claim—实验—图表—引用映射"),
    Gate("G10", "官方格式和 AI 合规", "format_checked", "当届规则、匿名和 AI 记录预检"),
    Gate("G11", "LaTeX/PDF 检查", "pdf_qa_passed", "编译、文本、元数据、渲染和 PDF 哈希"),
    Gate("G12", "人工冻结", "human_frozen", "人工 signoff、最终提交文件和版本冻结"),
)

GATE_IDS = tuple(gate.gate_id for gate in GATES)
GATE_BY_ID = {gate.gate_id: gate for gate in GATES}

# The state names deliberately retain the existing intake/modeling vocabulary;
# the gate table above is the authority for their numbering.
MAIN_STATES = ("intake",) + tuple(gate.state for gate in GATES)
MAIN_TRANSITIONS = {
    left: right for left, right in zip(MAIN_STATES, MAIN_STATES[1:])
}

REVISION_STATES = (
    "revision_pending",
    "impact_classified",
    "targeted_validation",
    "validation_passed",
    "validation_failed",
    "restore_affected_gate",
)
REVISION_TRANSITIONS = {
    "gate_passed": "revision_pending",
    "revision_pending": "impact_classified",
    "impact_classified": "targeted_validation",
    "targeted_validation": ("validation_passed", "validation_failed"),
    "validation_failed": "targeted_validation",
    "validation_passed": "restore_affected_gate",
    "restore_affected_gate": "gate_passed",
}
STATES = MAIN_STATES + REVISION_STATES

CHANGE_LEVELS = ("R0", "R1", "R2", "R3")
CHANGE_SURFACES = (
    "text_only",
    "paper_claim",
    "code_only",
    "experiment_logic",
    "data_contract",
    "model_formula",
    "objective_constraint",
    "candidate_pdf",
)

# These are identifiers, not shell commands.  A record may request these
# checks, but no script executes arbitrary command strings from YAML.
SAFE_CHECK_IDS = frozenset(
    {
        "file_allowlist",
        "basic_markdown_latex_syntax",
        "latex_fast_compile",
        "claim_experiment_binding",
        "figure_table_source_check",
        "citation_crossref_check",
        "latex_compile",
        "code_tests",
        "small_case_check",
        "affected_experiment_rerun",
        "new_experiment_record",
        "output_hash",
        "claim_revalidation",
        "paper_consistency_check",
        "data_or_model_contract",
        "small_case_or_hand_check",
        "units_dimensions_check",
        "feasibility_check",
        "objective_recompute",
        "robustness_check",
        "independent_or_human_closure",
        "pdf_static_qa",
        "pdf_visual_qa",
        "pdf_hash",
    }
)

# The catalog is intentionally explicit. ``implemented`` means that the
# trusted runner has a deterministic implementation; ``manual_required``
# means that a human or an independent reviewer must supply signed evidence;
# ``not_implemented`` is a hard failure until a future runner is added.
CHECK_IMPLEMENTATION_STATUS = {
    "file_allowlist": "implemented",
    "basic_markdown_latex_syntax": "implemented",
    "latex_fast_compile": "implemented",
    "claim_experiment_binding": "implemented",
    "figure_table_source_check": "manual_required",
    "citation_crossref_check": "implemented",
    "latex_compile": "implemented",
    "code_tests": "implemented",
    "small_case_check": "manual_required",
    "affected_experiment_rerun": "manual_required",
    "new_experiment_record": "manual_required",
    "output_hash": "implemented",
    "claim_revalidation": "manual_required",
    "paper_consistency_check": "manual_required",
    "data_or_model_contract": "manual_required",
    "small_case_or_hand_check": "manual_required",
    "units_dimensions_check": "manual_required",
    "feasibility_check": "manual_required",
    "objective_recompute": "manual_required",
    "robustness_check": "manual_required",
    "independent_or_human_closure": "implemented",
    "pdf_static_qa": "implemented",
    "pdf_visual_qa": "manual_required",
    "pdf_hash": "implemented",
}

if set(CHECK_IMPLEMENTATION_STATUS) != SAFE_CHECK_IDS:  # pragma: no cover - contract guard
    raise RuntimeError("check implementation catalog must cover every safe check ID")

MINIMUM_AFFECTED_GATES = {
    "R0": frozenset(),
    "R1": frozenset({"G9", "G10", "G11"}),
    "R2": frozenset({"G4", "G5", "G6", "G8", "G9"}),
    "R3": frozenset({"G1", "G2", "G4", "G5", "G6", "G7", "G8", "G9"}),
}

BASE_CHECKS = {
    "R0": ["file_allowlist", "basic_markdown_latex_syntax"],
    "R1": [
        "file_allowlist",
        "claim_experiment_binding",
        "figure_table_source_check",
        "citation_crossref_check",
        "latex_compile",
        "paper_consistency_check",
    ],
    "R2": [
        "file_allowlist",
        "code_tests",
        "claim_experiment_binding",
        "small_case_check",
        "affected_experiment_rerun",
        "new_experiment_record",
        "output_hash",
        "claim_revalidation",
        "paper_consistency_check",
    ],
    "R3": [
        "file_allowlist",
        "claim_experiment_binding",
        "data_or_model_contract",
        "small_case_or_hand_check",
        "units_dimensions_check",
        "feasibility_check",
        "objective_recompute",
        "affected_experiment_rerun",
        "new_experiment_record",
        "output_hash",
        "robustness_check",
        "claim_revalidation",
        "independent_or_human_closure",
        "paper_consistency_check",
    ],
}


def _surface_policy(level: str, gates: frozenset[str], checks: list[str], reviews: tuple[str, ...] = ()) -> dict:
    return {"change_level": level, "affected_gates": gates, "required_checks": tuple(checks), "required_review_nodes": reviews}


SURFACE_POLICIES = {
    "text_only": _surface_policy("R0", frozenset(), BASE_CHECKS["R0"]),
    "paper_claim": _surface_policy("R1", MINIMUM_AFFECTED_GATES["R1"], BASE_CHECKS["R1"], ("C3",)),
    "code_only": _surface_policy("R2", MINIMUM_AFFECTED_GATES["R2"], BASE_CHECKS["R2"]),
    "experiment_logic": _surface_policy(
        "R2",
        frozenset({"G4", "G5", "G6", "G7", "G8", "G9"}),
        BASE_CHECKS["R2"] + ["independent_or_human_closure"],
        ("C2", "C3"),
    ),
    "data_contract": _surface_policy("R3", MINIMUM_AFFECTED_GATES["R3"], BASE_CHECKS["R3"], ("C1", "C2", "C3")),
    "model_formula": _surface_policy("R3", MINIMUM_AFFECTED_GATES["R3"], BASE_CHECKS["R3"], ("C2", "C3")),
    "objective_constraint": _surface_policy("R3", MINIMUM_AFFECTED_GATES["R3"], BASE_CHECKS["R3"], ("C1", "C2", "C3")),
    "candidate_pdf": _surface_policy(
        "R1",
        MINIMUM_AFFECTED_GATES["R1"],
        BASE_CHECKS["R1"] + ["pdf_static_qa", "pdf_visual_qa", "pdf_hash"],
    ),
}


def _dedupe(items: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(items))


def required_checks_for(
    change_level: str,
    changed_files: Iterable[str] = (),
    *,
    candidate_submission_pdf: bool = False,
    change_surfaces: Iterable[str] = (),
) -> list[str]:
    """Return safe check IDs for a change level; never return shell commands."""

    if change_level not in CHANGE_LEVELS:
        raise ValueError(f"unknown change level: {change_level}")
    paths = [PurePosixPath(path.replace("\\", "/")) for path in changed_files]
    surfaces = list(change_surfaces)
    invalid_surfaces = set(surfaces).difference(CHANGE_SURFACES)
    if invalid_surfaces:
        raise ValueError(f"unknown change surfaces: {sorted(invalid_surfaces)}")
    checks: list[str] = []
    if surfaces:
        for surface in surfaces:
            checks.extend(SURFACE_POLICIES[surface]["required_checks"])
        if "text_only" in surfaces and any(path.suffix in {".tex", ".sty", ".cls"} for path in paths):
            checks.append("latex_fast_compile")
    else:
        checks.extend(BASE_CHECKS[change_level])
        if change_level == "R0" and any(path.suffix in {".tex", ".sty", ".cls"} for path in paths):
            checks.append("latex_fast_compile")
    if candidate_submission_pdf and "candidate_pdf" not in surfaces:
        checks.extend(["pdf_static_qa", "pdf_visual_qa", "pdf_hash"])
    return _dedupe(checks)


def change_level_for_surfaces(change_surfaces: Iterable[str]) -> str:
    surfaces = list(change_surfaces)
    if not surfaces:
        raise ValueError("at least one change surface is required")
    invalid = set(surfaces).difference(CHANGE_SURFACES)
    if invalid:
        raise ValueError(f"unknown change surfaces: {sorted(invalid)}")
    return max((SURFACE_POLICIES[surface]["change_level"] for surface in surfaces), key={level: i for i, level in enumerate(CHANGE_LEVELS)}.get)


def affected_gates_for_surfaces(change_surfaces: Iterable[str]) -> list[str]:
    surfaces = list(change_surfaces)
    if not surfaces:
        return []
    gates: set[str] = set()
    for surface in surfaces:
        if surface not in SURFACE_POLICIES:
            raise ValueError(f"unknown change surface: {surface}")
        gates.update(SURFACE_POLICIES[surface]["affected_gates"])
    return [gate_id for gate_id in GATE_IDS if gate_id in gates]


def required_review_nodes_for(change_surfaces: Iterable[str]) -> list[str]:
    nodes: set[str] = set()
    for surface in change_surfaces:
        if surface not in SURFACE_POLICIES:
            raise ValueError(f"unknown change surface: {surface}")
        nodes.update(SURFACE_POLICIES[surface]["required_review_nodes"])
    return sorted(nodes)


def validate_gate_ids(gate_ids: Iterable[str]) -> list[str]:
    """Return invalid gate IDs while preserving the caller's order."""

    return [gate_id for gate_id in gate_ids if gate_id not in GATE_BY_ID]


def validate_revision_scope(
    change_level: str,
    affected_gates: Iterable[str],
    *,
    change_surfaces: Iterable[str] = (),
    gate_impact: str | None = None,
) -> tuple[bool, str]:
    """Check that a revision does not claim an implausibly small scope."""

    if change_level not in CHANGE_LEVELS:
        return False, f"unknown change level: {change_level}"
    surfaces = list(change_surfaces)
    if surfaces:
        invalid_surfaces = set(surfaces).difference(CHANGE_SURFACES)
        if invalid_surfaces:
            return False, f"unknown change surfaces: {sorted(invalid_surfaces)}"
        inferred_level = change_level_for_surfaces(surfaces)
        if inferred_level != change_level:
            return False, f"change level {change_level} disagrees with change surfaces {surfaces}"
        inferred_gates = set(affected_gates_for_surfaces(surfaces))
        if set(affected_gates) != inferred_gates:
            return False, f"affected gates do not match declared surfaces: expected {sorted(inferred_gates)}"
    affected = set(affected_gates)
    invalid = affected.difference(GATE_BY_ID)
    if invalid:
        return False, f"unknown affected gates: {sorted(invalid)}"
    if change_level == "R0":
        if gate_impact not in {None, "no_gate_impact"}:
            return False, "R0 must declare gate_impact=no_gate_impact"
        if affected:
            return False, "R0 cannot affect any Gate"
    elif gate_impact == "no_gate_impact":
        return False, f"{change_level} cannot declare no_gate_impact"
    if change_level in {"R0", "R1"} and affected.intersection({f"G{i}" for i in range(0, 9)}):
        return False, f"{change_level} cannot affect modeling gates G0-G8"
    if change_level == "R2" and affected.intersection({"G0", "G1", "G2", "G3"}):
        return False, "R2 cannot affect input, contract, or baseline gates G0-G3"
    return True, "ok"
