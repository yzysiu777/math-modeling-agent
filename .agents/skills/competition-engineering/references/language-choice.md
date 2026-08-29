# Python 与 MATLAB

两者并列主力。**规格的 `language` 字段说了算**；规格没指定时按下表默认，并把理由写进
`experiments/board.md` 的运行记录。

## 默认倾向

| 场景 | 倾向 | 原因 |
|---|---|---|
| 数据清洗、特征工程、统计建模 | Python | pandas / statsmodels / scikit-learn 生态完整 |
| 机器学习、深度学习 | Python | 框架和预训练资源都在这边 |
| 大规模 MIP / 约束规划 | Python | OR-Tools、PuLP、Pyomo 接商用求解器方便 |
| 需要被阶段检查或 CI 读取的部分 | Python | **只有 Python 能被自动检查执行** |
| 数值仿真、常微分/偏微分方程 | MATLAB | 求解器成熟、步长控制省心 |
| 控制系统、信号处理 | MATLAB | 工具箱直接可用，少造轮子 |
| 矩阵密集的原型迭代 | MATLAB | 表达接近数学公式，改起来快 |
| 图像处理、小波、滤波 | MATLAB | 工具箱函数齐 |

选不定时选 Python —— 它能被自动检查覆盖，这个优势在赛程后期很值钱。

## 硬性规则：复算必须有 Python 版本

`scripts/check_case.py`、`make case-check`、`make final-check` 和 CI 都只能运行 Python。
MATLAB 侧的复算结果无法被自动读取，也就无法点亮确定性风险标志。

所以无论主实现是哪种语言：

```text
MATLAB 主实现
  → 导出 outputs/data/<EXP-ID>_solution.csv（约定格式）
  → Python 读入并独立复算
  → 写 outputs/checks/<EXP-ID>.json
```

这不是重复劳动 —— 用另一种语言独立重算，本身就是更强的验证。同一套代码算两遍
证明不了任何事。

## 跨语言数据格式

两种语言写出**完全相同**的文件格式，写作手不需要知道也不应该关心某个结果是谁跑的。

### CSV

- UTF-8 编码（MATLAB 需显式指定，见 `matlab-conventions.md`）；
- 第一行列名，与规格第 5 段的列名表逐字一致；
- 小数点用 `.`，不用千位分隔符；
- 缺失值写空字段，不写 `NaN`、`NA` 或 `-999`；
- 不写行索引列；
- 行尾统一 LF。Python 侧 `csv.writer(handle, lineterminator="\n")`，否则 Windows/macOS
  默认写出 CRLF，跨平台 diff 和 MATLAB 读入都会出问题。

### JSON（指标文件）

```json
{
  "exp_id": "EXP-OPT-003",
  "spec_id": "SPEC-A1-M03",
  "language": "matlab",
  "objective": 1234.56,
  "feasible": true,
  "runtime_sec": 12.4,
  "seed": 42,
  "metrics": {"gap": 0.008}
}
```

`objective`、`feasible`、`runtime_sec` 是最低要求，其余按规格补。

## 环境记录

在 `board.md` 的运行记录里写清版本，比赛后期换机器重跑时能省很多时间：

- Python：解释器版本、关键库版本、求解器与版本；
- MATLAB：版本号、用到的工具箱名称。

不需要做完整的环境锁定 —— 记录到能重现的程度即可。

## 混用的边界

一个实验尽量只用一种语言做主实现。需要混用时（例如 MATLAB 仿真 + Python 优化），
在规格第 3 段的数据契约里写清交界处的文件、字段、单位和时间语义，按混合建模的
上下游接口对待，并用 `validate_hybrid_interface` 检查。

不要在同一个脚本里调用另一种语言的引擎 —— 比赛环境下调试成本远高于收益，
用文件交换。
