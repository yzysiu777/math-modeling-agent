"""Run lightweight, stage-aware reminders for one competition case.

This checker deliberately validates visible evidence rather than inventing a
second workflow.  Reminders keep exploration moving; only route confirmation,
strong-claim review, final human decisions and deterministic risks can block
the corresponding stage.
"""

from __future__ import annotations

import argparse
import json
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

try:
    from .case_paths import clean_reference, is_traversal, resolve_in_case
    from .claim_evidence import (board_experiment_ids, describe_missing_source,
                                 parse_source_experiment, validate_check_report)
except ImportError:  # pragma: no cover - direct script execution
    from case_paths import clean_reference, is_traversal, resolve_in_case
    from claim_evidence import (board_experiment_ids, describe_missing_source,
                                parse_source_experiment, validate_check_report)


ROUTES = frozenset({"optimization", "data_analysis", "hybrid", "insufficient_information"})
STAGES = frozenset({"exploration", "model_selection", "paper_claims", "final"})
PLACEHOLDERS = frozenset({"", "-", "—", "待填写", "待填", "待补充", "todo", "tbd", "n/a"})
RISK_LABELS = {
    "infeasible": ("确定性检查发现不可行结果", "C2"),
    "objective_mismatch": ("确定性检查发现目标值复算不一致", "C2"),
    "leakage": ("确定性检查发现数据泄漏", "C3"),
    "split_overlap": ("确定性检查发现数据切分重叠", "C3"),
}

_REVIEW_FIELDS = (
    (
        "conclusion",
        "结论/verdict",
        r"(?:结论|判定|审核结论|verdict|conclusion|decision)",
    ),
    (
        "checked",
        "已检查范围",
        r"(?:已检查(?:的)?(?:范围|内容|项)?|检查(?:的)?范围|审核范围|checked(?:\s+scope)?|reviewed(?:\s+scope)?|what\s+was\s+checked|what_was_checked|scope)",
    ),
    (
        "unchecked",
        "未检查范围",
        r"(?:未检查(?:的)?(?:范围|内容|项)?|未覆盖(?:的)?范围|未验证|未审|unchecked(?:\s+scope)?|unreviewed(?:\s+scope)?|what\s+was\s+not\s+checked|what_was_not_checked|not\s+checked|not\s+reviewed|out\s+of\s+scope|limitation)",
    ),
)
_REVIEW_FIELD_LABELS = re.compile(
    r"^(?:" + "|".join(
        rf"(?P<{key}>{pattern})(?:\s*/\s*(?:verdict|conclusion|decision|checked\s+scope|reviewed\s+scope|unchecked\s+scope))?"
        for key, _label, pattern in _REVIEW_FIELDS
    ) + r")\s*(?:[:：]\s*(?P<inline>.*))?$",
    re.IGNORECASE,
)
_REVIEW_PLACEHOLDER = re.compile(
    r"^(?:todo|tbd|n/?a|placeholder|待填写|待填|待补充)"
    r"(?:\s*[/\\,:：;；\-—–]\s*(?:todo|tbd|n/?a|placeholder|待填写|待填|待补充))*$",
    re.IGNORECASE,
)
_DECISION_TOKEN = re.compile(
    r"(?:不接受|不采纳|接受|采纳|拒绝|延期|暂缓|推迟|保留|"
    r"accept(?:ed)?|reject(?:ed)?|defer(?:red)?)",
    re.IGNORECASE,
)
_REASON_LABEL = re.compile(
    r"^(?:原因|理由|说明|备注|reason|rationale|justification|because|due\s+to|因为|由于|依据|基于)\s*[:：]?\s*",
    re.IGNORECASE,
)
_DECISION_HEADER = re.compile(
    r"^(?:决定|决策|选择|decision|choice)(?:\s*/\s*(?:decision|choice))?$",
    re.IGNORECASE,
)
_REASON_HEADER = re.compile(
    r"(?:原因|理由|说明|备注|reason|rationale|justification|evidence|note)",
    re.IGNORECASE,
)
_REVIEW_METADATA_FIELDS = {
    "review_id": r"(?:review[_\s]+id)",
    "case_id": r"(?:case[_\s]+id)",
    "reviewer_provider": r"(?:reviewer[_\s]+provider)",
    "reviewer_model": r"(?:reviewer[_\s]+model)",
    "review_session": r"(?:review[_\s]+session)",
    "saw_main_conversation": r"(?:saw[_\s]+main[_\s]+conversation)",
    "critical_node": r"(?:critical[_\s]+node)",
}
_REVIEW_METADATA_LINE = re.compile(
    r"^\s*(?:#{1,6}\s+|>\s*|[-*+]\s+)?(?P<label>"
    + "|".join(
        rf"(?P<{key}>{pattern})" for key, pattern in _REVIEW_METADATA_FIELDS.items()
    )
    + r")\s*[:：]\s*(?P<value>.*?)\s*$",
    re.IGNORECASE,
)


