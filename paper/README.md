# 华为杯 LaTeX 协作模板

这是一个可编译的团队论文工程，依据历史官方格式快照和公开社区模板的可迁移做法设计，但它不是组委会发布的官方模板。正式比赛必须把当届官方封面、统一摘要页、论文标准文档和 AI 规定冻结后再提交。

## 官方依据与参考

- 2025 格式规范：[中国研究生数学建模竞赛官方发布页](https://www.cmathc.org.cn/mcm/tz/317.html)；
- 2025 开赛公告：[官方公告](https://www.cmathc.org.cn/cpmcm/news/512.html)；
- 社区参考：[mathliuyang/CPIPC](https://github.com/mathliuyang/CPIPC)；
- 社区参考：[latexstudio/GMCMthesis](https://github.com/latexstudio/GMCMthesis)。

社区模板只用于观察 LaTeX 工程化、封面 PDF 插入、图表目录和编译组织方式，不能替代官方文件。官方格式强调摘要页、连续页码、无页眉、正文匿名、统一字体字号、单倍行距、顺序编码制参考文献和 PDF 提交；这些规则会随当届文件重新核验。

## 编译

在仓库根目录执行：

```bash
make paper
make paper-ci
make qa
```

需要 XeLaTeX、biber、latexmk、PyYAML 和 jsonschema。首次使用可执行 `python3 -m venv .venv && .venv/bin/python -m pip install -r requirements-dev.txt`。CI 采用 TeX Live 的 Fandol 字体配置；正式比赛可在比赛机器上按当届官方文件切换 `fontset` 和封面，但必须重新编译和 QA。

## 团队协作约定

- `main.tex` 只装配章节，不在其中堆积正文；
- 每位成员在独立 `paper/<章节>` 分支编辑对应 `sections/*.tex`；
- 图和表由脚本生成，源数据与结果实验 ID 写入图表说明；
- 所有引用统一进入 `bibliography/references.bib`，不手工改数字编号；
- `paper/config/paper-profile.tex` 保存题目、关键词、官方版本和封面开关；
- `PaperOfficialCoverPages` 记录官方封面 PDF 的页面范围；默认 `-` 表示导入全部页面，正式提交前必须按当届文件核对；
- `paper/official/<year>/manifest.yaml` 记录当届官方文件来源、日期、大小和可选哈希；冻结正式模板时再记录哈希；
- `paper/build/` 只存构建产物，不提交 Git。

## 封面和摘要页

模板默认生成明确标注的内部封面占位页，保证 CI 能编译。正式提交时必须按照当届官方模板准备封面 PDF 和统一摘要页；如果启用外部官方封面，先在 `paper/config/paper-profile.tex` 开启开关并核对 PDF 路径、匿名规则和页面顺序。
