# 当前架构

## 目标

工作台在四天内帮助团队扩大方法空间、用低成本实验筛选路线、纠正关键错误，并把稳定
结果及时写入论文。工程质量体现在模型、算法、实验和论文的一致性。

## 三个生产角色 + 横向审核与校验

```text
建模手 Modeler ──SPEC──▶ 编程手 Engineer ──结果+图──▶ 写作手 Writer
     ▲                        │                        │
     └──── questions ◀────────┴──── questions ◀────────┘

        Independent Reviewer C1 / C2 / C3（人工触发，横切三者）
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
| 人类队员 | 关键假设、路线取舍、比赛策略、官方规则和最终提交 |

## 为什么拆成独立会话

拆分的目的是让**忠实实现成为结构保证而不是自觉**。

同一会话里，「我知道上游想要什么」会悄悄替代「契约里写了什么」，规格逐渐变成摆设，
到第三天回头看，实现和论文里的模型已经对不上。分开之后，编程手物理上看不到建模手的
推理，规格没写的就是没定的，只能回问。

第二个收益是上下文纯净度：四天赛程的会话很长，早期约束容易被后期细节挤掉。

## 三份契约

| 契约 | 载体 | 上游 → 下游 |
|---|---|---|
| SPEC | `cases/<id>/specs/SPEC-*.md` | 建模手 → 编程手 |
| 结果回传 | `experiments/outputs/` + `figures/manifest.md` + `board.md` | 编程手 → 写作手 |
| 回问 | `specs/SPEC-*.questions.md` | 下游 → 上游 |

三条总纪律：下游不读上游会话；契约没写到的建模决策一律回问；下游不得反向修改上游
产物。规则在 `prompts/contracts/`，字段模板在 `templates/`。

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

`models/candidates.md` 的状态字段是路线取舍的**唯一权威**；`models/comparison.md` 的
散文复述与之不一致时给出提醒（这个错误在搭建示例案例时真实发生过一次）。

## 设计原则

- 先发散出足够多的想法，再用固定维度收敛；
- 先用 probe 轻测试证伪，再投入完整实现；
- 先运行便宜、可解释、可手算的实验；
- 保留 Champion 和不同方法族的 Challenger；
- 上下游只通过落盘契约交接，建模决策不得由下游代做；
- 数值检查使用独立计算，语义判断交给模型与队员；
- Independent Reviewer 横切三个角色，只在关键节点挑战，不产出主解也不接管环节；
- 论文与实验同步，每个数字可追溯到实验和数据文件；
- 当届官方规则在比赛开始后重新核对。

## 能力边界

工作台不包含具体历年题目的标准答案，不自动调用任何审核模型 API，也不能替代队员理解
题面或确认最终提交。

已知的确定性检查边界：

- `scripts/check_spec.py` 只检查规格字段齐全、状态合法、判据含数值、full 规格的输出
  契约与复算要求非空，以及 probe 闭环字段的取值合法。**它判断不了建模是否正确，
  也判断不了判据是否合理，更判断不了探针本身设计得好不好。**
- `scripts/model_pool.py` 检查空字段、非法状态、重复路线 ID 和明显重复的方法族，但
  MIP 的 arc-flow、path-flow、time-indexed 是否构成独立路线，仍由 C2 与队员判断。
- `scripts/check_case.py` 只确认可见记录存在并互相指得通，不做题意、数学或语义审核。
  它能发现「claim 指向的文件不存在」，发现不了「文件里的数字是错的」。
- `scripts/make_review_packet.py` 摘录可见证据并标注 `packet_complete`。
  `packet_complete: true` 只表示**该节点要求的文件存在且与各条 Claim 对应**，
  不表示证据充分、模型正确或审核通过。C1 的题面依据靠文件名或 `input/README.md` 的
  显式声明识别 —— 一份数据 CSV 不会被当成题面；C3 的证据逐条按 Claim 自己填写的引用
  收集，无关实验的复算报告不能填补缺口。
- 证据路径解析集中在 `scripts/case_paths.py`：含 `..` 或绝对路径的引用直接拒绝而不
  规范化，解析走真实路径（跟随符号链接）并必须落在案例目录内，且每类证据只能落在
  它自己的目录（数据在 `outputs/data/`、复算报告在 `outputs/checks/`）。
- `scripts/router.py` 是关键词种类计数。三个词表有重叠（「分配」「资源」同时出现在
  优化与决策表），长题面必然饱和，实际结果多为 `hybrid`。**它是交叉参考，不是路由
  决定**；路由由建模手读题面判断，并由队员在 `checkpoint.yaml` 确认一次。
- MATLAB 无法在 CI 或阶段检查中运行，因此关键结论的复算必须有 Python 版本。
