# 当前架构

## 目标

工作台在四天内帮助团队扩大方法空间、用低成本实验筛选路线、纠正关键错误，并把稳定
结果及时写入论文。工程质量体现在模型、算法、实验和论文的一致性。

## 三个生产角色 + 横向审核与校验

```text
建模手 Modeler ──SPEC──▶ 编程手 Engineer ──结果+图──▶ 写作手 Writer
     ▲                        │                        │
     └──── questions ◀────────┴──── questions ◀────────┘

        Independent Reviewer C1 / C2 / C3（节点自动提醒，横切三者）
        确定性脚本（规格、结构、切分、约束、目标值、LaTeX、PDF）
        人类队员（关键假设、路线取舍、比赛策略、官方规则、最终提交）
```

| 主体 | 主要职责 |
|---|---|
| 建模手 | 题意重构、头脑风暴、路线评估、probe 轻测试、实现规格 |
| 编程手 | 忠实实现（Python / MATLAB）、实验、独立复算、图表 |
| 写作手 | 论文章节、数字溯源、表述强度复核、润色 |
| Independent Reviewer（横向机制，非生产角色） | C1 题意、C2 架构、C3 结果与强结论挑战 |
| 确定性脚本 | 规格、结构、切分、泄漏、约束、目标值、LaTeX 和 PDF 检查 |
| 人类队员 | 无法消除的官方硬冲突、授权扩张、官方规则和最终提交 |

## 为什么角色隔离但复用会话

Modeler、Engineer、Writer 各复用一个持续会话；C1/C2/C3 各用一个新的 Reviewer 会话。
这样既保留正式实现与审核的视角差异，又避免每阶段重复加载全部协议。

同一会话里，「我知道上游想要什么」会悄悄替代「契约里写了什么」，规格逐渐变成摆设，
到第三天回头看，实现和论文里的模型已经对不上。分开之后，编程手物理上看不到建模手的
推理，规格没写的就是没定的，只能回问。

第二个收益是上下文纯净度：四天赛程的会话很长，早期约束容易被后期细节挤掉。

## 三个交接面

| 契约 | 载体 | 上游 → 下游 |
|---|---|---|
| SPEC | `cases/<id>/specs/SPEC-*.md` | 建模手 → 编程手 |
| 结果回传 | `experiments/outputs/` + `figures/manifest.md` + `board.md` | 编程手 → 写作手 |
| 阻塞回问 | 同一 SPEC/实验板；仅人工专属问题才建 `.questions.md` | 下游 → 上游或人工 |

三条总纪律：下游不读上游隐藏推理；可逆实现选择由当前角色直接补齐并显式记录；只有
官方硬冲突、授权扩张和最终提交回人工。规则在 `prompts/contracts/`。

## 运行结构

`AGENTS.md` 是 Codex 自动读取的项目规则；`.agents/skills/` 提供三个与角色一一对应、
按任务加载的方法库；`prompts/` 保存角色提示词和契约；`cases/` 保存每道题的状态；
`paper/` 与 `writing/` 负责论文。

```text
AGENTS.md ── agent.md（三角色共同协议）
  ├─ prompts/{modeler,engineer,writer}.md + prompts/contracts/
  ├─ .agents/skills/competition-modeling
  ├─ .agents/skills/competition-engineering
  ├─ .agents/skills/competition-paper-writing
  ├─ cases/<case_id>/
  ├─ prompts/reviewer/C1-C3 + REVIEWER.md
  └─ paper/ + writing/
```

## 自动化的确定性风险链路

复算报告 `experiments/outputs/checks/<EXP-ID>.json` 由
`scripts/model_checks.py:write_check_report` 生成，`scripts/check_case.py` 自动读取
失败项并点亮 `checkpoint.yaml` 对应的确定性风险标志。

这条链路刻意做成自动的：靠人手在比赛期间记得把 `infeasible`、`leakage` 之类的标志改成
`true`，实际上等于这些阻断永远不会触发。人手填写的值仍然保留为覆盖手段。

## 证据闭环的三处检查

工作台不承担防伪职责 —— 它防的是**论文引用不存在或已经失败的证据**：

| 检查 | 防什么 | 阶段行为 |
|---|---|---|
| probe → full 闭环 | full 规格自报 probe 通过，但探针规格不存在、实验不在板上、状态不是 done，或记录里没有明确 PASS 判定 | 早期提醒，强结论阶段阻断 |
| claim_map 证据存在性 | 论文数字指向不存在、越界、读不出或属于别的实验的证据 | 已写下的主张引用无效证据时，`paper_claims` 与 `final` **均阻断**；论文骨架尚未建立只在 `paper_claims` 提醒 |
| 复算报告可读性 | 损坏的 JSON 被当成「检查通过」 | 早期提醒，强结论阶段阻断 |

三者都只做结构、存在性和已记录状态校验，不做数值证明，也不做文件哈希。

路线卡、七维度比较和 Champion/Challenger 统一保存在 `models/candidates.md`，不再维护
第二份 `models/comparison.md`。

## 设计原则

- 先发散出足够多的想法，再用固定维度收敛；
- 先用 probe 轻测试证伪，再投入完整实现；
- 先运行便宜、可解释、可手算的实验；
- 保留 Champion 和不同方法族的 Challenger；
- 上下游通过落盘契约交接；普通可逆选择由当前角色直接完成并显式记录；
- 数值检查使用独立计算，语义判断交给模型与队员；
- Independent Reviewer 横切三个角色，只在关键节点挑战，不产出主解也不接管环节；
- 论文与实验同步，摘要、结论和核心图表的关键数字可追溯到实验和数据文件；
- 当届官方规则在比赛开始后重新核对。

## 能力边界

工作台不包含具体历年题目的标准答案，不自动调用任何审核模型 API，也不能替代队员理解
题面或确认最终提交。

已知的确定性检查边界：

- `scripts/check_spec.py` 只检查五段 Full SPEC、实验板上的 Probe PASS，以及 Reviewer
  Probe 影响路线时是否在冻结前复算。**它判断不了建模是否正确或判据是否合理。**
- `scripts/model_pool.py` 检查空字段、非法状态、重复路线 ID 和明显重复的方法族，但
  MIP 的 arc-flow、path-flow、time-indexed 是否构成独立路线，仍由 C2 与队员判断。
- `scripts/check_case.py` 只确认可见记录存在并互相指得通，不做题意、数学或语义审核。
  它能发现「claim 指向的文件不存在」，发现不了「文件里的数字是错的」。
- `scripts/make_review_packet.py` 生成一张不内嵌原文的审核卡，列出获准材料；C1 会读取
  `data_root:` 或历史散文路径，并扫描数据根及父目录的直接说明文件。卡片完整不表示模型
  正确，Reviewer 仍需按 C1/C2/C3 视角挑战。
- 证据路径解析集中在 `scripts/case_paths.py`：含 `..` 或绝对路径的引用直接拒绝而不
  规范化，解析走真实路径（跟随符号链接）并必须落在案例目录内，且每类证据只能落在
  它自己的目录（数据在 `outputs/data/`、复算报告在 `outputs/checks/`）。
- `scripts/router.py` 是关键词种类计数，只作交叉参考。正式路由由 Modeler 阅读完整题面
  决定，并在 C1 被独立挑战；不再要求队员对普通路由机械签字。
- MATLAB 无法在 CI 或阶段检查中运行，因此关键结论的复算必须有 Python 版本。