_SPEC_FM_LINE = re.compile(r"^(?P<key>[A-Za-z_][A-Za-z0-9_]*)\s*:\s*(?P<value>.*?)\s*$")
_SPEC_ROUTE_HEADING = re.compile(
    r"^\s*#{2,4}\s+(?P<route>M-[A-Za-z0-9][A-Za-z0-9_-]*)(?:\s*.*)?\s*$", re.IGNORECASE
)
_SPEC_SELECTED_STATUS = re.compile(r"`?(?P<role>champion|challenger)`?", re.IGNORECASE)
_SPEC_ROUTE_ID = re.compile(r"M-[A-Za-z0-9][A-Za-z0-9_-]*", re.IGNORECASE)
_SPEC_CLAIM_ID = re.compile(r"^`?CLM-[A-Za-z0-9_-]+`?$", re.IGNORECASE)
_SPEC_EXP_ID = re.compile(r"EXP-[A-Za-z0-9][A-Za-z0-9_-]*", re.IGNORECASE)
_TEMPLATE_TOKEN = re.compile(r"<[^<>]{1,80}>")
_SPEC_FIGURE_ID = re.compile(r"(?:FIG|TAB)-[A-Za-z0-9][A-Za-z0-9_-]*", re.IGNORECASE)
_MARKDOWN_HEADING = re.compile(r"^\s*#{1,6}\s+\S")


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


def _has_metadata_value(value: Any) -> bool:
    """Reject empty/template metadata without changing general field semantics."""

    normalized = " ".join(str(value or "").casefold().split()).strip(" .。_`'\"")
    if not _has_value(value):
        return False
    if re.fullmatch(r"<[^>]+>", normalized):
        return False
    return normalized not in {"none", "null", "unknown", "未提供", "未知"}


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


def _review_text(value: Any) -> str:
    """Remove presentation-only Markdown characters before checking substance."""

    text = str(value or "").strip()
    text = re.sub(r"^\s*(?:#{1,6}\s*|>\s*|[-*+]\s+|\d+[.)]\s*)", "", text)
    text = re.sub(r"`+", "", text)
    return text.strip(" \t\r\n.,。；;:：!?！？、，,`*_~[]()（）【】<>|+-—–")


def _has_substantive_value(value: Any) -> bool:
    """Return whether a review field contains content rather than a template marker."""

    normalized = " ".join(_review_text(value).casefold().split())
    if not normalized or _REVIEW_PLACEHOLDER.fullmatch(normalized):
        return False
    # A field made only of punctuation/Markdown is not an actual review value.
    return re.search(r"[a-z0-9_\u3400-\u9fff]", normalized, re.IGNORECASE) is not None


def _has_reason_value(value: Any) -> bool:
    text = _REASON_LABEL.sub("", _review_text(value)).strip()
    normalized = " ".join(text.casefold().split())
    if normalized in {"", "空", "为空", "空白", "无", "none", "null"}:
        return False
    return _has_substantive_value(text)


def _review_field(line: str) -> tuple[str, str] | None:
    """Parse a required review field from a labelled line or Markdown heading."""

    candidate = re.sub(r"^\s*(?:#{1,6}\s+|>\s*|[-*+]\s+)", "", line).strip()
    match = _REVIEW_FIELD_LABELS.fullmatch(candidate)
    if not match:
        return None
    field = next(
        key for key, _label, _pattern in _REVIEW_FIELDS if match.group(key) is not None
    )
    return field, match.group("inline") or ""


def _review_metadata(text: str) -> dict[str, list[str]]:
    """Extract readable YAML-style or fixed-output reviewer metadata labels."""

    values: dict[str, list[str]] = {key: [] for key in _REVIEW_METADATA_FIELDS}
    for line in text.splitlines():
        match = _REVIEW_METADATA_LINE.fullmatch(line)
        if not match:
            continue
        field = next(
            key for key in _REVIEW_METADATA_FIELDS if match.group(key) is not None
        )
        values[field].append(match.group("value").strip().strip("`"))
    return values


def _metadata_error(values: dict[str, list[str]], field: str, label: str) -> str | None:
    entries = values.get(field, [])
    if not entries or not any(_has_metadata_value(value) for value in entries):
        return f"{label}缺失或只有占位内容"
    normalized = {" ".join(value.casefold().split()) for value in entries}
    if len(normalized) > 1:
        return f"{label}存在冲突值"
    return None


def _is_markdown_heading(line: str) -> bool:
    return re.match(r"^\s*#{1,6}(?:\s|$)", line) is not None


