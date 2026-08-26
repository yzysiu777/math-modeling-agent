# 实施路线图

本路线不依赖任何历史题。验收使用合成微型问题和结构检查。

## 阶段 0：安全基线与版本化

目标：保证改造可回滚。

交付：

- 为当前目录建立 Git 仓库或不可变快照；
- 记录现有文件清单和 SHA-256；
- 将本次 `audit/` 设为设计基线；
- 建立变更分支或副本，不在原型上直接大改。

验收：能恢复到本次审核前状态；所有原始文件哈希可验证。

## 阶段 1：去题目化与 canonical 层

目标：移除三道题依赖，建立供应商无关规则。

交付：

- `policies/` canonical 规则；
- 通用 `AGENTS.md`；
- `orchestrator`、`task_router`、`solution_lead`；
- `optimization_modeler`、`data_analyst`、`independent_adversary`；
- Codex/Claude 仅作为 adapters；
- 四态 `problem_type` 和可扩展 tag。

验收：全目录搜索不再在 canonical 文件中出现具体历史题名、年份或专用字段；具体示例如需保留，只能放非默认加载的 archive/examples。

## 阶段 2：状态机、Gate 与 Schema v2

目标：从提示词集合升级为可恢复工作台。

交付：

- G0-G15；
- state event、artifact、claim、experiment、review、signoff Schema；
- append-only event log；
- pause/resume/retry/reject/freeze 协议；
- finding 关闭和失效传播规则。

验收：

- YAML/JSON Schema 可解析；
- 非法状态转换会失败；
- 作者无法关闭自己的 P1；
- 修改数据合同会自动标记下游实验和论文 claim 失效；
- 中断后能从快照和事件日志恢复。

## 阶段 3：两条专业 Skill

目标：形成独立、可组合的专业能力。

### Operations Optimization Skill

包含：问题形式化、方法路由、baseline、可行性、目标重算、精确/启发式边界、多目标、随机/鲁棒、敏感性和求解器记录。

### Data Analysis Skill

包含：数据合同、EDA、清洗、泄漏、切分、统计/预测/聚类路由、baseline、评价、不确定性、解释和因果边界。

### Hybrid Contract

包含：参数版本、单位、不确定性、情景、优化输入哈希和联合评价。

验收：两个 Skill 可单独运行，也能通过接口组成 Hybrid；任何一个轨道更新会正确使下游工件失效。

## 阶段 4：最小确定性验证层

目标：让关键 Gate 不依赖模型自述。

优先实现：

1. manifest/schema validator；
2. file hash/read-only validator；
3. data quality/leakage validator；
4. optimization feasibility/objective validator；
5. experiment/reproduction validator；
6. claim-to-result/paper validator；
7. PDF preflight 和渲染清单。

验收：每个 validator 有成功、失败和边界测试；模型只能消费验证输出，不能改写输出为 PASS。

## 阶段 5：盲审与多模型协议

目标：让 Claude 对抗链真正独立可审计。

交付：

- review bundle 生成器；
- 文件白名单和哈希；
- exposure declaration；
- blind/nonblind/reproduction 模式；
- disagreement record；
- finding closure workflow；
- 成本、并发、重试和停止条件。

验收：已暴露 Codex 结论的审查不能标记 blind；同模型子 Agent 不计为跨模型独立复核；未解决 P1 阻断后续 Gate。

## 阶段 6：论文系统 v2

目标：形成题数动态、证据驱动、当届规则可替换的论文生产线。

交付：

- official rules manifest；
- dynamic paper outline；
- evidence-calibrated language policy；
- claim-to-paper ledger；
- citation/AI/figure/table/formula validators；
- final PDF QA 和 hash-bound signoff。

验收：章节由 problem contract 生成；摘要数字全部可追溯；官方规则未知时状态为 PENDING；签署与 PDF 哈希一致。

## 阶段 7：合成评测与比赛演练

目标：证明架构通用，而不是证明某道题能做。

合成评测至少覆盖：

- 线性规划可行/不可行；
- 0-1 分配和约束遗漏；
- 小网络最优对照；
- 资源排程；
- 多目标权重变化；
- 随机/鲁棒情景；
- 回归切分；
- 不平衡分类与校准；
- 时间泄漏；
- 聚类稳定性；
- 相关与因果措辞；
- 预测参数进入优化的 Hybrid；
- 论文数字、引用、身份和哈希错误。

验收指标：路由正确率、P0/P1 召回、约束违规检出率、泄漏检出率、复现成功率、claim 追溯率、PDF QA 通过率、token/时间预算。

## 阶段 8：可选自动编排

只有前述文件工作台稳定后再考虑 API 编排、可视化面板和自动任务调度。官方 OpenAI 文档把多代理标记为适合独立边界清楚的并行任务，并提示共享可变状态和强顺序依赖不适合盲目并行；因此自动化应从有界、可测的环节开始。

## 竞赛前最小可用门槛

必须完成阶段 0-7。若时间不足，宁可保留“单 Codex 主链 + Claude 两次独立审查 + 确定性验证器 + 人工 Gate”，也不要上线未经评测的复杂全自动编排。

## 本轮之后的推荐第一步

先实施阶段 0 和阶段 1，并由一个新 reviewer 只审“是否完全去除历史题依赖、canonical 与 adapter 是否分离”。通过后再进入状态机和 Schema 设计。

