# 竞赛论文写作与交付系统

本目录把华为杯数学建模论文的“写什么、怎么写、怎么排、怎么验收”固定成一套可执行规则。

核心原则：

1. 当届组委会发布的论文标准文档优先于本目录的一切规则。
2. 官方硬规则、从高奖论文抽取的稳定做法、团队内部推荐风格必须分开标注，不能混称为“国奖模板”。
3. 论文不是最后才润色的文本，而是由题面证据、数据契约、模型、实验、图表、结论和引用共同生成的可审计工件。
4. 任何数字、公式、算法性能、最优性和因果性表述都必须回到 claim register、实验记录或正式来源。
5. Codex 可以组织写作和修改，Claude 负责独立攻击论文；任何模型都不能自己批准最终稿。

## 阅读顺序

1. [OFFICIAL_RULES.md](OFFICIAL_RULES.md)：官方规则、版本冻结和竞赛日更新办法。
2. [PAPER_STYLE_GUIDE.md](PAPER_STYLE_GUIDE.md)：固定的论文骨架和推荐版式。
3. [NATIONAL_AWARD_LANGUAGE.md](NATIONAL_AWARD_LANGUAGE.md)：严谨、克制、可证据化的竞赛论文语言。
4. [FIGURE_TABLE_FORMULA_RULES.md](FIGURE_TABLE_FORMULA_RULES.md)：图、表、公式、单位和交叉引用。
5. [AI_COMPLIANCE.md](AI_COMPLIANCE.md)：Codex/Claude 使用记录与赛事合规边界。
6. [QA_CHECKLIST.md](QA_CHECKLIST.md)：从摘要到最终 PDF 的写作门禁。
7. [STYLE_EVIDENCE.md](STYLE_EVIDENCE.md)：官方文件与本地高奖论文抽样证据。

## 固定工作流

~~~text
题面与附件冻结
  → 论文问题树与 claim register
  → 先写摘要骨架和结果表占位
  → 分问题写“分析—假设—模型—求解—结果—检验”
  → Codex 结构/内容写作
  → Claude 盲审或对抗审查
  → 确定性检查：数字、公式、代码、图表、引用、页数、匿名性
  → 人工确认并导出 PDF
  → 渲染 PDF 逐页视觉检查
  → 计算最终文件哈希后锁定
~~~

## 本目录中的“模板”是什么

official/2025/ 保存了公开可获取的 2025 年官方格式规范和模板，作为证据快照，不代表 2026 年比赛一定沿用。真正参赛时，必须以题包中当届《竞赛论文标准文档》覆盖/校准它。

templates/ 保存的是内容模板、语言模板和版式 token，不替换当届官方封面、Logo 或摘要页。

当前推荐的实现策略是：

- 比赛交付：使用当届官方 Word 标准文档，避免封面、Logo、摘要页和匿名规则出错；
- 团队内部写作：可以用 Markdown/LaTeX 组织正文和图表，再回填或导出到官方标准文档；
- 最终验收：只以导出的 PDF 为准，不能以 Word 编辑器中“看起来正常”为准。

## 角色入口

- [prompts/paper_architect.md](prompts/paper_architect.md)：论文架构师，负责问题树、篇幅和证据映射。
- [prompts/mathematical_writer.md](prompts/mathematical_writer.md)：数学建模作者，负责把已验证结果写成正文。
- [prompts/figure_table_editor.md](prompts/figure_table_editor.md)：图表与公式编辑。
- [prompts/citation_editor.md](prompts/citation_editor.md)：来源、引用和 AI 使用说明。
- [prompts/paper_reviewer.md](prompts/paper_reviewer.md)：Claude/独立审查者。
- [prompts/formatting_qa.md](prompts/formatting_qa.md)：最终 PDF 格式门禁。

## 当前未锁死的内容

- 2026 年华为杯详细格式文档在竞赛题包中发布前，不应假定与 2025 年完全相同。
- “国奖语言”没有组委会公布的词典；本目录提供的是证据化、克制化的团队写作规范。
- 具体封面 Logo、题号、队号、摘要页和提交命名必须在比赛日从官方文件重新核对。
