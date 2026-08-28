# 华为杯数学建模 Agent 工作台

这是一个为中国研究生数学建模竞赛四天赛程设计的本地协作工作台，支持：

- 运筹优化：规划、网络、路径、调度、资源分配、多目标、鲁棒与随机优化；
- 数据分析：清洗、统计、回归、分类、聚类、预测、时序与可解释性；
- 混合建模：数据模型生成参数、预测或场景，优化模型完成决策。

Codex 负责题意重构、候选模型、代码、实验和论文初稿；Claude 由队员在 C1、C2、C3
三个关键节点手动调用；队员决定关键假设、路线取舍、强结论和最终提交。

## 1. 启用工作台

### 1.1 在 Codex 中打开

把下面目录作为 Codex 项目打开，并新建任务：

```text
/Users/lambency/Desktop/研 0 /数学建模/agent
```

Codex 会自动读取根目录 `AGENTS.md`，并从 `.agents/skills/` 发现三个仓库级 Skill：

- `industrial-mathematical-modeling`：运筹、数据分析和混合建模；
- `model-race`：候选路线、低成本实验和 Champion/Challenger；
- `competition-paper-writing`：论文结构、证据化语言和 LaTeX 协作。

修改 `AGENTS.md` 或 Skill 后，请新建 Codex 任务，使新会话重新加载项目指令。

### 1.2 首次准备

```bash
cd "/Users/lambency/Desktop/研 0 /数学建模/agent"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

论文编译需要本机安装 XeLaTeX、latexmk 和 biber。只做建模与实验时，可以暂不安装
LaTeX 工具链。

## 2. 新题开始：五分钟建立案例

题型尚未判断时使用：

```bash
.venv/bin/python scripts/create_case.py \
  --case-id huawei-cup-2026-a \
  --route insufficient_information
```

已经确定题型时，可将路由改为 `optimization`、`data_analysis` 或 `hybrid`。

把题面和附件放入：

```text
cases/huawei-cup-2026-a/input/
```

然后在 Codex 中发送：

```text
请接管 cases/huawei-cup-2026-a。读取题面、附件、case_brief.md 和项目指令，
先重构题意并判断路由。为每个关键子问题提出至少三条方法论不同的候选路线，
建立可解释 baseline，安排成本最低且最能区分路线的实验，并同步维护论文。
```

启动时，队员只需要补充 `case_brief.md` 中确实掌握的信息。其余模型池、比较表和
实验板由 Codex 根据题面更新。

## 3. 比赛主流程

```text
题意重构
  -> 候选路线头脑风暴
  -> 可解释 baseline
  -> 小实验赛马
  -> Champion / Challenger
  -> Claude 关键挑战
  -> 正式模型与稳健性实验
  -> 论文同步写作
  -> 数值、引用、格式和 PDF 检查
