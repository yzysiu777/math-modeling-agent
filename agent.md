# 三角色共同执行协议

本文件是三个角色**共同遵守**的规则。角色专属的执行细节在各自提示词里，不在这里
重复，避免两处指令冲突：

- 建模手：`prompts/modeler.md`
- 编程手：`prompts/engineer.md`
- 写作手：`prompts/writer.md`
- 独立审核者：`REVIEWER.md`、`prompts/reviewer/`

## 为什么分三个会话

同一个会话里做完全部工作会更省事，但会失去两样东西：

1. **忠实性**。「我知道上游想要什么」会悄悄替代「契约里写了什么」，规格逐渐变成
   摆设。等到第三天回头看，实现和论文里的模型已经对不上了。
2. **上下文纯净度**。四天赛程的会话会变得很长，早期约束容易被后期细节挤掉。分角色
   天然限定了每个会话要装的东西。

代价是每次切换要开新任务、粘一句话（见 `prompts/README.md`）。这个代价是值得的。

## 交接纪律

三条总纪律，详见 `prompts/contracts/README.md`：

**一、下游不读上游的会话。** 编程手不看建模手的推理，写作手不看编程手的调试过程。
理由不是保密，是防止下游用「我猜上游是这个意思」替代「契约里写了什么」。

**二、契约没写到的建模决策，下游一律回问，不得自行发明。** 判断标准只有一条：这个
决定会不会改变目标、约束、指标定义、数据口径或结论强度？会 → 建模决策 → 回问并停止
该条路线；不会 → 工程决策 → 自己定，继续做。分不清就当成建模决策回问。

**三、下游不得反向修改上游产物。** 编程手不改 `models/` 下的路线定义，写作手不改
`outputs/data/` 下的任何数值。要改，回问上游。

## 主动执行边界

三个角色都主动完成范围明确、可逆、可验证的工作，不把等待人工确认当作默认状态。

以下必须交给队员决定：

- 题意关键歧义会改变目标或硬约束；
- 最终路线取舍主要取决于比赛策略而非数值；
- Independent Reviewer 发现的架构风险；
- 强结论是否值得写入摘要或结论；
- 当届官方格式、AI 声明和最终提交文件。

其余明确、可逆、可验证的任务主动完成。

## 证据表达

严格区分四档强度，任何角色都不得越档表述：

| 强度 | 什么时候可以用 |
|---|---|
| 可行解 | 满足全部建模约束 |
| 当前算法最好解 | 在本文比较的方法中表现最好 |
| 给定假设下最优 | 在明确写出的假设与模型下取得最优，须写明假设 |
| 全局最优 | 有精确求解器的最优性证明，或规模允许穷举 |

同样严格区分关联、预测贡献和因果。

任何未验证的内容标注为待核对，不写成确定事实。**脚本通过只代表相应检查已通过，
不代表整个模型已经正确。**

## 确定性检查与风险链路

复算结果写 `experiments/outputs/checks/<EXP-ID>.json`，由
`scripts/model_checks.py:write_check_report` 生成。`scripts/check_case.py` 自动读取
其中的失败项并点亮 `checkpoint.yaml` 的确定性风险标志。

**这条链路是自动的，不依赖有人记得去改控制文件。** 因此复算失败必须照实写入 ——
为了让检查变绿而省略、调大容差或换实例，等于关掉了整套安全网。

## 阶段检查

四个阶段是同一条主线上的检查时点，不是四套运行模式：

| 时点 | 命令 | 行为 |
|---|---|---|
| 题意与便宜实验 | `make case-check CASE=... STAGE=exploration` | 只提醒，不阻止探索 |
| 冻结 Champion 前 | `make case-check CASE=... STAGE=model_selection` | 未确认路由阻断；缺 C2、缺规格、重复失败提醒 |
| 写摘要/结论前 | `make case-check CASE=... STAGE=paper_claims` | 缺 C3 或确定性严重错误阻断 |
| 最终提交前 | `make final-check CASE=...` | 另查规格、人工决定、claim_map 和 LaTeX/PDF QA |

`REMINDER` 不阻止继续工作。单次实验失败只记录和提醒；重复失败、性能担忧、不可行、
目标复算不一致、泄漏或切分重叠要说明责任人和建议 C2/C3。

**不用关键词猜测失败原因或效果好坏**；依据实验板和已实际运行的确定性检查记录提醒。

## Independent Reviewer 交接

只在 C1（题意）、C2（模型架构）和 C3（结果/强结论）交接。用
`make review-packet CASE=... NODE=C2` 生成草稿，补完最担心的问题和 3–5 个待答问题，
再由队员复制到全新会话。

审核包必须注明 `reviewer_provider`、`reviewer_model`、`review_session: fresh`、
`saw_main_conversation: false` 和 `critical_node`。审核者可以是 Gemini、Grok、隔离的
新 Codex 任务、其他模型或人类专家；provider 值允许扩展，不构成厂商白名单。不能把
同厂商不同模型本身写成完整独立性，也不能传递主解完整聊天或隐藏推理。

收到报告后把队员的「接受/拒绝/延期及原因」写入 `decisions.md`，再实施修改和针对性
复算。

## 案例目录

```text
cases/<case_id>/
├── input/                    题面、附件和字段说明（只读）
├── case_brief.md             队员唯一需要填的启动文件
├── checkpoint.yaml           路由确认、审核状态与风险标志
├── models/                   candidates.md、comparison.md
├── specs/                    SPEC-*.md 与 SPEC-*.questions.md
├── experiments/
│   ├── board.md
│   ├── code/{python,matlab}/
│   └── outputs/{data,figures,checks,logs}/
├── decisions.md              影响路线或强结论的人工决定
├── reviews/{,packets/}       C1/C2/C3 报告与生成的审核包
└── paper/claim_map.md        论文数字溯源表
```
