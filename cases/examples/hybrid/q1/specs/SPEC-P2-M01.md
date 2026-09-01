---
spec_id: SPEC-P2-M01
case_id: hybrid
route_id: M-01
subproblem: 问题2
method_family: forecast-then-optimize
status: full
language: matlab
probe_exp_id: ""
probe_result: WAIVED
probe_waiver_reason: "Python 确定性演示与手算已通过，但开发环境无 MATLAB，主实现尚未执行"
reviewer_probe_recheck_exp_id: ""
---

# 预测驱动库存决策 Full SPEC

## 1. 目标与判据

- 检查点预测进入确定性库存决策后，在需求扰动下的成本变化。
- 点预测 8、容量 10 时，最优备货量必须为 8，目标成本为 8。
- 需求 6/8/10 时成本必须为 8/8/18，且所有备货量满足 `0 <= q <= 10`。
- MATLAB 输出与 Python 独立复算差异不超过 `1e-9`；未运行 MATLAB 前不得宣称跨语言通过。

## 2. 数学模型

整数决策 $q\in[0,10]$，点预测 $\hat d=8$，持有成本 $h=1$，缺货惩罚 $p=5$。求
$\min hq+p\max(\hat d-q,0)$。模型只覆盖单期、单品和点预测，不覆盖多期滚动、提前期或
有分布依据的鲁棒决策。

## 3. 数据契约与显式假设

上游接口包含整数 `demand`（units）、比例 `service_level` 和单位字典 `units`。
`demand` 缺失时停止，不用历史均值静默替代；超过容量时保留原值，由缺货项体现。
场景 6/8/10 为手工构造，不代表经验分布，`service_level` 在本规格中不进入目标函数。

## 4. 算法与输出

MATLAB 入口 `q1/code/matlab/run_EXP_HYB_001.m` 枚举 `q=0:10`，输出 UTF-8 CSV
和指标 JSON；Python 入口 `q1/code/python/recompute_EXP_HYB_001.py` 从输出字段
重新计算容量、目标和各场景成本。两种语言只通过文件交换，不互相调用运行时。

## 5. 复算与遗留假设

Python 侧逐行确认容量和成本，禁止把 MATLAB 报告的 objective 直接回代。当前
`EXP-HYB-001` 仅有 Python 确定性演示与手算 PASS，Full 的 MATLAB Probe 明确 WAIVED；
首次在有 MATLAB 的竞赛机运行后必须补跨语言复算。情景概率、服务水平约束和误差分布
仍未确定，不能把 2.25 倍写成一般稳健性结论。