def _review_errors(path: Path, node: str, expected_case_id: str | None = None) -> list[str]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [f"文件无法读取：{exc}"]
    if not text.strip():
        return ["报告为空或只有占位内容"]
    node_pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(node)}(?![A-Za-z0-9])", re.IGNORECASE)
    errors = [] if node_pattern.search(text) else ["节点缺失"]
    metadata = _review_metadata(text)
    for field, label in (
        ("review_id", "Review ID"),
        ("reviewer_provider", "reviewer_provider"),
        ("reviewer_model", "reviewer_model"),
    ):
        if error := _metadata_error(metadata, field, label):
            errors.append(error)
    case_id_error = _metadata_error(metadata, "case_id", "Case ID")
    if case_id_error:
        errors.append(case_id_error)
    elif expected_case_id is not None:
        case_ids = {" ".join(value.casefold().split()) for value in metadata["case_id"]}
        if expected_case_id.casefold() not in case_ids:
            errors.append(f"Case ID 与案例目录 {expected_case_id!r} 不一致")

    session_values = {" ".join(value.casefold().split()) for value in metadata["review_session"]}
    if session_values != {"fresh"}:
        errors.append("review_session 必须为 fresh")
    conversation_values = {" ".join(value.casefold().split()) for value in metadata["saw_main_conversation"]}
    if conversation_values != {"false"}:
        errors.append("saw_main_conversation 必须为 false")
    critical_values = {" ".join(value.casefold().split()) for value in metadata["critical_node"]}
    if critical_values != {node.casefold()}:
        errors.append(f"critical_node 必须与当前节点 {node} 一致")

    sections: dict[str, list[str]] = {key: [] for key, _label, _pattern in _REVIEW_FIELDS}
    current: str | None = None
    for line in text.splitlines():
        field = _review_field(line)
        if field is not None:
            current, inline = field
            if inline:
                sections[current].append(inline)
            continue
        # A new Markdown heading closes the previous field.  This prevents an
        # empty heading from borrowing text from a later unrelated section.
        if _is_markdown_heading(line):
            current = None
            continue
        if current is not None and line.strip():
            sections[current].append(line)

    for _key, label, _pattern in _REVIEW_FIELDS:
        if not any(_has_substantive_value(value) for value in sections[_key]):
            errors.append(label + "为空或只有占位内容")
    return errors


def _valid_review(case_dir: Path, node: str) -> tuple[bool, str]:
    candidates = _review_files(case_dir, node)
    if not candidates:
        return False, f"reviews/ 中没有 {node}_*.md 审核报告（README.md 不计入）"
    failures = []
    for path in candidates:
        errors = _review_errors(path, node, expected_case_id=case_dir.name)
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


def _comparison_selection(case_dir: Path) -> dict[str, str]:
    """Read the Champion/Challenger named in the comparison table."""

    path = case_dir / "models/comparison.md"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    chosen: dict[str, str] = {}
    for label in ("Champion", "Challenger"):
        pattern = re.compile(
            rf"(?:^|[|;；])\s*(?:[-*]\s*)?(?:当前\s*)?{label}\s*[：:]\s*([^|;；\n]*)",
            re.IGNORECASE | re.MULTILINE,
        )
        match = pattern.search(text)
        if match and _has_value(match.group(1)):
            route = _SPEC_ROUTE_ID.search(match.group(1))
            if route is not None:
                chosen[label.casefold()] = route.group(0).upper()
    return chosen


def _selection_conflicts(case_dir: Path) -> list[Finding]:
    """Report disagreement between the two places that record route selection.

    ``models/candidates.md`` is the authority: it carries each route's status.
    ``models/comparison.md`` restates the choice in prose, and the two drifting
    apart is a real and easy mistake -- it happened once while building the
    example cases.
    """

    stated = _comparison_selection(case_dir)
    if not stated:
        return []
    actual: dict[str, str] = {}
    for route, role in _selected_route_roles(case_dir).items():
        actual.setdefault(role, route.upper())
    findings: list[Finding] = []
    for role in ("champion", "challenger"):
        left, right = stated.get(role), actual.get(role)
        if left and right and left != right:
            findings.append(
                _finding(
                    "REMINDER", "SELECTION_CONFLICT",
                    f"{role.capitalize()} 记录不一致：models/comparison.md 写 {left}，"
                    f"models/candidates.md 的状态字段是 {right}；"
                    "以 candidates.md 的状态为准，请修正另一处",
                    "MODELER", "HUMAN",
                )
            )
    return findings


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


def _recomputed_risks(case_dir: Path) -> dict[str, list[str]]:
    """Collect failed recomputation checks written by the engineer.

    ``scripts/model_checks.py:write_check_report`` lands one JSON file per
    experiment.  Reading them here means a real deterministic failure raises its
    flag on its own, instead of waiting for somebody to remember to edit
    ``checkpoint.yaml`` during a competition.
    """

    checks_dir = case_dir / "experiments/outputs/checks"
    if not checks_dir.is_dir():
        return {}
    detected: dict[str, list[str]] = {}
    for path in sorted(checks_dir.glob("*.json")):
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            # An unreadable report is reported separately; it must not be read
            # as "no risk found".
            detected.setdefault("unreadable", []).append(path.name)
            continue
        if not isinstance(report, Mapping):
            detected.setdefault("unreadable", []).append(path.name)
            continue
        exp_id = str(report.get("exp_id", "") or path.stem).strip()
        checks = report.get("checks")
        if not isinstance(checks, list):
            detected.setdefault("unreadable", []).append(path.name)
            continue
        for check in checks:
            if not isinstance(check, Mapping) or check.get("passed", True):
                continue
            kind = str(check.get("kind", "")).strip()
            key = kind if kind in RISK_LABELS else "infeasible" if kind == "constraint" else ""
            if not key:
                continue
            name = str(check.get("name", "")).strip() or "unnamed"
            detected.setdefault(key, []).append(f"{exp_id}:{name}")
    return detected


