---
spec_id: SPEC-P1-M02-probe
case_id: data-analysis
route_id: M-02
subproblem: 问题1
method_family: linear regression
status: probe
language: python
depends_on: []
---

# 时间感知线性回归 轻测试（probe）

## 1. 要证伪的假设

「特征 x 与标签 y 的线性关系在训练区间之外仍然成立。」如果外推区间上误差与训练区间
相当，这条路线值得深入；否则要换成时序模型或分段模型。

同时要证伪一条更基础的假设：「按时间切分确实避免了泄漏。」

## 2. 判据

- 通过：线性回归在留出时段的 MAE ≤ 1.0，且明显低于历史均值 baseline（低于其
  1/5）；`check_data_split` 在正常切分上返回 0 个错误。
- 失败：MAE > 1.0，或切分检查报出重叠/时间倒置，或线性回归不优于 baseline。

## 3. 最小实例 / 最小样本

- 规模：9 条记录，一实体一时间点。
- 来源：合成数据。
- 构造方式：`y = 2x + (x mod 2)`，`x = time = 1…9`；按时间切成 train 1–5、
  validation 6–7、test 8–9。
- 真值来源：解析解。斜率真值 2，噪声项是 0/1 交替，故留出段 MAE 期望约 0.5。

## 4. 实现要点

- 输入：上述合成数据，不读外部文件。
- 核心步骤：
  1. `check_data_split(train, validation, test, key="id", time_key="time")`；
  2. 在 train 上用最小二乘闭式解求斜率与截距；
  3. 在 test 上算 MAE，与历史均值 baseline 对比；
  4. 另构造一个重复实体的切分作反例，确认检查器**真的会报错**。
- 输出：两个 MAE、切分错误列表、反例是否被检出。
- 随机种子：不涉及随机（合成数据确定性生成）。

## 5. 结果回填

- 实验 ID：EXP-DA-002
- 实际结果：线性回归 test MAE = 0.5，历史均值 baseline test MAE = 10.9；正常切分
  0 个错误；泄漏反例被检出（`test contains duplicate id values`）。
- 判定：`PASS`
- 观察到的额外信息：baseline 差得离谱（10.9）是因为合成数据是强趋势的，历史均值必然
  严重低估外推段。**这不能写成「线性模型显著优于统计基线」的一般结论** —— 换成弱趋势
  数据结论可能反转。
- 建议：`升级为 full 规格`，并在 full 规格里加一个弱趋势对照数据集。
