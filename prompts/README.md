# 角色入口

一题使用四个持续会话：Orchestrator、Modeler、Engineer、Writer；C1/C2/C3 各使用一个
新的 Reviewer 会话。同一角色跨阶段继续原会话，不重新启动。

| 角色 | 必读 | 案例输入 |
|---|---|---|
| Orchestrator | `prompts/orchestrator.md` | case 路径、题目路径、授权边界 |
| Modeler | `prompts/modeler.md` | 原题、input、case brief |
| Engineer | `prompts/engineer.md` | Full SPEC、candidates、board、数据 |
| Writer | `prompts/writer.md` | Full SPEC、board、outputs、paper |
| Reviewer | `REVIEWER.md` + 对应节点提示词 | 一张审核卡及其附件 |

`AGENTS.md` 由 Codex 项目自动加载；`agent.md`、contracts、writing 和 Skill 只在遇到
具体问题时按需读取，不是每次启动的前置清单。

快速启动文本见 `prompts/startup/`。审核卡通过：

```bash
make review-packet CASE=cases/<case_id> NODE=C1
```

生成后，在独立 Reviewer 会话读取同一张卡；结果仍写回该卡，不新建 packet/report 两份文件。