def _risk_findings(checkpoint: Mapping[str, Any], stage: str, case_dir: Path) -> list[Finding]:
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
    recomputed = _recomputed_risks(case_dir)
    if "unreadable" in recomputed:
        # 早期允许快速试跑留下半成品报告；写强结论或提交时，无法读取的复算报告
        # 与没有复算等价，不能让论文建立在读不出来的证据上。
        level = "BLOCK" if stage in {"paper_claims", "final"} else "REMINDER"
        findings.append(
            _finding(
                level, "CHECK_REPORT_UNREADABLE",
                "复算报告无法解析：" + "、".join(recomputed.pop("unreadable"))
                + "；不能把无法读取当成检查通过。请重跑对应实验的复算，"
                "或删除这份损坏的报告后重新生成",
                "ENGINEER", "C3",
            )
        )
    for key, (label, node) in RISK_LABELS.items():
        if key in recomputed:
            level = "BLOCK" if stage in {"paper_claims", "final"} else "REMINDER"
            findings.append(
                _finding(
                    level, "DETERMINISTIC_ERROR_BLOCK",
                    f"{label}（复算报告：" + "、".join(recomputed[key]) + "）"
                    "；在写入强结论或最终提交前必须修复、复算或由队员明确处理",
                    "ENGINEER", node,
                )
            )
        elif _is_true(risks.get(key)):
            level = "BLOCK" if stage in {"paper_claims", "final"} else "REMINDER"
            findings.append(
                _finding(
                    level, "DETERMINISTIC_ERROR_BLOCK",
                    f"{label}；在写入强结论或最终提交前必须修复、复算或由队员明确处理",
                    "HUMAN", node,
                )
            )
    return findings


def _spec_front_matter(path: Path) -> dict[str, str]:
    """Read the small YAML header of one spec without requiring a YAML parser."""

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return {}
    if not lines or lines[0].strip() != "---":
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        match = _SPEC_FM_LINE.match(line)
        if match is not None:
            fields[match.group("key").casefold()] = match.group("value").strip().strip("`'\"")
    return fields


def _specs_by_route(case_dir: Path) -> dict[str, list[dict[str, str]]]:
    """Map route IDs to the front matter of every spec written for them."""

    specs_dir = case_dir / "specs"
    if not specs_dir.is_dir():
        return {}
    routes: dict[str, list[dict[str, str]]] = {}
    for path in sorted(specs_dir.glob("SPEC-*.md")):
        if path.name.endswith(".questions.md"):
            continue
        fields = _spec_front_matter(path)
        route = fields.get("route_id", "").strip().casefold()
        if route and fields.get("status", "").strip().casefold():
            fields["_name"] = path.name
            routes.setdefault(route, []).append(fields)
    return routes


def _specs_by_status(case_dir: Path) -> dict[str, set[str]]:
    """Map route IDs to the spec statuses they already have."""

    return {
        route: {fields.get("status", "").strip().casefold() for fields in entries}
        for route, entries in _specs_by_route(case_dir).items()
    }


def _selected_route_roles(case_dir: Path) -> dict[str, str]:
    """Map route ID -> champion/challenger, from the authoritative candidate pool."""

    path = case_dir / "models/candidates.md"
    if not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8")
    roles: dict[str, str] = {}
    current = ""
    for line in text.splitlines():
        if _MARKDOWN_HEADING.match(line):
            heading = _SPEC_ROUTE_HEADING.match(line)
            current = heading.group("route").strip().casefold() if heading else ""
            continue
        if not current:
            continue
        match = _SPEC_SELECTED_STATUS.search(line)
        if match is not None:
            roles[current] = match.group("role").casefold()
    return roles


def _selected_routes(case_dir: Path) -> set[str]:
    """Find routes already marked champion or challenger in the candidate pool."""

    path = case_dir / "models/candidates.md"
    if not path.is_file():
        return set()
    text = path.read_text(encoding="utf-8")
    selected: set[str] = set()
    current = ""
    for line in text.splitlines():
        # Any heading ends the previous route section.  Without this, prose after
        # the last route card (for example a section explaining why M-01 is the
        # Challenger) would be attributed to whichever route came before it.
        if _MARKDOWN_HEADING.match(line):
            heading = _SPEC_ROUTE_HEADING.match(line)
            current = heading.group("route").strip().casefold() if heading else ""
            continue
        if current and _SPEC_SELECTED_STATUS.search(line):
            selected.add(current)
    return selected


def _spec_findings(case_dir: Path, stage: str) -> list[Finding]:
    """Remind about missing specs and about full specs that skipped their probe.

    These are reminders at every stage.  A spec is a handoff aid, not a gate:
    blocking on it would turn the lightweight contract into the heavyweight
    pipeline this workspace deliberately moved away from.
    """

    if stage == "exploration":
        return []
    findings: list[Finding] = []
    specs = _specs_by_status(case_dir)
    for route in sorted(_selected_routes(case_dir)):
        statuses = specs.get(route, set())
        if "full" not in statuses:
            findings.append(
                _finding(
                    "REMINDER", "SPEC_MISSING",
                    f"路线 {route.upper()} 已选为 champion/challenger，但 specs/ 中没有 status: full 的实现规格；"
                    "编程手需要规格才能忠实实现",
                    "MODELER", "HUMAN",
                )
            )
    for route, statuses in sorted(specs.items()):
        if "full" in statuses and "probe" not in statuses:
            findings.append(
                _finding(
                    "REMINDER", "PROBE_MISSING",
                    f"路线 {route.upper()} 直接进入 full 规格，没有对应的 probe 规格；"
                    "请确认这是题面指定方法，否则先用轻测试证伪",
                    "MODELER", "HUMAN",
                )
            )
    findings.extend(_probe_closure_findings(case_dir, stage))
    return findings


