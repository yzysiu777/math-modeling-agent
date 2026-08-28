"""Run lightweight, stage-aware reminders for one competition case.

This checker deliberately validates visible evidence rather than inventing a
second workflow.  Reminders keep exploration moving; only route confirmation,
strong-claim review, final human decisions and deterministic risks can block
the corresponding stage.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

try:
    import yaml
except ImportError:  # pragma: no cover - installed by requirements-dev.txt
    yaml = None

try:
    from .experiment_board import parse_markdown_table
except ImportError:  # pragma: no cover - direct script execution
    from experiment_board import parse_markdown_table


ROUTES = frozenset({"optimization", "data_analysis", "hybrid", "insufficient_information"})
STAGES = frozenset({"exploration", "model_selection", "paper_claims", "final"})
PLACEHOLDERS = frozenset({"", "-", "—", "待填写", "待填", "待补充", "todo", "tbd", "n/a"})
RISK_LABELS = {
    "infeasible": ("确定性检查发现不可行结果", "C2"),
    "objective_mismatch": ("确定性检查发现目标值复算不一致", "C2"),
    "leakage": ("确定性检查发现数据泄漏", "C3"),
    "split_overlap": ("确定性检查发现数据切分重叠", "C3"),
}


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
        blocking = "是" if self.blocks else "否"
        return (
            f"{self.level} {self.code} | 原因：{self.reason} | "
            f"责任人：{self.owner} | 建议节点：{self.node} | 阻断：{blocking}"
        )


@dataclass(frozen=True)
class CaseReport:
    findings: tuple[Finding, ...]

    @property
    def blocked(self) -> bool:
        return any(finding.blocks for finding in self.findings)

    @property
    def exit_code(self) -> int:
        return 1 if self.blocked else 0


def _has_value(value: Any) -> bool:
    normalized = " ".join(str(value or "").casefold().split()).strip(" .。_`'\"")
    return bool(normalized) and normalized not in PLACEHOLDERS


def _is_true(value: Any) -> bool:
    return value is True or (isinstance(value, str) and value.strip().casefold() == "true")


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _finding(level: str, code: str, reason: str, owner: str, node: str) -> Finding:
    return Finding(level, code, reason, owner, node)


def _load_checkpoint(case_dir: Path) -> tuple[dict[str, Any] | None, str | None]:
    path = case_dir / "checkpoint.yaml"
    if not path.is_file():
        return None, f"缺少案例控制文件：{path}"
    if yaml is None:
        return None, "当前环境缺少 PyYAML，无法读取 checkpoint.yaml"
    try:
        with path.open(encoding="utf-8") as handle:
            payload = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError) as exc:
        return None, f"checkpoint.yaml 无法读取：{exc}"
    if not isinstance(payload, dict):
        return None, "checkpoint.yaml 顶层必须是可读的键值记录"
    return payload, None


def _review_files(case_dir: Path, node: str) -> list[Path]:
    reviews = case_dir / "reviews"
    if not reviews.is_dir():
        return []
    pattern = re.compile(rf"^{re.escape(node)}(?:\.md$|[_ -].*\.md$)", re.IGNORECASE)
    return sorted(
        path for path in reviews.iterdir()
        if path.is_file() and pattern.fullmatch(path.name)
    )


def _placeholder_only(line: str) -> bool:
    compact = re.sub(r"^[#>*\-\s]+", "", line).strip().casefold()
    return compact in PLACEHOLDERS or compact in {"todo", "placeholder", "..."}


def _review_errors(path: Path, node: str) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"文件无法读取：{exc}"]
    if not text.strip() or all(_placeholder_only(line) for line in text.splitlines() if line.strip()):
        return ["报告为空或只有占位内容"]
    checks = (
        ("节点", rf"(?<![A-Za-z0-9]){re.escape(node)}(?![A-Za-z0-9])"),
        ("结论/verdict", r"(?:结论|判定|审核结论|verdict|conclusion|decision)"),
        ("已检查范围", r"(?:已检查|检查范围|审核范围|checked|reviewed|scope)"),
        ("未检查范围", r"(?:未检查|未覆盖|未验证|未审|unchecked|unreviewed|not\s+checked|not\s+reviewed|out of scope|limitation)"),
    )
    errors = [label + "缺失" for label, pattern in checks if not re.search(pattern, text, re.IGNORECASE)]
    field_patterns = (
        ("结论", r"(?:结论|判定|审核结论|verdict|conclusion|decision)\s*[:：]\s*(.*?)\s*$"),
        ("已检查范围", r"(?:已检查(?:的)?(?:范围|内容|项)?|检查(?:的)?范围|审核范围|checked|reviewed|scope)\s*[:：]\s*(.*?)\s*$"),
        ("未检查范围", r"(?:未检查(?:的)?(?:范围|内容|项)?|未覆盖(?:的)?范围|未验证|未审|unchecked|unreviewed|not\s+checked|not\s+reviewed|out of scope|limitation)\s*[:：]\s*(.*?)\s*$"),
    )
    for label, pattern in field_patterns:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
        if match and not _has_value(match.group(1)):
            errors.append(label + "为空或只有占位内容")
    return errors


def _valid_review(case_dir: Path, node: str) -> tuple[bool, str]:
    candidates = _review_files(case_dir, node)
    if not candidates:
        return False, f"reviews/ 中没有 {node}_*.md 审核报告（README.md 不计入）"
    failures = []
    for path in candidates:
        errors = _review_errors(path, node)
        if not errors:
            return True, path.name
        failures.append(f"{path.name}: {'、'.join(errors)}")
    return False, "; ".join(failures)


def _review_note(checkpoint: Mapping[str, Any], node: str) -> str:
    notes = _mapping(checkpoint.get("review_notes"))
    return str(notes.get(node, checkpoint.get(f"{node}_note", "")) or "")


def _review_status(checkpoint: Mapping[str, Any], node: str) -> str:
    reviews = _mapping(checkpoint.get("reviews"))
    return str(reviews.get(node, "pending") or "pending").strip().casefold()


def _brief_has_route_changing_ambiguity(case_dir: Path) -> bool:
    path = case_dir / "case_brief.md"
    if not path.is_file():
        return False
    pattern = re.compile(r"^\s*-\s*(会改变路线的歧义|当前疑点)\s*[：:]\s*(.*?)\s*$")
    return any(
        (match := pattern.match(line)) is not None and _has_value(match.group(2))
        for line in path.read_text(encoding="utf-8").splitlines()
    )


def _routing_findings(
    checkpoint: Mapping[str, Any] | None,
    checkpoint_error: str | None,
    stage: str,
) -> tuple[list[Finding], str | None]:
    if checkpoint is None:
        level = "REMINDER" if stage == "exploration" else "BLOCK"
        return [
            _finding(level, "ROUTE_CONFIRMATION_REQUIRED", checkpoint_error or "案例控制文件不可用", "HUMAN", "HUMAN")
        ], None
    routing = _mapping(checkpoint.get("routing"))
    suggested = str(routing.get("suggested", "") or "").strip()
    if suggested not in ROUTES:
        return [
            _finding(
                "BLOCK", "ROUTE_CONFIRMATION_REQUIRED",
                f"checkpoint.yaml 的 suggested 路由无效：{suggested or '<empty>'}；请先依据完整题面修正",
                "HUMAN", "HUMAN",
            )
        ], None
    confirmed = routing.get("confirmed", False)
    if confirmed is True:
        confirmed_route = str(routing.get("confirmed_route", "") or "").strip()
        missing = [
            label for label, value in (
                ("confirmed_route", confirmed_route),
                ("confirmed_by", routing.get("confirmed_by", "")),
                ("note", routing.get("note", "")),
            ) if not _has_value(value)
        ]
        if confirmed_route not in ROUTES:
            missing.append("confirmed_route（必须是四类路由之一）")
        if missing:
            return [
                _finding(
                    "BLOCK", "ROUTE_CONFIRMATION_REQUIRED",
                    "confirmed=true 但人工确认记录不完整：" + "、".join(missing),
                    "HUMAN", "HUMAN",
                )
            ], None
        return [], confirmed_route
    if confirmed is not False:
        return [
            _finding("BLOCK", "ROUTE_CONFIRMATION_REQUIRED", "confirmed 必须明确为 true 或 false", "HUMAN", "HUMAN")
        ], None
    level = "REMINDER" if stage == "exploration" else "BLOCK"
    return [
        _finding(
            level, "ROUTE_CONFIRMATION_REQUIRED",
            f"路由器建议为 {suggested}，但尚未由队员结合完整题面确认；探索可继续，正式路线冻结前请确认一次",
            "HUMAN", "HUMAN",
        )
    ], suggested


def _comparison_missing(case_dir: Path) -> list[str]:
    path = case_dir / "models/comparison.md"
    if not path.is_file():
        return ["Champion", "Challenger"]
    text = path.read_text(encoding="utf-8")
    missing = []
    for label in ("Champion", "Challenger"):
        pattern = re.compile(
            rf"(?:^|[|;；])\s*(?:[-*]\s*)?(?:当前\s*)?{label}\s*[：:]\s*([^|;；\n]*)",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(text)
        if not match or not _has_value(match.group(1)):
            missing.append(label)
    return missing


def _failure_findings(case_dir: Path) -> list[Finding]:
    path = case_dir / "experiments/board.md"
    if not path.is_file():
        return []
    rows = parse_markdown_table(path.read_text(encoding="utf-8"))
    failed = [row for row in rows if row.get("status", "").strip().casefold() == "failed"]
    if not failed:
        return []
    routes = [row.get("候选路线", "").strip().casefold() for row in failed if _has_value(row.get("候选路线", ""))]
    route_counts = Counter(routes)
    if any(count >= 2 for count in route_counts.values()) or len(route_counts) >= 2:
        return [
            _finding(
                "REMINDER", "EXPERIMENT_FAILURE_PATTERN",
                f"已记录 {len(failed)} 个 failed 实验，存在同一路线重复失败或多路线失败；请核对实验口径并决定是否触发 C2",
                "HUMAN", "C2",
            )
        ]
    return [
        _finding(
            "REMINDER", "EXPERIMENT_FAILURE_RECORDED",
            "已有单个 failed 实验；请保留失败证据并决定是否继续，不自动阻断探索",
            "HUMAN", "HUMAN",
        )
    ]


def _risk_findings(checkpoint: Mapping[str, Any], stage: str) -> list[Finding]:
    findings: list[Finding] = []
    if _is_true(checkpoint.get("performance_concern")):
        findings.append(
            _finding(
                "REMINDER", "HUMAN_DECISION_REQUIRED",
                "checkpoint 已标记性能/效果担忧；请由队员检查比较口径并考虑触发 C2",
                "HUMAN", "C2",
            )
        )
    risks = _mapping(checkpoint.get("deterministic_risks"))
    for key, (label, node) in RISK_LABELS.items():
        if _is_true(risks.get(key)):
            level = "BLOCK" if stage in {"paper_claims", "final"} else "REMINDER"
            findings.append(
                _finding(
                    level, "DETERMINISTIC_ERROR_BLOCK",
                    f"{label}；在写入强结论或最终提交前必须修复、复算或由队员明确处理",
                    "HUMAN", node,
                )
            )
    return findings


def _decision_covers_node(case_dir: Path, node: str) -> bool:
    path = case_dir / "decisions.md"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    node_pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(node)}(?![A-Za-z0-9])", re.IGNORECASE)
    choice_pattern = re.compile(
        r"(?:接受|采纳|拒绝|不采纳|延期|暂缓|保留|accept(?:ed)?|reject(?:ed)?|defer(?:red)?)",
        re.IGNORECASE,
    )
    placeholder_choice = re.compile(r"accept\s*/\s*reject|pause\s*/\s*defer", re.IGNORECASE)
    return any(
        node_pattern.search(line)
        and choice_pattern.search(line)
        and not placeholder_choice.search(line)
        for line in text.splitlines()
    )


def check_case(case_dir: Path, stage: str) -> CaseReport:
    """Return visible reminders and blockers for one case and one stage."""

    if stage not in STAGES:
        raise ValueError(f"stage must be one of {sorted(STAGES)}")
    if not case_dir.is_dir():
        return CaseReport((
            _finding("BLOCK", "ROUTE_CONFIRMATION_REQUIRED", f"案例目录不存在：{case_dir}", "HUMAN", "HUMAN"),
        ))

    checkpoint, checkpoint_error = _load_checkpoint(case_dir)
    findings, effective_route = _routing_findings(checkpoint, checkpoint_error, stage)
    if checkpoint is None:
        return CaseReport(tuple(findings))
    if not _has_value(checkpoint.get("case_id")):
        findings.insert(
            0,
            _finding("BLOCK", "ROUTE_CONFIRMATION_REQUIRED", "checkpoint.yaml 缺少 case_id，无法确认它属于当前案例", "HUMAN", "HUMAN"),
        )

    route_unclear = effective_route == "insufficient_information"
    c1_needed = route_unclear or _brief_has_route_changing_ambiguity(case_dir)
    c1_valid, c1_detail = _valid_review(case_dir, "C1")
    c1_status = _review_status(checkpoint, "C1")
    if c1_status == "not_needed" and _has_value(_review_note(checkpoint, "C1")) and not route_unclear:
        pass
    elif c1_status == "complete" and not c1_valid:
        level = "REMINDER" if stage == "exploration" else "BLOCK"
        findings.append(
            _finding(
                level, "C1_RECOMMENDED",
                f"C1 被标为 complete，但没有有效报告（{c1_detail}）；不能只改控制文件绕过审核记录",
                "HUMAN", "C1",
            )
        )
    elif c1_needed and not c1_valid:
        findings.append(
            _finding(
                "REMINDER", "C1_RECOMMENDED",
                f"C1 题意挑战尚未留下有效报告（{c1_detail}）；请由队员判断歧义并可手动触发 Claude C1",
                "HUMAN", "C1",
            )
        )
    elif c1_status == "not_needed" and not _has_value(_review_note(checkpoint, "C1")):
        level = "REMINDER" if stage == "exploration" else "BLOCK"
        findings.append(
            _finding(level, "C1_RECOMMENDED", "C1 被标为 not_needed，但没有留下简短理由，不能用空状态绕过记录", "HUMAN", "C1")
        )

    c2_valid, c2_detail = _valid_review(case_dir, "C2")
    if stage in {"model_selection", "paper_claims", "final"} and not c2_valid:
        findings.append(
            _finding(
                "REMINDER", "C2_RECOMMENDED",
                f"进入正式模型/路线取舍阶段但没有有效 C2 报告（{c2_detail}）；请由队员触发 Claude C2",
                "HUMAN", "C2",
            )
        )

    claims_active = _is_true(checkpoint.get("paper_claims_active"))
    c3_required = stage in {"paper_claims", "final"} or claims_active
    c3_valid, c3_detail = _valid_review(case_dir, "C3")
    if c3_required and not c3_valid:
        findings.append(
            _finding(
                "BLOCK", "C3_REQUIRED",
                f"当前阶段准备写入论文强结论，但没有有效 C3 报告（{c3_detail}）；先完成 C3 复核",
                "HUMAN", "C3",
            )
        )

    findings.extend(_failure_findings(case_dir))
    findings.extend(_risk_findings(checkpoint, stage))

    missing_comparison = _comparison_missing(case_dir)
    if missing_comparison:
        level = "BLOCK" if stage == "final" else "REMINDER"
        findings.append(
            _finding(
                level, "HUMAN_DECISION_REQUIRED",
                "models/comparison.md 尚未明确 " + "、".join(missing_comparison) + "；请由队员完成路线取舍记录",
                "HUMAN", "HUMAN",
            )
        )

    if stage in {"paper_claims", "final"}:
        for node, valid in (("C1", c1_valid), ("C2", c2_valid), ("C3", c3_valid)):
            if valid and not _decision_covers_node(case_dir, node):
                level = "BLOCK" if stage == "final" else "REMINDER"
                findings.append(
                    _finding(
                        level, "HUMAN_DECISION_REQUIRED",
                        f"{node} 报告已存在，但 decisions.md 没有对应的接受、拒绝或延期记录",
                        "HUMAN", "HUMAN",
                    )
                )
    return CaseReport(tuple(findings))


def main() -> int:
    parser = argparse.ArgumentParser(description="check one case for lightweight human-review reminders")
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
