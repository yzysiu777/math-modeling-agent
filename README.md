# 华为杯数学建模 Agent 工作台

面向中国研究生数学建模竞赛四天赛程的本地协作工作台，支持：

- 运筹优化：规划、网络、路径、调度、资源分配、多目标、鲁棒与随机优化；
- 数据分析：清洗、统计、回归、分类、聚类、预测、时序与可解释性；
- 混合建模：数据模型生成参数、预测或场景，优化模型完成决策。

## 三个角色

工作分给三个**独立会话**，靠落盘文件接力：

```text
建模手 Modeler ──SPEC──▶ 编程手 Engineer ──结果+图──▶ 写作手 Writer
     ▲                        │                        │
     └──── questions ◀────────┴──── questions ◀────────┘

        Independent Reviewer C1 / C2 / C3（人工触发，横切三者）
```

| 角色 | 做什么 | 不做什么 |
|---|---|---|
| **建模手** | 头脑砖暴、路线评估、probe 轻测试、写实现规格 | 不写生产代码、不出论文级图表 |
| **编程手** | 按规格实现（Python / MATLAB）、跑实验、独立复算、出图 | 不改模型、不美化结果、不写论文 |
| **写作手** | 写论文、核数字溯源、润色图表和语言 | 不改任何数值、不提升结论强度 |

独立会话不是形式 —— 它让「忠实实现」成为结构保证：编程手看不到建模手的推理，
只能照规格做；规格没写的就是没定的，必须回问。

队员决定关键假设、路线取舍、强结论和最终提交。Independent Reviewer 由队员在 C1、C2、
C3 手动触发，可以是 Gemini、Grok、隔离的新 Codex 任务、其他模型或人类专家，不绑定
任何厂商。

## 1. 启用工作台

### 1.1 在 Codex 中打开

把下面目录作为 Codex 项目打开：

```text
/Users/lambency/Desktop/研 0 /数学建模/agent
```

Codex 会自动读取根目录 `AGENTS.md`，并从 `.agents/skills/` 发现三个与角色一一对应的
Skill：`competition-modeling`、`competition-engineering`、`competition-paper-writing`。

修改 `AGENTS.md` 或 Skill 后，请新建 Codex 任务，使新会话重新加载项目指令。

### 1.2 首次准备

```bash
cd "/Users/lambency/Desktop/研 0 /数学建模/agent"
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

论文编译需要本机安装 XeLaTeX、latexmk 和 biber。只做建模与实验时可以暂不安装。
MATLAB 只在本机运行，不进 CI。

## 2. 新题开始：五分钟建立案例

```bash
.venv/bin/python scripts/create_case.py \
  --case-id huawei-cup-2026-a \
  --route insufficient_information
```

题型已确定时把路由改为 `optimization`、`data_analysis` 或 `hybrid`。把题面和附件放入
`cases/huawei-cup-2026-a/input/`，然后只填 `case_brief.md` 里确实掌握的信息 ——
其余由建模手根据题面生成。

## 3. 三个角色怎么用

每次开**新的 Codex 任务**，项目根目录设为本仓库，粘贴对应的一句话。完整触发语和切换
时机见 [prompts/README.md](prompts/README.md)。

```text
读取 prompts/modeler.md 并按其执行，接管 cases/<case_id>。
```

```text
读取 prompts/engineer.md 并按其执行，实现 cases/<case_id>/specs/<spec_id>.md。
```

```text
读取 prompts/writer.md 并按其执行，为 cases/<case_id> 撰写和复核论文。
```

不必等一个角色做完所有事才切。常见节奏是：建模手出两条 probe 规格 → 切编程手跑完
→ 切回建模手评估 → 升 full 规格，一天内来回几轮。同一时间只让一个角色写工作树。

## 4. 比赛主流程

```text
题意重构
  -> 头脑砖暴（发散 ≥6 条，收敛 ≥3 条方法论不同的路线）
  -> 七维度评估，决定先跑哪条 probe
  -> probe 轻测试证伪（≤50 行、≤1 分钟）
  -> 通过的路线写 full 规格
  -> 编程手忠实实现 + 独立复算 + 出图
  -> Champion / Challenger
  -> Independent Reviewer 关键挑战
  -> 稳健性实验
  -> 写作手同步论文 + 数字溯源
  -> 数值、引用、格式和 PDF 检查
