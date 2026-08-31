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
    from .claim_evidence import board_experiment_ids, parse_source_experiment, validate_check_report
    from .experiment_board import parse_markdown_table
    from .make_review_packet import _data_roots
except ImportError:  # pragma: no cover
    from claim_evidence import board_experiment_ids, parse_source_experiment, validate_check_report
    from experiment_board import parse_markdown_table
    from make_review_packet import _data_roots


ROUTES = {"optimization", "data_analysis", "hybrid", "insufficient_information"}
STAGES = {"exploration", "model_selection", "paper_claims", "final"}
PLACEHOLDERS = {"", "-", "—", "待填写", "待填", "待补充", "todo", "tbd", "n/a"}
RISK_LABELS = {
    "infeasible": "不可行结果",
    "objective_mismatch": "目标值复算不一致",
    "leakage": "数据泄漏",
    "split_overlap": "数据切分重叠",
}
NODE_DECISION = re.compile(
    r"^[ \t]*Node\s+decision[ \t]*[:：][ \t]*(GO|GO_WITH_FIXES|STOP)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
REJECTED_FINDING = re.compile(
    r"^[ \t]*Rejected\s+finding[ \t]*[:：][ \t]*(.*?)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
REVIEWER_SIGNBACK = re.compile(
    r"^[ \t]*Reviewer\s+sign-back[ \t]*[:：][ \t]*(ACCEPT_REJECTION|REJECT_REJECTION)[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)


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


def _review_files(case_dir: Path, node: str) -> list[Path]:
    directory = case_dir / "reviews"
    if not directory.is_dir():
        return []
    pattern = re.compile(rf"^{node}(?:[_. -].*)?\.md$", re.IGNORECASE)
    return sorted(path for path in directory.iterdir() if path.is_file() and pattern.fullmatch(path.name))


def _review_decision(case_dir: Path, node: str) -> tuple[str | None, str]:
    failures: list[str] = []
    for path in reversed(_review_files(case_dir, node)):
        text = path.read_text(encoding="utf-8")
        match = NODE_DECISION.search(text)
        if match is None:
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
        return match.group(1).upper(), path.name
    return None, "; ".join(failures) or f"reviews/ 中没有 {node} 审核卡"


def _review_findings(case_dir: Path, stage: str) -> list[Finding]:
    required = () if stage == "exploration" else (("C1", "C2") if stage == "model_selection" else ("C1", "C2", "C3"))
    findings: list[Finding] = []
    for node in required:
        decision, detail = _review_decision(case_dir, node)
        if decision is None:
            findings.append(_finding(
                "BLOCK", f"{node}_REQUIRED",
                f"{node} 尚无可执行决定（{detail}）；Orchestrator 应生成外部 Claude 提示词，由队员人工启动",
                "ORCHESTRATOR", node,
            ))
        elif decision == "STOP":
            findings.append(_finding(
                "BLOCK", f"{node}_STOP",
                f"{node} 返回 STOP（{detail}）；由生产 AI 补证据、换路线或降结论，队员人工启动所需 Agent",
                "ORCHESTRATOR", node,
            ))
    return findings


def _startup_findings(case_dir: Path, checkpoint: Mapping[str, Any], stage: str) -> list[Finding]:
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

    brief = case_dir / "case_brief.md"
    brief_text = brief.read_text(encoding="utf-8", errors="replace") if brief.is_file() else ""
    if not brief_text or any(marker in brief_text for marker in (
        "- 用户真正要回答什么：\n", "| Q1 |  |  |  |  |", "- 数据文件和粒度：\n",
    )):
        findings.append(_finding(
            level, "CASE_BRIEF_INCOMPLETE",
            "case_brief.md 仍缺研究目标、子问题或数据说明",
            "MODELER", "C1",
        ))

    route = checkpoint.get("route", {})
    route = route if isinstance(route, Mapping) else {}
    if route.get("confirmed_by_human") is not True:
        findings.append(_finding(
            level, "ROUTE_CONFIRMATION_REQUIRED",
            "Router 仅供参考；Modeler 提出正式路由后需队员确认一次",
            "HUMAN", "C1",
        ))
    return findings


def _failed_experiment_findings(case_dir: Path) -> list[Finding]:
    board = case_dir / "experiments/board.md"
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


def _risk_findings(case_dir: Path, checkpoint: Mapping[str, Any], stage: str) -> list[Finding]:
    strong = stage in {"paper_claims", "final"}
    findings: list[Finding] = []
    risks = checkpoint.get("deterministic_risks", {})
    risks = risks if isinstance(risks, Mapping) else {}
    for key, label in RISK_LABELS.items():
        if risks.get(key) is True:
            findings.append(_finding(
                "BLOCK" if strong else "REMINDER", "DETERMINISTIC_ERROR",
                f"checkpoint 标记 {label}；修复并重跑相关实验后再写强结论",
                "ENGINEER", "C3" if key in {"leakage", "split_overlap"} else "C2",
            ))

    checks_dir = case_dir / "experiments/outputs/checks"
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


def _claim_findings(case_dir: Path, stage: str) -> list[Finding]:
    if stage not in {"paper_claims", "final"}:
        return []
    path = case_dir / "paper/claim_map.md"
    level = "BLOCK" if stage == "final" else "REMINDER"
    if not path.is_file():
        return [_finding(level, "CLAIM_MAP_MISSING", "关键 Claim 尚未建立来源映射", "WRITER", "C3")]
    rows = [row for row in parse_markdown_table(path.read_text(encoding="utf-8")) if str(row.get("Claim ID", "")).strip().upper().startswith("CLM-")]
    if not rows:
        return [_finding(level, "CLAIM_MAP_EMPTY", "尚无已填写的关键 Claim；论文骨架可继续", "WRITER", "C3")]

    known = board_experiment_ids(case_dir)
    findings: list[Finding] = []
    for row in rows:
        claim_id = str(row.get("Claim ID", "")).strip()
        source = parse_source_experiment(str(row.get("来源 EXP-ID", "")))
        if not source.ok or source.exp_id.casefold() not in known:
            findings.append(_finding("BLOCK", "CLAIM_SOURCE_MISSING", f"{claim_id} 的来源实验无效：{source.problem or source.exp_id}", "WRITER", "C3"))
            continue
        data_ref = str(row.get("数据文件", "")).strip().strip("`")
        if _has_value(data_ref):
            data_path = case_dir / data_ref
            allowed = (case_dir / "experiments/outputs/data").resolve()
            try:
                if not data_path.is_file() or allowed not in data_path.resolve().parents:
                    raise ValueError
            except (OSError, ValueError):
                findings.append(_finding("BLOCK", "CLAIM_EVIDENCE_MISSING", f"{claim_id} 的数据文件不可用", "WRITER", "C3"))
        report_ref = str(row.get("复算报告", "")).strip().strip("`")
        if _has_value(report_ref):
            report_path = case_dir / report_ref
            verdict = validate_check_report(report_path, source.exp_id)
            if not verdict.ok or verdict.has_failed_check:
                findings.append(_finding("BLOCK", "CLAIM_CHECK_FAILED", f"{claim_id} 的复算报告无效或未通过：{verdict.problem}", "ENGINEER", "C3"))
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
    route = checkpoint.get("route", {})
    route = route if isinstance(route, Mapping) else {}
    value = str(route.get("value", "")).strip()
    if value not in ROUTES:
        findings.append(_finding("BLOCK", "ROUTE_MISSING", "Modeler 尚未写入正式路由", "MODELER", "C1"))
    elif value == "insufficient_information":
        findings.append(_finding("REMINDER", "ROUTE_UNRESOLVED", "继续可逆探索并让 C1 给补证据动作", "MODELER", "C1"))

    findings.extend(_startup_findings(case_dir, checkpoint, stage))

    human_block = str(checkpoint.get("human_block", "")).strip()
    if _has_value(human_block):
        findings.append(_finding("BLOCK", "HUMAN_ONLY_BLOCK", human_block, "HUMAN", "HUMAN"))

    findings.extend(_review_findings(case_dir, stage))
    findings.extend(_failed_experiment_findings(case_dir))
    findings.extend(_risk_findings(case_dir, checkpoint, stage))
    findings.extend(_claim_findings(case_dir, stage))
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
