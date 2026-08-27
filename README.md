# 数学建模 Agent 工作台

这是一个只面向“华为杯”中国研究生数学建模竞赛的可复核协作工作台，服务于三类任务：

- 运筹优化：规划、网络、路径、调度、资源分配、多目标、鲁棒与随机优化；
- 数据分析：数据清洗、统计推断、预测、分类、聚类、时序和可解释性；
- 混合建模：数据分析产生参数、预测或场景，优化模型完成决策。

工作台采用唯一固定竞赛流程：“Codex 主解 + Claude 在 C1/C2/C3 人工触发审核 + 确定性验证器 + 人工最终签字”。模型意见只产生候选和发现，不能替代数据检查、数学推导、程序复现或人的决定。

## 快速入口

1. 先读 [AGENTS.md](AGENTS.md) 和 [agent.md](agent.md)。
2. 新建案例时复制 [templates/case_manifest.yaml](templates/case_manifest.yaml)。
3. 依次阅读 [protocol/workflow.md](protocol/workflow.md) 和 [protocol/gates.md](protocol/gates.md)。
4. 按路由读取 `skills/industrial-mathematical-modeling/` 下的运筹、数据分析或混合检查清单。
5. 论文任务先读 [writing/README.md](writing/README.md)，再使用 `paper/` 中的 LaTeX 工程。
6. 需要 Claude 时，严格按照 [CLAUDE.md](CLAUDE.md) 和 `prompts/claude/` 的 C1/C2/C3“先审后改”协议交接。

## 目录结构

```text
agent/
├── AGENTS.md                         总规则、权限和质量门
├── agent.md                          Codex 主 Agent 执行协议
├── CLAUDE.md                         Claude 审核和修订边界
├── roles/                            与平台无关的权威角色定义
├── adapters/                         Codex/Claude 平台适配入口
├── prompts/                          启动、审核和修订提示词
├── protocol/                         唯一工作流、状态和门禁
├── schemas/                          JSON Schema 与记录接口
├── templates/                        案例、实验、审核和签字模板
├── skills/                           项目级可携带 Skill
├── scripts/                          路由、Schema、状态、回归和论文检查器
├── tests/                            不依赖具体历史题目的合成测试
├── paper/                            可编译的 XeLaTeX 协作工程
├── writing/                          论文语言、引用、AI 记录和格式规则
├── audit/                            架构调研和改造决策记录
└── config/                           不含密钥的模型配置示例
```

案例内的团队协作记录只放在 `cases/<case_id>/coordination/`，契约见
[protocol/team-collaboration.md](protocol/team-collaboration.md)。任何仓库外的
Planner/Executor 控制面、交接单或开发审核记录都不复制进本仓库，也不由竞赛
运行时自动加载。

修订闭环的三个入口是：`scripts/classify_change.py`（R0–R3）、
`scripts/plan_targeted_validation.py`（安全检查 ID）和
`scripts/check_revision_closure.py`（验证记录关闭）。
`scripts/check_approved_revision.py` 先检查非空文件白名单与前后哈希，
再单独检查回归验证，二者不会互相替代。

`scripts/run_trusted_check.py` 只接受固定 check ID，并为实际执行写入时间戳、
stdout/stderr 路径与哈希；尚未自动化的检查会明确记录为 `manual_required`，
不能伪装成通过。`scripts/check_evidence_graph.py` 校验“输入/附件哈希 → 代码
版本 → 实验 → 输出哈希 → 图表/表格 → claim → 论文定位”的证据链。
`scripts/check_work_item.py` 校验案例级单写入者、非自审、源/结果 revision 和
工作范围冲突。

## 一次案例的推荐目录

```text
case-workspace/
├── AGENTS.md
├── CLAUDE.md
├── case_manifest.yaml
├── input/                    原始题面和附件，只读；默认不进入公共 Git
├── source/                   公开资料、文献、代码来源和哈希
├── data_dictionary/         字段、单位、标签和数据契约
├── artifacts/               问题契约、模型、图表、表格和结论
├── runs/                    实验命令、环境、日志和结果摘要
├── reviews/                 Claude、人工和复现审查报告
├── failures/                失败尝试、反例和废弃路线
└── final/                   经过门禁的论文源文件和交接记录
```

原始输入不能被覆盖；案例中的大数据和私有审核包默认通过 `.gitignore` 排除，只有经过人工确认的清单、哈希、源代码、实验摘要和论文源文件进入 Git。

## Codex、Claude 与人工的分工

| 参与者 | 默认职责 | 禁止事项 |
|---|---|---|
| Codex | 题意重构、路由、baseline、模型、代码、实验、论文初稿 | 把未验证结果写成定论；自行关闭高风险审核 |
| Claude | 盲审、数据/模型/复现/论文对抗审查、批准后的修订提案 | 直接改 `main`；自审自批；以一致性替代证据 |
| 确定性工具 | Schema、数据质量、约束、指标、复现、PDF 检查 | 以启发式输出冒充证明 |
| 人工队员 | 批准目标、选择模型、确认修订、签署最终交付 | 将模型输出直接视作事实 |

## 固定竞赛流程与局部回归

- `main` 保存可交付版本；`luna/competition-review-refactor` 用于本次架构回归，后续 `model/<任务>`、`analysis/<任务>`、`paper/<章节>` 和 `review/<编号>` 是默认工作分支。
- PR 必须通过结构检查、合成测试和 LaTeX CI；高风险发现未关闭时禁止合并。仓库不提供互相竞争的工作流模式。
- 通过 Gate 后的改动按 R0–R3 分级；R0 只做局部语法/快速编译，R1 检查论文证据，R2 重跑受影响代码与实验，R3 重新检查数据/模型、可行性、目标和稳健性。
- `scripts/check_approved_revision.py` 分别报告修改范围和回归验证；`allowed_files` 为空时 fail closed。
- 变更先声明 `text_only`、`paper_claim`、`code_only`、`experiment_logic`、`data_contract`、`model_formula`、`objective_constraint` 或 `candidate_pdf`；仅凭文件名不能自动判为 R0–R3。
- `paper/main.tex` 只做装配，正文分散在 `paper/sections/`；引用统一维护在 `paper/bibliography/references.bib`。
- `make paper` 编译本地版本，`make paper-ci` 编译 CI 预览，`make qa` 执行静态检查。
- CI 使用可携带字体完成编译；正式投稿必须以当届官方模板、规则和比赛日字体预检为准。

## 当前版本边界

本仓库提供流程、提示词、接口、检查器和论文工程模板，不自动调用 Codex 或 Claude API。模型名称、账号、预算、数据路径和密钥必须保存在本地私有配置中，不能提交到 Git。

当前 `writing/official/2025/` 中的文件只是历史格式快照。比赛日必须重新获取当届官方论文标准和 AI 使用规定，并在 `paper/official/<year>/manifest.yaml` 中记录来源、日期和哈希。

## 验收入口

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
PYTHON=.venv/bin/python make validate test
make paper-ci
make qa
```

所有检查通过仍不替代人工最终签字；交接时必须报告证据、限制、失败路线、未验证项和人工实际检查范围。
