# 竞赛论文写作与交付

本目录固定论文内容、语言、图表、引用、AI 使用记录和 PDF 检查。它服务于轻量建模
流程，不要求队员先完成一套与题目无关的记录。

## 阅读顺序

1. [OFFICIAL_RULES.md](OFFICIAL_RULES.md)：比赛日官方文件优先级；
2. [PAPER_STYLE_GUIDE.md](PAPER_STYLE_GUIDE.md)：正文结构、语言和协作；
3. [NATIONAL_AWARD_LANGUAGE.md](NATIONAL_AWARD_LANGUAGE.md)：证据化表达；
4. [FIGURE_TABLE_FORMULA_RULES.md](FIGURE_TABLE_FORMULA_RULES.md)：图表、公式和单位；
5. [AI_COMPLIANCE.md](AI_COMPLIANCE.md)：AI 使用和人工核验；
6. [QA_CHECKLIST.md](QA_CHECKLIST.md)：内容、引用、编译和 PDF 检查。

比赛开始后重新获取当届模板、匿名规则、字体、页数和 AI 规定，历史文件只作为工程
参考，不能替代官方标准。

## 工作节奏

```text
首个 baseline
  -> 结果表和图表清单
  -> 章节骨架与符号表
  -> 稳定实验和结果段
  -> C3 强结论挑战
  -> 摘要/结论统一核数
  -> XeLaTeX 编译、PDF 检查和人工确认
```

## LaTeX 工程

`paper/` 是团队默认工程：`main.tex` 只装配章节，正文位于 `sections/`，图表分离，
引用统一维护在 `bibliography/references.bib`，样式通过 `style/` 与 `config/` 管理。

```bash
make paper
make paper-ci
make qa
```

CI PDF 只是预览。正式提交前，队员必须用当届官方文件核对封面/摘要页、匿名、页码、
字体、元数据和 AI 声明，并人工打开最终 PDF。
