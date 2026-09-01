"""FIG-OPT-001：贪心 baseline 与精确枚举的总成本对照。

绘图脚本只读 `outputs/data/`，不重新计算任何数值 —— 数据一变只需重跑本脚本。
样式遵守 .agents/skills/competition-engineering/references/figure-standards.md。

matplotlib 不在 requirements-dev.txt 中（那份依赖只服务确定性检查）。缺库时本脚本
明确报告跳过并返回 0，不伪造图片，也不让 CI 因为缺少绘图依赖而失败。
安装：pip install -r requirements-experiments.txt
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

CASE = Path(__file__).resolve().parents[3]
OUT = CASE / "q1/outputs"
FIG_ID = "FIG-OPT-001"
EXP_ID = "EXP-OPT-002"

PALETTE = ["#0072B2", "#E69F00"]


def load_metrics() -> dict:
    return json.loads((OUT / f"data/{EXP_ID}_metrics.json").read_text(encoding="utf-8"))


def main() -> int:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print(f"SKIP {FIG_ID}: matplotlib 未安装；pip install -r requirements-experiments.txt")
        return 0

    matplotlib.rcParams.update({
        "font.sans-serif": ["Songti SC", "Heiti SC", "Source Han Sans SC", "SimHei", "DejaVu Sans"],
        "axes.unicode_minus": False,
        "font.size": 10, "axes.labelsize": 10,
        "xtick.labelsize": 9, "ytick.labelsize": 9, "legend.fontsize": 9,
        "lines.linewidth": 1.3,
        "axes.grid": True, "grid.linewidth": 0.5, "grid.alpha": 0.3,
        "savefig.bbox": "tight",
    })

    metrics = load_metrics()
    labels = {"base": "基础实例\n(容量 2/2)", "capacity_edge": "容量边界实例\n(容量 1/2)"}
    names = list(metrics["instances"])
    exact = [metrics["instances"][name]["objective"] for name in names]
    greedy = [metrics["instances"][name]["baseline_objective"] for name in names]

    fig, axes = plt.subplots(figsize=(8.5 / 2.54 * 2, 6 / 2.54 * 2))
    width = 0.35
    positions = range(len(names))
    bars = [
        axes.bar([p - width / 2 for p in positions], greedy, width,
                 label="M-01 贪心 baseline", color=PALETTE[0]),
        axes.bar([p + width / 2 for p in positions], exact, width,
                 label="M-02 精确枚举", color=PALETTE[1], hatch="//"),
    ]
    for group in bars:
        for bar in group:
            axes.annotate(f"{bar.get_height():g}",
                          (bar.get_x() + bar.get_width() / 2, bar.get_height()),
                          ha="center", va="bottom", fontsize=9)

    axes.set_xticks(list(positions))
    axes.set_xticklabels([labels.get(name, name) for name in names])
    axes.set_ylabel("总成本 / 成本单位")
    axes.set_ylim(0, max(exact + greedy) * 1.25)
    axes.legend(frameon=False)
    axes.set_title(f"两条路线在同一实例集上的总成本对照（{EXP_ID}）", fontsize=10)

    (OUT / "figures").mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(OUT / f"figures/{FIG_ID}.{ext}", dpi=300)
    plt.close(fig)
    print(f"WROTE {OUT / 'figures'}/{FIG_ID}.pdf 和 .png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
