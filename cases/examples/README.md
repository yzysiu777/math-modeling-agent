# 三个通用能力演示

这些演示不对应任何历年具体题目，用来展示**三角色接力**：建模手写规格 → 编程手忠实
实现并复算 → 写作手取数溯源。

```bash
python3 cases/examples/optimization/experiments/code/python/run_demo.py
python3 cases/examples/data-analysis/experiments/code/python/run_demo.py
python3 cases/examples/hybrid/experiments/code/python/run_demo.py
make demos
```

## 每个演示展示什么

| 演示 | 主实现 | 重点展示 |
|---|---|---|
| `optimization/` | Python | **完整的三角色回路**：实验板 Probe → 五段 Full SPEC → 实现 → 复算 → 出图 → 溯源表，含一次真实的回问与规格更正 |
| `data-analysis/` | Python | 时间序切分、泄漏**反例**复算（检查器必须真的会报错） |
| `hybrid/` | **MATLAB** + Python 复算 | 跨语言契约：MATLAB 求解导出，Python 独立复算 |

## optimization：最值得先读的一个

它保留了一次**真实发生的规格错误**。早期 Full SPEC 曾预测容量边界实例的最优值是 6；
编程手实测得到 4，按契约**没有就地改判据**，而是写了
`SPEC-P1-M02.questions.md` 回问；建模手确认预测算错并更正规格，同时记下「这个实例
其实测不到容量约束」这条发现。当前五段规格保留最终结论，问答文件保留发现过程。

如果当时编程手顺手把 6 改成 4，这条发现就永远不会浮出来。这就是把交接做成文件契约
的全部理由。

按顺序读：

```text
models/candidates.md          发散 7 条 → 收敛 3 条，含砍掉的想法与七维度比较
experiments/board.md          Probe 假设、预设判据、结果和下一步
specs/SPEC-P1-M02.md          五段 Full SPEC
specs/SPEC-P1-M02.questions.md  回问与答复
experiments/outputs/          data / figures / checks 三类产物
paper/claim_map.md            三条主张的强度为什么是那样定的
```

## hybrid：MATLAB 侧的验证状态

`experiments/code/matlab/run_EXP_HYB_001.m` **未在开发环境中实际执行**（该环境无
MATLAB）。已验证的是：

- Python 复算脚本 `recompute_EXP_HYB_001.py` 的三条路径 —— 缺少 MATLAB 产物时正确
  跳过、数据正确时 PASS、数据被改错时 FAIL；
- 规格里的手算预期值（q\* = 8，成本 8；场景成本 8 / 8 / 18）。

因此 `outputs/data/` 下**没有提交 MATLAB 产物** —— 手工编造的结果文件比没有结果更
危险。因此 Full SPEC 明确使用 `probe_result: WAIVED`，并非伪造 PASS。本机首次实测时请
运行 `.m` 脚本，再跑复算脚本，然后更新实验板与 Full SPEC 的复算状态。

## 绘图依赖

绘图脚本需要 matplotlib，它不在 `requirements-dev.txt` 里（那份只服务确定性检查，
CI 也只装它）。缺库时绘图脚本明确报告跳过并返回 0，不伪造图片：

```bash
pip install -r requirements-experiments.txt
python cases/examples/optimization/experiments/code/python/plot_FIG_OPT_001.py
```

## 复制成新案例

不要直接复制这些目录。用脚本生成干净骨架：

```bash
python3 scripts/create_case.py --case-id your-case --route insufficient_information
```

然后重写 `case_brief.md` 和 `input/`，其余由三个角色按题面生成。
