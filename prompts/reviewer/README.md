# Independent Reviewer 关键挑战提示词

工作台在 C1、C2、C3 三个关键节点使用厂商无关的 Independent Reviewer。每次只复制一个
提示词到新的审核会话，并附上精简审核包。审核者不重做整题、不要求全量实验、不直接
修改案例文件，只输出挑战报告；队员将接受、拒绝或延期及原因写入 `decisions.md`，再
由 Codex 修改和复算。

| 节点 | 文件 | 重点 |
|---|---|---|
| C1 | `C1_problem_challenge.md` | 题意、目标、约束、单位、遗漏、替代解释和最小反例 |
| C2 | `C2_model_challenge.md` | 方法族、公式、算法不变量、实现一致性和架构反例 |
| C3 | `C3_results_challenge.md` | 复算、对照公平性、泄漏、稳定性、数字来源和强结论 |

## 可选审核者

以下是使用场景提示，不是排名，也不是硬依赖；比赛日要重新确认实际可用性：

- Gemini Pro：适合 C1、长文/PDF、数据和 C3 论文一致性审核；
- Grok 旗舰推理模型：适合 C2 架构反驳、反例和替代算法；
- Codex fresh task：外部模型不可用时的后备方案，必须新建任务、隔离上下文并使用不同审核提示词；
- human specialist：处理题意、模型取舍和无法由模型决定的专业问题。

无论选择哪种审核者，都必须使用新会话、精简审核包、不同方法论视角和反例任务。相同
厂商的不同模型最多提供上下文/方法论隔离，不能仅凭厂商名称声称完整独立性。

## 元信息

每个包和报告都填写：

```yaml
reviewer_provider: <实际承担者；允许新增值，不是封闭白名单>
reviewer_model: <实际模型或人工角色>
review_session: fresh
saw_main_conversation: false
critical_node: C1 | C2 | C3
```

`fresh` 表示新会话或上下文隔离的新任务；`saw_main_conversation: false` 表示未看到主
解完整聊天和主模型自我辩护。不得保存或要求隐藏思维链。
