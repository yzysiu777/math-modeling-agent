# Claims and Evidence

## Claim rule

A claim is any sentence that asserts a fact, model property, numerical result, causal relation, optimality property, or generalization. Register it before it enters the final report.

## Minimum evidence by claim type

| Claim | Minimum evidence |
|---|---|
| Data/definition |题面或字段说明 + 数据检查 |
| Derivation | 变量/假设/公式 + 符号和维度检查 |
| Algorithm | 伪代码/源代码 + 小例子或单元测试 |
| Feasibility | 约束检查器输出 |
| Optimality | 小规模穷举、严格求解器或明确限定为启发式最好解 |
| Predictive performance | 患者/样本隔离、指标、对照和稳定性 |
| Causal interpretation | 设计或假设足以支持因果，否则只能写关联 |
| Generalization | 外部/留出验证或明确局限 |
| Reproducibility | 输入清单、代码版本、命令、环境和输出；普通数据/实验文件哈希可选，冻结版本时再记录 |

## Evidence quality

- `A`: 原始题面、官方数据、确定性计算或独立复现。
- `B`: 作者原始代码/论文、公开可追溯实验。
- `C`: 可信二手解释或方法参考，只能支持背景和线索。
- `D`: 未验证来源，只能列为待核查，不得进入强结论。

## Writing rule

把“模型找到的一个解”“当前算法的最好解”“在给定假设下的最优解”“全局最优解”分开写。把“相关”与“因果”分开写。把“论文声称”与“本次复现验证”分开写。
