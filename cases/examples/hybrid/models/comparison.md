# 混合路线比较

| 路线 ID | 上游 | 下游 | 误差处理 | 指标 | 状态 | 选择理由 |
|---|---|---|---|---|---|---|
| M-01 | point forecast | deterministic quantity | none | cost/feasibility | challenger | 最短端到端 baseline |
| M-02 | scenario forecast | robust quantity | scenarios | cost/service | champion | 可解释地传递误差 |
| M-03 | quantile forecast | service constraint | quantile | service/cost | candidate | 直接控制缺货风险 |

接口版本：`demand`、`service_level`、`units`；上游误差必须在下游压力测试中出现。

## 当前结论

当前 Champion：M-01（点预测—确定性优化）；当前 Challenger：M-02（情景/鲁棒决策）。

先跑 M-01 的 probe，验证「点预测直接代入确定性模型」在需求偏离时是否稳健 ——
这条假设不成立的话，整条两阶段路线都要换成场景/鲁棒版本。

Challenger 选 M-02 的理由：它显式处理预测误差，完全不依赖点预测精度，是 M-01 的
失效模式下的兜底；M-03（分位数预测）与 M-01 同样建立在「上游预测可用」之上，做不了
保险。

## 已知的比较局限

扰动场景 {6, 8, 10} 是手工挑的，没有分布依据。在有上游误差分布之前，「成本恶化
不超过 2.25 倍」只对这三个点成立，不能写成稳健性结论。见 `specs/SPEC-P2-M01.md`
第 8 段 Q2。
