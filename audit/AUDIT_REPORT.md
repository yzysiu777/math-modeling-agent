# 数学建模 Agent 工作台审核报告

报告状态：`DESIGN_DRAFT`。静态检查已完成，独立对抗复核尚未执行，本报告未被作者自我批准。

## 1. 执行结论

当前系统不适合直接投入未知的运筹优化题或数据分析题。它可以作为设计原型继续使用，但在以下 P1 问题修复前，只能标记为 `DESIGN_PROTOTYPE`：

1. 通用规则仍被三道历史题污染；
2. 没有可执行的双轨路由和混合任务接口；
3. 缺少运筹建模师、数据分析师和独立 Orchestrator 等关键角色；
4. 工作流是说明文档，不是可恢复、可校验的状态机；
5. Claude 的盲审隔离只靠提示词，没有材料白名单和污染声明。

本次静态审核未发现正在造成数据损坏或竞赛违规的 P0 事件，但发现 10 项 P1 和 4 项 P2。若在现状下直接启动比赛，P1 很可能转化为错误路由、遗漏约束、数据泄漏、虚假盲审或不可复现结论。

## 2. 已有优点

- `AGENTS.md:30-38` 已明确角色不得自我批准。
- `AGENTS.md:50-64` 已建立 claim、实验、失败和模型分歧的证据原则。
- `protocol/workflow.md:37-65` 坚持 baseline、小例子和确定性验证优先。
- `protocol/gates.md:48-56` 已规定关键 Gate 不通过时不得强化结论。
- `CLAUDE.md:20-35` 已区分盲审、对抗和复现模式。
- `writing/README.md:5-11` 正确区分官方规则、内部风格和论文证据链。
- `writing/OFFICIAL_RULES.md:34-43` 已要求比赛日冻结当届标准文档及最终 PDF。
- `writing/checks/check_pdf.sh` 是只读预检，不冒充数学正确性证明。

这些内容应保留并迁移到新的供应商无关架构中。

## 3. Findings

### A-01 [P1] 通用入口被具体历史题硬编码

- 证据：`README.md:7,71,77`；`roles/codex_lead.md:30-34`；`roles/claude_adversary.md:20-32`；`roles/model_reviewer.md:16-20`；`protocol/workflow.md:41-43`；`schemas/claim_record.yaml:3`；`templates/case_manifest.yaml:1-3`；`skills/industrial-mathematical-modeling/SKILL.md:43-52`。
- 影响：未知题目会被错误映射到临床、航迹或 DAG 调度语义；Schema 甚至无法合法登记其他问题。
- 最小修复：从所有 canonical 文件删除具体题目枚举；改为 `optimization | data_analysis | hybrid | insufficient_information`，题型细分放到可扩展标签中。
- 阻塞：是。

### A-02 [P1] 缺少通用路由和混合任务协议

- 证据：`templates/case_manifest.yaml:3` 只有三个具体题型和 `other`；现有目录没有 router 角色、路由 Schema 或路由复核记录。
- 影响：数据驱动优化、预测后决策等混合题会在轨道之间丢失参数版本、误差和责任边界。
- 最小修复：新增 `task_router`、`routing_record` 和 `hybrid_interface_contract`，路由输出必须可人工覆盖。
- 阻塞：是。

### A-03 [P1] 专业角色不足

- 证据：`roles/` 只有 lead、adversary、data auditor、通用 model reviewer、reproducibility reviewer 和 final gatekeeper；没有 `orchestrator`、`optimization_modeler`、`data_analyst`、`paper_architect` 的 canonical 角色卡。
- 影响：建模者与审查者职责混合；数据分析和运筹优化的验收标准无法分别固化。
- 最小修复：建立供应商无关角色层，再由 Codex/Claude 适配器映射。
- 阻塞：是。

### A-04 [P1] 工作流不是可执行状态机

- 证据：`protocol/workflow.md:3-91` 是线性叙述；没有状态 Schema、合法转换、事件日志、重试次数、恢复点、冻结状态或失效传播规则。
- 影响：中断后无法可靠恢复；模型、数据或约束变更后，不知道哪些 Gate 和实验必须重新运行。
- 最小修复：采用 append-only 事件日志、状态快照、合法转换表和 artifact invalidation graph。
- 阻塞：是。

### A-05 [P1] Claude 盲审只靠文字约束

- 证据：`CLAUDE.md:22-24` 和 `config/models.example.yaml:13-14` 声明初始可见范围，但没有生成隔离审查包、材料白名单、输入哈希或 reviewer exposure 声明。
- 影响：Claude 可能已经看到 Codex 结论，却仍被记录为 blind；“模型独立性”不可审计。
- 最小修复：每次盲审生成只读 `review_bundle/<id>/manifest.yaml`，记录允许文件、哈希、既往暴露和模式；发生暴露后自动降级为 `nonblind_adversarial`。
- 阻塞：是。

### A-06 [P1] Gate 数量和职责不足

- 证据：`protocol/gates.md:13-22` 只有 G0-G7；数据质量、假设、算法正确性、可行性、引用、AI 合规、PDF QA 和人工冻结被合并。
- 影响：一个宽泛 PASS 不能证明具体风险已关闭，复核者也无法知道失败后的恢复动作。
- 最小修复：拆成 16 个 Gate，每个 Gate 固定输入、检查器、责任人、通过标准、阻断级别和重新打开条件。
- 阻塞：是。

### A-07 [P1] Schema 过薄且存在范围冲突

- 证据：`schemas/claim_record.yaml:3` 硬编码三题；`experiment_record.yaml` 缺少开始/结束时间、数据契约版本、工作区脏状态、求解器证书/最优间隙、统计切分和产物哈希；`review_record.yaml` 缺少目标哈希、作者、复核关闭者、污染状态和 `resolves` 关系。
- 影响：记录可以被填写，但不足以证明复现、独立性或结论升级合法。
- 最小修复：为所有 Schema 增加 `schema_version`、唯一 ID、内容哈希、作者/审查者分离、状态转换和失效触发字段。
- 阻塞：是。

