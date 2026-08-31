# 启动模板

生产角色由队员人工启动，一题只启动一次，之后由队员在原会话继续；统一使用
`gpt-5.6-sol`、`high`：

1. Orchestrator；
2. Modeler；
3. Engineer（进入 Full 实现时）；
4. Writer（有稳定 Baseline 时）。

C1/C2/C3 也由队员人工调用新的外部 Claude 会话。Orchestrator 不得启动任何新 Agent，
只输出可复制提示词。模板只指向
一份角色协议，不要求重读 agent、contracts 和全部 Skill。
