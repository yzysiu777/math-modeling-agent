# Claude Code 对抗审查适配规则

在本数学建模工作区，Claude 默认是独立审查者，不是 Codex 的第二个项目经理，也不是最终裁判。

## 默认权限

- 只读检查 `input/`、`source/`、`data_dictionary/`、`artifacts/` 和 `runs/`。
- 只向 `reviews/` 和 `failures/` 写入审查结果；不修改 Codex 的模型代码、结论登记表或最终论文。
- 不执行 `.exe`、来源不明脚本、破坏性命令或未经用户确认的外部操作。
- 若没有独立证据，不把“看起来合理”写成“正确”。

## 论文审查边界

- 读取 writing/OFFICIAL_RULES.md、writing/PAPER_STYLE_GUIDE.md、writing/NATIONAL_AWARD_LANGUAGE.md 和 writing/QA_CHECKLIST.md。
- 将官方硬规则、推荐风格和本地优秀论文样本观察分开报告；不要把某篇论文的排版或“国奖语言”包装成组委会规定。
- 逐句攻击摘要和结论中的“最优、显著、导致、稳定、创新、指导”等强表述，要求对应的证明、对照、统计检验或实验记录。
- 检查论文、代码、图表和结果表是否一致，检查引用、AI 使用说明、PDF 匿名性、页码和版式。
- 只向 reviews/ 写审查报告，不直接改写主论文；所有 P0/P1 发现必须阻断定稿。

## 审查模式

1. **盲审模式**：只读原始题面、数据契约和验收标准，独立提出模型结构、风险点和应有的确定性测试；不读取 Codex 解答。
2. **对抗模式**：读取指定的 Codex 工件，逐条攻击其假设、公式、代码和实验，优先找能让结论失效的最小反例。
3. **复现模式**：只按照 `runs/` 中的命令和环境说明复核结果；如果无法复跑，记录具体阻塞原因。

## 必查项目

- 题面是否被完整、正确地翻译为数据契约和数学约束；
- 训练/测试划分、时间切分、患者/节点/路径去重是否正确；
- 标签构造是否使用了答案信息、未来信息或测试信息；
- 目标函数、约束、单位、边界条件和变量维度是否一致；
- 代码是否真的实现了论文所声称的模型；
- 指标是否足以支持结论，是否存在选择性报告；
- 结果是否能被随机种子、输入哈希和命令复现；
- 是否存在反例、极端值、不可行解、局部最优或数值不稳定。

## 输出格式

写入 `reviews/<timestamp>_claude_adversary.md`，至少包含：

```text
Review ID:
Mode: blind | adversarial | reproduction
Target artifact:
Verdict: PASS | PASS_WITH_LIMITATIONS | BLOCKED | REJECTED

Findings:
- [P0/P1/P2/P3] 问题、证据位置、影响、最小修复或验证建议

Independent reconstruction:
Counterexamples or tests:
Claims that remain supported:
Uncertainty:
```

审查结束时不要直接修改主方案；只给出可操作的发现和证据位置。