```

### 第一步：题意重构

从题面提取子问题、输入、输出、目标、硬约束、字段、单位、时间边界、评价指标和交付物。
未知就写未知，不用常识补成题面事实。

路由由建模手读题面判断。`scripts/router.py` 只是关键词粗筛（词表重叠、长题面会饱和），
只能作交叉参考。`checkpoint.yaml` 记录一次人工路由确认；建议路由不是正式路由。

### 第二步：头脑砖暴与评估

每个关键子问题先**无过滤地列 ≥6 条**想法，跨方法族取样，刻意包含一条极简路线和一条
超预算路线来框定上下界；再收敛到 **≥3 条方法论真正不同**的路线进 `models/candidates.md`。

「真正不同」的判据：如果路线 A 因为某个假设失败，路线 B 会不会因为同一假设失败？
会 → 它们不是独立路线。MIP 的 arc-flow、path-flow、time-indexed 是三种表述，不是三条
路线；`scripts/model_pool.py` 查不出这种重复，需要建模手和 C2 判断。

评估用七个固定维度（预期效果、实现成本、运行成本、数据满足度、可解释性、论文价值、
风险）写进 `models/comparison.md`，**结论必须落到「先跑哪条 probe」**。

方法参考：`.agents/skills/competition-modeling/references/` 下的方法卡与
`brainstorming.md`、`route-evaluation.md`。

### 第三步：轻测试先行

每条留下来的路线先写 probe 规格（`templates/spec_probe.md`）：找出这条路线最可能不
成立的那条假设，用 ≤50 行代码、≤1 分钟去打它，判据在写代码前定死。

probe `FAIL` 是好结果 —— 一分钟换掉一条错路。**一条路线在 probe 通过前不写 full 规格**，
例外只有题面直接指定了算法。

### 第四步：规格与忠实实现

建模手按 `templates/spec.md` 写 full 规格，八段齐全，判据可判定，复算要求写清。
写完自检：只读这份文件，看不到本会话的人能不能唯一确定实现？

编程手按规格实现，**不得修改模型**。规格没覆盖的建模决策写
`specs/<spec_id>.questions.md` 并停止该条路线；纯工程决策自己定。

Python 和 MATLAB 并列主力，规格的 `language` 字段说了算。**关键结论的复算必须有
Python 版本** —— 阶段检查和 CI 只能运行 Python。

```bash
make spec-check CASE=cases/<case_id>
```

### 第五步：复算与出图

复算必须**独立重算**，不能复用求解器自己的中间结果。结果写
`experiments/outputs/checks/<EXP-ID>.json`，`check_case.py` 会自动读取失败项并点亮
确定性风险标志 —— 这条链路是自动的，不依赖有人记得改控制文件。

图按 `.agents/skills/competition-engineering/references/figure-standards.md` 出，
同时导出 PDF 和 PNG，回填 `experiments/outputs/figures/manifest.md`。数据一变，
对应图立刻标 `stale` 并重跑脚本 —— 永远不手工修图。

### 第六步：Independent Reviewer 关键挑战

```bash
make review-packet CASE=cases/<case_id> NODE=C2
```

| 节点 | 使用时机 | 谁触发 |
|---|---|---|
| C1 | 题意、目标或硬约束存在关键歧义 | 建模手提醒 |
| C2 | 候选路线形成，准备确定主架构 | 建模手提醒 |
| C3 | 主要结果稳定，准备写摘要和结论 | 写作手提醒 |

脚本生成草稿，主 Agent 补完最担心的问题和 3–5 个待答问题，队员复制到**全新会话**。
包和报告注明 `reviewer_provider`、`reviewer_model`、`review_session: fresh`、
`saw_main_conversation: false` 和 `critical_node`。队员把采纳或拒绝理由写入
`decisions.md`，再让主 Agent 实施修改和针对性复算。

### 第七步：同步论文

从第一个稳定 baseline 开始维护论文，不等到最后一天。根目录 `paper/` 是共享 LaTeX
工程，写作规范位于 `writing/`。

**论文里每个数字都必须在 `paper/claim_map.md` 里追到 EXP-ID 和数据文件**，追不到的
不许写进正文。写作手润色只动语言、结构和视觉，**不动任何数值、单位、有效位数和结论
强度**；发现对不上就回问编程手，不就地「修正」。

```bash
make paper-ci   # 编译预览 PDF 并运行 LaTeX QA
make qa         # 检查已生成 PDF
```

### 第八步：按阶段运行案例检查

四个阶段使用同一个轻量检查器，不是四套运行模式：

```bash
make case-check CASE=cases/huawei-cup-2026-a STAGE=exploration
make case-check CASE=cases/huawei-cup-2026-a STAGE=model_selection
make case-check CASE=cases/huawei-cup-2026-a STAGE=paper_claims
make final-check CASE=cases/huawei-cup-2026-a
```

探索阶段的 `REMINDER` 返回成功，允许继续建模；准备正式路线时未确认路由会 `BLOCK`；
论文强主张阶段要求有效 C3；最终检查还要求人工决定、规格通过、claim_map 可追溯，
并执行根论文 PDF QA。检查器只确认可见记录存在，不替代题意、数学或语义审核。

仓库模板是团队内部工程模板，不是当届官方提交模板。比赛开始后必须重新核对官方封面、
摘要页、匿名要求、字体、页数、文件命名和 AI 使用规定。

## 5. 案例目录说明

```text
cases/<case_id>/
├── input/                    题面、附件和字段说明（只读）
├── case_brief.md             队员唯一需要填的启动文件
├── checkpoint.yaml           路由确认、审核状态与风险标志
├── models/
│   ├── candidates.md         候选路线池
│   └── comparison.md         七维度评估与当前取舍
├── specs/                    SPEC-*.md 实现规格；SPEC-*.questions.md 回问
├── experiments/
│   ├── board.md              实验队列、结果和下一步
│   ├── code/python/          Python 实现与绘图
│   ├── code/matlab/          MATLAB 实现与绘图
│   └── outputs/
│       ├── data/             结果 CSV / JSON
│       ├── figures/          每图 PDF + PNG，配 manifest.md
│       ├── checks/           复算报告 <EXP-ID>.json
│       └── logs/
├── decisions.md              路线与强结论的人工决定
├── reviews/                  C1/C2/C3 报告；packets/ 存生成的审核包
└── paper/claim_map.md        论文数字溯源表
```

三个不绑定历年题目的演示位于 `cases/examples/`。

## 6. 仓库目录说明

```text
agent/
├── AGENTS.md                 Codex 自动读取的项目规则与三角色索引
├── agent.md                  三角色共同执行协议
├── REVIEWER.md               Independent Reviewer 独立审核边界
├── prompts/
│   ├── README.md             三角色接力图与触发语
│   ├── modeler.md            建模手
│   ├── engineer.md           编程手
│   ├── writer.md             写作手
│   ├── contracts/            SPEC / 结果回传 / 回问 三份契约
│   └── reviewer/             C1/C2/C3 审核提示词
├── .agents/skills/           三个与角色一一对应的 Skill
├── cases/                    真实案例与通用演示
├── templates/                案例、规格、实验、审核包、溯源表模板
├── scripts/                  初始化、结构检查、规格检查、复算与审核包生成
├── paper/                    XeLaTeX 论文工程
├── writing/                  论文内容、语言、图表和格式规范
├── protocol/                 竞赛流程与团队协作说明
├── docs/                     当前架构和文档索引
└── tests/                    通用合成测试
```

外部 Planner/Executor 协作控制台不属于比赛运行时，也不放入本仓库。

## 7. 检查命令

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
.venv/bin/python scripts/check_spec.py --case-dir cases/<case_id>
```

