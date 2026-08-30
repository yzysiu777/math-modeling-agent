# C1/C2/C3 节点提示词

共同规则在根目录 `REVIEWER.md`。每个节点由队员人工调用一个新的外部 Claude 会话，
并使用一张审核卡：

- C1：原题、附件、字段与 brief；
- C2：Champion/Challenger、Full SPEC、Probe 与关键假设；
- C3：3–5 条关键 Claim、数据和复算。

Reviewer 给出节点决定；采纳零往返，生产角色拒绝 finding 时才回签一次。
Orchestrator 不得自行启动 Reviewer，也不得用生产 Codex 会话替代 Claude。