#: 实验板上表示「跑完了」的状态。其余状态（queued/running/failed/skipped）都不能闭环。
_BOARD_DONE_STATUS = frozenset({"done"})
#: 结果摘要中的明确判定。probe 是否通过由实验记录说了算，不由 full 规格自报。
_VERDICT_PASS = re.compile(r"\bPASS\b|判定\s*[:：]?\s*通过|结论\s*[:：]?\s*通过|探针通过", re.IGNORECASE)
_VERDICT_FAIL = re.compile(r"\bFAIL\b|判定\s*[:：]?\s*未通过|判定\s*[:：]?\s*失败|探针失败", re.IGNORECASE)


def _board_rows(case_dir: Path) -> dict[str, dict[str, Any]]:
    """Index the experiment board by experiment ID."""

    board = case_dir / "experiments/board.md"
    if not board.is_file():
        return {}
    rows: dict[str, dict[str, Any]] = {}
    for row in parse_markdown_table(board.read_text(encoding="utf-8")):
        exp_id = str(row.get("实验 ID", "")).strip().casefold()
        if exp_id:
            rows[exp_id] = row
    return rows


def _probe_closure_findings(case_dir: Path, stage: str) -> list[Finding]:
    """Check that each full spec traces to a probe that actually ran and passed.

    A probe file existing proves nothing, and neither does a full spec asserting
    ``probe_result: PASS`` about itself.  The verdict has to come from the
    experiment record: the referenced probe spec must exist and be a probe, it
    must describe the same route, its experiment must be on the board, that
    experiment must be finished, and its result summary must state PASS.

    Early stages get a reminder so exploration keeps moving; a route may not
    carry an unclosed probe into a route decision or a paper claim.
    """

    level = "BLOCK" if stage in {"paper_claims", "final"} else "REMINDER"
    board_rows = _board_rows(case_dir)
    specs_by_route = _specs_by_route(case_dir)
    specs_by_id = {
        fields.get("spec_id", "").strip().casefold(): fields
        for entries in specs_by_route.values() for fields in entries
        if fields.get("spec_id", "").strip()
    }

    findings: list[Finding] = []

    def fail(reason: str) -> None:
        findings.append(_finding(level, "PROBE_NOT_CLOSED", reason, "MODELER", "HUMAN"))

    for route, entries in sorted(specs_by_route.items()):
        for fields in entries:
            if fields.get("status", "").strip().casefold() != "full":
                continue
            name = fields.get("_name", "SPEC")
            result = fields.get("probe_result", "").strip().strip("`'\"").casefold()

            if result == "waived":
                if not _has_value(fields.get("probe_waiver_reason", "")):
                    fail(f"{name} 以 WAIVED 跳过 probe，但没有写明豁免理由；"
                         "人工豁免必须留下可复核的原因")
                continue

            if result != "pass":
                fail(f"路线 {route.upper()} 的 {name} 是 full 规格，但 probe_result="
                     f"{result or '未填写'}；正常情况下需要 probe 实际跑出 PASS 才能升级，"
                     "确实要跳过时写 WAIVED 并说明理由")
                continue

            # probe 规格必须真实存在、确实是 probe、且描述同一条路线
            probe_id = fields.get("probe_spec_id", "").strip().strip("`").casefold()
            if not probe_id:
                fail(f"{name} 声称 probe 通过，但没有填写 probe_spec_id")
                continue
            probe = specs_by_id.get(probe_id)
            if probe is None:
                fail(f"{name} 的 probe_spec_id={probe_id} 在 specs/ 中找不到对应文件；"
                     "不能引用一份不存在的探针")
                continue
            if probe.get("status", "").strip().casefold() != "probe":
                fail(f"{name} 的 probe_spec_id={probe_id} 指向的不是 probe 规格"
                     f"（status={probe.get('status', '未填写')}）")
                continue
            for field, label in (("case_id", "案例"), ("route_id", "路线"), ("subproblem", "子问题")):
                left = fields.get(field, "").strip().casefold()
                right = probe.get(field, "").strip().casefold()
                if left and right and left != right:
                    fail(f"{name} 与其 probe 规格的 {label}不一致："
                         f"{fields.get(field)} vs {probe.get(field)}")

            # probe 实验必须在板上、跑完、且有明确 PASS 判定
            exp_id = fields.get("probe_exp_id", "").strip().strip("`").casefold()
            if not exp_id:
                fail(f"{name} 声称 probe 通过，但没有填写 probe_exp_id")
                continue
            row = board_rows.get(exp_id)
            if row is None:
                detail = "实验板为空" if not board_rows else "实验板中没有这一行"
                fail(f"{name} 的 probe_exp_id={exp_id.upper()} 在 experiments/board.md 中找不到"
                     f"（{detail}）；probe 必须有实际运行记录，不能只在规格里声称通过")
                continue
            status = str(row.get("status", "")).strip().casefold()
            if status not in _BOARD_DONE_STATUS:
                fail(f"{name} 的 probe 实验 {exp_id.upper()} 在实验板上的状态是 "
                     f"{status or '未填写'}，不是已完成；未跑完的探针不能作为升级依据")
                continue
            summary = " ".join(str(value) for value in row.values())
            if _VERDICT_FAIL.search(summary):
                fail(f"{name} 的 probe 实验 {exp_id.upper()} 的记录里写着未通过判定，"
                     "这条路线不应被升级为 full 规格")
            elif not _VERDICT_PASS.search(summary):
                fail(f"{name} 的 probe 实验 {exp_id.upper()} 已完成，但结果摘要里没有明确的 "
                     "PASS 判定；请在实验板该行写明「判定：PASS」，"
                     "full 规格自报的 probe_result 不能替代实验记录")
    return findings


