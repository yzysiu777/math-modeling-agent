# 目标架构方案

## 1. 设计原则

1. canonical 层供应商无关：角色叫 `solution_lead`、`independent_adversary`，而不是把业务职责写死为 Codex 或 Claude。
2. 平台适配层负责把 Codex 映射为默认协调/实现模型，把 Claude 映射为默认独立审查模型。
3. 模型输出默认是 proposal，不是 evidence。
4. 可判定的工作交给程序、统计检验、求解器和人工复核。
5. 作者不得关闭自己的审查发现；主模型不得签署最终交付。
6. 原始输入、运行记录、审查和失败记录采用不可覆盖策略。
7. 只在独立、边界清楚的工作流中并行；共享可变状态必须单写者或串行提交。

## 2. 分层架构

```text
L0  Human Governance
    目标、授权、路由覆盖、关键取舍、最终签署

L1  Orchestrator and State
    状态机、任务队列、依赖、预算、重试、暂停、恢复、事件日志

L2  Intake and Routing
    problem_contract、source_manifest、task_router、hybrid_interface_contract

L3  Domain Workstreams
    Optimization Track | Data Analysis Track | Hybrid Coordinator

L4  Deterministic Evidence
    schema/data/leakage/constraint/objective/statistics/reproduction/paper validators

L5  Independent Review
    blind reconstruction、adversarial review、reproduction review、finding closure

L6  Paper Production
    paper architecture、evidence-calibrated writing、citation、figures、formatting

L7  Final Gate and Freeze
    gatekeeper、human sign-off、PDF hash、submission freeze
```

## 3. 推荐 canonical 目录

```text
agent-v2/
├── README.md
├── AGENTS.md
├── policies/
│   ├── authority.md
│   ├── evidence.md
│   ├── autonomy.md
│   ├── independence.md
│   └── artifact-lifecycle.md
├── roles/
│   ├── orchestrator.md
│   ├── task_router.md
│   ├── solution_lead.md
│   ├── optimization_modeler.md
│   ├── data_analyst.md
│   ├── data_auditor.md
│   ├── independent_adversary.md
│   ├── reproducibility_engineer.md
│   ├── paper_architect.md
│   ├── citation_editor.md
│   ├── formatting_qa.md
│   └── final_gatekeeper.md
├── protocols/
│   ├── state-machine.md
│   ├── routing.md
│   ├── gates.md
│   ├── disagreement-resolution.md
│   └── recovery.md
├── schemas/
│   ├── project_manifest.schema.yaml
│   ├── routing_record.schema.yaml
│   ├── state_event.schema.yaml
│   ├── artifact_record.schema.yaml
│   ├── claim_record.schema.yaml
│   ├── experiment_record.schema.yaml
│   ├── review_record.schema.yaml
│   └── human_signoff.schema.yaml
├── validators/
│   ├── manifest/
│   ├── data_quality/
│   ├── leakage/
│   ├── optimization/
│   ├── reproducibility/
│   └── paper/
├── skills/
│   ├── modeling-core/
│   ├── operations-optimization/
│   ├── data-analysis/
│   └── competition-paper-writing/
├── writing/
├── adapters/
│   ├── codex/
│   └── claude/
└── evals/
    ├── synthetic/
    └── expected/
```

`roles/` 是唯一权威角色层，适配器不得改变权限、Gate 或自批规则。

## 4. 共享工作流

```text
目标与授权
  → 输入冻结
  → 题意合同与路由
  → 数据合同/数学合同
  → 独立方案草图
  → baseline
  → 候选方法
  → 确定性验证
  → 稳健性与敏感性
  → 对抗审查
  → 独立复现
  → 论文证据映射
  → 引用/AI/格式审计
  → 人工签署与冻结
```

每一阶段必须写入工件，不以聊天上下文作为唯一状态。

## 5. 运筹优化轨道

### 5.1 必备合同

- 集合、索引和时间尺度；
- 已知参数及单位；
- 决策变量、类型、上下界；
- 目标函数及量纲；
- 硬约束、软约束和惩罚项；
- 可行性定义；
- 输出格式和允许误差；
- 最优性、最优间隙或启发式声明边界。

### 5.2 方法路由

- 连续线性结构：LP；
- 离散决策或逻辑关系：MILP/CP-SAT；
- 网络结构：最短路、流、匹配、运输；
- 时间和资源：排程、RCPSP、车辆路径、库存；
- 不确定参数：随机规划、鲁棒优化、情景分析；
- 非线性或非凸：NLP、分解、近似或启发式；
- 多目标：词典序、加权和、ε-constraint、Pareto；
- 状态递推：动态规划；
- 精确法不可承受时：启发式/元启发式，但必须保留界、可行性和小规模最优对照。

### 5.3 验证链

1. 人工可算微型实例；
2. 独立约束检查器；
3. 独立目标值重算；
4. 小规模穷举或严格求解器对照；
5. 求解器状态、证书、gap、时间限制和数值容差；
6. 多随机种子和停止准则；
7. 参数扰动、规模扩展和不可行情景；
8. 只在证据满足时使用“最优”，否则写“可行”“较优”或“当前算法最好”。

