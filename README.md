# 华为杯数学建模工业级 Agent 工作台

这是一个面向中国研究生数学建模竞赛的、可复制的多智能体协作模板。目标不是让两个模型“互相投票”，而是把模型推理、数据验证、复现实验、对抗审查和人工决策分层，形成可追溯的竞赛建模生产线。

## 先看什么

1. [RESEARCH_REPORT.md](RESEARCH_REPORT.md)：调研结论、架构判断、支持的 Skills 和三道题的落地路线。
2. [AGENTS.md](AGENTS.md)：Codex 及其他 coding agent 的长期工作规则。
3. [CLAUDE.md](CLAUDE.md)：Claude Code 作为独立对抗审查者时的适配规则。
4. [protocol/workflow.md](protocol/workflow.md)：从题面接收到最终论文的阶段流程。
5. [protocol/gates.md](protocol/gates.md)：每个阶段的准入、验收和阻断条件。
6. [skills/industrial-mathematical-modeling/SKILL.md](skills/industrial-mathematical-modeling/SKILL.md)：可复制的项目级 Skill。

## 核心判断

“Codex 主模型 + Claude 对抗模型”是合理的候选架构，但必须加上第三层：**确定性验证器与人工门禁**。Claude 的不同模型先验可以降低单一模型路径依赖，却不能把“模型不一致”当作真值，也不能代替数据检查、公式推导、求解器结果和复现实验。

建议角色分工：

- Codex：项目协调、资料盘点、代码/实验编排、候选模型实现、结果汇总和论文草稿。
- Claude：独立建模、反例构造、数据泄漏审查、公式/约束攻击、结果复核；默认只读，不改主方案。
- Python/统计库/图算法/优化求解器：对数据、公式、约束、指标和结果做可重复的确定性检查。
- 人：批准目标、确认建模取舍、处理无法自动裁决的争议，并签署最终论文。

## 目录说明

```text
agent/
├── README.md                         本文件
├── RESEARCH_REPORT.md                调研报告
├── AGENTS.md                         Codex/通用 coding agent 规则
├── CLAUDE.md                         Claude Code 适配规则
├── roles/                            权威角色提示词
│   ├── codex_lead.md
│   ├── claude_adversary.md
│   ├── data_auditor.md
│   ├── model_reviewer.md
│   ├── reproducibility_reviewer.md
│   └── final_gatekeeper.md
├── prompts/                          可直接复制的启动提示词
├── protocol/                         流程、门禁和升级规则
├── schemas/                          声明、实验、审查和运行记录字段
├── templates/                        案例清单、实验卡、审查报告模板
├── config/                           不含密钥的模型配置示例
├── skills/
│   └── industrial-mathematical-modeling/  可携带的 Codex Skill 包
└── adapters/                         平台适配入口
    ├── codex/AGENTS.md
    └── claude/CLAUDE.md
```

## 使用方式

把某一道题复制成独立案例工作区，例如：

```text
case-workspace/
├── AGENTS.md                 从本目录复制或引用
├── CLAUDE.md                 需要 Claude Code 时复制
├── case_manifest.yaml
├── input/                    原始题面、附件，只读
├── source/                   论文、官方资料、代码仓库
├── data_dictionary/         字段、单位、标签和数据契约
├── artifacts/                模型、图表、表格、推导和中间结论
├── runs/                     每次实验的命令、环境、日志和结果
├── reviews/                  Claude/其他审查者的审查记录
├── failures/                 失败尝试、反例和废弃路线
└── final/                    经过门禁的论文和答辩材料
```

原则上不要把三道题混在同一个运行状态里。每道题要有独立的 `case_manifest.yaml`、原始数据哈希、运行日志和结论登记表。

## 当前版本边界

- 这是提示词、流程和目录模板，不是已经接通 Codex API、Claude API 或求解器的自动编排平台。
- `config/models.example.yaml` 不含任何密钥；真正的模型名、账户、预算和 API 地址应在本地私有配置中填写。
- 2025 A 可能包含较大 CSV 和较重调度实验，先做小算例和确定性 baseline，再扩大规模。
- 任何“通过”都必须有证据记录；没有运行记录的模型只能标记为“候选”或“未验证”。

## 论文写作与交付

论文不作为最后一步的语言润色。请先读 writing/README.md，它包含官方模板快照、论文结构、国奖语言的证据化写法、图表公式规范、AI 合规记录和最终 PDF 门禁。

论文专项 Skill 位于 skills/competition-paper-writing/，负责官方模板版本冻结、正文结构、语言证据化、引用/AI 审计和最终 PDF 验收。
