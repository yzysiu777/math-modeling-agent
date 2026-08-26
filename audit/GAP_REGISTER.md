# 缺口台账

状态：`OPEN` 表示尚未实施；本轮只完成设计。

| ID | 缺口 | 严重度 | 当前证据 | 目标修复 | 责任角色 | 状态 |
|---|---|---|---|---|---|---|
| GAP-001 | canonical 文件硬编码三道题 | P1 | README、roles、workflow、schemas、skills | 通用四态路由和可扩展标签 | Architect | OPEN |
| GAP-002 | 无 task router | P1 | 无角色/Schema | router role + routing record | Orchestrator | OPEN |
| GAP-003 | 无 Hybrid 接口 | P1 | 无工件 | versioned interface contract | Hybrid coordinator | OPEN |
| GAP-004 | 无 optimization modeler | P1 | roles 缺失 | 专业角色和优化合同 | Architect | OPEN |
| GAP-005 | 无 data analyst | P1 | roles 缺失 | 专业角色和分析合同 | Architect | OPEN |
| GAP-006 | 无显式 Orchestrator | P1 | lead 职责过载 | 状态管理与建模分离 | Architect | OPEN |
| GAP-007 | 无机器可执行状态机 | P1 | workflow 仅叙述 | event log + transitions | Orchestrator | OPEN |
| GAP-008 | 无恢复/失效传播 | P1 | 无 recovery 协议 | checkpoint + invalidation | Orchestrator | OPEN |
| GAP-009 | 盲审隔离不可证明 | P1 | visibility 仅文字 | review bundle + exposure | Adversary owner | OPEN |
| GAP-010 | Gate 不足且过度合并 | P1 | G0-G7 | G0-G15 | Gatekeeper | OPEN |
| GAP-011 | claim Schema 硬编码 | P1 | `claim_record.yaml:3` | v2 generic claim | Schema owner | OPEN |
| GAP-012 | experiment Schema 复现字段不足 | P1 | 无时间、完整环境、证书和产物哈希 | v2 experiment | Repro engineer | OPEN |
| GAP-013 | review Schema 无关闭/污染关系 | P1 | 无 target hash/resolves/exposure | v2 review | Review owner | OPEN |
| GAP-014 | 人工签署不绑定工件 | P1 | final_handoff 自由文本 | signoff Schema | Human owner | OPEN |
| GAP-015 | 无数据质量/泄漏验证器 | P1 | 只有角色提示词 | validator scripts | Data auditor | OPEN |
| GAP-016 | 无优化可行性/目标验证器 | P1 | 只有审查原则 | validator scripts | Optimization reviewer | OPEN |
| GAP-017 | 无 claim-paper 一致性验证器 | P1 | 论文依赖人工登记 | paper validator | Paper QA | OPEN |
| GAP-018 | 官方镜像来源等级偏高 | P1 | cmathc 列为官方资料 | A0 官方附件/C 镜像 | Citation editor | OPEN |
| GAP-019 | 2026 详细规则未冻结 | P1 | 只有邀请函 | 比赛日 manifest | Human + compliance | OPEN |
| GAP-020 | 提示词重复 | P2 | 多层重复规则 | canonical policy + rule ID | Architect | OPEN |
| GAP-021 | 无成本/时间/重试策略 | P2 | model config 占位 | risk-based routing | Orchestrator | OPEN |
| GAP-022 | 论文固定三问 | P2 | outline 和 style guide | 动态章节 | Paper architect | OPEN |
| GAP-023 | 无通用合成评测 | P2 | 依赖历史题 | synthetic eval suite | Eval owner | OPEN |
| GAP-024 | 目录无版本控制 | P2 | 非 Git repo | Git 或不可变快照 | Human owner | OPEN |

## 依赖顺序

```text
GAP-001
  → GAP-002/003/004/005/006
  → GAP-007/008/010
  → GAP-011/012/013/014
  → GAP-015/016/017
  → GAP-020/021/023

GAP-018/019
  → 论文合规和最终冻结
```

## 关闭标准

任何缺口不能因“文件已经创建”而关闭。必须满足：

1. 对应工件存在；
2. Schema 或提示词可解析；
3. 合成评测覆盖成功路径和失败路径；
4. 独立 reviewer 确认；
5. 文档链接和角色引用一致；
6. 没有重新引入具体历史题依赖。

