# 复算配方

复算的核心原则：**独立重算**。用主求解器自己算出的目标值去验证它自己，什么也验证
不了。要从**决策变量的取值**出发，按照规格里写的数学表述，重新算一遍。

工具在 `scripts/model_checks.py`。它接受普通 Python 值和可调用对象，不需要先搭一套
记录系统。

## 输出

所有复算最后汇总成一份报告：

```python
from scripts.model_checks import write_check_report

write_check_report(
    OUT / "checks",
    exp_id="EXP-OPT-003",
    spec_id="SPEC-A1-M03",
    checks=[
        {"name": "capacity", "kind": "constraint", "passed": True, "detail": ""},
        {"name": "objective", "kind": "objective_mismatch", "passed": True, "detail": "rel_err=2.1e-9"},
    ],
)
```

`kind` 只能取 `constraint`、`infeasible`、`objective_mismatch`、`leakage`、
`split_overlap`。任一 `passed: false` 会被 `scripts/check_case.py` 自动读取并点亮
`checkpoint.yaml` 的确定性风险标志。**这条链路是自动的，所以失败必须照实写。**

## 配方一：运筹解的可行性与目标值

```python
from scripts.model_checks import audit_optimization_result, write_check_report

solution = {"x": x_values, "y": y_values}     # 决策变量取值

constraints = [
    # 每条约束一个 (名称, 可调用)；返回 bool 或 (bool, 说明)
    ("capacity", lambda s: all(
        sum(s["x"][i][j] * demand[j] for j in D) <= cap[i] for i in F)),
    ("assign_once", lambda s: all(
        abs(sum(s["x"][i][j] for i in F) - 1) < 1e-9 for j in D)),
    ("link_xy", lambda s: all(
        s["x"][i][j] <= s["y"][i] for i in F for j in D)),
    ("domain", lambda s: all(v in (0, 1) for row in s["x"] for v in row)),
]

# 目标函数按规格第 2 段重写一遍，不要调用求解器的 objective value
objective = lambda s: (
    sum(open_cost[i] * s["y"][i] for i in F)
    + sum(ship_cost[i][j] * s["x"][i][j] for i in F for j in D)
)

audit = audit_optimization_result(
    solution, objective, constraints,
    reported_objective=solver_obj,        # 求解器报的值，用来比对
    tolerance=1e-6,
)
```

`audit["passed"]` 为 False 时看 `violations` 和 `objective_matches`。

转成报告：

```python
checks = [{"name": v["name"], "kind": "constraint", "passed": False, "detail": v["detail"]}
          for v in audit["violations"]]
if not audit["violations"]:
    checks.append({"name": "all_constraints", "kind": "constraint", "passed": True, "detail": f"checked {len(constraints)}"})
checks.append({
    "name": "objective", "kind": "objective_mismatch",
    "passed": audit["objective_matches"],
    "detail": f'recomputed={audit["objective"]}, reported={audit["reported_objective"]}',
})
```

**常见的坑**：约束用求解器的模型对象重新表达 —— 那是在验证「求解器有没有正确执行
自己的模型」，不是在验证「模型有没有正确表达题目」。约束必须从**规格文字**重写。

## 配方二：数据切分与泄漏

```python
from scripts.model_checks import check_data_split

errors = check_data_split(
    train_rows, val_rows, test_rows,
    key="patient_id",          # 实体主键，不是行号
    time_key="admit_time",     # 时序题必填，检查时间顺序泄漏
)
```

查三件事：切分内主键重复、切分间主键重叠、时间顺序倒置。

```python
checks = [{"name": "split", "kind": "split_overlap", "passed": not errors,
           "detail": "; ".join(errors)}]
```

含时间泄漏时另记一条 `kind: "leakage"`。

**`check_data_split` 查不出的泄漏**，要自己检查：

| 泄漏类型 | 表现 | 自查方法 |
|---|---|---|
| 预处理泄漏 | 标准化/填充/编码在全量数据上 `fit` | 检查 `fit` 只在 train 上调用过 |
| 特征泄漏 | 特征里含未来信息或标签衍生量 | 逐个特征问「预测时刻这个值可得吗」 |
| 分组泄漏 | 同一实体的不同记录跨切分 | 用实体 ID 做 key（上面已覆盖），但要选对 ID |
| 目标编码泄漏 | 用全量标签做类别编码 | 检查编码是否在折内计算 |

发现这类泄漏，`kind` 写 `leakage`。

## 配方三：混合题的上下游接口

```python
from scripts.model_checks import validate_hybrid_interface

errors = validate_hybrid_interface(
    payload,                                   # 上游给下游的字典
    required_fields={"demand_forecast": list, "horizon": int, "units": dict},
    expected_units={"demand_forecast": "件/天"},
)
```

除字段和单位外，混合题还要测**上游误差对下游的影响**（规格第 1 段通常会要求）：

```python
for scale in (0.8, 0.9, 1.0, 1.1, 1.2):
    perturbed = {**payload, "demand_forecast": [v * scale for v in payload["demand_forecast"]]}
    result = downstream_solve(perturbed)
    # 记录：是否仍可行、目标值变化幅度
```

上游预测缺失、极端值时下游是否还有可行解，是混合题最值得报告的发现之一。

## 配方四：MATLAB 主实现的复算

MATLAB 侧导出 CSV/JSON，Python 侧读入独立复算：

```python
from scripts.model_checks import load_result, audit_optimization_result

sol = load_result(OUT / "data/EXP-OPT-003_solution.csv")     # list[dict]
meta = load_result(OUT / "data/EXP-OPT-003_metrics.json")    # dict

solution = {"x": rebuild_matrix(sol)}
audit = audit_optimization_result(solution, objective, constraints,
                                  reported_objective=meta["objective"], tolerance=1e-6)
```

用另一种语言从落盘数据重算，是比同语言重算更强的验证 —— 它同时检查了导出格式是否
正确。

## 复算失败怎么办

| 情况 | 动作 |
|---|---|
| 实现有 bug | 自己修，重跑，报告里保留最终结果 |
| 规格自相矛盾（约束冲突、单位不一致） | 写 `.questions.md` 回问，**不要「修」规格** |
| 模型确实不可行 | 照实记录 `kind: "infeasible"`。这通常说明建模假设有问题，是重要发现 |
| 目标值差一点点 | 先看是不是浮点容差；确认不是，就是模型表达与实现不一致，要查清楚 |

**不要为了让检查变绿而调大容差、跳过约束或换实例。** 复算的价值全部来自它诚实。
