# 图表清单

编程手每生成一张图就回填一行。写作手只从这张表取图，不直接去目录里翻文件。

| FIG-ID | 来源 EXP-ID | 生成脚本 | 数据文件 | 图题草稿 | 论文位置 | 状态 |
|---|---|---|---|---|---|---|
| FIG-OPT-001 | EXP-OPT-002 | `q1/code/python/plot_FIG_OPT_001.py` | `q1/outputs/data/EXP-OPT-002_metrics.json` | 两条路线在同一实例集上的总成本对照 | 第 4 章 结果 | `final` |

## 本例说明

图与计算分离：`run_demo.py` 负责算并落盘，`plot_FIG_OPT_001.py` 只读
`outputs/data/`。数据一变只需重跑绘图脚本，不用重算。

绘图依赖不在 `requirements-dev.txt` 里（那份只服务确定性检查）。缺 matplotlib 时脚本
明确报告跳过并返回 0，不伪造图片：

```bash
pip install -r requirements-experiments.txt
python cases/examples/optimization/q1/code/python/plot_FIG_OPT_001.py
```

## 产物要求

每个 FIG-ID 同时存在 `<FIG-ID>.pdf`（矢量，入 LaTeX）和 `<FIG-ID>.png`（300 dpi，预览）。
样式遵守 `.agents/skills/competition-engineering/references/figure-standards.md`。

数据更新后对应图立刻标 `stale` 并重跑脚本；论文里不允许出现 `stale` 状态的图。
