---
spec_id: SPEC-P1-M02
case_id: data-analysis
route_id: M-02
subproblem: 问题1
method_family: linear regression
status: full
language: python
depends_on: []
---

# 时间感知线性回归 实现规格

probe（`SPEC-P1-M02-probe`）已通过。本规格固定切分口径与复算要求，使其可作为其余
路线的公平对照。

## 1. 目标与判据

- 本次要回答的问题：在无未来信息泄漏的前提下，线性回归相对历史均值 baseline 能降低
  多少留出段误差？
- 通过判据：
  - 留出段线性回归 MAE = 0.5，历史均值 baseline MAE = 10.9（合成数据下为确定值）；
  - `check_data_split` 在正常切分上返回 0 个错误；
  - 刻意构造的泄漏反例被检出（否则说明检查器形同虚设）。
- 失败判据：切分检查报错、反例未被检出、或 MAE 与上述值不符。
- 达到失败判据时的动作：`停止并回问`。

## 2. 数学表述

- 实体集合 $E$，每个实体一个时间点 $t$，特征 $x$，标签 $y$。
- 模型：$\hat{y} = \beta_0 + \beta_1 x$，最小二乘闭式解
  $\beta_1 = \sum(x-\bar{x})(y-\bar{y}) / \sum(x-\bar{x})^2$，$\beta_0 = \bar{y} - \beta_1\bar{x}$。
- 指标：$\mathrm{MAE} = \frac{1}{n}\sum|y_i - \hat{y}_i|$，单位与 $y$ 相同。
- baseline：$\hat{y} = \bar{y}_{\text{train}}$（历史均值）。
- 模型边界：单特征、无正则、假设线性关系在外推区间成立 —— 这一条已由 probe 在本合成
  数据上验证，换数据必须重验。

## 3. 数据契约

- 输入：合成数据 `y = 2x + (x mod 2)`，`x = time = 1…9`，`id = e1…e9`。
- 字段表：

| 列名 | 类型 | 单位 | 说明 |
|---|---|---|---|
| `id` | str | — | 实体主键，切分依据 |
| `time` | int | 期 | 时间顺序，切分依据 |
| `x` | int | — | 特征 |
| `y` | int | — | 标签 |

- 粒度与主键：一个实体一个时间点，主键 `id`。
- 切分规则（**写死**）：按 `time` 升序，1–5 为 train，6–7 为 validation，8–9 为 test。
  不打乱，不分层，不做交叉验证。
- 缺失值：本合成数据无缺失；接入真实数据后此段必须重写，不得沿用。
- 明确禁止：**不得在全量数据上 fit 任何预处理器**（标准化、编码、填充）。本规格不用
  预处理器，接入真实数据时这条仍然有效。

## 4. 算法

- 求解方式：`统计模型`，最小二乘闭式解，不迭代。
- 伪代码：

```text
1. 按 time 切分 train / validation / test
2. check_data_split 验证无重叠、无时间倒置
3. 在 train 上求 beta_0, beta_1
4. 在 test 上预测并计算 MAE
5. 与历史均值 baseline 的 MAE 对比
6. 构造重复实体的反例切分，确认检查器报错
```

- 随机种子：不涉及随机。
- 终止条件：闭式解，一次算完。
- 规模预算：9 条记录，运行时间 < 0.1 s。

## 5. 输出契约

### 数据产物

| 文件 | 格式 | 列名与单位 | 说明 |
|---|---|---|---|
| `experiments/outputs/data/EXP-DA-002_predictions.csv` | CSV UTF-8 | `id`、`time`（期）、`y_true`、`y_pred_baseline`、`y_pred_linear` | 留出段逐行预测 |
| `experiments/outputs/data/EXP-DA-002_metrics.json` | JSON | 见共享格式，另含 `split`、`baseline_test_mae`、`linear_test_mae` | 切分规模与两个 MAE |

### 图表产物

本规格不出图。留出段只有 2 个点，画图会给读者「趋势成立」的错误印象；等接入真实
数据、样本量足够后再出预测对照图。

## 6. 复算要求

| 复算项 | 使用函数 | 判定阈值 |
|---|---|---|
| 切分内主键无重复、切分间无重叠 | `scripts/model_checks.py:check_data_split` | 0 个错误，`kind: split_overlap` |
| 时间顺序无倒置 | 同上（`time_key="time"`） | 0 个错误 |
| 泄漏反例能被检出 | 同上，输入重复实体的切分 | 必须返回非空错误，`kind: leakage` |

复算报告写入 `experiments/outputs/checks/EXP-DA-002.json`。

「反例能被检出」这一项容易被当成多余 —— 它不是。一个从不报错的检查器和没有检查器
是一样的，而这种失效是静默的。

## 7. 明确不做

- 不做特征工程、不加正则、不调超参；
- 不做交叉验证（时序数据 + 9 条记录，K 折没有意义）；
- 不出图；
- 不实现树模型或时序模型（那是 M-01 与 M-03）。

## 8. 未决问题

| 编号 | 未决内容 | 影响范围 | 建模手计划何时定 |
|---|---|---|---|
| Q1 | 合成数据趋势过强，baseline 必然惨败。需要补一个弱趋势对照数据集，否则「线性优于统计基线」的比较没有说服力 | 论文中路线对比的结论强度 | 接入真实题面数据后补 |
| Q2 | 留出段只有 2 个点，MAE 的方差无法估计。是否需要滚动原点评估？ | 误差估计的可信度 | 样本量确定后决定 |
