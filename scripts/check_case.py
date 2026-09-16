"""Cheap competition reminders: review nodes, real errors and key claims only."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

try:
    from .case_paths import reference_violation_code, resolve_in_case
    from .claim_evidence import board_experiment_ids, parse_source_experiment, validate_check_report
    from .check_spec import parse_spec
    from .experiment_board import parse_markdown_table
    from .ingest import statement_provenance_problem
    from .make_review_packet import _data_roots, node_decision
except ImportError:  # pragma: no cover
    from case_paths import reference_violation_code, resolve_in_case
    from claim_evidence import board_experiment_ids, parse_source_experiment, validate_check_report
    from check_spec import parse_spec
    from experiment_board import parse_markdown_table
    from ingest import statement_provenance_problem
    from make_review_packet import _data_roots, node_decision


CASE_LEVEL = "__case__"
ROUTES = {"optimization", "data_analysis", "hybrid", "insufficient_information"}
STAGES = {"exploration", "model_selection", "paper_claims", "final"}
PLACEHOLDERS = {"", "-", "—", "待填写", "待填", "待补充", "todo", "tbd", "n/a"}
RISK_LABELS = {
    "infeasible": "不可行结果",
    "objective_mismatch": "目标值复算不一致",
    "leakage": "数据泄漏",
    "split_overlap": "数据切分重叠",
}
REJECTED_FINDING = re.compile(
    r"^[ \t]*Rejected\s+finding[ \t]*[:：][ \t]*(.*?)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
REVIEWER_SIGNBACK = re.compile(
    r"^[ \t]*Reviewer\s+sign-back[ \t]*[:：][ \t]*(ACCEPT_REJECTION|REJECT_REJECTION)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
QUESTION_DIR = re.compile(r"^q[1-9][0-9]*$", re.IGNORECASE)
ROUTE_LINE = re.compile(
    r"^[ \t]*(?:推荐路由|Recommended\s+route|Route)[ \t]*[:：][ \t]*"
    r"(optimization|data_analysis|hybrid|insufficient_information)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
CHAMPION_LINE = re.compile(
    r"^[ \t]*(?:[-*][ \t]*)?(?:Champion|选定路线)[ \t]*[:：][ \t]*`?"
    r"(?P<route>M-[A-Za-z0-9_-]+)`?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
OPTION_ENUMERATION = re.compile(
    r"选项\s*[A-Z]|方案[一二三四五六七八九十]|\bA\s*[、,，/]\s*B\s*[、,，/]\s*C\b",
    re.IGNORECASE,
)
RECOMMENDED_ACTION = re.compile(
    r"^[ \t]*推荐动作[ \t]*[:：][ \t]*(.*?)[ \t]*$", re.MULTILINE
)
OUTPUT_REFERENCE = re.compile(
    r"(?<![A-Za-z0-9_-])(q[1-9][0-9]*/outputs/[A-Za-z0-9_./\-]+)", re.IGNORECASE
)
APPROVAL_MATTER = re.compile(r"^[ \t]*-[ \t]*事项[ \t]*[:：][ \t]*(.*)$", re.MULTILINE)
WAIT_ONLY_MATTER = re.compile(r"官方(?:材料|文字|数据).*冲突|授权扩张|最终提交")


@dataclass(frozen=True)
class Finding:
    level: str
    code: str
    reason: str
    owner: str
    node: str

    @property
    def blocks(self) -> bool:
        return self.level == "BLOCK"

    def render(self) -> str:
        return (
            f"{self.level} {self.code} | 原因：{self.reason} | 责任人：{self.owner} | "
            f"建议节点：{self.node} | 阻断：{'是' if self.blocks else '否'}"
        )


@dataclass(frozen=True)
class CaseReport:
    findings: tuple[Finding, ...]

    @property
    def blocked(self) -> bool:
        return any(item.blocks for item in self.findings)

    @property
    def exit_code(self) -> int:
        return int(self.blocked)


def _finding(level: str, code: str, reason: str, owner: str, node: str) -> Finding:
    return Finding(level, code, reason, owner, node)


def _has_value(value: Any) -> bool:
    normalized = " ".join(str(value or "").casefold().split()).strip(" .。_`'\"")
    return bool(normalized) and normalized not in PLACEHOLDERS


def _load_checkpoint(case_dir: Path) -> tuple[dict[str, Any] | None, str]:
    path = case_dir / "checkpoint.yaml"
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        return None, str(exc)
    return (payload, "") if isinstance(payload, dict) else (None, "顶层不是映射")


def _markdown_section(text: str, heading: str) -> str:
    match = re.search(
        rf"^[ \t]*##[ \t]+{re.escape(heading)}[ \t]*$\n(?P<body>.*?)(?=^[ \t]*##[ \t]+|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("body").strip().strip("`<>") if match else ""


def _pending_approval_findings(case_dir: Path, stage: str) -> list[Finding]:
    directory = case_dir / "队员工作区/待批准"
    files = sorted(directory.glob("*.md")) if directory.is_dir() else []
    if not files:
        return []

    invalid: list[str] = []
    for path in files:
        text = path.read_text(encoding="utf-8", errors="replace")
        action = _markdown_section(text, "不回应的默认动作")
        if action not in {"按推荐执行", "必须等待"}:
            invalid.append(f"{path.name} 的不回应默认动作必须是“按推荐执行”或“必须等待”")
            continue
        matter = APPROVAL_MATTER.search(text)
        if action == "必须等待" and (
            matter is None or WAIT_ONLY_MATTER.search(matter.group(1)) is None
        ):
            invalid.append(f"{path.name} 只有官方材料冲突、授权扩张、最终提交可以“必须等待”")

    findings: list[Finding] = []
    if invalid:
        findings.append(_finding(
            "BLOCK", "CHECKPOINT_INVALID", "；".join(invalid), "ORCHESTRATOR", "HUMAN",
        ))
    if stage == "final":
        findings.append(_finding(
            "BLOCK", "HUMAN_ONLY_BLOCK",
            f"队员工作区/待批准 中仍有 {len(files)} 项未裁决；最终提交必须等待队员处理",
            "HUMAN", "HUMAN",
        ))
    else:
        findings.append(_finding(
            "REMINDER", "PENDING_APPROVAL",
            f"队员工作区/待批准 中有 {len(files)} 项；普通取舍无回应时按批准单推荐继续",
            "ORCHESTRATOR", "HUMAN",
        ))
    return findings


def _question_context(
    case_dir: Path, checkpoint: Mapping[str, Any]
) -> tuple[str | None, Path, Mapping[str, Any]]:
    raw = str(checkpoint.get("current_question", "")).strip().casefold()
    if not raw:
        return None, case_dir, checkpoint
    questions = checkpoint.get("questions", {})
    questions = questions if isinstance(questions, Mapping) else {}
    state = questions.get(raw, {})
    state = state if isinstance(state, Mapping) else {}
    return raw, case_dir / raw, state


def _review_files(case_dir: Path, node: str, question: str | None = None) -> list[Path]:
    directory = (case_dir / "reviews") if question is None else (case_dir / question / "reviews")
    if not directory.is_dir():
        return []
    pattern = re.compile(rf"^{node}(?:[_. -].*)?\.md$", re.IGNORECASE)
    return sorted(path for path in directory.iterdir() if path.is_file() and pattern.fullmatch(path.name))


def _case_review_files(case_dir: Path, node: str) -> list[Path]:
    """Case-level review cards live beside the shared paper, not under a question."""

    directory = case_dir / "paper/reviews"
    if not directory.is_dir():
        return []
    pattern = re.compile(rf"^{node}(?:[_. -].*)?\.md$", re.IGNORECASE)
    return sorted(
        path for path in directory.iterdir() if path.is_file() and pattern.fullmatch(path.name)
    )


def _review_decision(
    case_dir: Path, node: str, question: str | None = None
) -> tuple[str | None, str]:
    failures: list[str] = []
    files = (
        _case_review_files(case_dir, node) if question == CASE_LEVEL
        else _review_files(case_dir, node, question)
    )
    for path in reversed(files):
        text = path.read_text(encoding="utf-8")
        decision = node_decision(text)
        if decision is None:
            failures.append(f"{path.name}: 未填写节点决定")
            continue
        rejection = REJECTED_FINDING.search(text)
        if rejection and _has_value(rejection.group(1)):
            signback = REVIEWER_SIGNBACK.search(text)
            if signback is None:
                failures.append(f"{path.name}: 拒绝 finding 但 Reviewer 未回签")
                continue
            if signback.group(1).upper() == "REJECT_REJECTION":
                failures.append(f"{path.name}: Reviewer 不接受拒绝理由")
                continue
        return decision, path.name
    where = "paper/reviews/" if question == CASE_LEVEL else "reviews/"
    return None, "; ".join(failures) or f"{where} 中没有 {node} 审核卡"


def _review_route(case_dir: Path, question: str) -> str | None:
    for path in reversed(_review_files(case_dir, "C1", question)):
        text = path.read_text(encoding="utf-8", errors="replace")
        if node_decision(text) is None:
            continue
        match = ROUTE_LINE.search(text)
        if match:
            return match.group(1).casefold()
    return None


def _review_card_policy_findings(case_dir: Path, question: str | None) -> list[Finding]:
    findings: list[Finding] = []
    paths: list[Path] = []
    nodes = ("C1", "C2", "C3")
    for node in nodes:
        paths.extend(_review_files(case_dir, node, question))
    for path in dict.fromkeys(paths):
        text = path.read_text(encoding="utf-8", errors="replace")
        if not OPTION_ENUMERATION.search(text):
            continue
        recommendation = RECOMMENDED_ACTION.search(text)
        if recommendation is None or not _has_value(recommendation.group(1)):
            findings.append(_finding(
                "REMINDER", "REVIEW_CARD_NO_RECOMMENDATION",
                f"{path.name} 列出了选项但没有非占位的推荐动作",
                "REVIEWER", "C1/C2/C3",
            ))
    return findings


def _legacy_review_findings(case_dir: Path, stage: str) -> list[Finding]:
    required = () if stage == "exploration" else (("C1", "C2") if stage == "model_selection" else ("C1", "C2", "C3"))
    findings: list[Finding] = []
    for node in required:
        decision, detail = _review_decision(case_dir, node)
        if decision is None:
            findings.append(_finding(
                "BLOCK", f"{node}_REQUIRED",
                f"{node} 尚无可执行决定（{detail}）；Orchestrator 应生成 Independent Reviewer 提示词，由队员人工启动",
                "ORCHESTRATOR", node,
            ))
        elif decision == "STOP":
            findings.append(_finding(
                "BLOCK", f"{node}_STOP",
                f"{node} 返回 STOP（{detail}）；由生产 AI 补证据、换路线或降结论，队员人工启动所需 Agent",
                "ORCHESTRATOR", node,
            ))
    return findings


def _board_path(work_dir: Path) -> Path:
    direct = work_dir / "board.md"
    return direct if direct.is_file() else work_dir / "experiments/board.md"


def _selected_route(work_dir: Path) -> str:
    brief = work_dir / "brief.md"
    if not brief.is_file():
        brief = work_dir / "case_brief.md"
    text = brief.read_text(encoding="utf-8", errors="replace") if brief.is_file() else ""
    match = CHAMPION_LINE.search(text)
    return match.group("route").upper() if match else ""


def _c2_trigger_reasons(work_dir: Path) -> list[str]:
    board = _board_path(work_dir)
    rows = parse_markdown_table(board.read_text(encoding="utf-8")) if board.is_file() else []
    champion = _selected_route(work_dir)

    def route_of(row: Mapping[str, Any]) -> str:
        return str(row.get("路线", row.get("候选路线", ""))).strip().upper()

    def is_pass(row: Mapping[str, Any]) -> bool:
        status = str(row.get("status", "")).strip().casefold()
        kind = str(row.get("类型", "")).strip().casefold()
        result = str(row.get("结果与判定", row.get("结果摘要", "")))
        return kind in {"probe", "reviewer_probe"} and status == "done" and re.search(
            r"\bPASS\b|判定\s*[:：]?\s*通过", result, re.IGNORECASE
        ) is not None

    reasons: list[str] = []
    if not champion or not any(route_of(row) == champion and is_pass(row) for row in rows):
        reasons.append("Champion 路线没有 status=done 且判定 PASS 的 probe")

    failed_by_route: dict[str, int] = {}
    for row in rows:
        if str(row.get("status", "")).strip().casefold() != "failed":
            continue
        route = route_of(row)
        if route:
            failed_by_route[route] = failed_by_route.get(route, 0) + 1
    repeated = sorted(route for route, count in failed_by_route.items() if count >= 2)
    if repeated:
        reasons.append(f"同一路线出现至少两行 failed：{'、'.join(repeated)}")

    risky_specs: list[str] = []
    specs_dir = work_dir / "specs"
    for path in sorted(specs_dir.glob("SPEC-*.md")) if specs_dir.is_dir() else []:
        if path.name.endswith(".questions.md"):
            continue
        spec, _ = parse_spec(path)
        result = spec.fields.get("probe_result", "").casefold() if spec else ""
        if result in {"waived", "pending"}:
            risky_specs.append(f"{path.name}={result.upper()}")
    if risky_specs:
        reasons.append(f"Full SPEC 的 probe_result 需挑战：{'、'.join(risky_specs)}")
    return reasons


def _deliverable_findings(work_dir: Path, question: str, stage: str) -> list[Finding]:
    """The deliverable contract is the anchor; an empty one makes the rest theatre.

    Every mechanism in the workbench points downwards -- weaken the claim, downgrade
    the route, refuse the unsupported sentence. None of them asks what the problem
    actually wanted delivered, so a chain of individually-correct downgrades can end
    somewhere far from the requirement with nothing lighting up. The contract is what
    the later checks compare against, so it has to be filled in first.
    """

    if stage not in {"model_selection", "paper_claims", "final"}:
        return []
    findings: list[Finding] = []
    brief = work_dir / "brief.md"
    text = brief.read_text(encoding="utf-8", errors="replace") if brief.is_file() else ""
    placeholder = "| D-01 | 场 / 序列 / 方案 / 分类 / 说明 |"
    if not text or "交付物契约" not in text or placeholder in text:
        findings.append(_finding(
            "REMINDER", "DELIVERABLE_CONTRACT_EMPTY",
            f"{question.upper()} 的交付物契约仍是模板占位；"
            "后面判断「做出来的东西还算不算题目要的」没有依据",
            "MODELER", "C1",
        ))

    board = work_dir / "board.md"
    board_text = board.read_text(encoding="utf-8", errors="replace") if board.is_file() else ""
    # 实验板出现降级，却没有一行说清降级后题面要求由什么承担。
    rows = [line for line in board_text.splitlines() if line.startswith("|") and "降级" in line]
    if rows and "承担" not in board_text:
        findings.append(_finding(
            "REMINDER", "DOWNGRADE_UNANSWERED",
            f"{question.upper()} 的实验板有降级记录，但没写降级后由什么承担交付物契约里的那一项",
            "MODELER", "C2",
        ))

    # 一条路不通不等于所有路不通。路线表里还有没试过的行却已经降级，说明跳过了换路。
    if rows:
        untried = [
            str(row.get("路线", "")).strip()
            for row in parse_markdown_table(text)
            if str(row.get("状态", "")).strip() == "待试"
        ]
        untried = [name for name in untried if name and name != "路线"]
        if untried:
            findings.append(_finding(
                "REMINDER", "UNTRIED_ROUTES",
                f"{question.upper()} 已有降级记录，但候选路线表里 {'、'.join(untried)} 仍是「待试」；"
                "换路应当在降级之前",
                "MODELER", "C2",
            ))
    return findings


def _single_route_findings(work_dir: Path, question: str, stage: str) -> list[Finding]:
    """One implemented route means there is nothing to compare it against.

    The workbench asks for six ideas and three routes on paper, then implements
    one -- so the race that justifies the choice never happens, and the paper has
    no comparison table to show for the work already done. This only reminds:
    a second route is a modelling judgement, not something a script can force.
    """

    if stage not in {"model_selection", "paper_claims", "final"}:
        return []
    specs_dir = work_dir / "specs"
    specs = [
        path for path in sorted(specs_dir.glob("SPEC-*.md"))
        if not path.name.endswith(".questions.md")
    ] if specs_dir.is_dir() else []
    if len(specs) >= 2:
        return []
    return [_finding(
        "REMINDER", "SINGLE_ROUTE",
        f"{question.upper()} 只有 {len(specs)} 条路线进入正式实现，统一对比表无从建立；"
        "第二条可以是同一路线的优化版或延伸版",
        "MODELER", "C2",
    )]


def _question_review_findings(
    case_dir: Path, question: str, work_dir: Path, stage: str
) -> list[Finding]:
    findings: list[Finding] = []
    c1_decision, c1_detail = _review_decision(case_dir, "C1", question)
    if c1_decision is None:
        findings.append(_finding(
            "REMINDER" if stage == "exploration" else "BLOCK", "C1_REQUIRED",
            f"{question.upper()} 尚无 C1 可执行决定（{c1_detail}）",
            "ORCHESTRATOR", "C1",
        ))
    elif c1_decision == "STOP":
        findings.append(_finding(
            "BLOCK", "C1_STOP", f"{question.upper()} 的 C1 返回 STOP（{c1_detail}）",
            "ORCHESTRATOR", "C1",
        ))

    # C2 每题必做，与 C1 同级。第三次实测里三条触发条件全假、C2 一次没跑，
    # 队员的结论是「c2 的一轮审核还是必要的，要不回去修改也耗费时间」——
    # 触发条件保留，但降级为审核卡里「本轮最担心什么」的输入，不再决定要不要审。
    if stage in {"model_selection", "paper_claims", "final"}:
        c2_decision, c2_detail = _review_decision(case_dir, "C2", question)
        if c2_decision == "STOP":
            findings.append(_finding(
                "BLOCK", "C2_STOP", f"{question.upper()} 的 C2 返回 STOP（{c2_detail}）",
                "ORCHESTRATOR", "C2",
            ))
        elif c2_decision is None:
            reasons = _c2_trigger_reasons(work_dir)
            detail = f"；本轮风险提示：{'；'.join(reasons)}" if reasons else ""
            findings.append(_finding(
                "BLOCK", "C2_REQUIRED",
                f"{question.upper()} 尚无 C2 可执行决定（{c2_detail}）{detail}",
                "ORCHESTRATOR", "C2",
            ))

    # C3 分两层：每题 D 结束一次，全案例收官前再一次。
    if stage in {"paper_claims", "final"}:
        c3_decision, c3_detail = _review_decision(case_dir, "C3", question)
        if c3_decision is None:
            findings.append(_finding(
                "REMINDER" if stage == "paper_claims" else "BLOCK", "C3_REQUIRED",
                f"{question.upper()} 尚无 C3 可执行决定（{c3_detail}）", "ORCHESTRATOR", "C3",
            ))
        elif c3_decision == "STOP":
            findings.append(_finding(
                "BLOCK", "C3_STOP", f"{question.upper()} 的 C3 返回 STOP（{c3_detail}）",
                "ORCHESTRATOR", "C3",
            ))
    return findings


def _case_c3_findings(case_dir: Path, stage: str) -> list[Finding]:
    """The whole-paper C3 that samples the highest-risk claims across questions."""

    if stage != "final":
        return []
    decision, detail = _review_decision(case_dir, "C3", CASE_LEVEL)
    if decision is None:
        return [_finding(
            "BLOCK", "CASE_C3_REQUIRED",
            f"全案例收官尚无 C3 可执行决定（{detail}）", "ORCHESTRATOR", "C3",
        )]
    if decision == "STOP":
        return [_finding(
            "BLOCK", "CASE_C3_STOP", f"全案例 C3 返回 STOP（{detail}）", "ORCHESTRATOR", "C3"
        )]
    return []


def _startup_findings(
    case_dir: Path,
    checkpoint: Mapping[str, Any],
    stage: str,
    question: str | None = None,
    work_dir: Path | None = None,
    question_state: Mapping[str, Any] | None = None,
) -> list[Finding]:
    level = "REMINDER" if stage == "exploration" else "BLOCK"
    findings: list[Finding] = []
    input_dir = case_dir / "input"
    local_materials = [
        path for path in input_dir.iterdir()
        if input_dir.is_dir() and path.is_file() and path.name.casefold() != "readme.md"
    ] if input_dir.is_dir() else []
    external_material = bool(_data_roots(case_dir))
    if not local_materials and not external_material:
        findings.append(_finding(
            level, "INPUT_MATERIAL_MISSING",
            "input/ 中没有题面或有效 data_root；可先准备材料，但不能冻结路线",
            "ORCHESTRATOR", "C1",
        ))
    if question and (case_dir / "sources.yaml").is_file():
        generated = (
            case_dir / "input/题面全文.md",
            case_dir / "input/数据清单.md",
            (work_dir or case_dir / question) / "数据范围.md",
        )
        missing_generated = [str(path.relative_to(case_dir)) for path in generated if not path.is_file()]
        if missing_generated:
            findings.append(_finding(
                level, "INPUT_MATERIAL_MISSING",
                f"阶段 0 尚未生成：{'、'.join(missing_generated)}；先运行 make ingest",
                "ORCHESTRATOR", "C1",
            ))
        statement = case_dir / "input/题面全文.md"
        if statement.is_file():
            provenance_problem = statement_provenance_problem(statement)
            if provenance_problem:
                findings.append(_finding(
                    level, "STATEMENT_PROVENANCE_INVALID", provenance_problem,
                    "ORCHESTRATOR", "C1",
                ))

    work_dir = work_dir or case_dir
    brief = work_dir / "brief.md" if question else case_dir / "case_brief.md"
    brief_text = brief.read_text(encoding="utf-8", errors="replace") if brief.is_file() else ""
    legacy_markers = (
        "- 用户真正要回答什么：\n", "| Q1 |  |  |  |  |", "- 数据文件和粒度：\n",
    )
    new_markers = ("- 本题要回答什么：\n", "- Champion：待 Probe", "- 数据范围：\n")
    markers = new_markers if question else legacy_markers
    if not brief_text or any(marker in brief_text for marker in markers):
        findings.append(_finding(
            level, "CASE_BRIEF_INCOMPLETE",
            f"{brief.relative_to(case_dir)} 仍缺研究目标、路线选择或数据说明",
            "MODELER", "C1",
        ))

    route_owner = question_state if question else checkpoint
    route_owner = route_owner if isinstance(route_owner, Mapping) else {}
    route = route_owner.get("route", {})
    route = route if isinstance(route, Mapping) else {}
    confirmed_by_c1 = bool(
        question
        and _review_route(case_dir, question) == str(route.get("value", "")).strip().casefold()
    )
    if route.get("confirmed_by_human") is not True and not confirmed_by_c1:
        findings.append(_finding(
            level, "ROUTE_CONFIRMATION_REQUIRED",
            "路由须由带节点决定且写明同一路由的 C1 卡确认；也可用 confirmed_by_human 覆盖",
            "ORCHESTRATOR", "C1",
        ))
    return findings


def _failed_experiment_findings(work_dir: Path) -> list[Finding]:
    board = _board_path(work_dir)
    if not board.is_file():
        return []
    failed = [
        row for row in parse_markdown_table(board.read_text(encoding="utf-8"))
        if str(row.get("status", "")).strip().casefold() == "failed"
    ]
    if not failed:
        return []
    routes = [str(row.get("路线", row.get("候选路线", ""))).strip() for row in failed]
    repeated = len(routes) >= 2 and (len(set(routes)) < len(routes) or len(set(routes)) >= 2)
    return [_finding(
        "REMINDER", "EXPERIMENT_FAILURE_PATTERN" if repeated else "EXPERIMENT_FAILURE_RECORDED",
        f"实验板已有 {len(failed)} 个失败试跑；保留证据并由 AI 调整，重复或跨路线失败时立即触发 C2",
        "ORCHESTRATOR", "C2" if repeated else "ENGINEER",
    )]


def _risk_findings(work_dir: Path, state: Mapping[str, Any], stage: str) -> list[Finding]:
    strong = stage in {"paper_claims", "final"}
    findings: list[Finding] = []
    risks = state.get("deterministic_risks", {})
    risks = risks if isinstance(risks, Mapping) else {}
    for key, label in RISK_LABELS.items():
        if risks.get(key) is True:
            findings.append(_finding(
                "BLOCK" if strong else "REMINDER", "DETERMINISTIC_ERROR",
                f"checkpoint 标记 {label}；修复并重跑相关实验后再写强结论",
                "ENGINEER", "C3" if key in {"leakage", "split_overlap"} else "C2",
            ))

    checks_dir = work_dir / "outputs/checks"
    if not checks_dir.is_dir():
        return findings
    for path in sorted(checks_dir.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            findings.append(_finding(
                "BLOCK" if strong else "REMINDER", "CHECK_REPORT_UNREADABLE",
                f"复算报告无法读取：{path.name}", "ENGINEER", "C3",
            ))
            continue
        checks = payload.get("checks") if isinstance(payload, Mapping) else None
        if not isinstance(checks, list):
            findings.append(_finding(
                "BLOCK" if strong else "REMINDER", "CHECK_REPORT_UNREADABLE",
                f"复算报告没有检查项：{path.name}", "ENGINEER", "C3",
            ))
            continue
        failed = [str(item.get("name", "unnamed")) for item in checks if isinstance(item, Mapping) and item.get("passed") is False]
        if failed:
            findings.append(_finding(
                "BLOCK" if strong else "REMINDER", "DETERMINISTIC_ERROR",
                f"{path.name} 未通过：{'、'.join(failed)}", "ENGINEER", "C3",
            ))
    return findings


def _cross_question_findings(work_dir: Path, question: str | None) -> list[Finding]:
    if question is None:
        return []
    paths = [work_dir / "brief.md", work_dir / "board.md", work_dir / "log.md"]
    specs_dir = work_dir / "specs"
    if specs_dir.is_dir():
        paths.extend(sorted(specs_dir.glob("SPEC-*.md")))
    for path in paths:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for reference in OUTPUT_REFERENCE.findall(text):
            code = reference_violation_code(reference, question)
            if code:
                return [_finding(
                    "BLOCK", code,
                    f"{path.relative_to(work_dir.parent)} 中 {question} 不得引用后续子问题 {reference}",
                    "MODELER", "C2",
                )]
    return []


def _claim_findings(
    case_dir: Path,
    stage: str,
    question: str | None = None,
    work_dir: Path | None = None,
    *,
    all_questions: bool = False,
) -> list[Finding]:
    if stage not in {"paper_claims", "final"}:
        return []
    path = case_dir / "paper/claim_map.md"
    level = "BLOCK" if stage == "final" else "REMINDER"
    if not path.is_file():
        return [_finding(level, "CLAIM_MAP_MISSING", "关键 Claim 尚未建立来源映射", "WRITER", "C3")]
    rows = [row for row in parse_markdown_table(path.read_text(encoding="utf-8")) if str(row.get("Claim ID", "")).strip().upper().startswith("CLM-")]
    if not rows:
        return [_finding(level, "CLAIM_MAP_EMPTY", "尚无已填写的关键 Claim；论文骨架可继续", "WRITER", "C3")]

    work_dir = work_dir or case_dir
    known_by_question: dict[str | None, set[str]] = {}

    def known_for(row_question: str | None) -> set[str]:
        if row_question in known_by_question:
            return known_by_question[row_question]
        if row_question:
            qdir = case_dir / row_question
            board = _board_path(qdir)
            rows_on_board = parse_markdown_table(board.read_text(encoding="utf-8")) if board.is_file() else []
            known = {
                str(row.get("实验 ID", "")).strip().casefold()
                for row in rows_on_board if str(row.get("实验 ID", "")).strip()
            }
        else:
            known = board_experiment_ids(case_dir)
        known_by_question[row_question] = known
        return known
    findings: list[Finding] = []
    for row in rows:
        claim_id = str(row.get("Claim ID", "")).strip()
        row_question = question
        if all_questions:
            candidate = str(row.get("子问题", "")).strip().casefold()
            if re.fullmatch(r"q[1-9][0-9]*", candidate):
                row_question = candidate
            else:
                findings.append(_finding(
                    "BLOCK", "CLAIM_SOURCE_MISSING",
                    f"{claim_id} 未声明有效子问题，无法绑定本题实验板",
                    "WRITER", "C3",
                ))
                continue
        known = known_for(row_question)
        source = parse_source_experiment(str(row.get("来源 EXP-ID", "")))
        if not source.ok or source.exp_id.casefold() not in known:
            findings.append(_finding("BLOCK", "CLAIM_SOURCE_MISSING", f"{claim_id} 的来源实验无效：{source.problem or source.exp_id}", "WRITER", "C3"))
            continue
        data_ref = str(row.get("数据文件", "")).strip().strip("`")
        if _has_value(data_ref):
            data_path = (
                resolve_in_case(case_dir, data_ref, "data", question=row_question)
                if row_question else None
            )
            if data_path is None:
                findings.append(_finding("BLOCK", "CLAIM_EVIDENCE_MISSING", f"{claim_id} 的数据文件不可用", "WRITER", "C3"))
        report_ref = str(row.get("复算报告", "")).strip().strip("`")
        if _has_value(report_ref):
            report_path = (
                resolve_in_case(case_dir, report_ref, "checks", question=row_question)
                if row_question else None
            )
            verdict = validate_check_report(report_path, source.exp_id) if report_path else None
            if verdict is None or not verdict.ok or verdict.has_failed_check:
                problem = verdict.problem if verdict else "路径不在允许的 checks 目录"
                findings.append(_finding("BLOCK", "CLAIM_CHECK_FAILED", f"{claim_id} 的复算报告无效或未通过：{problem}", "ENGINEER", "C3"))
        if str(row.get("状态", "")).strip().casefold() == "stale":
            findings.append(_finding("BLOCK", "CLAIM_STALE", f"{claim_id} 已过期", "WRITER", "C3"))
    return findings


def check_case(case_dir: Path, stage: str) -> CaseReport:
    if stage not in STAGES:
        raise ValueError(f"stage must be one of {sorted(STAGES)}")
    if not case_dir.is_dir():
        return CaseReport((_finding("BLOCK", "CASE_MISSING", f"案例目录不存在：{case_dir}", "ORCHESTRATOR", "HUMAN"),))
    checkpoint, error = _load_checkpoint(case_dir)
    if checkpoint is None:
        return CaseReport((_finding("BLOCK", "CHECKPOINT_INVALID", f"checkpoint.yaml 不可读：{error}", "ORCHESTRATOR", "HUMAN"),))

    findings: list[Finding] = []
    if str(checkpoint.get("case_id", "")).strip() != case_dir.name:
        findings.append(_finding("BLOCK", "CASE_ID_MISMATCH", "checkpoint case_id 与目录名不一致", "ORCHESTRATOR", "HUMAN"))
    question, work_dir, question_state = _question_context(case_dir, checkpoint)
    contexts: list[tuple[str | None, Path, Mapping[str, Any]]] = [
        (question, work_dir, question_state)
    ]
    raw_questions = checkpoint.get("questions", {})
    if question and stage == "final" and isinstance(raw_questions, Mapping):
        contexts = []
        for qname in sorted(
            raw_questions,
            key=lambda item: int(str(item)[1:]) if QUESTION_DIR.fullmatch(str(item)) else 10**9,
        ):
            state = raw_questions.get(qname, {})
            contexts.append((
                str(qname).casefold(), case_dir / str(qname).casefold(),
                state if isinstance(state, Mapping) else {},
            ))

    for qname, qdir, state in contexts:
        if qname and (not QUESTION_DIR.fullmatch(qname) or not qdir.is_dir()):
            findings.append(_finding(
                "BLOCK", "CHECKPOINT_INVALID",
                f"checkpoint 中 {qname!r} 没有对应目录", "ORCHESTRATOR", "HUMAN",
            ))
        route_owner = state if qname else checkpoint
        route = route_owner.get("route", {})
        route = route if isinstance(route, Mapping) else {}
        value = str(route.get("value", "")).strip()
        if value not in ROUTES:
            findings.append(_finding(
                "BLOCK", "ROUTE_MISSING", f"{(qname or '案例').upper()} 尚未写入正式路由",
                "MODELER", "C1",
            ))
        elif value == "insufficient_information":
            findings.append(_finding(
                "REMINDER", "ROUTE_UNRESOLVED",
                f"{(qname or '案例').upper()} 继续可逆探索并让 C1 给补证据动作", "MODELER", "C1",
            ))

        findings.extend(_startup_findings(
            case_dir, checkpoint, stage, qname, qdir, state
        ))

    human_block = str(checkpoint.get("human_block", "")).strip()
    if _has_value(human_block):
        findings.append(_finding("BLOCK", "HUMAN_ONLY_BLOCK", human_block, "HUMAN", "HUMAN"))
    findings.extend(_pending_approval_findings(case_dir, stage))

    if question:
        for index, (qname, qdir, state) in enumerate(contexts):
            if qname is None:
                continue
            findings.extend(_question_review_findings(case_dir, qname, qdir, stage))
            findings.extend(_single_route_findings(qdir, qname, stage))
            findings.extend(_deliverable_findings(qdir, qname, stage))
            findings.extend(_review_card_policy_findings(case_dir, qname))
            findings.extend(_cross_question_findings(qdir, qname))
            findings.extend(_failed_experiment_findings(qdir))
            findings.extend(_risk_findings(qdir, state, stage))
        findings.extend(_case_c3_findings(case_dir, stage))
    else:
        findings.extend(_legacy_review_findings(case_dir, stage))
        findings.extend(_review_card_policy_findings(case_dir, None))
        findings.extend(_failed_experiment_findings(case_dir))
        findings.extend(_risk_findings(case_dir, checkpoint, stage))
    findings.extend(_claim_findings(
        case_dir, stage, question, work_dir, all_questions=bool(question and stage == "final")
    ))
    return CaseReport(tuple(findings))


def main() -> int:
    parser = argparse.ArgumentParser(description="run cheap competition reminders")
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--stage", choices=sorted(STAGES), required=True)
    args = parser.parse_args()
    report = check_case(args.case_dir, args.stage)
    if not report.findings:
        print("OK | 当前阶段无提醒 | 责任人：- | 建议节点：- | 阻断：否")
    else:
        for finding in report.findings:
            print(finding.render())
    return report.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
