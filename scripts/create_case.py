"""Create the smallest useful competition case workspace."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
ROUTES = {"optimization", "data_analysis", "hybrid", "insufficient_information"}
CASE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{1,63}$")


def _candidate_seed(route: str) -> str:
    return f"""# 候选路线与比较

案例路由：`{route}`

先发散至少六条，再把至少三条方法论不同的路线写成卡片。以下仅为结构占位。

## M-01：可解释 baseline

- 方法族：simple interpretable baseline
- 核心思想：待根据题面替换
- 最便宜的证伪实验：待根据题面替换
- 状态：`candidate`

## M-02：结构不同的候选

- 方法族：structural mathematical model
- 核心思想：待根据题面替换
- 最便宜的证伪实验：待根据题面替换
- 状态：`candidate`

## M-03：风险不同的候选

- 方法族：risk-aware alternative
- 核心思想：待根据题面替换
- 最便宜的证伪实验：待根据题面替换
- 状态：`candidate`

## 七维度比较

| 路线 | 效果 | 实现成本 | 运行成本 | 数据满足度 | 可解释性 | 论文价值 | 风险 | 下一步 |
|---|---|---|---|---|---|---|---|---|
| M-01 |  |  |  |  |  |  |  |  |
| M-02 |  |  |  |  |  |  |  |  |
| M-03 |  |  |  |  |  |  |  |  |

## 当前取舍

- Champion：待 Probe
- Challenger：待 Probe
- 下一项最有信息价值的实验：EXP-001
"""


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
        "input", "models", "specs",
        "experiments/code/python", "experiments/code/matlab",
        "experiments/outputs/data", "experiments/outputs/figures",
        "experiments/outputs/checks", "experiments/outputs/logs",
        "reviews", "paper",
    ):
        (case_dir / relative).mkdir(parents=True, exist_ok=True)

    brief = (TEMPLATES / "case_brief.md").read_text(encoding="utf-8")
    brief = brief.replace("# 案例简报：<案例名称>", f"# 案例简报：{case_id}")
    brief = brief.replace("- 案例 ID：", f"- 案例 ID：{case_id}")
    brief = brief.replace(
        "- 当前路由：`optimization` / `data_analysis` / `hybrid` / `insufficient_information`",
        f"- 当前路由：`{route}`",
    )
    (case_dir / "case_brief.md").write_text(brief, encoding="utf-8")
    (case_dir / "models/candidates.md").write_text(_candidate_seed(route), encoding="utf-8")
    (case_dir / "experiments/board.md").write_text(
        (TEMPLATES / "experiment_board.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (case_dir / "checkpoint.yaml").write_text(_checkpoint_seed(case_id, route), encoding="utf-8")
    (case_dir / "decisions.md").write_text(
        (TEMPLATES / "decision_log.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (case_dir / "reviews/README.md").write_text(
        "# Independent Reviewer 审核卡\n\n"
        "C1/C2/C3 各保存一张可往返填写的审核卡。采纳 finding 零往返；拒绝 finding 时由原\n"
        "Reviewer 在同一卡回签一次。不要再建立 packets/ 副本。\n",
        encoding="utf-8",
    )
    (case_dir / "specs/README.md").write_text(
        "# Full SPEC\n\n"
        "只为进入正式赛马的路线建立五段 Full SPEC。Probe 直接写实验板，不建独立规格。\n\n"
        "- 模板：`templates/spec.md`\n"
        "- 检查：`make spec-check CASE=cases/<case_id>`\n",
        encoding="utf-8",
    )
    (case_dir / "paper/README.md").write_text(
        "# 案例论文\n\n记录本案例与根 paper/ 工程的章节、图表和引用对应关系。\n",
        encoding="utf-8",
    )
    (case_dir / "paper/claim_map.md").write_text(
        (TEMPLATES / "claim_map.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (case_dir / "experiments/outputs/figures/manifest.md").write_text(
        (TEMPLATES / "figure_manifest.md").read_text(encoding="utf-8"), encoding="utf-8"
    )
    (case_dir / "experiments/outputs/checks/README.md").write_text(
        "# 复算报告\n\nChampion 和论文关键结果的复算报告写在这里。\n",
        encoding="utf-8",
    )
    (case_dir / "input/README.md").write_text(
        "# 原始输入\n\n把题面和小型说明附件放在这里并保持只读。\n\n"
        "大数据保持原位，每个获准目录单独写一行：\n\n"
        "`data_root: /absolute/path/to/allowed/data`\n",
        encoding="utf-8",
    )
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