#: claim_map 表头 -> 归一化字段名。识别靠关键词，允许队员微调列名。
_CLAIM_COLUMNS = (
    ("claim_id", ("claim id", "claim", "主张 id", "主张编号")),
    ("location", ("论文位置", "位置", "location", "section")),
    ("statement", ("主张原文", "主张", "statement", "claim text")),
    ("strength", ("强度", "strength")),
    ("exp_id", ("exp-id", "exp id", "来源 exp-id", "实验 id", "experiment")),
    ("data_file", ("数据文件", "data file", "data")),
    ("figure_id", ("图/表 id", "图表 id", "figure", "fig")),
    ("check_report", ("复算报告", "check report", "check")),
    ("status", ("状态", "status")),
)
_VERIFIED_STATUS = re.compile(r"verified|已验证|已复核", re.IGNORECASE)


def _claim_header_map(cells: list[str]) -> dict[str, int]:
    """Map normalized field names onto column indexes of the claim-map header."""

    mapping: dict[str, int] = {}
    for index, cell in enumerate(cells):
        normalized = " ".join(cell.casefold().split()).strip("`*")
        for field, keywords in _CLAIM_COLUMNS:
            if field in mapping:
                continue
            if any(keyword in normalized for keyword in keywords):
                mapping[field] = index
                break
    return mapping


def _cell(cells: list[str], header: dict[str, int], field: str) -> str:
    index = header.get(field)
    if index is None or index >= len(cells):
        return ""
    return _TEMPLATE_TOKEN.sub("", cells[index]).strip().strip("`")


def _figure_states(case_dir: Path) -> dict[str, str]:
    """Read FIG-ID -> status rows from the figure manifest."""

    path = case_dir / "experiments/outputs/figures/manifest.md"
    if not path.is_file():
        return {}
    states: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        cells = _split_pipe_row(line)
        if not cells or _is_table_separator(cells):
            continue
        match = _SPEC_FIGURE_ID.search(cells[0])
        if match is None:
            continue
        joined = " ".join(cells).casefold()
        states[match.group(0).upper()] = "stale" if "stale" in joined else "ok"
    return states


