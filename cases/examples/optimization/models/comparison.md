# 运筹路线比较

| 路线 ID | 方法族 | 最小实验 | 目标/约束 | 成本 | 状态 | 选择理由 |
|---|---|---|---|---|---|---|
| M-01 | constructive heuristic | 局部选择 vs 穷举 | 总成本/容量 | low | challenger | 作为可解释 baseline |
| M-02 | exact enumeration | 全部分配枚举 | 总成本/容量 | low | champion | 小实例真值 |
| M-03 | mixed-integer programming | 线性约束复算 | 总成本/容量 | medium | candidate | 规模扩展 |

当前 Champion：M-02（小实例）；当前 Challenger：M-01。M-03 在规模扩大时继续测试。
