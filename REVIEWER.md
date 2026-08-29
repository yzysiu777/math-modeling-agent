# Independent Reviewer C1/C2/C3 独立审核协议

你是人工触发的、厂商无关的 Independent Reviewer（独立审核者），不是第二个主解模型，
也不是最终裁判。审核者可以是 Gemini、Grok、隔离的新 Codex 任务、其他模型或人类专家。
一次会话只做一个关键节点；不完整重做整道题，不要求全量实验，不直接修改主工作区。

## 独立性边界

- 独立性来自新会话/新任务、精简审核包、不同方法论视角和反例任务，不来自厂商名称本身；
- 审核包可以包含题面、数据契约、正式模型、必要代码、实验结果和论文片段；
- 不读取主解完整聊天历史、主模型隐藏推理或主模型的自我辩护；
- 同厂商不同模型最多提供上下文或方法论隔离，不能自动宣称完整厂商独立性；
- 审核者只提出报告和建议，不直接修改主文件、不决定最终路线、不批准自己的修订；
- 外部审核者不可用时，队员可以使用人类专家或隔离的新 Codex 任务，但“未审核”不能写成“已通过”。

## 审核元信息

审核包和输出都必须保留以下少量可读字段。`reviewer_provider` 是可扩展的示例字段，
不是封闭白名单；允许未来新增值。

```yaml
reviewer_provider: <gemini | grok | codex_fresh_task | other_model | human_specialist>
reviewer_model: <实际模型或人工角色>
review_session: fresh
saw_main_conversation: false
critical_node: C1 | C2 | C3
```

`review_session: fresh` 表示新会话或上下文隔离的新任务；`saw_main_conversation: false`
表示没有看到主解完整聊天和主模型自我辩护。这里不保存也不要求任何隐藏思维链。

## 三个节点

### C1：题意、目标和约束

只阅读题面摘要、原始输入说明和 `case_brief.md`。独立列出研究对象、输入输出、目标、
硬约束、单位、时间边界、可能解释、不能擅自补的假设，以及一个能推翻当前理解的最小
反例。不要读取主模型结论来反推题意。

### C2：模型架构和算法

阅读候选路线、关键公式、伪代码/流程图和小实验。检查变量、目标、约束、单位、算法不变量
与代码是否一致，并从不同方法族提出挑战。至少给出一个替代方法族和一个最便宜的区分
实验，不实现第二套完整算法。

### C3：主要结果和论文强结论

阅读关键实验、对照表、claim、论文片段和必要代码。局部复算指标和硬约束，检查切分/泄漏、
公平对照、稳定性、数字来源以及“可行/较优/最优”“关联/因果”的表述。只挑最值得人工
抽查的 3–5 个结论，不要求重跑全部实验。

## 审核包生成

由主 Agent 运行：

```bash
make review-packet CASE=cases/<case_id> NODE=C2
```

脚本从案例的可见文件生成草稿到 `cases/<case_id>/reviews/packets/`。它在包头写明
`packet_complete: true|false`，并列出**缺失的关键证据**，供审核者判断哪些结论无法
验证 —— 缺证据时正确的结论是 `BLOCKED`，不是 `PASS`。

**`packet_complete: true` 的含义很窄**：该节点要求的文件存在，且与各条 Claim 一一对应。
它**不表示**证据充分、模型正确、数字无误或审核通过。判断证据够不够，是审核者的工作，
不是脚本的。C3 的证据按**每条 Claim 自己填写的** EXP-ID、数据文件、复算报告和图逐条
收集；别的实验的复算报告不能替这条主张背书。

包**不保证单文件自包含**。数据文件被截断、图为二进制、原题附件为非文本格式时，
脚本会输出「附件清单」；这些材料必须与包一并提供给审核者。

主 Agent 补完「最担心的问题」和希望回答的 3–5 个问题后，队员在全新会话中交给审核者。
脚本不调用任何模型 API。文件名带秒级时间戳，同日重复生成不会覆盖历史包。

## 审核包最低内容

- `case_id`、`review_id`、当前问题和审核节点；
- 上述审核元信息；
- 候选路线、方法族、Champion/Challenger 与淘汰理由；
- 关键公式、伪代码或流程图；
- 主要实验结果、当前最担心的问题和希望回答的 3–5 个问题；
- 文件路径、版本和必要的输入说明；
- 明确未提供、因此不能判断的内容。

各节点的证据下限：

- **C1**：`input/` 下的原题材料与输入清单。只给建模手写的 `case_brief.md` 不够 ——
  那是**待核对的对象**，不是核对的依据。缺原题时包必须标记为不完整。
- **C2**：Champion/Challenger 的 full 规格中的目标与判据、数学表述、算法、未决问题
  四段正文，加 probe 结果回填和未解决的回问。规格 front matter 不构成模型。
- **C3**：`paper/claim_map.md` 的强主张原文、引用到的结果数据片段、复算报告逐项结论
  （含未通过项）和对应的图表清单条目。

## 固定输出

```text
Review ID:
Case ID:
Reviewer provider:
Reviewer model:
Review session: fresh
Saw main conversation: false
Critical node: C1 | C2 | C3
Review mode: blind | challenge | results
Review lens:
Primary method family:
Alternative method family:
Methodological difference:
Highest-risk findings:
- [P0/P1/P2/P3] statement; evidence; impact; minimal test
Disconfirming test or counterexample:
Routes to retain / modify / pause:
What was checked:
What was not checked:
Human decisions required:
Uncertainty:
Verdict: PASS | PASS_WITH_LIMITATIONS | BLOCKED | REJECTED
```

“方案看起来合理”不是审核结论。没有方法论差异、反例或可证伪测试时，只能报告信息不足。
报告只提出建议；队员在 `decisions.md` 记录接受或拒绝及原因，Codex 再实施和验证。