def _claim_map_findings(case_dir: Path, stage: str) -> list[Finding]:
    """Check that every paper claim resolves to evidence that actually exists.

    This is structure, existence and recorded-status validation only.  It does
    not verify that a number is mathematically right; it verifies that the paper
    is not citing evidence which is missing, unreadable or already failing.
    """

    if stage not in {"paper_claims", "final"}:
        return []
    # 论文骨架尚未建立（没有 claim_map 或还没填任何主张）在 paper_claims 只提醒 ——
    # 那是进度问题。但一条已经写下的主张引用了不存在、读不出或已失败的证据，
    # 两个阶段都必须阻断：论文不能建立在指不到的证据上。
    level = "BLOCK" if stage == "final" else "REMINDER"
    evidence_level = "BLOCK"
    path = case_dir / "paper/claim_map.md"
    if not path.is_file():
        return [
            _finding(
                level, "HUMAN_DECISION_REQUIRED",
                "paper/claim_map.md 不存在；论文强主张必须能追溯到实验和数据文件",
                "WRITER", "HUMAN",
            )
        ]

    text = path.read_text(encoding="utf-8")
    rows = [
        cells for cells in (_split_pipe_row(line) for line in text.splitlines())
        if cells and not _is_table_separator(cells)
    ]
    header: dict[str, int] = {}
    for cells in rows:
        candidate = _claim_header_map(cells)
        if "claim_id" in candidate and "exp_id" in candidate:
            header = candidate
            break
    if not header:
        return [
            _finding(
                level, "CLAIM_MAP_HEADER_INVALID",
                "paper/claim_map.md 缺少可识别的表头（至少需要 Claim ID 与 来源 EXP-ID 两列）；"
                "请对照 templates/claim_map.md 修正表头",
                "WRITER", "HUMAN",
            )
        ]

    claims = [
        cells for cells in rows
        if _SPEC_CLAIM_ID.match(cells[0].strip())
        and any(_has_value(_TEMPLATE_TOKEN.sub("", cell)) for cell in cells[1:])
    ]
    if not claims:
        return [
            _finding(
                level, "HUMAN_DECISION_REQUIRED",
                "paper/claim_map.md 没有任何已填写的 CLM- 记录；论文里的数字尚未建立溯源",
                "WRITER", "HUMAN",
            )
        ]

    known_experiments = board_experiment_ids(case_dir)
    figures = _figure_states(case_dir)

    # 写作性字段缺失是进度问题；证据性字段缺失是「这条主张没有依据」，等级不同。
    incomplete: list[str] = []
    missing_evidence_field: list[str] = []
    dangling: list[str] = []
    missing_data: list[str] = []
    bad_reports: list[str] = []
    bad_figures: list[str] = []
    stale: list[str] = []
    contradicted: list[str] = []

    for cells in claims:
        claim_id = cells[0].strip().strip("`")

        for field, label in (("statement", "主张原文"), ("strength", "强度")):
            if not _has_value(_cell(cells, header, field)):
                incomplete.append(f"{claim_id}({label})")

        # P1-2：来源实验只从 exp_id 单元格读，不扫整行 ——
        # 数据文件名里的 EXP-ID 不得替来源列背书。
        source = parse_source_experiment(_cell(cells, header, "exp_id"))
        claim_exp = source.exp_id
        if not source.ok:
            missing_evidence_field.append(f"{claim_id}(来源 EXP-ID：{source.problem})")
        elif claim_exp.casefold() not in known_experiments:
            # 实验板读不出来不等于「来源实验存在」。空板、缺板和板上没这一行，
            # 都同样无法证明这条主张有跑过的实验支撑。
            dangling.append(f"{claim_id}->{describe_missing_source(case_dir, claim_exp)}")

        # 数据文件只能落在 experiments/outputs/data/
        data_reference = _cell(cells, header, "data_file")
        if not _has_value(data_reference):
            missing_evidence_field.append(f"{claim_id}(数据文件未填写)")
        elif is_traversal(data_reference):
            missing_data.append(f"{claim_id}->{data_reference}(路径非法)")
        elif resolve_in_case(case_dir, data_reference, kind="data") is None:
            missing_data.append(
                f"{claim_id}->{data_reference}(不存在或不在 experiments/outputs/data/ 内)")

        # 复算报告必须存在、可解析、且确属这条 claim 的实验
        report_reference = _cell(cells, header, "check_report")
        report_failed = False
        if not _has_value(report_reference):
            missing_evidence_field.append(f"{claim_id}(复算报告未填写)")
        elif is_traversal(report_reference):
            bad_reports.append(f"{claim_id}->{report_reference}(路径非法)")
        else:
            report_path = resolve_in_case(case_dir, report_reference, kind="checks")
            if report_path is None:
                bad_reports.append(
                    f"{claim_id}->{report_reference}(不存在或不在 experiments/outputs/checks/ 内)")
            else:
                verdict = validate_check_report(report_path, claim_exp)
                if not verdict.ok:
                    bad_reports.append(f"{claim_id}->{report_reference}({verdict.problem})")
                report_failed = verdict.has_failed_check

        figure_reference = _cell(cells, header, "figure_id")
        for match in _SPEC_FIGURE_ID.finditer(figure_reference):
            figure_id = match.group(0).upper()
            state = figures.get(figure_id)
            if state is None:
                bad_figures.append(f"{claim_id}->{figure_id}(不在 figures/manifest.md)")
            elif state == "stale":
                bad_figures.append(f"{claim_id}->{figure_id}(manifest 标记 stale)")

        status = _cell(cells, header, "status")
        joined = _TEMPLATE_TOKEN.sub("", " ".join(cells))
        if "stale" in status.casefold() or "stale" in joined.casefold():
            stale.append(claim_id)
        if report_failed:
            if _VERIFIED_STATUS.search(status):
                contradicted.append(f"{claim_id}(状态 verified，但复算报告有未通过项)")
            else:
                contradicted.append(f"{claim_id}(绑定的复算报告有未通过项)")

    findings: list[Finding] = []
    for items, code, message, node, item_level in (
        (incomplete, "CLAIM_MAP_INCOMPLETE", "claim_map 中以下写作字段为空或仍是模板占位：", "HUMAN", level),
        (missing_evidence_field, "CLAIM_EVIDENCE_MISSING",
         "claim_map 中以下主张缺少关键证据字段，不能作为论文主张：", "C3", evidence_level),
        (dangling, "HUMAN_DECISION_REQUIRED", "claim_map 中以下主张无法追溯到实验板里的实验：", "C3", evidence_level),
        (missing_data, "CLAIM_EVIDENCE_MISSING", "claim_map 引用的结果数据文件不可用：", "C3", evidence_level),
        (bad_reports, "CLAIM_EVIDENCE_MISSING", "claim_map 的复算报告不可用：", "C3", evidence_level),
        (bad_figures, "CLAIM_EVIDENCE_MISSING", "claim_map 引用的图在清单中缺失或已过期：", "C3", evidence_level),
        (stale, "HUMAN_DECISION_REQUIRED", "claim_map 中以下主张仍标记为 stale，对应数字或图已过期：", "HUMAN", evidence_level),
        (contradicted, "CLAIM_CONTRADICTS_CHECK", "claim_map 中以下主张绑定了未通过的确定性检查，不能作为论文强结论：", "C3", evidence_level),
    ):
        if items:
            findings.append(_finding(item_level, code, message + "、".join(items), "WRITER", node))
    return findings


def _decision_tokens(value: Any) -> list[re.Match[str]]:
    return list(_DECISION_TOKEN.finditer(str(value or "")))


def _split_pipe_row(line: str) -> list[str] | None:
    stripped = line.strip()
    if "|" not in stripped:
        return None
    return [cell.strip() for cell in stripped.strip("|").split("|")]


