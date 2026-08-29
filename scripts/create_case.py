"""Create the smallest useful case workspace from the Markdown templates."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
ROUTES = {"optimization", "data_analysis", "hybrid", "insufficient_information"}
CASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,63}$")


def _candidate_seed(route: str) -> str:
    return f"""# 候选路线池\n\n案例路由：`{route}`\n\n以下是能通过轻量结构检查的启动草稿；Codex 应根据题面替换，不把占位路线当成正式方案。\n\n## M-01：可解释 baseline\n\n- 方法族：simple interpretable baseline\n- 核心思想：用最小可运行规则或统计量建立可解释比较线\n- 最便宜的证伪实验：在小样本/小实例上与题面已知结果或手算结果对照\n- 状态：`candidate`\n\n## M-02：结构不同的候选\n\n- 方法族：structural mathematical model\n- 核心思想：把题面中的主要关系显式写成公式或约束\n- 最便宜的证伪实验：构造一个能区分结构假设的边界样例\n- 状态：`candidate`\n\n## M-03：风险/假设不同的候选\n\n- 方法族：risk-aware or data-driven alternative\n- 核心思想：改变关键假设、误差处理或数据使用方式，检验结果是否稳健\n- 最便宜的证伪实验：对关键输入或误差做一次小规模扰动并比较指标/可行性\n- 状态：`candidate`\n"""


def _comparison_seed() -> str:
    return (TEMPLATES / "model_comparison.md").read_text(encoding="utf-8")


def _board_seed() -> str:
    return (TEMPLATES / "experiment_board.md").read_text(encoding="utf-8")


def _checkpoint_seed(case_id: str, route: str) -> str:
    checkpoint = (TEMPLATES / "checkpoint.yaml").read_text(encoding="utf-8")
    return checkpoint.replace("<case_id>", case_id).replace("<route>", route)


def create_case(case_id: str, route: str, cases_root: Path = ROOT / "cases") -> Path:
    if not CASE_ID.fullmatch(case_id):
        raise ValueError("case-id must be 2-64 ASCII letters, digits, '-' or '_'")
    if route not in ROUTES:
        raise ValueError(f"route must be one of {sorted(ROUTES)}")
    case_dir = cases_root / case_id
    if case_dir.exists():
        raise FileExistsError(f"case already exists: {case_dir}")
    for relative in (
        "input", "models", "experiments/code", "experiments/outputs", "reviews", "paper",
    ):
        (case_dir / relative).mkdir(parents=True, exist_ok=False)
    brief = (TEMPLATES / "case_brief.md").read_text(encoding="utf-8")
    brief = brief.replace("# 案例简报：<案例名称>", f"# 案例简报：{case_id}")
    brief = brief.replace("- 案例 ID：", f"- 案例 ID：{case_id}")
    brief = brief.replace("- 当前路由：`optimization` / `data_analysis` / `hybrid` / `insufficient_information`", f"- 当前路由：`{route}`")
    (case_dir / "case_brief.md").write_text(brief, encoding="utf-8")
    (case_dir / "models/candidates.md").write_text(_candidate_seed(route), encoding="utf-8")
    (case_dir / "models/comparison.md").write_text(_comparison_seed(), encoding="utf-8")
    (case_dir / "experiments/board.md").write_text(_board_seed(), encoding="utf-8")
    (case_dir / "checkpoint.yaml").write_text(_checkpoint_seed(case_id, route), encoding="utf-8")
    (case_dir / "decisions.md").write_text((TEMPLATES / "decision_log.md").read_text(encoding="utf-8"), encoding="utf-8")
    (case_dir / "reviews/README.md").write_text("# 审核记录\n\n保存 C1、C2、C3 的精简报告和队员决定。\n", encoding="utf-8")
    (case_dir / "paper/README.md").write_text("# 案例论文\n\n在这里记录本案例与根 `paper/` 工程的章节、图表和引用对应关系。\n", encoding="utf-8")
    (case_dir / "input/README.md").write_text("# 原始输入\n\n把题面和附件放在这里并保持只读，记录来源和字段说明。\n", encoding="utf-8")
    return case_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="create a lightweight modeling case")
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--route", choices=sorted(ROUTES), required=True)
    parser.add_argument("--cases-root", type=Path, default=ROOT / "cases")
    args = parser.parse_args()
    try:
        path = create_case(args.case_id, args.route, args.cases_root)
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL create case: {exc}")
        return 1
    print(f"created case: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
