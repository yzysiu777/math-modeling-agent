# 当前架构

## 目标

工作台在四天内帮助团队扩大方法空间、用低成本实验筛选路线、纠正关键错误，并把稳定
结果及时写入论文。工程质量体现在模型、算法、实验和论文的一致性。

## 四个协作主体

| 主体 | 主要职责 |
|---|---|
| Codex | 主解、候选路线、代码、实验、图表和论文初稿 |
| Independent Reviewer | C1 题意、C2 架构、C3 结果与强结论挑战 |
| 确定性脚本 | 结构、切分、泄漏、约束、目标值、LaTeX 和 PDF 检查 |
| 人类队员 | 关键假设、路线取舍、比赛策略、官方规则和最终提交 |

## 运行结构

`AGENTS.md` 是 Codex 自动读取的项目规则；`.agents/skills/` 提供按任务加载的方法；
`cases/` 保存每道题的模型和实验状态；`paper/` 与 `writing/` 负责论文；`prompts/reviewer/`
提供三个 Independent Reviewer 挑战入口。

```text
AGENTS.md
  ├─ .agents/skills/industrial-mathematical-modeling
  ├─ .agents/skills/model-race
  ├─ .agents/skills/competition-paper-writing
  ├─ cases/<case_id>/
  ├─ prompts/reviewer/C1-C3
  └─ paper/ + writing/
```

## 设计原则

- 先产生方法论不同的路线，再通过实验收敛；
- 先运行便宜、可解释、可手算的实验；
- 保留 Champion 和不同方法族的 Challenger；
- Independent Reviewer 只挑战关键节点，不完整重做主解；
- 数值检查使用独立计算，语义判断交给模型与队员；
- 论文与实验同步，强结论必须有相应证据；
- 当届官方规则在比赛开始后重新核对。

## 能力边界

工作台不包含具体历年题目的标准答案，不自动调用任何审核模型 API，也不能替代队员理解题面
或确认最终提交。结构检查器只能发现明显缺失和重复，不能判断两条模型路线在数学意义
上是否真正独立；`scripts/model_pool.py` 还会检查非法状态和重复路线 ID，但 MIP 的
arc-flow、path-flow、time-indexed 等建模表述是否构成独立路线，仍由 C2 与队员判断。
