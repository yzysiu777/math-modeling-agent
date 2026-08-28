# 数学建模 Agent 工作台

这是一个面向华为杯四天赛程的轻量数学建模工作台，服务于三类题目：

- 运筹优化：规划、网络、路径、调度、资源分配、多目标、鲁棒与随机优化；
- 数据分析：清洗、统计推断、预测、分类、聚类、时序和可解释性；
- 混合建模：数据分析产生参数、预测或场景，优化模型完成决策。

核心目标是快速产生真正不同的候选路线，用低成本实验进行赛马，在关键节点让
Claude 做独立挑战，并同步推进高质量 LaTeX 论文。Codex 负责主线执行，Claude
由队员手动触发，队员保留模型取舍和最终提交决定。

## 十分钟开始

1. 阅读 [AGENTS.md](AGENTS.md) 和 [agent.md](agent.md)，了解最少但必须遵守的规则。
2. 创建案例目录：

   ```bash
   python3 scripts/create_case.py --case-id demo-01 --route optimization
   ```

3. 只填写 `cases/demo-01/case_brief.md`：子问题、输入输出、目标、硬约束、单位、
   指标、歧义和当前假设。其余文件先由 Agent 生成草稿。
4. 让 Codex 读取题面与附件，建立至少三条方法论不同的路线，先写入
   `models/candidates.md`，再把最便宜的区分实验放入 `experiments/board.md`。
5. 统一切分、统一指标，先跑可解释 baseline；保留一个 Champion 和一个方法论
   不同的 Challenger。每次取舍在 `decisions.md` 用一行记录理由。
6. 在题意、模型架构、主要结果三个关键节点，复制对应的
   `prompts/claude/C1_problem_challenge.md`、C2 或 C3 到新的 Claude 会话。
7. 从实验结果同步更新 `paper/` 和案例的 `paper/` 说明，最后运行：

   ```bash
   PYTHON=.venv/bin/python make validate
   PYTHON=.venv/bin/python make test
   make paper-ci
   make qa
   ```

## 唯一工作流

```text
题意重构
  -> 多路线头脑风暴
  -> 候选模型池
  -> 快速 baseline
  -> 小实验赛马
  -> Champion / Challenger
  -> Claude C1/C2/C3 关键挑战
  -> 深化模型与稳健性
  -> 论文同步写作
  -> 数值、引用、格式和 PDF 检查
```

详细规则见 [protocol/competition-workflow.md](protocol/competition-workflow.md)。
普通实验和论文小修改直接在案例目录及对应 Git 分支中推进，不需要先填一套复杂
的开发表单。只有会显著改变题意、目标、约束、比赛策略或最终提交的决定才停下来
请队员确认。

## 目录结构

```text
agent/
├── README.md                         十分钟入口
├── AGENTS.md                         少量硬规则
├── agent.md                          Codex 主 Agent 协议
├── CLAUDE.md                         Claude C1/C2/C3 协议
├── protocol/                         唯一竞赛流程与协作约定
├── roles/                            建模、数据、论文角色卡
├── prompts/                          启动和关键挑战提示词
├── skills/                           可携带的工业级方法 Skill
├── templates/                        案例、模型、实验和论文模板
├── scripts/                          路由、案例初始化、实验与数值检查
├── cases/examples/                   三个通用演示
├── paper/                            XeLaTeX 团队论文工程
├── writing/                          国奖语言、图表、引用和 AI 记录
└── audit/                            历史架构资料，仅供回看，不参与运行时
```

案例使用以下简洁结构：

```text
cases/<case_id>/
├── input/                    题面和附件，只读
├── case_brief.md             唯一启动表单
├── models/
│   ├── candidates.md         候选路线池
│   └── comparison.md         公平比较与取舍
├── experiments/
│   ├── board.md              实验队列
│   ├── code/                 可运行代码
│   └── outputs/              关键输出
├── decisions.md              保留、淘汰和人工决定
├── reviews/                  C1/C2/C3 报告
└── paper/                    案例论文入口或说明
```

外部 Planner/Executor 控制面不属于本仓库，也不会被案例运行时读取。

## 三类能力

`skills/industrial-mathematical-modeling/` 给出运筹、数据分析和混合题的检查重点；
`skills/model-race/` 给出候选路线、实验信息价值和 Champion/Challenger 的操作法。
`scripts/model_checks.py` 提供可复用的约束可行性、目标复算、数据切分/泄漏和模型
比较函数。它们是辅助证据，不替代题面理解和队员判断。

## 论文工程

论文从 baseline 开始同步维护：问题重述、符号、模型、实验、图表、结论和引用
保持可追踪。`paper/` 使用 XeLaTeX、ctex、biblatex/biber 和统一 `.bib`；历史
官方文件只作参考，比赛日必须重新确认当届格式、匿名规则和 AI 使用规定。

## Git 协作

主线使用 `main`，个人修改使用 `model/<任务>`、`analysis/<任务>`、`paper/<章节>`
或 `review/<编号>`。每次提交说明“方法、数据、实验或论文发生了什么”，保留被
淘汰路线和失败实验的简短记录。外部开发任务的交接文件只在协作控制面保存。