### A-08 [P1] 确定性验证层大多停留在原则

- 证据：当前唯一实际检查脚本是 `writing/checks/check_pdf.sh`；没有数据契约验证、泄漏检查、约束检查、目标值重算、求解器状态核验、实验记录校验和 claim-to-result 一致性检查器。
- 影响：系统仍可能用语言模型的“检查结论”代替程序证据。
- 最小修复：先实现 6 个最小验证器：manifest/schema、数据质量、数据泄漏、优化可行性与目标重算、实验复现、论文数字/引用映射。
- 阻塞：是。

### A-09 [P1] 官方来源等级需要校正

- 证据：`writing/OFFICIAL_RULES.md:61,63` 将 `cmathc.org.cn` 页面放在“官方资料”下，但该站页面底部说明其为互联网整理；真正的 2025 格式和 AI 附件可从研创网官方公告直接取得。
- 影响：二手镜像可能被错误标记为 A 级官方原件。
- 最小修复：官方公告和官方附件设为 A；镜像只能设为 C，并记录原始附件 URL、哈希和获取日期。
- 阻塞：比赛日前是。

### A-10 [P1] 人工签署不可机器核验

- 证据：`templates/final_handoff.md:32-36` 只有自由文本签名；没有签署人角色、时间、目标文件哈希、批准范围和撤销条件。
- 影响：无法证明人工批准的是哪一个 PDF、哪一版模型和哪些未解决限制。
- 最小修复：新增 `human_signoff.yaml`，签署必须绑定 artifact hash、Gate 快照和已知限制。
- 阻塞：最终交付时是。

### A-11 [P2] 提示词重复，存在版本漂移

- 证据：`agent.md`、`AGENTS.md`、`CLAUDE.md`、`roles/`、`skills/` 和 `writing/prompts/` 多处重复 baseline、证据、不可自批和论文措辞规则。
- 影响：修改一处后其他文件可能过期，且长上下文降低有效注意力。
- 最小修复：规则只在 canonical policy 出现一次；角色卡引用规则 ID；适配器只处理平台差异。

### A-12 [P2] 没有风险驱动的模型、成本和时间路由

- 证据：`config/models.example.yaml:2-20` 只有占位模型和 `high_or_max`，没有预算、并发、超时、重试、降级或按风险选模型的策略。
- 影响：比赛中可能把高成本多代理用于简单任务，或在关键证明/审查上使用不足配置。
- 最小修复：按任务风险而不是角色名称决定模型级别，并记录 token、时间、重试和停止条件。

### A-13 [P2] 论文骨架仍假定固定三问和具体题型

- 证据：`writing/PAPER_STYLE_GUIDE.md:11-21,88-106`；`writing/QA_CHECKLIST.md:25`；`writing/templates/paper_outline.md:13-17`。
- 影响：未知题目可能出现两问、四问、连续任务或混合章节，固定骨架会破坏论证结构。
- 最小修复：根据 `problem_contract.subproblems[]` 动态生成章节，不在 canonical 模板中写死题数。

### A-14 [P2] 缺少通用回归评测集

- 证据：现有调研与检查清单依赖三道历史题，没有与历史题无关的合成微型测试和架构回归指标。
- 影响：无法判断重构后是否真的提升路由、约束正确性、泄漏检测和论文证据链。
- 最小修复：建立不含竞赛原题的合成微型评测集，覆盖 LP/MIP、网络、调度、随机/多目标、回归、分类、聚类、时间切分、泄漏和混合决策。

## 4. 官方规则核对

- 2026 官方邀请函已确认比赛使用《竞赛论文标准文档》、提交 PDF/MD5，并要求文献和程序标注来源；截至本次审核，公开邀请函没有给出完整 2026 排版细则：[研创网 2026 邀请函](https://cpipc.acge.org.cn/cw/contestNews/detail/4/2c9080189dcfa24e019dddacc24a1314?page=0)。
- 2025 官方公告提供格式规范、模板和 AI 规定附件，并明确封面、匿名、摘要、PDF 和 MD5 要求：[研创网 2025 开赛公告](https://cpipc.acge.org.cn/cw/contestNews/detail/4/2c90801b9914a68201994b1403512e96?page=1)。
- 本地 2025 格式 PDF 与模板 DOC 文件类型正常，哈希与 `writing/official/2025/README.md:16-19` 一致。

因此，论文系统可以保留 2025 快照作为历史证据，但 2026 比赛日必须以题包中当届文档替换 ACTIVE 规则，不能提前宣布格式已确认。

## 5. 架构判断

“Codex 主模型 + Claude 对抗模型”合理，但仅作为平台映射：

- Codex：默认映射到 `orchestrator + solution_lead`；
- Claude：默认映射到 `independent_adversary`；
- 程序与求解器：负责可重复、可判定的事实检查；
- 人工：批准目标、路由覆盖、关键取舍和最终冻结。

OpenAI 官方文档指出，多代理适合独立、边界清楚的工作流，不适合强顺序依赖或争用同一可变状态的任务；Anthropic 官方工程文章同样强调多代理的高 token 成本、上下文隔离和持久化工件。因此，不能让多个 Agent 同时改同一份模型或论文；并行应限定为独立探索、独立审查和独立复现。

## 6. 本次未做

- 未重写原有工作台文件；
- 未创建实际编排程序；
- 未接入 Codex API、Claude API 或求解器；
- 未用任何历史题验证架构；
- 未宣称 2026 当届完整格式规则已经发布。
