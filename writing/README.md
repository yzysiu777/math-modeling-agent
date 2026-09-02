# 竞赛论文写作与交付

本目录固定论文内容、语言、图表、引用、AI 使用记录和 PDF 检查。它服务于**写作手**
角色（`prompts/writer.md`），不要求队员先完成一套与题目无关的记录。

## 写作手的三条铁律

1. **关键结论要能追溯。** 摘要、结论和核心图表里的关键数字与强主张，必须在
   `paper/claim_map.md` 里追到 EXP-ID 和结果文件。普通表格由结果数据生成，不逐格登记。
2. **润色不动数值。** 可以改语言、结构、排版和图表视觉；不得改动任何数值、单位、
   有效位数或结论强度。发现对不上，回到对应 SPEC 和实验板让 Engineer 重跑；只有命中
   人工专属边界才建立 `.questions.md`。
3. **表述强度匹配证据。** 可行解 / 当前最好 / 给定假设下最优 / 全局最优；关联 /
   预测贡献 / 因果。

模型真值读取 `q<k>/specs/SPEC-*.md`，结果真值读取 `q<k>/board.md`、图表清单和
`q<k>/outputs/data/`。不从聊天记录抄数字。

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
  -> 问题—模型—实验—图表—结论—引用 映射
  -> 章节骨架与符号表（不依赖最终结果，第一天就能写）
  -> 摘要骨架（结果留空，早写能暴露「我们到底证明了什么」）
  -> 稳定实验和结果段，把摘要、结论和核心图表的关键数字加入 claim_map
  -> C3 强结论挑战（从 claim_map 挑 3–5 条风险最高的）
  -> 摘要/结论统一核数、表述强度复核
  -> XeLaTeX 编译、PDF 检查和人工确认
```

## 润色的合法范围

**可以**：重排成论文级三线表；统一配色、字号、线宽、图例位置；补坐标轴标签、单位、
图注；把日志式描述改写成学术语言；调整段落顺序、统一术语。

**不可以**：改数值或有效位数（包括「四舍五入更好看」）；改单位；提升结论强度；
挑选有利子集重新作图；补一个没跑过的对照。

需要重画图时回问编程手重跑生成脚本，**永远不手工修图** —— 手改的图无法复现，
数据更新后无法同步，C3 一查就露。

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

## 排版片段

[LATEX_SNIPPETS.md](LATEX_SNIPPETS.md) 收录三线表、跨行表、长表、伪代码、子图、公式、
代码附录和引用的可直接复制片段。`make snippet-check` 会把它们全部实际编译一遍，
所以这份文档不会烂掉；`make paper-example` 编译上游完整示例，看排版效果。

## 已退役

`writing/prompts/` 的六份角色提示词写于三角色合并之前，与「一题一个持续 Writer
会话」的现行结构矛盾，已删除。其中真正有用的写作约束吸收进 `prompts/writer.md`，
C3 审查提示词以 `prompts/reviewer/C3_results_challenge.md` 为准，引用审计已由
`scripts/qa_latex.py` 的引用检查与 `paper/文献清单.md` 承担。
