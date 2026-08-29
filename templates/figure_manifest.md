# 图表清单

编程手每生成一张图就回填一行。写作手只从这张表取图，不直接去目录里翻文件。

| FIG-ID | 来源 EXP-ID | 生成脚本 | 数据文件 | 图题草稿 | 论文位置 | 状态 |
|---|---|---|---|---|---|---|
| FIG-001 | EXP- | `experiments/code/python/plot_.py` | `outputs/data/_.csv` |  | 第 x 章 | `draft` |

## 字段约定

- `FIG-ID`：全案例唯一，图和表分开编号（表用 `TAB-`）。
- `来源 EXP-ID`：必须在 `experiments/board.md` 中存在。图不能凭空产生。
- `生成脚本`：能重新跑出同一张图的入口。改图重跑脚本，不要手工修图。
- `数据文件`：图里每个点的来源。写作手核数字时按这一列追溯。
- `图题草稿`：编程手写事实描述即可；写作手负责改成论文语言，但**不得改变其中的数值和结论强度**。
- `状态`：`draft`（可用于讨论） / `final`（已定稿进论文） / `stale`（数据已更新，图待重跑）。

## 产物要求

每个 FIG-ID 同时存在两个文件：

```text
experiments/outputs/figures/<FIG-ID>.pdf   矢量，入 LaTeX
experiments/outputs/figures/<FIG-ID>.png   300 dpi，供预览和讨论
```

样式遵守 `.agents/skills/competition-engineering/references/figure-standards.md`。
Python 与 MATLAB 生成的图必须视觉一致（同字体、同字号、同配色）。

## 数据更新后

上游数据一变，对应图立刻标 `stale` 并重跑脚本。论文里不允许出现 `stale` 状态的图。
