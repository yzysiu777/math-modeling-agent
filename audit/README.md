# 数学建模 Agent 工作台审核与架构设计

审核日期：2026-08-26  
审核范围：`/Users/lambency/Desktop/研 0 /数学建模/agent` 现有指令、角色、协议、Schema、模板、Skill、适配器与论文系统。
明确排除：任何历年赛题、附件、题库和具体题目的建模内容。

审核状态：`STATIC_AUDIT_COMPLETE / INDEPENDENT_REVIEW_PENDING`。本轮作者未自我批准本报告；正式实施前应由独立新会话或人工 reviewer 复核 P1 findings 和目标架构。

## 结论

现有工作台具备正确的工程方向：证据优先、baseline 优先、独立审查、禁止自我批准、实验复现、论文与 PDF 门禁。但它仍然是围绕三道历史题搭建的原型，尚不适合直接作为“运筹优化 + 数据分析”两类未知题目的通用生产系统。

推荐保留现有证据链思想，重构为：

```text
人工治理层
  → Orchestrator / 状态机
  → Intake + 通用路由
  → Optimization / Data Analysis / Hybrid 专业轨道
  → 确定性验证器
  → 独立对抗与复现审查
  → 论文生产线
  → 最终人工签署与冻结
```

Codex 适合作为默认协调与实现模型；Claude 适合作为独立对抗审查模型。二者不是投票关系，Claude 也不是自动真值来源。争议必须回到数据、推导、程序、求解器证书、复现实验或人工裁决。

## 阅读顺序

1. [AUDIT_REPORT.md](AUDIT_REPORT.md)：当前系统是否可用、最严重问题和证据。
2. [ARCHITECTURE_PROPOSAL.md](ARCHITECTURE_PROPOSAL.md)：目标分层架构和双轨工作流。
3. [ROUTING_MATRIX.md](ROUTING_MATRIX.md)：运筹优化、数据分析、混合任务的通用路由。
4. [STATE_MACHINE.md](STATE_MACHINE.md)：状态、Gate、恢复和冻结规则。
5. [ROLE_RESPONSIBILITY_MATRIX.md](ROLE_RESPONSIBILITY_MATRIX.md)：角色边界和 RACI。
6. [PAPER_SYSTEM_REVIEW.md](PAPER_SYSTEM_REVIEW.md)：论文写作、语言、官方格式和 AI 合规。
7. [REQUIREMENTS_MATRIX.md](REQUIREMENTS_MATRIX.md)：需求覆盖情况。
8. [GAP_REGISTER.md](GAP_REGISTER.md) 与 [RISK_REGISTER.md](RISK_REGISTER.md)：缺口和风险台账。
9. [IMPLEMENTATION_ROADMAP.md](IMPLEMENTATION_ROADMAP.md)：分阶段改造路线。
10. [DECISION_LOG.md](DECISION_LOG.md)：本次架构决定和待用户裁决项。

## 本次写入边界

- 仅新增本 `audit/` 目录。
- 未修改、删除或覆盖原有 Agent 文件。
- 未读取或引用历年真题目录。
- 本轮交付是审核与目标设计，不代表现有工作台已经完成改造。

## 验证摘要

- 目标目录存在，原有文件均保留。
- 8 个 YAML 文件可被解析。
- `writing/checks/check_pdf.sh` 通过 shell 语法检查。
- 2025 官方 PDF/DOC 文件类型正常，SHA-256 与本地清单一致。
- 未发现 Markdown 相对链接断裂。
- 当前目录不是 Git 仓库，因此后续实施前应先建立可回滚的版本管理或快照策略。