## 6. 数据分析轨道

### 6.1 必备合同

- 观测单位、主键和粒度；
- 字段含义、类型、单位和允许范围；
- 目标变量、标签生成和时间窗口；
- 数据来源、采样机制和已知偏差；
- 训练、验证、测试或时间切分；
- 禁止信息和泄漏路径；
- 主要指标、次要指标和业务解释；
- 推断、预测、描述或聚类任务边界。

### 6.2 方法路由

- 描述与关系：EDA、可视化、相关与稳健统计；
- 参数推断：估计、置信区间、假设检验和效应量；
- 预测：回归、分类、时间序列、生存或其他与目标匹配的方法；
- 无监督结构：聚类、降维、异常检测；
- 变量作用：特征重要性、局部/全局解释，但不自动升级为因果；
- 不确定性：重采样、交叉验证、预测区间、校准和敏感性分析。

### 6.3 验证链

1. 数据质量和粒度审计；
2. 切分前后的泄漏检查；
3. 简单透明 baseline；
4. 与任务匹配的交叉验证或时间回测；
5. 指标、区间、波动和校准；
6. 子群、极端值、漂移和误差分析；
7. 预处理、特征选择和调参必须在训练折内完成；
8. 相关、预测贡献和因果效应严格分开表述。

## 7. Hybrid 轨道

混合任务不是把两个报告拼接，而是建立版本化接口：

```text
Data Analysis Track
  → parameter_estimates@version + uncertainty/scenarios
  → hybrid_interface_contract
  → Optimization Track
  → decisions + objective + constraint_slacks
  → backtest/scenario evaluation
```

要求：

- 数据分析输出作为优化输入时必须冻结版本和置信范围；
- 不确定性必须通过情景、分布或鲁棒集合传入优化，不只传点估计；
- 优化结果不能反向污染训练标签；
- 联合评价同时报告预测质量、决策质量、可行性和稳健性；
- 任一轨道更新都使下游实验失效并触发重跑。

## 8. Codex 与 Claude

### Codex 默认职责

- Orchestrator 和 solution lead；
- 文件盘点、任务分解、代码和实验实现；
- 候选模型比较；
- 论文结构和草稿整合；
- 修复审查发现，但不能自行关闭发现。

### Claude 默认职责

- 独立题意重建；
- 盲审方案和最小反例；
- 数据泄漏、约束、最优性、统计结论和论文强措辞攻击；
- 独立复现；
- 关闭由其他角色修复的 finding，或维持阻断。

### 独立性协议

- blind 模式只接收带哈希的白名单材料包；
- 审查者必须声明是否曾看到作者结论；
- 同一模型的子 Agent 只能算“focused review”，不能算跨模型独立复核；
- Claude 与 Codex 一致不能升级 claim；
- Claude 的反对若无证据，只是待验证假设；
- 未解决 P0/P1 交给确定性测试或人工，不采用多数投票。

## 9. 确定性验证器优先级

MVP 至少实现：

1. Schema 与 manifest 验证；
2. 原始文件哈希和只读性检查；
3. 数据质量与泄漏检查；
4. 优化解可行性、约束松弛和目标重算；
5. 实验命令、环境、随机种子、输出哈希复现检查；
6. 论文数字、图表、引用和 claim 的一致性检查；
7. PDF 文本、元数据、身份、渲染和最终哈希检查。

模型负责提出测试，程序负责执行和记录测试。

## 10. 冲突裁决

```text
发现分歧
  → 建立 disagreement_record
  → 优先运行最低成本的确定性测试
  → 再查题面/数据/正式来源
  → 仍未解决则标记 disputed
  → 人工选择：补数据、降级结论、披露限制或放弃路线
```

作者不能关闭自己的 finding；审查者也不能把个人偏好当作 P1。每次关闭必须记录新证据和关闭者。

## 11. 成本与上下文

- 默认单主链；只有独立探索、审查或复现才并行。
- 每个 workstream 固定目标、输入白名单、输出 Schema、最大调用数、最大时间和停止条件。
- 简单分类、格式检查和抽取使用低成本配置；核心建模、复杂调试和最终审查使用高能力配置。
- 每阶段结束生成短状态快照；长日志写文件，不反复塞回上下文。
- 模型配置只能通过代表性评测选择，不能默认“最高推理强度永远最好”。

## 12. 目标验收

新架构只有同时满足以下条件才可标记 `COMPETITION_READY`：

- 任意未知输入均可路由到四种状态之一；
- 两条专业轨道有独立合同、baseline 和验证器；
- 混合接口能传播参数版本和不确定性；
- 任何重要 claim 均可追溯到工件；
- P0/P1 无法由作者自行关闭；
- 中断后能从状态快照和事件日志恢复；
- 论文只消费已支持 claim；
- 当届官方规则已冻结；
- 最终 PDF 与人工签署绑定同一哈希。

