# 竞赛论文写作与交付系统

本目录把论文的内容、语言、引用、AI 使用记录和 PDF 验收固定为一套可执行规则。官方硬规则、团队内部风格、优秀论文观察和模型建议必须分开记录。

## 阅读顺序

1. [OFFICIAL_RULES.md](OFFICIAL_RULES.md)：当届规则冻结和官方文件优先级；
2. [PAPER_STYLE_GUIDE.md](PAPER_STYLE_GUIDE.md)：正文结构和 LaTeX 协作约定；
3. [NATIONAL_AWARD_LANGUAGE.md](NATIONAL_AWARD_LANGUAGE.md)：证据化、克制化表达；
4. [FIGURE_TABLE_FORMULA_RULES.md](FIGURE_TABLE_FORMULA_RULES.md)：图、表、公式和单位；
5. [AI_COMPLIANCE.md](AI_COMPLIANCE.md)：AI 使用记录和人工核验；
6. [QA_CHECKLIST.md](QA_CHECKLIST.md)：内容、引用、编译和 PDF 门禁；
7. [STYLE_EVIDENCE.md](STYLE_EVIDENCE.md)：规则来源和证据等级。

## 固定工作流

```text
题面与附件冻结
  -> 子问题—模型—实验—图表—结论—引用映射
  -> 摘要骨架与结果表清单
  -> 分子问题完成分析—假设—模型—求解—结果—检验闭环
  -> Codex 起草
  -> Claude 独立审查
  -> 确定性检查：数字、公式、代码、图表、引用和规则
  -> XeLaTeX 编译与 CI
  -> PDF 文本/元数据/渲染 QA
  -> 人工确认、哈希冻结和提交
```

## LaTeX 工程

`paper/` 是团队协作的默认工程：`main.tex` 只负责装配，正文放在 `sections/`，图表分离存放，引用统一放在 `bibliography/references.bib`，样式通过 `style/` 和 `config/` 管理。

```bash
make paper       # 本地 XeLaTeX + biber 完整编译
make paper-ci    # CI 可携带字体编译
make qa          # 源文件和生成 PDF 的静态检查
make clean       # 清理中间文件
```

CI 预览版不是自动提交版。正式比赛必须用当届官方标准、模板、字体和封面完成最终预检。

## 论文角色

- `roles/paper_architect.md`：建立问题树、篇幅和证据映射；
- `writing/prompts/mathematical_writer.md`：将已支持结果写成正文；
- `writing/prompts/citation_editor.md`：审计来源与引用；
- `writing/prompts/figure_table_editor.md`：审计图表、公式和单位；
- `writing/prompts/formatting_qa.md`：验收最终 PDF；
- `prompts/claude/04_latex_paper_audit.md`：交给 Claude 做独立论文审查。

作者、审查者和最终批准者必须分离。没有 claim、实验、来源或人工决定支持的内容不得进入最终强结论。
