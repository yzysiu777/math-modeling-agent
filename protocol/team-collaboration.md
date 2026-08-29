# 案例团队协作

本文件约束仓库内案例协作，不约束外部开发控制面。团队用 Git 分支和 Markdown 源文件
协作，不把开发交接单复制到案例。

## 文件分工

- `case_brief.md`：队长维护题意、目标和歧义；
- `models/`：建模成员维护候选路线和比较；
- `experiments/`：实验成员维护代码、板和关键输出；
- `reviews/`：人工复制保存 C1/C2/C3 报告；
- `paper/`：论文成员维护案例级说明，根 `paper/` 维护共享 LaTeX 工程；
- `decisions.md`：队长记录路线和提交取舍。

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

提交说明包含：改变了什么、为什么改变、运行了什么、结果和下一步。被淘汰路线
保留在 `models/comparison.md` 或 `experiments/board.md`，不删除来美化结果。

## Independent Reviewer 使用

队员手动把精简审核包复制到新的 Independent Reviewer 会话。审核者可以是 Gemini、
Grok、隔离的新 Codex 任务、其他模型或人类专家。报告保存到案例 `reviews/`，只提出
挑战和建议；队员明确接受或拒绝后，Codex 才实施修改。不得让同一主会话同时写方案、
审方案和替自己宣布结果。

每个审核包/报告都保留 `reviewer_provider`、`reviewer_model`、`review_session: fresh`、
`saw_main_conversation: false` 和 `critical_node`。审核者是否独立取决于新会话、最小
审核包、方法论差异和反例任务，不取决于厂商名称；不传递主解完整聊天或隐藏推理。
