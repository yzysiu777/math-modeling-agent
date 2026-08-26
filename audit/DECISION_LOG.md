# 架构决策日志

## 已作出的设计决定

### ADR-001：系统只面向两类通用任务和 Hybrid

- 状态：ACCEPTED
- 决定：主路由固定为 `optimization | data_analysis | hybrid | insufficient_information`。
- 理由：这是用户明确范围；具体历史题、年份和专用字段不得进入 canonical 层。
- 影响：现有硬编码内容必须迁移或删除。

### ADR-002：角色供应商无关

- 状态：ACCEPTED
- 决定：canonical 角色使用 `solution_lead`、`independent_adversary` 等业务名称；Codex/Claude 只在 adapter 和配置中映射。
- 理由：避免供应商和模型版本变化破坏工作流，也让职责可被其他平台接管。
- 影响：现有 `codex_lead`、`claude_adversary` 需要转为适配器或角色映射。

### ADR-003：Codex 主链 + Claude 对抗链合理，但不采用投票

- 状态：ACCEPTED
- 决定：Codex 默认协调和实现，Claude 默认独立审查；冲突由证据、程序或人工裁决。
- 理由：模型多样性可以减少路径依赖，但一致性和多数票都不是真值。
- 影响：必须建设 blind bundle、finding closure 和 disagreement record。

### ADR-004：确定性验证器是独立层

- 状态：ACCEPTED
- 决定：数据、约束、目标、统计、复现、论文数字和 PDF 检查尽量程序化。
- 理由：语言模型不能自证计算和实现正确。
- 影响：当前只有 PDF 预检，需新增至少 6 类 validator。

### ADR-005：采用 append-only 状态和工件记录

- 状态：ACCEPTED
- 决定：状态由事件日志重放；运行、审查和失败不覆盖。
- 理由：支持恢复、追溯、审查关闭和失效传播。
- 影响：需要 state event、artifact registry 和 snapshot。

### ADR-006：使用 16 个 Gate

- 状态：ACCEPTED
- 决定：将目标、路由、数据、假设、baseline、公式、算法、可行性、结果、稳健性、复现、论文、合规、PDF 和人工冻结拆开。
- 理由：当前 8 Gate 过度合并，无法准确阻断和恢复。

### ADR-007：论文语言改为证据校准语言

- 状态：ACCEPTED
- 决定：“国奖语言”仅作为内部俗称，canonical 名称使用 `evidence-calibrated language`。
- 理由：组委会没有官方“国奖语言词典”，不能把风格建议冒充规则。

### ADR-008：2025 文件只能是历史快照

- 状态：ACCEPTED
- 决定：2026 ACTIVE 规则必须在比赛日从官方题包/公告冻结；未知字段保持 PENDING。
- 理由：2026 官方邀请函尚未给出完整公开排版细则。

### ADR-009：评测不得使用指定历史题

- 状态：ACCEPTED
- 决定：架构回归使用通用合成微型问题和结构测试。
- 理由：避免再次把工作台拟合到少数题目。

## 需要用户裁决

### ADR-P01：实施方式

- 选项 A：在现有目录中原位重构；
- 选项 B：新建 `agent-v2/`，现有目录作为只读原型。
- 推荐：B。当前目录不是 Git 仓库，新建 v2 更容易回滚和对比。

### ADR-P02：运行平台

- 选项 A：先做纯文件工作台，由 Codex/Claude 人工启动；
- 选项 B：立即建设 API 自动编排。
- 推荐：A。先通过合成评测，再自动化。

### ADR-P03：Claude 接入形式

- 选项 A：Claude Code 独立会话和审查包；
- 选项 B：Anthropic API；
- 选项 C：人工复制提示词。
- 推荐：先 A 或 C，前提是材料白名单和审查记录完整；API 可后置。

### ADR-P04：默认文档语言

- 选项 A：人类可读文档中文、Schema/状态英文；
- 选项 B：全部中文；
- 选项 C：全部英文。
- 推荐：A，延续现有 `zh-human-readable-en-schema` 思路。

### ADR-P05：求解器策略

- 待确认可用的商业/开源求解器、许可证、机器资源和比赛环境。
- 未确认前，架构只定义 solver adapter，不写死 Gurobi、CPLEX 或其他产品。

### ADR-P06：官方 Word 与内部 LaTeX/Markdown

- 推荐：内部可使用 Markdown/LaTeX 管理内容与图表，最终必须回到当届官方标准文档并以 PDF 为准。
- 待确认团队实际协作偏好和 Word/LaTeX 熟练度。

## 决策变更规则

任何 ACCEPTED 决策若被修改，必须记录：变更人、原因、替代方案、新证据、受影响文件、需要重新执行的 Gate 和迁移计划。不得直接覆盖本日志。

