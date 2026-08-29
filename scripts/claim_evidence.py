"""Shared parsing for the two evidence fields a paper claim must get right.

``scripts/check_case.py`` and ``scripts/make_review_packet.py`` both need to
answer the same two questions about a claim: which experiment is it sourced
from, and does its recomputation report actually belong to that experiment.
Round 2 answered them twice, in two places, and the copies drifted -- one read
the whole claim row and let a filename mask a wrong source ID, and both accepted
a report with no ``exp_id`` at all.  One implementation, one contract.

Neither function knows anything about the numbers involved.  They check
identity and structure: that a claim names exactly one experiment, and that the
report in front of you is that experiment's report and states its verdicts as
booleans.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from .experiment_board import parse_markdown_table
except ImportError:  # pragma: no cover - direct script execution
    from experiment_board import parse_markdown_table

#: A canonical experiment ID.  Anchored so ``EXP-001_solution`` is not accepted
#: as if it were ``EXP-001``: a filename fragment must never pass as a source ID.
EXP_ID = re.compile(r"EXP-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", re.IGNORECASE)
_EXACT_EXP_ID = re.compile(r"^EXP-[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*$", re.IGNORECASE)
_PLACEHOLDER = frozenset({"", "-", "—", "待填写", "待填", "待补充", "todo", "tbd", "n/a"})
_TEMPLATE_TOKEN = re.compile(r"<[^<>]{1,80}>")


@dataclass(frozen=True)
class SourceExperiment:
    """The single experiment a claim is sourced from, or why it cannot be read."""

    exp_id: Optional[str]
    problem: str = ""

    @property
    def ok(self) -> bool:
        return self.exp_id is not None and not self.problem


@dataclass(frozen=True)
class ReportVerdict:
    """Whether a recomputation report backs the claim that cites it."""

    has_failed_check: bool = False
    problem: str = ""

    @property
    def ok(self) -> bool:
        return not self.problem


def parse_source_experiment(cell: str) -> SourceExperiment:
    """Read the source experiment from the claim's own EXP-ID cell.

    Only this cell counts.  Reading the whole row lets an experiment ID that
    happens to appear in a data filename stand in for the declared source, which
    is exactly how a claim pointing at an unknown experiment slipped through.
    """

    cleaned = _TEMPLATE_TOKEN.sub("", str(cell or "")).strip().strip("`").strip()
    if not cleaned or cleaned.casefold() in _PLACEHOLDER:
        return SourceExperiment(None, "来源 EXP-ID 为空或仍是占位")

    found = EXP_ID.findall(cleaned)
    if not found:
        return SourceExperiment(None, f"来源单元格 {cleaned!r} 中没有规范的 EXP-ID")
    if len(found) > 1:
        return SourceExperiment(
            None, f"来源单元格含 {len(found)} 个 EXP-ID（{'、'.join(found)}），必须唯一")
    if not _EXACT_EXP_ID.match(cleaned):
        return SourceExperiment(
            None, f"来源单元格 {cleaned!r} 含 EXP-ID 之外的内容，无法唯一解析")
    return SourceExperiment(cleaned.upper())


def validate_check_report(path: Path, claim_exp: Optional[str]) -> ReportVerdict:
    """Check that one recomputation report belongs to ``claim_exp`` and is well formed.

    ``exp_id`` is required: a report that does not say which experiment it
    describes cannot be shown to describe this one, and "unlabelled" must not
    read as "matching".
    """

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return ReportVerdict(problem="无法解析")
    if not isinstance(payload, dict):
        return ReportVerdict(problem="格式不符合约定")

    raw_exp = str(payload.get("exp_id", "") or "").strip().strip("`")
    if not raw_exp or raw_exp.casefold() in _PLACEHOLDER:
        return ReportVerdict(problem="报告缺少 exp_id，无法确认它属于哪个实验")
    found = EXP_ID.findall(raw_exp)
    if len(found) != 1 or not _EXACT_EXP_ID.match(raw_exp):
        return ReportVerdict(problem=f"报告的 exp_id {raw_exp!r} 不是唯一且规范的 EXP-ID")
    if claim_exp and raw_exp.upper() != claim_exp.upper():
        return ReportVerdict(
            problem=f"报告属于 {raw_exp.upper()}，与 claim 的 {claim_exp.upper()} 不一致")

    checks = payload.get("checks")
    if not isinstance(checks, list) or not checks:
        return ReportVerdict(problem="没有任何检查项")
    for item in checks:
        if not isinstance(item, dict):
            return ReportVerdict(problem="检查项格式不符合约定")
        if not isinstance(item.get("passed"), bool):
            return ReportVerdict(
                problem=f"检查项 {item.get('name', '?')} 的 passed 不是布尔值")
    return ReportVerdict(has_failed_check=any(not item["passed"] for item in checks))


def board_experiment_ids(case_dir: Path) -> set[str]:
    """Return the experiment IDs recorded on the case's experiment board.

    Shared by the case checker and the packet generator so "which experiments
    exist" has one answer.  An unreadable, missing or empty board yields an
    empty set -- callers must treat that as *no experiment is known to exist*,
    never as *every experiment is fine*.
    """

    board = case_dir / "experiments/board.md"
    try:
        text = board.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    found: set[str] = set()
    for row in parse_markdown_table(text):
        exp_id = str(row.get("实验 ID", "") or "").strip().strip("`")
        if exp_id and _EXACT_EXP_ID.match(exp_id):
            found.add(exp_id.casefold())
    return found


def describe_missing_source(case_dir: Path, claim_exp: str) -> str:
    """Explain why a claim's source experiment cannot be shown to exist."""

    board = case_dir / "experiments/board.md"
    if not board.is_file():
        return f"{claim_exp}（experiments/board.md 不存在，无法证明该实验跑过）"
    if not board_experiment_ids(case_dir):
        return f"{claim_exp}（experiments/board.md 没有任何实验行）"
    return f"{claim_exp}（experiments/board.md 中没有这一行）"


def failed_checks(path: Path) -> list[dict]:
    """Return the failing entries of a report already known to be well formed."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return []
    checks = payload.get("checks") if isinstance(payload, dict) else None
    if not isinstance(checks, list):
        return []
    return [item for item in checks
            if isinstance(item, dict) and item.get("passed") is False]
