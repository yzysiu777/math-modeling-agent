# 角色与责任矩阵

## 1. 角色卡

| 角色 | 核心输入 | 核心输出 | 可以阻断 | 禁止事项 |
|---|---|---|---|---|
| `human_owner` | 目标、风险、方案与最终工件 | 批准、覆盖、签署 | 任意阶段 | 不得把未理解的 AI 输出直接签署 |
| `orchestrator` | project manifest、state events | 任务计划、状态、预算、交接 | 流程不完整 | 不得替专业角色证明模型正确 |
| `task_router` | problem contract | routing record | 信息不足或路由冲突 | 不得猜测缺失目标、标签或约束 |
| `solution_lead` | 已批准合同和路由 | baseline、候选、实验、整合稿 | 实现依赖缺失 | 不得批准自己的模型或审查 |
| `optimization_modeler` | 优化合同、数据接口 | formulation、算法、solution record | 数学合同不完整 | 不得把启发式写成全局最优 |
| `data_analyst` | 数据合同、分析目标 | EDA、baseline、模型、评测 | 标签/切分不明确 | 不得把相关写成因果 |
| `data_auditor` | 原始数据、字典、处理记录 | data quality/leakage report | G3 | 不得用模型分数替代数据质量判断 |
| `independent_adversary` | 盲审包或指定工件 | finding、反例、复核建议 | 未解决 P0/P1 | 不得直接改主方案或以偏好否决 |
| `reproducibility_engineer` | manifest、环境、命令、日志 | reproduction report | G11 | 不得猜参数或补隐藏步骤 |
| `paper_architect` | problem/claim/result map | 章节树、篇幅、图表计划 | 证据映射缺失 | 不得编造结果或批准 claim |
| `mathematical_writer` | supported claims | 正文草稿、待审句子 | 无 | 不得强化证据强度 |
| `citation_editor` | 正文、来源登记 | citation review | 不可验证来源 | 不得凭记忆补 DOI/作者/页码 |
| `formatting_qa` | 当届模板、最终 PDF | final PDF QA | G14 | 不得用 Word 预览代替 PDF 验收 |
| `final_gatekeeper` | 所有 Gate、finding、最终工件 | 交付判定 | G12-G15 | 不得补写实验或自签最终稿 |

## 2. 平台映射

| Canonical 角色 | 默认平台 | 独立性说明 |
|---|---|---|
| Orchestrator / Solution lead | Codex | 主链协调、实现和工件整合 |
| Optimization modeler / Data analyst | Codex 或其他专业模型 | 可以是 Codex 子工作流，但不能自审 |
| Independent adversary | Claude 独立会话 | 使用隔离材料包；若已暴露则标记非盲 |
| Focused reviewer | Codex 子 Agent | 提高覆盖，不算跨模型独立审查 |
| Deterministic validator | 程序、统计库、求解器 | 产出可重复证据，不是语言模型意见 |
| Final approver | 人工 | 唯一可以完成 G15 的角色 |

若 Claude 不可用，可以使用另一个新会话或人工审查，但必须如实标记独立性等级；不得伪造 `claude_adversary` 记录。

## 3. RACI

符号：R 执行，A 最终负责，C 咨询/复核，I 知会。

| 活动 | Human | Orchestrator | Router | Opt/Data Modeler | Data Auditor | Adversary | Repro | Paper/QA | Gatekeeper |
|---|---|---|---|---|---|---|---|---|---|
| 目标与范围 | A | R | I | I | I | I | I | I | C |
| 输入冻结 | C | A/R | I | I | C | I | I | I | C |
| 路由 | A | C | R | C | C | C | I | I | I |
| 数据合同 | C | I | I | R | A | C | I | I | C |
| 模型合同 | A | C | I | R | C | C | I | I | C |
| Baseline/候选 | C | C | I | A/R | C | I | I | I | I |
| 确定性验证 | I | C | I | C | C | C | A/R | I | C |
| 对抗审查 | I | I | I | C | C | A/R | C | C | I |
| Finding 修复 | I | C | I | R | C | A(关闭) | C | I | C |
| 独立复现 | I | I | I | C | C | C | A/R | I | C |
| 论文结构和正文 | C | C | I | C | C | C | I | A/R | I |
| 引用/AI/格式 | C | I | I | I | I | C | I | A/R | C |
| 最终 Gate | A | I | I | I | I | C | C | C | R |
| PDF 冻结和提交 | A/R | I | I | I | I | I | I | C | C |

## 4. 自我批准防线

- `artifact.author` 与 `review.reviewer` 不能相同；
- 同一模型、同一会话、同一上下文可以做自检，但只能标记 `self_check`；
- P0/P1 finding 的关闭者必须是原 reviewer 或 human owner；
- final gatekeeper 只检查证据，不创建缺失证据；
- human signoff 必须绑定目标 artifact hash。

## 5. Claude 对抗模式

### Blind reconstruction

输入：题意合同、输入 manifest、数据合同、验收标准。  
隐藏：Codex 模型、代码、结果、论文措辞。  
输出：独立问题重建、候选 baseline、风险、最小反例和应有测试。

### Nonblind adversarial

输入：明确列出的模型、代码、实验和 claim。  
输出：逐条 finding、证据位置、影响、最小修复、仍支持的结论。

### Reproduction

输入：发布给复现者的命令、环境和输入。  
禁止：读取作者隐藏笔记或自行猜参数。  
输出：成功、偏差、阻塞和输出哈希。

## 6. 冲突规则

- 不是投票系统；
- 先比证据质量，再运行能区分两种主张的测试；
- 仍无法裁决时保持 `disputed`；
- 人工可以决定“继续、降级、披露、放弃”，但不能把无证据主张改成 `supported`。