```

### 第一步：题意重构

Codex 从题面提取子问题、输入、输出、目标、硬约束、字段、单位、时间边界、评价指标
和交付物。只有会改变目标、约束或主路线的歧义需要队员决定。

### 第二步：建立候选模型池

每个关键子问题至少保留三条不同方法族的路线。路线卡写清核心思想、数学表达、假设、
数据需求、成本、风险和最便宜的证伪实验。

方法参考位于：

- `.agents/skills/industrial-mathematical-modeling/references/optimization-method-cards.md`
- `.agents/skills/industrial-mathematical-modeling/references/data-analysis-method-cards.md`
- `.agents/skills/industrial-mathematical-modeling/references/hybrid-method-cards.md`

### 第三步：实验赛马

先跑手算、小实例、小样本、短迭代和简单 baseline。所有路线使用统一数据切分、实例、
约束口径和指标。当前最好路线记为 Champion，同时保留一个方法论不同的 Challenger。

常用文件：

- `models/candidates.md`：候选路线；
- `models/comparison.md`：公平比较和当前取舍；
- `experiments/board.md`：实验问题、配置、结果和下一步；
- `decisions.md`：影响路线或论文强结论的人工决定。

### 第四步：Claude 关键挑战

Claude 不接管主解，只审核关键节点：

| 节点 | 使用时机 | 提示词 |
|---|---|---|
| C1 | 题意、目标或硬约束存在关键歧义 | `prompts/claude/C1_problem_challenge.md` |
| C2 | 候选路线形成，准备确定主架构 | `prompts/claude/C2_model_challenge.md` |
| C3 | 主要结果稳定，准备写摘要和结论 | `prompts/claude/C3_results_challenge.md` |

让 Codex 按 `templates/claude_review_packet.md` 生成精简材料，人工复制到新的 Claude
会话。队员将采纳或拒绝理由写入 `decisions.md`，再让 Codex 实施修改和针对性复算。

### 第五步：同步论文

从第一个稳定 baseline 开始维护论文，不等到最后一天。根目录 `paper/` 是共享 LaTeX
工程，写作规范位于 `writing/`。重点保持公式、代码、实验、图表和结论一致。

```bash
make paper-ci   # 编译预览 PDF 并运行 LaTeX QA
make qa         # 检查已生成 PDF
```

仓库模板是团队内部工程模板，不是当届官方提交模板。比赛开始后必须重新核对官方封面、
摘要页、匿名要求、字体、页数、文件命名和 AI 使用规定。

## 4. 案例目录说明

```text
cases/<case_id>/
├── input/                    题面、附件和字段说明
├── case_brief.md             题意、目标、约束、单位和疑点
├── models/
│   ├── candidates.md         候选路线池
│   └── comparison.md         统一口径下的模型比较
├── experiments/
│   ├── board.md              实验队列、结果和下一步
│   ├── code/                 可运行代码
│   └── outputs/              关键结果和图表数据
├── decisions.md              路线与强结论的人工决定
├── reviews/                  Claude C1/C2/C3 报告
└── paper/                    案例与根论文工程的对应说明
```

三个不绑定历年题目的演示位于 `cases/examples/`，可用于了解最短工作路径。

## 5. 仓库目录说明

```text
agent/
├── AGENTS.md                 Codex 自动读取的项目规则
├── CLAUDE.md                 Claude 独立挑战边界
├── agent.md                  Codex 详细执行协议
├── .agents/skills/           Codex 自动发现的建模、赛马和论文 Skill
├── cases/                    真实案例与通用演示
├── prompts/                  Codex 启动和 Claude C1/C2/C3 提示词
├── templates/                案例、候选路线、实验和审核包模板
├── scripts/                  初始化、结构检查和数值检查
├── paper/                    XeLaTeX 论文工程
├── writing/                  论文内容、语言、图表和格式规范
├── protocol/                 竞赛流程与团队协作说明
├── roles/                    团队职责参考
├── docs/                     当前架构和文档索引
└── tests/                    通用合成测试
```

外部 Planner/Executor 协作控制台不属于比赛运行时，也不放入本仓库。

## 6. 检查命令

日常建模只运行与当前修改相关的检查。准备合并、交接或提交论文时运行完整检查：

```bash
PYTHON=.venv/bin/python make validate
PYTHON=.venv/bin/python make test
PYTHON=.venv/bin/python make demos
PYTHON=.venv/bin/python make paper-ci
PYTHON=.venv/bin/python make qa
```

单独检查案例文件：

```bash
.venv/bin/python scripts/model_pool.py cases/<case_id>/models/candidates.md
.venv/bin/python scripts/experiment_board.py cases/<case_id>/experiments/board.md
```

这些脚本检查明显缺失、重复、数据泄漏、约束和目标值，不判断模型在科学意义上是否
正确。方法论差异和强结论仍需 Codex、Claude 与队员共同判断。

## 7. 团队 Git 协作

推荐分支：

- `model/<任务>`：模型、公式和算法；
- `analysis/<任务>`：数据、实验和图表；
- `paper/<章节>`：论文内容和排版；
- `review/<编号>`：Claude 意见处理和复算。

每次提交写清改变内容、实验结果和下一步。同一份 `.tex` 或 Markdown 文件同一时间只
安排一个主要写入者，减少比赛期间的合并冲突。

## 8. 常见问题

### Codex 没有读取项目规则

确认任务的项目根目录是本仓库，而不是上级“数学建模”目录；然后新建任务。根目录
`AGENTS.md` 在新会话开始时加载。

### Skill 没有显示

确认 `.agents/skills/<skill-name>/SKILL.md` 存在。修改 Skill 后新建任务；也可以在提示
中明确写 `$industrial-mathematical-modeling`、`$model-race` 或
`$competition-paper-writing`。

### 还不知道题型

用 `insufficient_information` 创建案例，让 Codex 先读取题面后再更新路由。

### Claude 是否需要 API

不需要。当前采用人工复制精简审核包的方式，不自动调用 Claude API。

### 最终 PDF 是否可以直接提交

不可以直接假定。CI PDF 只用于预览；当届官方格式和最终文件必须由队员人工确认。

## 9. 进一步阅读

- [当前架构](docs/architecture.md)
- [文档索引](docs/README.md)
- [竞赛流程](protocol/competition-workflow.md)
- [团队协作](protocol/team-collaboration.md)
- [论文系统](writing/README.md)
- [论文工程](paper/README.md)