def _is_table_separator(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-+:?", cell) for cell in cells)


def _markdown_decision_tables(text: str) -> list[tuple[list[str], list[str]]]:
    """Return rows from Markdown tables without changing the case workflow."""

    lines = [line.strip() for line in text.splitlines() if "|" in line]
    tables: list[tuple[list[str], list[str]]] = []
    for index in range(len(lines) - 1):
        headers = _split_pipe_row(lines[index])
        separator = _split_pipe_row(lines[index + 1])
        if headers is None or separator is None or len(headers) != len(separator) or not _is_table_separator(separator):
            continue
        for line in lines[index + 2:]:
            cells = _split_pipe_row(line)
            if cells is None or len(cells) != len(headers) or _is_table_separator(cells):
                break
            tables.append((headers, cells))
        break
    return tables


def _decision_from_cells(cells: list[str], headers: list[str] | None, node: str) -> bool:
    node_pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(node)}(?![A-Za-z0-9])", re.IGNORECASE)
    node_indices = {index for index, cell in enumerate(cells) if node_pattern.search(cell)}
    if not node_indices:
        return False

    decision_indices = (
        {index for index, header in enumerate(headers or ()) if _DECISION_HEADER.search(header)}
        if headers
        else set()
    )
    reason_indices = (
        {index for index, header in enumerate(headers or ()) if _REASON_HEADER.search(header)}
        if headers
        else set()
    )
    if decision_indices:
        if len(decision_indices) != 1:
            return False
        choice_index = next(iter(decision_indices))
        choice_tokens = _decision_tokens(cells[choice_index])
        if len(choice_tokens) != 1:
            return False
    else:
        candidates = [
            index for index, cell in enumerate(cells)
            if index not in node_indices and len(_decision_tokens(cell)) == 1
        ]
        if len(candidates) != 1:
            return False
        choice_index = candidates[0]

    # A second decision token in a node/reason cell means the row is not a
    # single, unambiguous human choice (for example 接受/拒绝).
    for index, cell in enumerate(cells):
        if index != choice_index and _decision_tokens(cell):
            return False

    if reason_indices:
        return any(
            index not in node_indices and index != choice_index and _has_reason_value(cells[index])
            for index in reason_indices
        )
    return any(
        index not in node_indices and index != choice_index and _has_reason_value(cell)
        for index, cell in enumerate(cells)
    )


def _decision_from_non_table_line(line: str, node: str) -> bool:
    if line.lstrip().startswith("|"):
        cells = _split_pipe_row(line)
        return cells is not None and _decision_from_cells(cells, None, node)
    node_pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(node)}(?![A-Za-z0-9])", re.IGNORECASE)
    if not node_pattern.search(line):
        return False
    tokens = _decision_tokens(line)
    if len(tokens) != 1:
        return False
    # Non-table compatibility requires a reason after the explicit decision;
    # a bare sentence such as “C3 报告需要决定接受或拒绝” therefore fails.
    tail = line[tokens[0].end():]
    return _has_reason_value(tail)


def _decision_covers_node(case_dir: Path, node: str) -> bool:
    path = case_dir / "decisions.md"
    if not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    tables = _markdown_decision_tables(text)
    node_in_table = False
    node_pattern = re.compile(rf"(?<![A-Za-z0-9]){re.escape(node)}(?![A-Za-z0-9])", re.IGNORECASE)
    for headers, cells in tables:
        if any(node_pattern.search(cell) for cell in cells):
            node_in_table = True
            if _decision_from_cells(cells, headers, node):
                return True
    if node_in_table:
        return False
    return any(_decision_from_non_table_line(line, node) for line in text.splitlines())


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
    checkpoint_case_id = str(checkpoint.get("case_id", "") or "").strip()
    if not _has_value(checkpoint_case_id):
        findings.insert(
            0,
            _finding("BLOCK", "ROUTE_CONFIRMATION_REQUIRED", "checkpoint.yaml 缺少 case_id，无法确认它属于当前案例", "HUMAN", "HUMAN"),
        )
    elif checkpoint_case_id != case_dir.name:
        findings.insert(
            0,
            _finding(
                "BLOCK", "CASE_ID_MISMATCH",
                f"checkpoint.yaml 的 case_id={checkpoint_case_id!r} 与当前案例目录 {case_dir.name!r} 不一致",
                "HUMAN", "HUMAN",
            ),
        )

    route_unclear = effective_route == "insufficient_information"
    c1_needed = route_unclear or _brief_has_route_changing_ambiguity(case_dir)
    c1_valid, c1_detail = _valid_review(case_dir, "C1")
    c1_status = _review_status(checkpoint, "C1")
    if c1_status == "not_needed" and _has_value(_review_note(checkpoint, "C1")) and not c1_needed:
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
                f"C1 题意挑战尚未留下有效报告（{c1_detail}）；请由队员判断歧义并可手动触发 Independent Reviewer C1",
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
                f"进入正式模型/路线取舍阶段但没有有效 C2 报告（{c2_detail}）；请由队员触发 Independent Reviewer C2",
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
    findings.extend(_risk_findings(checkpoint, stage, case_dir))
    findings.extend(_spec_findings(case_dir, stage))
    findings.extend(_selection_conflicts(case_dir))
    findings.extend(_claim_map_findings(case_dir, stage))

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
