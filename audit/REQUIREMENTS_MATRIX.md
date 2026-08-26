# 需求覆盖矩阵

状态含义：`已有`、`部分`、`缺失`、`需更新`。本表描述当前系统，不代表目标方案已经实现。

| 需求 | 当前状态 | 当前证据 | 目标工件 | 优先级 |
|---|---|---|---|---|
| 未知题目通用入口 | 缺失 | 根规则和 Schema 硬编码三道题 | `project_manifest`、通用标签 | P1 |
| 运筹优化专业轨道 | 部分 | 通用 `model_reviewer`，无建模角色 | `optimization_modeler`、优化合同 | P1 |
| 数据分析专业轨道 | 部分 | 有 `data_auditor`，无 `data_analyst` | 数据分析合同、评测协议 | P1 |
| Hybrid 任务 | 缺失 | 无接口合同 | `hybrid_interface_contract` | P1 |
| 四态路由 | 缺失 | 只有具体题型和 `other` | `routing_record` | P1 |
| Orchestrator | 缺失 | Codex lead 同时承担多种职责 | 独立状态协调角色 | P1 |
| 状态机 | 缺失 | 仅有线性 workflow 文档 | `state_event`、转换表 | P1 |
| 暂停、恢复、重试 | 缺失 | 无恢复协议 | checkpoint + recovery policy | P1 |
| 原始输入冻结 | 已有 | `AGENTS.md:50-57` | 保留并机器化 | P2 |
| Claim 证据链 | 部分 | claim Schema 字段不足且硬编码 | v2 claim Schema | P1 |
| 实验复现 | 部分 | 有实验卡，无完整环境和哈希关系 | v2 experiment Schema | P1 |
| 失败路线保留 | 已有 | `failures/` 规则 | append-only failure record | P2 |
| Claude 盲审 | 部分 | 有提示词，无隔离材料包 | review bundle + exposure | P1 |
| 模型冲突裁决 | 部分 | 原则上交给程序或人 | disagreement protocol | P1 |
| 程序化数据检查 | 缺失 | 无实际数据验证器 | data quality/leakage validators | P1 |
| 程序化优化检查 | 缺失 | 无可行性和目标重算器 | optimization validators | P1 |
| 16 个质量门禁 | 缺失 | 当前只有 8 个合并 Gate | v2 gates | P1 |
| RACI | 缺失 | 角色说明散落 | role responsibility matrix | P1 |
| 人工签署绑定哈希 | 缺失 | 仅自由文本签名 | `human_signoff.yaml` | P1 |
| 成本和时间控制 | 部分 | 只有“降低并行度”原则 | budget + retry + model routing | P2 |
| 论文独立生产线 | 已有 | `writing/` 结构完整 | 保留并去题目化 | P2 |
| 证据化论文语言 | 已有 | `NATIONAL_AWARD_LANGUAGE.md` | 改名并引用规则 ID | P2 |
| 官方规则与内部风格分离 | 已有 | `writing/README.md:5-11` | 保留 | P2 |
| 2026 当届详细格式 | 需更新 | 只有邀请函和 2025 快照 | 比赛日官方 manifest | P1 |
| PDF 预检 | 部分 | `check_pdf.sh` 可用但只警告 | 扩展 deterministic QA | P2 |
| 论文题数动态化 | 缺失 | 模板固定问题一至三 | 基于 subproblems 动态生成 | P2 |
| 通用架构回归评测 | 缺失 | 依赖历史题 | synthetic evals | P2 |

## 需求到实施阶段

### MVP

- 去除三题硬编码；
- 新增路由、两个专业角色和 Hybrid 接口；
- 新增状态机、16 Gate、v2 Schema；
- 新增最小确定性验证器；
- 新增盲审 bundle 和人工签署 Schema。

### 竞赛可用版

- 完整论文动态模板；
- 官方规则 manifest 和比赛日刷新流程；
- 合成评测集；
- 成本、时间、重试和模型路由；
- 一键生成最终交接与 Gate 快照。

### 长期版

- API 编排；
- 可视化状态面板；
- 自动实验注册、结果血缘和失效传播；
- 多平台适配和评测回归。

