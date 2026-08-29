---
spec_id: SPEC-P2-M01
case_id: hybrid
route_id: M-01
subproblem: 问题2
method_family: forecast-then-optimize
status: full
language: matlab
depends_on: []

# probe 闭环：full 规格必须能追溯到已经跑过的 probe。
probe_spec_id: SPEC-P2-M01-probe
probe_exp_id: EXP-HYB-001
probe_result: PENDING
probe_waiver_reason: "本机无 MATLAB，probe 尚未实际执行；规格第 1 段已写明手算预期值供实测核对"
---

# 预测驱动库存决策 实现规格（MATLAB 主实现）

本规格演示**跨语言契约**：MATLAB 求解并导出，Python 独立复算。

## 1. 目标与判据

- 本次要回答的问题：两阶段（预测后优化）路线在预测误差下的成本恶化幅度是多少？
- 通过判据：
  - 最优备货量 q\* = 8 units，对应成本 8 成本单位；
  - 需求 6/8/10 三个场景下成本分别为 8、8、18 成本单位；
  - Python 侧独立复算的目标值与 MATLAB 报告值相对误差 ≤ 1e-9；
  - 备货量满足 0 ≤ q ≤ 10。
- 失败判据：任一约束违反，或跨语言复算不一致。
- 达到失败判据时的动作：`停止并回问`。

## 2. 数学表述

- 决策变量：$q \in \mathbb{Z}$，备货量，单位 units。
- 参数：容量 $u = 10$ units；持有成本 $h = 1$ 成本单位/unit；缺货惩罚
  $p = 5$ 成本单位/unit；上游点预测需求 $\hat{d} = 8$ units。
- 目标：$\min\ h\,q + p\,\max(\hat{d} - q,\ 0)$。
- 约束：
  - C1（非负）：$q \ge 0$。
  - C2（容量）：$q \le u$。
- 模型边界：单期、单品、点预测；不刻画多期滚动与订货提前期。

## 3. 数据契约

- 上游接口（分析模块 → 决策模块）：

| 字段 | 类型 | 单位 | 时间语义 | 说明 |
|---|---|---|---|---|
| `demand` | int | units | 下一期 | 点预测需求 |
| `service_level` | float | 比例 | 下一期 | 目标服务水平，本规格不参与目标函数 |
| `units` | dict | — | — | 单位声明，供 `validate_hybrid_interface` 检查 |

- 缺失值处理：`demand` 缺失时停止并回问，不用历史均值替代（那会改变模型口径）。
- 极端值：`demand` > 容量时仍按公式计算，缺货惩罚会体现，不截断。
- 明确禁止：不得因为某场景成本高就调整 `shortage_cost`。

## 4. 算法

- 求解方式：`精确求解`（容量范围内枚举，规模极小，不引入求解器）。
- 伪代码：

```text
1. candidates = 0:capacity
2. costs = holding*q + shortage*max(forecast - q, 0)
3. [bestCost, idx] = min(costs)
4. 固定 bestQuantity，在扰动场景 {6,8,10} 上重算成本
```

- 随机种子：`rng(42, 'twister')`。
- 终止条件：枚举完毕。
- 规模预算：11 个候选，运行时间 < 0.1 s。

## 5. 输出契约

### 数据产物

| 文件 | 格式 | 列名与单位 | 说明 |
|---|---|---|---|
| `experiments/outputs/data/EXP-HYB-001_solution.csv` | CSV UTF-8 | `exp_id`、`demand_units`（units）、`quantity_units`（units）、`cost_yuan`（成本单位） | 每个扰动场景一行 |
| `experiments/outputs/data/EXP-HYB-001_metrics.json` | JSON | 见共享格式，另含 `quantity`、`forecast`、`capacity`、`holding_cost`、`shortage_cost` | 复算脚本依赖这些参数 |

MATLAB 侧 `writetable` 必须带 `'Encoding','UTF-8'` 且不写行名，否则 Python 侧读入会
出现列名乱码或多余索引列。

### 图表产物

本规格不出图；扰动场景对比图由 `SPEC-P2-M02` 与场景/鲁棒路线一起出，避免只画一条
路线的曲线让读者误以为已做对照。

## 6. 复算要求

**复算在 Python 侧完成**（`experiments/code/python/recompute_EXP_HYB_001.py`），因为
阶段检查与 CI 只能运行 Python。MATLAB 侧不写复算报告。

| 复算项 | 使用函数 | 判定阈值 |
|---|---|---|
| C1 非负、C2 容量 | `scripts/model_checks.py:check_constraints` | 无 violation |
| 目标值独立重算 | `scripts/model_checks.py:recompute_objective` | 相对误差 ≤ 1e-9 |
| 压力场景成本逐行复算 | 按第 2 段目标函数逐行重算 CSV | 绝对误差 ≤ 1e-9 |

目标函数必须从本规格第 2 段的文字重写，不得读入 MATLAB 算出的 `objective` 再回代 ——
那只能验证 MATLAB 有没有正确执行它自己的代码。

## 7. 明确不做

- 不实现场景生成或鲁棒优化版本（那是 M-03）；
- 不做多期滚动；
- 不在 MATLAB 里调用 Python 引擎或反之，一律用文件交换；
- 不出图。

## 8. 未决问题

| 编号 | 未决内容 | 影响范围 | 建模手计划何时定 |
|---|---|---|---|
| Q1 | `service_level` 目前只在接口里声明，未进入目标函数。是作为硬约束（服务水平 ≥ 0.9）还是作为多目标的第二目标？ | 目标函数与 C 约束集 | 接入真实题面后确定 |
| Q2 | 扰动场景 {6,8,10} 是手工挑的，没有分布依据。是否改为按上游预测误差分布抽样？ | 稳健性结论的可推广性 | 上游 M-01 给出误差分布后确定 |
