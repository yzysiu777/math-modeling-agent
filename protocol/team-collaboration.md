# 案例团队协作

本文件约束仓库内案例协作，不约束外部开发控制面。团队用 Git 分支和 Markdown 源文件
协作，不把开发交接单复制到案例。

## 文件分工

- `case_brief.md`：Modeler 维护题意、目标和歧义；
- `models/candidates.md`：Modeler 统一维护候选路线、比较和取舍；
- `experiments/`：实验成员维护代码、板和关键输出；
- `reviews/`：Orchestrator 到节点创建一张卡，Reviewer 在同一卡填写；
- `paper/`：论文成员维护案例级说明，根 `paper/` 维护共享 LaTeX 工程；
- `decisions.md`：只记录官方硬冲突、授权扩张和最终提交等人工决定。

同一时刻一份文件只有一个写入者。大段内容通过独立分支和小提交合并，先解决
同一文件冲突再继续实验。原始题面和附件不改名到失去来源，也不放入自动生成的
输出目录。

## 推荐分支

```text
model/<任务>       模型公式、算法和小实例
analysis/<任务>    数据清洗、实验和比较
paper/<章节>       论文章节、图表和引用
review/<编号>      审核意见整理和复现
```

提交说明包含：改变了什么、为什么改变、运行了什么、结果和下一步。被淘汰路线保留在
`models/candidates.md`，失败实验保留在 `experiments/board.md`，不删除来美化结果。

## Independent Reviewer 使用

Orchestrator 到节点生成轻量审核卡，并把卡与卡中列出的原始材料交给新的 Independent
Reviewer 会话。审核者可以是 Gemini、Grok、隔离的新 Codex 任务、其他模型或专家。
产出方可直接采纳并实施 finding；若拒绝，Reviewer 必须在同一卡回签一次。不得让同一
主会话同时写方案、审方案和替自己宣布结果。

每张审核卡保留 `reviewer_provider`、`reviewer_model`、`review_session: fresh`、
`saw_main_conversation: false` 和 `critical_node`。审核者是否独立取决于新会话、最小
审核包、方法论差异和反例任务，不取决于厂商名称；不传递主解完整聊天或隐藏推理。
