# 混合路线比较

| 路线 ID | 上游 | 下游 | 误差处理 | 指标 | 状态 | 选择理由 |
|---|---|---|---|---|---|---|
| M-01 | point forecast | deterministic quantity | none | cost/feasibility | challenger | 最短端到端 baseline |
| M-02 | scenario forecast | robust quantity | scenarios | cost/service | champion | 可解释地传递误差 |
| M-03 | quantile forecast | service constraint | quantile | service/cost | candidate | 直接控制缺货风险 |

接口版本：`demand`、`service_level`、`units`；上游误差必须在下游压力测试中出现。
