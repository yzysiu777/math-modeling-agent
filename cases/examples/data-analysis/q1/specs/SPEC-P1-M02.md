---
spec_id: SPEC-P1-M02
case_id: data-analysis
route_id: M-02
subproblem: 问题1
method_family: linear regression
status: full
language: python
probe_exp_id: EXP-DATA-002
probe_result: PASS
probe_waiver_reason: ""
reviewer_probe_recheck_exp_id: ""
---

# 时间感知线性回归 Full SPEC

## 1. 目标与判据

- 在不使用未来信息的前提下比较线性回归与历史均值 baseline。
- 固定留出段上，线性回归 MAE 必须为 0.5，baseline MAE 为 10.9。
- 正常切分必须返回 0 个错误，刻意构造的泄漏反例必须被检查器检出。
- 全部路线使用相同时间切分和 MAE 口径。

## 2. 数学模型

模型为 $\hat y=\beta_0+\beta_1x$，仅在训练段用最小二乘闭式解估计参数；指标为
$\mathrm{MAE}=n^{-1}\sum_i|y_i-\hat y_i|$。baseline 使用训练段标签均值。模型边界是单
特征、小样本、确定性合成数据；不声称线性关系能推广到其他数据。

## 3. 数据契约与显式假设

数据为 `x=time=1…9`、`y=2x+(x mod 2)`、唯一主键 `id=e1…e9`。按时间固定切成
train 1–5、validation 6–7、test 8–9，不打乱。任何填充、编码或标准化只能在训练段拟合。
本数据无缺失；接入真实数据时必须重写缺失、异常、重复、单位和时间基准规则。

## 4. 算法与输出

入口为 `q1/code/python/run_demo.py`：先检查切分，再在 train 上求系数，在 test
上计算两个 MAE，最后用重复实体构造泄漏反例。输出逐行预测、指标 JSON 和
`q1/outputs/checks/EXP-DATA-002.json`。留出段只有两个点，本演示不生成趋势图。

## 5. 复算与遗留假设

独立检查主键无重复、集合无交叠、时间无倒置，且泄漏反例必须产生错误；MAE 从逐行预测
重新计算。`EXP-DATA-002` 已 PASS，未使用 Reviewer Probe。合成数据趋势过强，不能据此
写“线性模型普遍优于统计基线”；真实竞赛中还需弱趋势压力样本或滚动原点评估。
