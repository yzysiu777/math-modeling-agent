---
spec_id: SPEC-<子问题>-<路线 ID>
case_id: <case_id>
route_id: M-
subproblem: <问题 1 / 问题 2 / ...>
method_family: <mixed-integer programming / dynamic programming / heuristic / tree model / ...>
status: full
language: python
depends_on: []

# probe 闭环：full 规格必须能追溯到已经跑过并通过的 probe。
# probe_result 取 PASS / FAIL / WAIVED。
# 只有题面直接指定算法等特殊情况才写 WAIVED，且必须写明豁免理由。
probe_spec_id: SPEC-<子问题>-<路线 ID>-probe
probe_exp_id: EXP-
probe_result: PASS
probe_waiver_reason: ""
---

# <路线名称> 实现规格

这份规格写给**看不到建模会话的编程手**。写完后逐段自检：只读这份文件，能不能唯一
确定实现？不能唯一确定的，写进第 8 段，不要指望下游猜对。

## 1. 目标与判据

- 本次要回答的问题：
- 通过判据（必须是可判定的数值或布尔条件）：
- 失败判据：
- 达到失败判据时的动作：`停止并回问` / `记录后继续` / `降级为 probe 重跑`

判据示例（可判定）：

```text
通过：在 12 个公开实例上全部返回可行解，且目标值与 EXP-OPT-002 枚举真值相对误差 ≤ 1e-6
失败：任一实例不可行，或求解时间 > 300 s
```

反例（不可判定，不要这样写）：`结果合理`、`效果比 baseline 好`、`收敛正常`。

## 2. 数学表述

- 集合与索引：
- 参数（名称、含义、单位、来源字段）：
- 决策变量 / 响应变量（名称、含义、变量域、单位）：
- 目标函数（含方向 min/max）：
- 约束（逐条编号，每条写清含义与单位）：
  - C1：
  - C2：
- 初始 / 终止条件：
- 已知的模型边界与不适用情形：

符号必须与 `models/candidates.md` 和论文符号表一致。同一个量不要在两处用不同符号。

## 3. 数据契约

- 输入文件（路径、格式、编码）：
- 字段表（列名、类型、单位、允许取值、是否可空）：
- 主键与粒度：
- 缺失值处理规则（逐字段写死，不留「按情况处理」）：
- 异常值规则：
- 单位换算：
- 数据切分规则（数据类题必填：切分依据、比例或时间边界、是否分层、随机种子）：
- 明确禁止的操作（例如：不得用全量数据拟合标准化器）：

## 4. 算法

- 求解方式：`精确求解器` / `启发式` / `元启发式` / `统计模型` / `机器学习` / `仿真`
- 伪代码或流程：

```text
1.
2.
3.
```

- 求解器与配置（名称、版本约束、关键参数）：
- 随机种子：
- 终止条件（迭代数 / 时间上限 / gap 阈值）：
- 规模预算（实例规模、内存、单次运行时间上限）：
- 复杂度预期：

## 5. 输出契约

### 数据产物

| 文件 | 格式 | 列名与单位 | 说明 |
|---|---|---|---|
| `experiments/outputs/data/<EXP-ID>_solution.csv` | CSV UTF-8 |  |  |
| `experiments/outputs/data/<EXP-ID>_metrics.json` | JSON |  | 至少含目标值、可行性、运行时间 |

### 图表产物

| FIG-ID | 图类型 | x 轴（含单位） | y 轴（含单位） | 必须标注 | 用途 |
|---|---|---|---|---|---|
| FIG- |  |  |  |  |  |

绘图必须遵守 `.agents/skills/competition-engineering/references/figure-standards.md`，
同时导出 PDF 与 PNG，并回填 `experiments/outputs/figures/manifest.md`。

## 6. 复算要求

编程手必须独立复算以下内容，**不得复用主求解过程的中间结果**，并把结果写入
`experiments/outputs/checks/<EXP-ID>.json`：

| 复算项 | 使用函数 | 判定阈值 |
|---|---|---|
| 逐条约束可行性 | `scripts/model_checks.py:check_constraints` |  |
| 目标值独立重算 | `scripts/model_checks.py:recompute_objective` | 相对误差 ≤ |
| 切分无重叠 / 无泄漏 | `scripts/model_checks.py:check_data_split` |  |
| 上下游接口一致 | `scripts/model_checks.py:validate_hybrid_interface` |  |

主实现使用 MATLAB 时，复算仍必须有 Python 版本 —— 阶段检查与 CI 只能运行 Python。

## 7. 明确不做

列出本次范围外的事，防止过度发挥：

-
-

## 8. 未决问题

建模手自己知道还没定的事。编程手撞上这些，或撞上本文件没写到的**建模决策**，
写入 `specs/<spec_id>.questions.md` 并停止该条路线，不得自行发明。

| 编号 | 未决内容 | 影响范围 | 建模手计划何时定 |
|---|---|---|---|
| Q1 |  |  |  |

纯工程决策（数据结构、循环写法、库选择、日志格式、文件组织）由编程手自主决定，
不用回问。
