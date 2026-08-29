# Python 实现约定

目标是**能被别人重跑**，不是工程优雅。比赛期间不做过度抽象。

## 目录

```text
experiments/code/python/
├── run_<EXP-ID>.py        每个实验一个入口，能直接 python 运行
├── lib/                   多个实验共用的部分才放这里
└── plot_<FIG-ID>.py       绘图脚本，与计算分开
```

**计算与绘图分开。** 数据改了只需重跑绘图脚本，不用重算；绘图脚本读
`outputs/data/` 的文件，不重新计算任何数值。

## 入口脚本骨架

```python
"""EXP-OPT-003: SPEC-A1-M03 的 MIP 实现。"""
from pathlib import Path
import json, random
import numpy as np

SEED = 42
CASE = Path(__file__).resolve().parents[3]      # cases/<case_id>/
OUT = CASE / "experiments/outputs"

def main() -> int:
    random.seed(SEED)
    np.random.seed(SEED)
    data = load_input(CASE / "input/...")
    solution, meta = solve(data)
    write_outputs(solution, meta)
    recompute_and_report(data, solution, meta)   # 见 recompute-recipes.md
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

## 随机种子

任何用到随机的地方**都要设种子并记录**：`random`、`numpy`、求解器自身的种子、
`scikit-learn` 的 `random_state`、深度学习框架的种子。

种子写在脚本顶部常量，同时写进 `board.md` 的运行记录和 `outputs/data/*_metrics.json`。

没设种子的实验结果不能用于论文对比 —— 差异可能全部来自随机性。

## 结果落盘

按 `language-choice.md` 的格式约定写：

```python
import csv, json

def write_outputs(solution, meta):
    (OUT / "data").mkdir(parents=True, exist_ok=True)
    with open(OUT / f"data/{EXP_ID}_solution.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["facility_id", "demand_id", "assigned", "cost_yuan"])  # 与规格列名表一致
        w.writerows(solution)
    with open(OUT / f"data/{EXP_ID}_metrics.json", "w", encoding="utf-8") as f:
        json.dump({"exp_id": EXP_ID, "spec_id": SPEC_ID, "language": "python",
                   "objective": meta["obj"], "feasible": meta["feasible"],
                   "runtime_sec": meta["t"], "seed": SEED}, f, ensure_ascii=False, indent=2)
```

列名逐字对齐规格第 5 段。写作手按列名取数，改列名等于毁掉下游。

## 求解器要点

| 库 | 适用 | 注意 |
|---|---|---|
| PuLP | 中小 MIP，语法直观 | 默认 CBC 慢；`prob.status` 必须检查，不要拿到解就当最优 |
| OR-Tools | 大规模 MIP、CP-SAT、路径问题 | CP-SAT 对调度类问题常远快于 MIP；要显式设时间上限 |
| SciPy | LP、非线性、`linprog`/`minimize` | `linprog` 只做连续；非线性要给初值和边界 |
| CVXPY | 凸优化，表达接近数学式 | 非凸会直接报错，不会悄悄给近似解 |
| NetworkX | 图算法原型 | 大图慢，只做 baseline 和验证 |

**求解状态必须检查并记录**：

```python
status = pulp.LpStatus[prob.status]        # Optimal / Infeasible / Unbounded / Not Solved
if status != "Optimal":
    # 照实记录，不要当成可行解继续
```

把 solver 返回的可行解写成「全局最优」是竞赛论文的高频错误。只有状态确实是
`Optimal` 且模型完整时才能说给定模型下最优。

## 数据处理要点

- 读入后立刻核对列名、行数、类型、缺失情况与规格是否一致，**对不上就回问**；
- 预处理器（标准化、编码、填充）只在训练集上 `fit`，测试集只 `transform` ——
  这是最常见的泄漏来源；
- 时序数据不要打乱切分；
- 按规格写死的规则处理缺失和异常，不要即兴发挥。

## 依赖

`requirements-dev.txt` 只装确定性检查需要的东西。实验用的额外依赖装在案例本地，
并在 `board.md` 记录版本。不要为了跑一个实验就改仓库根依赖。

## 不做的事

- 不做过度抽象（比赛四天，继承层次没有回报）；
- 不写单元测试覆盖实验代码（复算就是它的测试）；
- 不做性能微优化，除非它是当前瓶颈且规格里写了时间预算；
- 不在实验脚本里改 `models/` 或 `specs/` 下的任何文件。
