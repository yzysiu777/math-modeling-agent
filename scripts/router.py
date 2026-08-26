"""Small deterministic first-pass router for modeling cases.

This is a triage aid, not a replacement for human reading of the problem
statement. It deliberately returns insufficient_information when there is no
reliable signal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


OPTIMIZATION_TERMS = (
    "优化", "规划", "调度", "路径", "路由", "分配", "资源", "约束", "容量",
    "网络", "库存", "排班", "选址", "assignment", "scheduling", "routing",
    "allocation", "resource", "constraint", "network", "optimization",
)
DATA_TERMS = (
    "数据", "统计", "预测", "分类", "回归", "聚类", "时序", "样本", "特征",
    "缺失", "异常", "标签", "显著性", "置信区间", "data", "forecast", "classification",
    "regression", "clustering", "time series", "feature", "missing", "inference",
)
DECISION_TERMS = (
    "决策", "选择", "安排", "分配", "资源", "成本", "收益", "maximize", "minimize",
    "decision", "schedule", "allocate", "capacity",
)


@dataclass(frozen=True)
class RouteResult:
    route: str
    optimization_score: int
    data_score: int
    evidence: tuple[str, ...]
    uncertainty: tuple[str, ...]


def _hits(text: str, terms: Iterable[str]) -> list[str]:
    lowered = text.lower()
    return [term for term in terms if term.lower() in lowered]


def route_problem(text: str, metadata: dict | None = None) -> RouteResult:
    """Return one of the four canonical routes from visible evidence only."""

    metadata = metadata or {}
    if not text or not text.strip():
        return RouteResult(
            "insufficient_information", 0, 0, (), ("题面或任务描述为空",)
        )

    opt_hits = _hits(text, OPTIMIZATION_TERMS)
    data_hits = _hits(text, DATA_TERMS)
    decision_hits = _hits(text, DECISION_TERMS)
    opt_score = len(opt_hits)
    data_score = len(data_hits)
    evidence = tuple(f"optimization:{item}" for item in opt_hits) + tuple(
        f"data_analysis:{item}" for item in data_hits
    )

    if opt_score == 0 and data_score == 0:
        return RouteResult(
            "insufficient_information", 0, 0, evidence,
            ("未发现足以判断题型的优化或数据分析信号",),
        )

    if opt_score > 0 and data_score > 0 and decision_hits:
        return RouteResult(
            "hybrid", opt_score, data_score, evidence,
            ("数据分析与决策优化同时出现，需建立上下游接口契约",),
        )

    if opt_score > data_score:
        return RouteResult(
            "optimization", opt_score, data_score, evidence,
            ("仍需由人工确认目标、变量、约束和最优性边界",),
        )

    if data_score > opt_score:
        return RouteResult(
            "data_analysis", opt_score, data_score, evidence,
            ("仍需由人工确认数据粒度、标签、切分和因果边界",),
        )

    return RouteResult(
        "insufficient_information", opt_score, data_score, evidence,
        ("优化与数据分析信号相当，需补充题意或人工确定主任务",),
    )