这些脚本检查明显缺失、重复、数据泄漏、约束和目标值，不判断模型在科学意义上是否
正确。案例检查还会提醒路由确认、C1/C2/C3、规格缺失、失败模式和人工决定；方法论差异
和强结论仍需三个角色、Independent Reviewer 与队员共同判断。

## 8. 团队 Git 协作

推荐分支：

- `model/<任务>`：模型、公式、规格；
- `analysis/<任务>`：代码、实验和图表；
- `paper/<章节>`：论文内容和排版；
- `review/<编号>`：Independent Reviewer 意见处理和复算。

每次提交写清改变内容、实验结果和下一步。同一份 `.tex` 或 Markdown 文件同一时间只
安排一个主要写入者，减少比赛期间的合并冲突。

## 9. 常见问题

### Codex 没有读取项目规则

确认任务的项目根目录是本仓库，而不是上级「数学建模」目录；然后新建任务。根目录
`AGENTS.md` 在新会话开始时加载。

### Skill 没有显示

确认 `.agents/skills/<skill-name>/SKILL.md` 存在。修改 Skill 后新建任务；也可以在提示
中明确写 `$competition-modeling`、`$competition-engineering` 或
`$competition-paper-writing`。

### 三个会话切来切去太麻烦

`prompts/README.md` 里有可直接复制的一句话触发语。合成一个会话会更省事，但会失去
忠实性和上下文纯净度 —— 理由见 `agent.md`。

### 编程手说规格里没写，但我觉得很明显

「明显」正是要写进规格的东西。下游从不回问，通常说明它在替上游做建模决定，比回问
太多危险得多。

### 还不知道题型

用 `insufficient_information` 创建案例，让建模手先读题面后再更新路由。

### Independent Reviewer 是否需要 API

不需要。当前采用人工复制精简审核包的方式，不自动调用任何模型 API，也不需要密钥。

### 最终 PDF 是否可以直接提交

不可以直接假定。CI PDF 只用于预览；当届官方格式和最终文件必须由队员人工确认。

## 10. 进一步阅读

- [三角色入口与触发语](prompts/README.md)
- [交接契约](prompts/contracts/README.md)
- [当前架构](docs/architecture.md)
- [文档索引](docs/README.md)
- [竞赛流程](protocol/competition-workflow.md)
- [团队协作](protocol/team-collaboration.md)
- [论文系统](writing/README.md)
- [论文工程](paper/README.md)
