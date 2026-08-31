# 角色入口

一个案例使用持续 Orchestrator；每个子问题各有持续 Modeler、Engineer、Writer。生产角色由队员
人工启动，固定 `gpt-5.6-sol`、`high`。C1/C2/C3 由队员人工启动新的 Independent Reviewer
会话，provider/model 如实填写。

| 角色 | 必读 | 当前输入 |
|---|---|---|
| Orchestrator | `prompts/orchestrator.md` | 案例、当前题、sources 与 checkpoint |
| Modeler | `prompts/modeler.md` | 题面、本题数据范围、brief、board |
| Engineer | `prompts/engineer.md` | 本题 Full SPEC、board、白名单 |
| Writer | `prompts/writer.md` | 本题 SPEC、outputs、共享 claim map |
| Reviewer | `REVIEWER.md` + 节点提示词 | 一张审核卡与允许材料 |

快速模板在 `prompts/startup/`。每份都必须填写“当前子问题”和“本题目录”。普通回报只用
`agent.md` 六行；跨角色时才展开交接。审核卡命令：

```bash
make review-packet CASE=cases/<case_id> NODE=C1 QUESTION=q1
```
