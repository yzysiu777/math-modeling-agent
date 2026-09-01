# 华为杯论文 LaTeX 工程

文档类采用社区模板 **gmcmthesis**（第二十二届 / 2025 版），承诺书页、标题摘要页、
页码起始位置、无页眉和正文匿名等官方版式由它负责。工程结构保持分章，供比赛期间
多人并行写作。

**它不是组委会发布的官方模板。** 比赛日以当届官方格式规范和 Word 模板为准，
冲突时以官方为准。2026 年格式发布后按 [upstream/README.md](upstream/README.md)
的步骤替换。

## 目录

```text
paper/
├── main.tex                    装配入口：文档类、元信息、摘要、章节、参考文献、附录
├── gmcmthesis.cls              上游文档类 + 已记录的最小条件闭合补丁
├── gmcm.bst                    上游书目样式（编译必需，经典 BibTeX）
├── figures/logo.pdf title.pdf  文档类硬编码引用，缺失即编译失败
├── config/paper-profile.tex    队伍元信息：标题、报名号、学校、队员、关键词
├── style/modeling-paper.sty    工作台辅助宏（只补文档类没有的少量内容）
├── sections/01-07*.tex         正文章节，每人一章，避免合并冲突
├── appendix/01-support.tex     支撑材料
├── bibliography/references.bib 参考文献（BibTeX 格式，非 biblatex）
├── official/<year>/manifest.yaml  当届官方文件的来源与哈希记录
└── upstream/                   上游原件、版本、校验和与升级步骤
```

## 编译

```bash
make paper           # 只编译论文
make paper-ci        # 编译 + LaTeX QA + 片段库编译验证
make qa              # 对已生成 PDF 做检查
make paper-example   # 编译上游示例（12 页），看这套模板支持哪些排版元素
                     # 仅 macOS / Windows：上游代码环境依赖 Courier New
make snippet-check   # 单独验证 writing/LATEX_SNIPPETS.md 里的片段编得过
```

排版元素怎么写，查 [../writing/LATEX_SNIPPETS.md](../writing/LATEX_SNIPPETS.md)，
不要临场翻语法。

需要 XeLaTeX、latexmk、**bibtex**（不是 biber）和 PyYAML。

### 字体

本机（macOS / Windows）直接编译，文档类会用系统中文字体，排版最接近提交稿。

Linux 与 CI 没有 SimSun/SimHei，需要 ctex 的 fandol 字体集：

```bash
make PAPER_FONTSET=fandol paper-ci
```

CI 已固定使用这一项。**fandol 与提交机字体不同，行距与断行会有细微差异** ——
最终稿必须在准备提交的那台机器上重编一次并人工翻看。

## 写作约定

- `main.tex` 只装配，不堆正文；
- 每位成员在独立 `paper/<章节>` 分支上改对应的 `sections/*.tex`，同一文件同一时间
  只一个主要写入者；
- 图表由脚本生成，图注写明来源实验 ID，见 `experiments/outputs/figures/manifest.md`；
- 摘要、结论、核心图表和关键对比中的数字要能在 `paper/claim_map.md` 追到实验 ID
  和数据文件；普通表格由结果文件生成，不逐格登记；
- 提交前 `config/paper-profile.tex` 里的「待填写」必须全部替换 —— 占位值会原样
  印在承诺书页和标题页上，这是刻意设计，方便人工核对时一眼看见。

## 参考文献

经典 BibTeX + `gmcm.bst`，**不是** biblatex/biber。写条目时注意：

- 用 `@article`、`@book`、`@inproceedings`、`@online`、`@techreport` 等标准类型；
- `urldate`、`langid` 这类 biblatex 专有字段会被忽略，不报错但也不生效；
- 正文用 `\cite{}`，顺序编码制由 `gmcm.bst` 处理。

## 脚本查得出什么，查不出什么

`make paper-ci` / `make qa` 用于草稿预览，能确认编译通过、必需文件齐全、分章结构、
摘要/关键词/参考文献和引用状态。草稿允许保留显式的「待填写」与模板示例。

`make final-check CASE=...` 才执行提交级检查：拒绝占位符、模板示例、未冻结官方配置、
页眉、错误页码位置、明显越界和身份信息泄漏。

**查不出**：字号、行距、页边距是否符合当届要求，封面字段是否填对，图表编号是否
连续，公式推导是否正确，数字是否与实验一致。这些必须人工对照当届官方 Word 模板
逐页核。CI 产出的 PDF 只是预览，不能直接当提交件。
