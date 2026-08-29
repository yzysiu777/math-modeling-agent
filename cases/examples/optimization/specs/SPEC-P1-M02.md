---
spec_id: SPEC-P1-M02
case_id: optimization
route_id: M-02
subproblem: 问题1
method_family: exact enumeration
status: full
language: python
depends_on: []

# probe 闭环：full 规格必须能追溯到已经跑过的 probe。
probe_spec_id: SPEC-P1-M02-probe
probe_exp_id: EXP-OPT-002
probe_result: PASS
probe_waiver_reason: ""
---

# 小规模精确枚举 实现规格

probe（`SPEC-P1-M02-probe`）已通过：枚举在 1 s 内给出与手算一致的真值。本规格把它
扩成可复用的对照基准，并补上 probe 暴露出的容量边界盲点。

## 1. 目标与判据

- 本次要回答的问题：全枚举能否稳定给出可作为对照基准的真值，并覆盖容量成为紧约束
  的情形？
- 通过判据：
  - 基础实例（容量 2/2）最小总成本 = 4，分配为 d1→A、d2→B、d3→B；
  - 容量边界实例（容量 1/2）最小总成本 = 4，A 被分配 1 个需求点；
    （原判据写的是 6，由编程手回问后更正，见 `SPEC-P1-M02.questions.md` Q1。
    该实例实际不构成容量紧约束，测不到容量处理是否正确。）
  - 两个实例的目标值独立重算与枚举报告值相对误差 ≤ 1e-9；
  - 全部约束逐条通过。
- 失败判据：任一实例无可行解、目标值不符、或约束检查报告 violation。
- 达到失败判据时的动作：`停止并回问`。

## 2. 数学表述

- 集合：需求点 $D=\{d_1,d_2,d_3\}$，服务点 $F=\{A,B\}$。
- 参数：成本 $c_{df}$（单位：成本单位），容量 $u_f$（单位：需求点个数）。
- 决策变量：$x_{df}\in\{0,1\}$，$x_{df}=1$ 表示需求点 $d$ 分配给服务点 $f$。
- 目标：$\min \sum_{d\in D}\sum_{f\in F} c_{df}x_{df}$。
- 约束：
  - C1（恰好分配一次）：$\sum_{f\in F} x_{df}=1,\ \forall d\in D$。
  - C2（容量）：$\sum_{d\in D} x_{df}\le u_f,\ \forall f\in F$。
  - C3（变量域）：$x_{df}\in\{0,1\}$。
- 初始/终止条件：无状态转移，一次性求解。
- 模型边界：仅适用于 $|F|^{|D|}$ 可枚举的规模；需求点超过约 20 个即不适用。

## 3. 数据契约

- 输入：本规格自带常量，不读外部文件（演示案例无附件）。
- 参数表：

| 名称 | 含义 | 单位 | 取值 |
|---|---|---|---|
| `COST[d][f]` | 需求点 d 分配给服务点 f 的成本 | 成本单位 | d1:{A:1,B:4}, d2:{A:2,B:1}, d3:{A:3,B:2} |
| `CAPACITY[f]` | 服务点 f 可承接的需求点数 | 个 | 基础实例 A:2,B:2；边界实例 A:1,B:2 |

- 缺失值处理：不适用（无外部数据）。
- 明确禁止：不得为了让实例可行而修改容量或成本；容量边界实例就是要测不可行边界。

## 4. 算法

- 求解方式：`精确求解`（全枚举）。
- 伪代码：

```text
1. 对 F^D 的每一种分配组合构造 solution
2. 用 check_constraints 逐条验证 C1、C2、C3
3. 对可行解用 recompute_objective 独立重算目标值
4. 返回目标值最小的可行解；若无可行解则报告不可行
```

- 求解器：无外部求解器，纯 Python。
- 随机种子：不涉及随机。
- 终止条件：枚举完毕。
- 规模预算：$2^3=8$ 种组合，单实例运行时间上限 1 s。
- 复杂度：$O(|F|^{|D|}\cdot|D|)$。

## 5. 输出契约

### 数据产物

| 文件 | 格式 | 列名与单位 | 说明 |
|---|---|---|---|
| `experiments/outputs/data/EXP-OPT-002_solution.csv` | CSV UTF-8 | `instance`（实例名）、`demand_id`、`facility_id`、`cost_yuan`（成本单位） | 每个实例的最优分配 |
| `experiments/outputs/data/EXP-OPT-002_metrics.json` | JSON | 见共享格式 | 含每个实例的 `objective`、`feasible`；**不含运行时间** |
| `experiments/outputs/logs/EXP-OPT-002_runtime.json` | JSON | `exp_id`、`runtime_sec` | 时序数据，每次运行都不同，不入版本控制 |

### 图表产物

| FIG-ID | 图类型 | x 轴 | y 轴 | 必须标注 | 用途 |
|---|---|---|---|---|---|
| FIG-OPT-001 | 分组条形图 | 实例（基础 / 容量边界） | 总成本（成本单位） | 每根柱顶标注数值；标出贪心与枚举的差距 | 论文第 4 章对照 M-01 与 M-02 |

## 6. 复算要求

不得复用枚举过程中的中间目标值，必须从最终分配重新计算。

| 复算项 | 使用函数 | 判定阈值 |
|---|---|---|
| C1 恰好分配一次 | `scripts/model_checks.py:check_constraints` | 无 violation |
| C2 容量 | `scripts/model_checks.py:check_constraints` | 无 violation |
| 目标值独立重算 | `scripts/model_checks.py:recompute_objective` | 相对误差 ≤ 1e-9 |

复算报告写入 `experiments/outputs/checks/EXP-OPT-002.json`。

## 7. 明确不做

- 不实现整数规划版本（那是 M-03 的 `SPEC-P1-M03`）；
- 不做多目标或鲁棒扩展；
- 不做规模扩展实验（枚举本就不适用于大规模）。

## 8. 未决问题

| 编号 | 未决内容 | 影响范围 | 建模手计划何时定 |
|---|---|---|---|
| Q1 | 容量边界实例若无可行解，应报告不可行还是允许部分未服务？演示案例中容量 1+2=3 恰好等于需求数，暂不触发 | C2 与目标定义 | 接入真实题面数据后确定 |
| Q2 | 需要补一个容量真正绑定的实例，当前两个实例都测不到 C2 是否正确实现 | 对照口径完整性 | 接入真实题面数据后补 |
