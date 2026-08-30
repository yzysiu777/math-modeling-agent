# 华为杯数学建模 Agent 工作台

这是面向四天竞赛的轻量工作台，支持运筹优化、数据分析和混合建模。它依靠强模型快速
头脑风暴、试跑和收敛，只保留少量真正有用的纠偏与复算。

## 快速启用

在 Codex 中打开：

```text
/Users/lambency/Desktop/研 0 /数学建模/agent
```

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
读取 AGENTS.md，接管 cases/<case_id>。按七阶段连续推进；复用 Modeler、Engineer、
Writer 会话，并在 C1/C2/C3 自动启动新的 Independent Reviewer。只有命中人工专属边界
或最终提交时再问我。
```

## 一题的会话

- 一个持续 Orchestrator 主任务；
- 一个持续 Modeler 任务，负责阶段 1–4，并可直接跑 Probe；
- 一个持续 Engineer 任务，负责正式实现、实验、复算和出图；
- 一个持续 Writer 任务，从稳定 Baseline 开始同步论文；
- C1、C2、C3 各一个新 Reviewer 任务。

同一角色跨阶段继续原任务，不重复加载协议。生产角色之间只传案例文件，不传隐藏推理。

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

命令生成一张位于 `reviews/C1_*.md` 的轻量审核卡。卡中不复制题面全文，只列允许读取
或上传的文件。Reviewer 在同一张卡给出 `GO`、`GO_WITH_FIXES` 或 `STOP`。

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
paper/claim_map.md            摘要、结论和核心图表的关键 Claim
decisions.md                  仅人工专属决定
```

Probe 不建立独立 SPEC；一般回问不建立 questions 文件；不再维护单独 comparison、
packet、阶段交接或逐条审核决议副本。

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
