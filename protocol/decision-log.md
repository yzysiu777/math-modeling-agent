# 决策日志写法

每次改变数据、模型、算法、参数或论文表述时，记录一条决策；若发生在
已通过 Gate 之后，同时建立 `change_impact_record`、
`revision_validation_record` 和必要的 `human_review_card`：

```text
Decision ID:
Time:
Owner:
Change:
Reason:
Alternatives considered:
Evidence:
Impact:
Required reruns:
Reviewer:
Status:
```

修订记录必须标注 `R0`、`R1`、`R2` 或 `R3`、受影响 Gate、claim、实验和
图表，以及只允许使用的安全检查 ID。R0 不自动复跑实验；R2/R3 影响实验
时必须有新实验 ID 和输出哈希。

禁止用“模型认为更好”“效果看起来更稳定”作为唯一理由。至少补充指标、反例、约束检查、论文依据或人工决定。
