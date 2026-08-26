# 数学建模 Agent 工作台

这是一个面向中国研究生数学建模竞赛的通用、可复核协作工作台，服务于三类任务：

- 运筹优化：规划、网络、路径、调度、资源分配、多目标、鲁棒与随机优化；
- 数据分析：数据清洗、统计推断、预测、分类、聚类、时序和可解释性；
- 混合建模：数据分析产生参数、预测或场景，优化模型完成决策。

工作台采用“Codex 主解 + Claude 人工触发审核 + 确定性验证器 + 人工最终签字”的结构。模型意见只产生候选和发现，不能替代数据检查、数学推导、程序复现或人的决定。

## 快速入口

1. 先读 [AGENTS.md](AGENTS.md) 和 [agent.md](agent.md)。
2. 新建案例时复制 [templates/case_manifest.yaml](templates/case_manifest.yaml)。
3. 依次阅读 [protocol/workflow.md](protocol/workflow.md) 和 [protocol/gates.md](protocol/gates.md)。
4. 按路由读取 `skills/industrial-mathematical-modeling/` 下的运筹、数据分析或混合检查清单。
5. 论文任务先读 [writing/README.md](writing/README.md)，再使用 `paper/` 中的 LaTeX 工程。
6. 需要 Claude 时，严格按照 [CLAUDE.md](CLAUDE.md) 和 `prompts/claude/` 的“先审后改”协议交接。

## 目录结构

```text
agent/
├── AGENTS.md                         总规则、权限和质量门
├── agent.md                          Codex 主 Agent 执行协议
├── CLAUDE.md                         Claude 审核和修订边界
├── roles/                            与平台无关的权威角色定义
├── adapters/                         Codex/Claude 平台适配入口
├── prompts/                          启动、审核和修订提示词
├── protocol/                         工作流、状态和门禁
├── schemas/                          JSON Schema 与记录接口
├── templates/                        案例、实验、审核和签字模板
├── skills/                           项目级可携带 Skill
├── scripts/                          路由、Schema、状态和论文检查器
├── tests/                            不依赖具体历史题目的合成测试
├── paper/                            可编译的 XeLaTeX 协作工程
├── writing/                          论文语言、引用、AI 记录和格式规则
├── audit/                            架构调研和改造决策记录
└── config/                           不含密钥的模型配置示例
```

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

## Git 与论文协作

- `main` 保存可交付版本；`model/<任务>`、`analysis/<任务>`、`paper/<章节>` 和 `review/<编号>` 是默认工作分支。
- PR 必须通过结构检查、合成测试和 LaTeX CI；高风险发现未关闭时禁止合并。
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

所有检查通过仍不替代人工最终签字；交接时必须报告证据、限制、失败路线和未验证项。
