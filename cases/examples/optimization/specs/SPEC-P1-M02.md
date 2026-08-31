---
spec_id: SPEC-P1-M02
case_id: optimization
route_id: M-02
subproblem: 问题1
method_family: exact enumeration
status: full
language: python
probe_exp_id: EXP-OPT-002
probe_result: PASS
probe_waiver_reason: ""
reviewer_probe_recheck_exp_id: ""
---

# 小规模精确枚举 Full SPEC

## 1. 目标与判据

- 回答全枚举能否为分配路线提供小规模真值。
- 基础实例最优成本必须为 4，全部需求恰好分配一次且容量无违反。
- 最终分配独立重算的目标值与求解结果差异不超过 `1e-9`。
- 比较范围固定为同一成本矩阵和容量口径；超过枚举预算时本路线失效。

## 2. 数学模型

需求集合 $D=\{d_1,d_2,d_3\}$，服务点集合 $F=\{A,B\}$。令
$x_{df}\in\{0,1\}$ 表示需求 $d$ 是否分配给服务点 $f$，求
$\min\sum_{d,f}c_{df}x_{df}$，满足 $\sum_f x_{df}=1$ 和
$\sum_d x_{df}\le u_f$。成本矩阵为
`d1:{A:1,B:4}, d2:{A:2,B:1}, d3:{A:3,B:2}`，基础容量为 A:2、B:2。
模型只适用于 $|F|^{|D|}$ 可枚举的规模。

## 3. 数据契约与显式假设

输入为规格内确定性常量，无缺失、重复、坐标或时间语义。成本单位统一为“成本单位”，
容量单位为“需求点个数”。不得为了得到预期答案修改成本或容量。所谓容量边界实例 A:1、
B:2 的最优值仍是 4，并未真正让容量约束改变最优解；这一局限必须保留。

## 4. 算法与输出

枚举 $F^D$ 的全部分配，先逐条检查分配和容量约束，再从最终分配独立计算目标值并取最小
可行解。入口为 `experiments/code/python/run_demo.py`。输出逐项分配 CSV、指标 JSON 和
`experiments/outputs/checks/EXP-OPT-002.json`；图表只比较已验证路线，不把运行缓存纳入 Git。

## 5. 复算与遗留假设

复算必须确认每个需求恰好分配一次、容量无违反、目标差异不超过 `1e-9`。`EXP-OPT-002`
已 PASS，未使用 Reviewer Probe。仍需在真实题面中补一个会改变最优解的容量绑定实例；
实际规模超过约 20 个需求点时，必须转向 MIP 或启发式并重新赛马。
