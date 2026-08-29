# 数据分析路线比较

| 路线 ID | 方法族 | 切分 | 指标 | 成本 | 状态 | 选择理由 |
|---|---|---|---|---|---|---|
| M-01 | descriptive/statistical baseline | time holdout | MAE | low | challenger | 最低可解释基线 |
| M-02 | linear regression | same time holdout | MAE | low | champion | 可解释且能使用特征 |
| M-03 | tree/time-series | same time holdout | MAE、稳定性 | medium | candidate | 检验非线性/自相关价值 |

统一口径：训练前五个时间点，验证中间两个，测试最后两个；所有预处理只在训练段拟合。

## 当前结论

当前 Champion：M-02（时间感知线性回归）；当前 Challenger：M-01（历史均值统计基线）。

先跑 M-02 的 probe，因为它同时验证两条假设：线性关系能否外推，以及按时间切分是否
真的避免了泄漏。后者对所有路线都成立，一次验证受益三条。

Challenger 选 M-01 而不是 M-03 的理由：M-01 完全不依赖「线性关系成立」这条假设，
M-02 失效时它仍然可用；M-03（树/时序模型）与 M-02 共享「训练区间的关系能外推到留出
区间」这一假设，做不了保险。

M-03 暂缓：9 条记录喂不动树模型，等真实数据规模确定后再评估。

## 已知的比较局限

合成数据趋势过强，baseline 的 MAE（10.9）必然远差于线性回归（0.5）。**这不构成
「线性模型显著优于统计基线」的一般结论** —— 见 `specs/SPEC-P1-M02.md` 第 8 段 Q1，
需要补一个弱趋势对照数据集。
