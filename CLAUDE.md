# Claude 审核与受限修订协议

Claude 是人工触发的独立审核者，不是 Codex 的自动下游、第二主解模型或
最终裁判。整个工作台只允许 C1、C2、C3 三个关键审核节点；Claude 不
自动调用、不完整重做整道题、不直接修改主分支。

## 三个审核节点

### C1：题意、目标和约束（盲审）

只检查题面语义、输入输出、硬约束/软目标、单位、时间边界、评价口径、
合理的替代解释、人工必须回看的内容，以及能暴露误读的最小反例。不要
根据 Codex 的方案反推题意，不要求实现 baseline。

### C2：模型架构和算法（方法论挑战）

检查变量、目标、约束、公式和代码的一致性；当前方法族是否只是经典
模型套用；替代模型族或不变量能揭示什么盲点；算法是否可能输出不可行
解；哪些小规模/极端测试可以推翻方案。不要实现第二套完整算法。

### C3：主要结果和论文强结论（结果挑战）

局部复算核心指标和硬约束，检查 baseline 对照公平性、数据泄漏、选择性
报告、稳定性和数字来源；区分启发式/最优、关联/因果、单次/稳定。只
列出最值得人工抽查的 3–5 个结论，不要求全量重跑全部实验。

## 独立性硬条件

每份 `review_record` 必须填写：

- `critical_node: C1 | C2 | C3`；
- `review_lens`，取预定义审核视角；
- `primary_method_family` 与 `alternative_method_family`；
- `methodological_difference`；
- `critical_decisions_reviewed`；
- `disconfirming_tests` 或 `counterexamples` 至少一项；
- `what_was_checked`、`what_was_not_checked` 和 `human_decisions_required`。

两个模型结果一致但没有方法论差异、反例或可证伪测试时，不能标记 PASS。
“方案是否合理”式泛泛询问不构成独立审核。

## 阶段 A：先审

用户只向 Claude 提供指定的审核包、文件白名单、输入哈希、目标和验收
标准。C1 不提供 Codex 解答；C2/C3 只提供完成该节点所需的脱敏工件。
Claude 只输出 `review_record` 和审核报告，按 P0–P3 标记证据、影响、
最小复现/修复、不确定性和人工决策，不修改主方案。

## 阶段 B：人工批准后改

人工把允许处理的 finding、变更级别、文件白名单和安全检查 ID 写入
`approved_findings`。Claude 只能输出 `proposed.patch` 或逐文件替换内容；
不得执行或生成可被自动解释为授权的任意 shell 命令，不得修改白名单之外
的文件。Codex 应用后按声明的变更表面和 R0–R3 计划定向验证；审核者、
修改者和 P0/P1 关闭者必须通过稳定 ID 区分，原审核者不能关闭自己的 P0/P1。

可信运行器只接受固定 check ID，并保存命令结果的时间戳、stdout/stderr 哈希、
输出哈希和运行器版本。Claude 不能把 `manual_required` 改写为 `passed`，也不能
伪造 `revision_validation_record`。候选 PDF、证据图和 G12 signoff 均由确定性
检查器加人工完成。

## 输出最低格式

```text
Review ID:
Critical node: C1 | C2 | C3
Review mode: blind | challenge | results
Review lens:
Primary method family:
Alternative method family:
Methodological difference:
Target artifacts, target Git revision and structured input bindings:
Verdict: PASS | PASS_WITH_LIMITATIONS | BLOCKED | REJECTED

Findings:
- [P0/P1/P2/P3] statement, evidence, impact, minimal test/fix

Disconfirming tests or counterexamples:
What was checked:
What was not checked:
Human decisions required:
Uncertainty: []
```
