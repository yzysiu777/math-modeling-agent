# 华为杯固定竞赛工作流

工作台只有一条适用于运筹优化、数据分析和混合建模的竞赛工作流。每个
Gate 首次通过都必须落盘退出证据；修改后不重置整个项目，而是按 R0–R3
进入局部修订循环。

## 主流程与 Gate

```text
intake
  -> routed                 G0 目标、题意与权限
  -> frozen                 G1 输入和数据冻结
  -> contracted             G2 数据契约、假设、符号和指标
  -> baseline_ready         G3 Baseline
  -> model_ready            G4 正式模型和算法
  -> validated              G5 正确性、可行性与边界
  -> results_verified       G6 结果可信度与稳健性
  -> reviewed               G7 独立审核
  -> gate_passed            G8 修订与回归
  -> paper_ready            G9 论文证据绑定
  -> format_checked         G10 官方格式和 AI 合规
  -> pdf_qa_passed          G11 LaTeX/PDF 检查
  -> human_frozen           G12 人工冻结
```

### Gate 合同镜像

下表必须与 `scripts/gate_contract.py` 的 Gate ID、名称、进入状态和退出证据逐项一致；
脚本校验完整行内容和顺序，修改流程文档时必须同步更新。

| Gate | 名称 | 进入状态 | 首次通过的退出证据 |
|---|---|---|---|
| G0 | 目标、题意与权限 | `routed` | 人工确认目标、交付物和权限边界 |
| G1 | 输入和数据冻结 | `frozen` | 输入清单、来源、只读状态和哈希 |
| G2 | 数据契约、假设、符号和指标 | `contracted` | 数据/模型契约、假设表和指标定义 |
| G3 | Baseline | `baseline_ready` | 可解释 baseline、小案例和运行记录 |
| G4 | 正式模型和算法 | `model_ready` | 公式、算法、代码版本和参数记录 |
| G5 | 正确性、可行性与边界 | `validated` | 手算/穷举、维度、约束和边界检查 |
| G6 | 结果可信度与稳健性 | `results_verified` | 对照、复算、敏感性和稳健性证据 |
| G7 | 独立审核 | `reviewed` | C1/C2/C3 审核记录和未解决问题 |
| G8 | 修订与回归 | `gate_passed` | 变更影响、定向验证和关闭记录 |
| G9 | 论文证据绑定 | `paper_ready` | claim—实验—图表—引用映射 |
| G10 | 官方格式和 AI 合规 | `format_checked` | 当届规则、匿名和 AI 记录预检 |
| G11 | LaTeX/PDF 检查 | `pdf_qa_passed` | 编译、文本、元数据、渲染和 PDF 哈希 |
| G12 | 人工冻结 | `human_frozen` | 人工 signoff、最终提交文件和版本冻结 |

### G0：目标、题意与权限

记录用户目标、比赛截止时间、交付物、允许/禁止的资料处理方式、语言
策略、团队成员和人工确认事项。没有人工确认不能把草稿目标当成正式目标。

### G1：输入和数据冻结

只读盘点题面、附件、来源、文件类型、大小、获取日期、权威等级和
SHA-256。原始输入不能覆盖；失败记录、审核记录和实验记录不能删除。

### G2：数据契约、假设、符号和指标

固定数据粒度、主键、单位、标签、时间边界、训练/验证/测试切分、禁止
字段、变量、参数、目标方向、硬约束、容差和评价指标。混合题同时冻结
上下游字段、误差、时间语义和可行性传递规则。

### G3：Baseline

先完成最小可运行、可解释、可手工核验的方案：优化题可用规则、线性
模型、小规模穷举或简单启发式；数据题可用统计量、线性/逻辑回归或朴素
预测；混合题先连接简单分析器和简单决策器。

### G4–G6：模型、正确性和结果

模型必须逐项对应题面；代码、公式、变量维度和单位保持一致。先做手算、
解析或小规模穷举，再扩大规模。优化解独立检查可行性和目标值，预测结果
检查切分、指标、校准和稳定性。所有关键结果绑定输入哈希、代码版本、
命令、环境、随机种子、输出哈希和限制。

### G7：三个关键节点的独立审核

Claude 只在以下三个节点由人工触发，且不重做整道题：

- **C1 题意、目标和约束**：盲审语义、边界、单位、遗漏和最小反例；
- **C2 模型架构和算法**：挑战模型族、公式—代码一致性、不变量和极端实例；
- **C3 主要结果和论文强结论**：局部复算、对照公平性、泄漏、稳健性和数字来源。

每次审核必须指定 `review_lens`、主/替代方法族、方法论差异、反例或可
证伪测试、已检查项、未检查项和需要人工决定的事项。没有这些字段的报告
不能作为独立审核证据。

### G8：修订与回归

没有待处理修改时，记录“无待回归变更”作为退出证据。发生修改时进入：

```text
gate_passed
  -> revision_pending
  -> impact_classified
  -> targeted_validation
  -> validation_passed | validation_failed
  -> restore_affected_gate
  -> gate_passed
```

`scripts/classify_change.py` 只有在声明语义变更表面后才生成 R0–R3 影响等级；
仅凭 `03-model.tex`、`modeling-paper.sty` 等路径只能给出风险提示并要求人工分类；
`scripts/plan_targeted_validation.py` 只生成预定义安全检查 ID；
`change_impact_record` 与 `revision_validation_record` 保存前后哈希、受影响
Gate、claim、实验、图表、可信运行器日志哈希和输出哈希。R0 的空 Gate 影响
必须同时有 `no_gate_impact` 证据；验证失败时不能关闭 finding。

### G9–G12：论文和交付

论文先建立“子问题—模型—实验—图表—结论—引用”映射，再进入 LaTeX。
当届官方标准、匿名规则、AI 使用规定和提交手册优先于历史模板。新的候选
提交 PDF 才触发完整静态和视觉 QA；PDF 生成哈希后任何字节变化都必须重跑。
最后由人工填写 `human_review_card` 和 `human_signoff`，冻结 Git 版本与 PDF。
