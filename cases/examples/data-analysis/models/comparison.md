# 数据分析路线比较

| 路线 ID | 方法族 | 切分 | 指标 | 成本 | 状态 | 选择理由 |
|---|---|---|---|---|---|---|
| M-01 | descriptive/statistical baseline | time holdout | MAE | low | challenger | 最低可解释基线 |
| M-02 | linear regression | same time holdout | MAE | low | champion | 可解释且能使用特征 |
| M-03 | tree/time-series | same time holdout | MAE、稳定性 | medium | candidate | 检验非线性/自相关价值 |

统一口径：训练前五个时间点，验证中间两个，测试最后两个；所有预处理只在训练段拟合。
