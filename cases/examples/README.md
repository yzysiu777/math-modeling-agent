# 三个通用能力演示

这些演示不对应任何历年具体题目，用来展示**按题工作台中的三角色接力**：建模手写规格，
编程手忠实实现并复算，写作手从结果文件取数。

```bash
python3 cases/examples/optimization/q1/code/python/run_demo.py
python3 cases/examples/data-analysis/q1/code/python/run_demo.py
python3 cases/examples/hybrid/q1/code/python/run_demo.py
make demos
```

## 每个演示展示什么

| 演示 | 主实现 | 重点展示 |
|---|---|---|
| `optimization/` | Python | Probe → 五段 Full SPEC → 实现 → 复算 → 出图 → 溯源表，并保留一次规格更正的发现 |
| `data-analysis/` | Python | 时间序切分、泄漏反例复算（检查器必须真的会报错） |
| `hybrid/` | MATLAB + Python 复算 | 跨语言输出契约与独立复算 |

每个演示都只有一个 `q1/` 工作台。路线池已经并入 `q1/brief.md`，实验状态在
`q1/board.md`，Full SPEC 在 `q1/specs/`，实现和证据分别在 `q1/code/` 与
`q1/outputs/`。题面来源只指向演示目录自己的 `input/source/` 小输入，不借用真实赛题。

## optimization：最值得先读的一个

它保留了一次真实发生的规格错误：早期规格曾预测容量边界实例的最优值是 6，编程手实测
得到 4，没有就地改判据；建模手复核后把更正与“这个实例测不到容量约束”的发现写回
Full SPEC 和 `q1/log.md`。现在只保留生效的规格，不再为历史问答单独维护一层转写文件。

按顺序读：

```text
q1/brief.md                   7 条想法收敛为 3 条路线及七维度比较
q1/board.md                   Probe 假设、预设判据、结果和下一步
q1/specs/SPEC-P1-M02.md       五段 Full SPEC 与更正后的发现
q1/log.md                     本题短日志
q1/outputs/                   data / figures / checks 三类产物
paper/claim_map.md            三条主张的证据与强度
```

## hybrid：MATLAB 侧的验证状态

`q1/code/matlab/run_EXP_HYB_001.m` 未在开发环境中实际执行（该环境无 MATLAB）。已验证
Python 复算脚本的缺产物跳过、正确数据 PASS、错误数据 FAIL 三条路径，以及规格里的手算
预期值。因而 `q1/outputs/data/` 没有伪造 MATLAB 产物；首次实测时先运行 `.m` 脚本，再
跑 Python 复算脚本并更新实验板和 Full SPEC。

## 绘图依赖

绘图脚本需要 matplotlib。缺库时脚本明确报告跳过并返回 0，不伪造图片：

```bash
pip install -r requirements-experiments.txt
python cases/examples/optimization/q1/code/python/plot_FIG_OPT_001.py
```

## 新建案例

不要直接复制这些目录。用脚本生成干净骨架：

```bash
python3 scripts/create_case.py --case-id your-case --route insufficient_information
```

然后配置 `sources.yaml`，完成阶段 0 抽取，再从 `q1/brief.md` 开始工作。
