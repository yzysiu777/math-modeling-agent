# 华为杯数学建模 Agent 工作台

这是面向四天竞赛的轻量工作台，支持运筹优化、数据分析和混合建模。它依靠强模型快速
头脑风暴、试跑和收敛，只保留少量真正有用的纠偏与复算。

## 快速启用

在 Codex 中打开：

```text
/Users/lambency/Desktop/研 0 /数学建模/agent
```

新建 Orchestrator 主任务时选择 `gpt-5.6-sol`，推理强度选择 `high`。后续生产 Agent 由
Orchestrator 使用同一配置创建；如果该配置不可用，不要自动换模型。

首次准备：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
```

新建案例：

```bash
.venv/bin/python scripts/create_case.py --case-id huawei-cup-2026-a --route insufficient_information
```

把原题和小型说明文件放入案例 `input/`，大数据保持原位只读，并在
`input/README.md` 重复写入：

```text
data_root: /absolute/path/to/allowed/data
```

然后在主 Codex 任务中发送：

```text
读取 AGENTS.md，接管 cases/<case_id>。生产角色统一使用 gpt-5.6-sol、high，并按七阶段
连续推进；复用 Modeler、Engineer、Writer 会话。C1/C2/C3 只生成审核卡和提示词，由我
人工调用外部 Claude。每阶段更新 reports/stage-0N.md，并明确人工核验项和下一 Agent。
```

## 一题的会话

- 一个持续 Orchestrator 主任务；
- 一个持续 Modeler 任务，负责阶段 1–4，并可直接跑 Probe；
- 一个持续 Engineer 任务，负责正式实现、实验、复算和出图；
- 一个持续 Writer 任务，从稳定 Baseline 开始同步论文；
- C1、C2、C3 各由人工打开一个新的外部 Claude 会话。

四个生产角色统一使用 `gpt-5.6-sol`、`high`。Orchestrator 可以调度生产角色，但不得启动
Claude Reviewer。同一角色跨阶段继续原任务，不重复加载协议；角色之间不传隐藏推理。

## 七阶段

1. 启动与题意重构 → C1；
2. 发散、七维度比较和路线收敛；
3. Probe；
4. Full SPEC、Baseline 和赛马 → C2；
5. Champion 复算和出图；
6. 论文、关键数字溯源 → C3；
7. 最终 LaTeX、PDF 和官方规则检查。

详细机制见 `protocol/competition-workflow.md`。

## 审核卡

```bash
make review-packet CASE=cases/<case_id> NODE=C1
```

命令生成一张位于 `reviews/C1_*.md` 的轻量审核卡。主 Agent 随后输出可复制提示词，由队员
人工调用新的外部 Claude。卡中不复制题面全文，只列允许读取或上传的文件。Claude 在同一
张卡给出 `GO`、`GO_WITH_FIXES` 或 `STOP`；网页版无法写本地文件时，由队员原样转交输出。

采纳意见直接实施；拒绝 finding 时由原 Reviewer 在同一卡回签一次。Reviewer Probe 若影响
Full SPEC 或 Champion，必须在冻结前复算。

## 案例中真正需要维护的文件

```text
case_brief.md                 题意、数据契约和官方歧义
checkpoint.yaml               当前阶段、路由、审核状态和确定性风险
models/candidates.md          路线、七维度比较、Champion/Challenger
experiments/board.md          Probe 与正式实验
specs/SPEC-*.md               进入正式赛马的五段 Full SPEC
reviews/C1_*.md ...           单卡式审核记录
reports/stage-01.md ...       七阶段汇报、人工核验清单和下一 Agent
paper/claim_map.md            摘要、结论和核心图表的关键 Claim
decisions.md                  仅人工专属决定
```

Probe 不建立独立 SPEC；一般回问不建立 questions 文件；不再维护单独 comparison、
packet、阶段交接或逐条审核决议副本。

## 每阶段如何看进度

每个生产 Agent 按 `agent.md` 输出统一 Agent 回报卡。Orchestrator 是 `reports/` 的唯一写入者，
每阶段更新对应文件，明确：当前完成了什么、人工应核验什么、下一步由哪个 Agent做什么，
以及需要人工调用 Claude 时的可复制提示词。

阶段 1–6 的报告是异步核验材料，AI 不因你尚未阅读而停工。发现漏洞时回复：

```text
退回阶段 S4：目标函数遗漏了等待成本，请重新检查 Champion 与 C2 结论。
```

Orchestrator 只返工受影响部分并更新原阶段报告。阶段 7 的最终 PDF 与实际提交必须等待人工。

## 人工调用 Claude

到 C1/C2/C3 时，主 Agent 会给出 `MANUAL_REVIEWER_LAUNCH` 和完整提示词。请新建外部
Claude 会话，把审核卡及其允许材料交给它。完成后回复：

```text
C2 已完成。审核卡：/absolute/path/to/reviews/C2_....md
```

Claude 的实际型号写入 `reviewer_model`；不要填成生产模型，也不要让主 Agent 自动替代。

## 常用命令

```bash
make spec-check CASE=cases/<case_id>
make case-check CASE=cases/<case_id> STAGE=exploration
make review-packet CASE=cases/<case_id> NODE=C2
make paper-ci
make qa
make final-check CASE=cases/<case_id>
```

探索检查以提醒为主。最终检查仍会拦截真实不可行、目标复算错误、数据泄漏、核心 Claim
证据缺失和 LaTeX/PDF 错误。

## 模式说明

没有“比赛模式/研究模式”开关，也没有两套配置。本仓库当前运行时就是比赛流程。
需要更深入时，在对应阶段增加路线、实验或稳健性分析；不要切换流水线。

当前模板和历史官方文件只能作为参考。比赛开始后必须重新核对当届官方封面、匿名要求、
字体、页数、文件命名、AI 使用规则和最终提交说明。
