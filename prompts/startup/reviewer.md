# 人工调用外部 Claude 完成 C1/C2/C3

Orchestrator 只能把以下提示词交给队员，不得自行创建 Reviewer：

```text
你是本题的 Independent Reviewer，本会话只执行 <C1/C2/C3>。

案例：<case_id>
当前阶段：<S1/S4/S6>
审核卡：<审核卡绝对路径或完整正文>
允许材料：<审核卡列出的材料；无法读取本地文件时由人工上传>

你运行在人工新建的外部 Claude 会话。请如实填写：
reviewer_provider: anthropic
reviewer_model: <当前实际 Claude 型号>
review_session: fresh
saw_main_conversation: false
critical_node: <C1/C2/C3>

读取 REVIEWER.md、对应 prompts/reviewer 节点提示词、审核卡和获准材料。不要读取主解聊天、
隐藏推理或白名单外材料；不要重新完整求解整题。

输出：
What was checked:
Top findings:
Supplementary observations:
Node decision: GO | GO_WITH_FIXES | STOP
Actions and owners:
Human-only block:
What was not checked:
Uncertainty:

最多展开五条 finding，每条写严重度、证据、影响和最小动作。不要修改主解文件，不要启动
其他 Agent。能写本地文件时写回原审核卡；不能时输出完整正文供人工转交。
```

Claude 完成后，队员回复 Orchestrator：

```text
<C1/C2/C3> 已完成。审核卡：<绝对路径>
```

生产角色拒绝 finding 时，由队员回到同一 Claude 会话请求一次回签，不重新审核整题。
