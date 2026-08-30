# 上游模板来源与更新方式

本目录保存 gmcmthesis 模板的**原件**，只作来源留痕与升级对照，不参与编译。
参与编译的是仓库根 `paper/` 下的 `gmcmthesis.cls`、`gmcm.bst` 和 `figures/`。

## 版本

```text
2025/09/16 v2.5 update by andy123t&latexstudio
```

由 latexstudio.net 创建、andy123t 更新的社区模板，对应**第二十二届（2025）**官方格式。
本次引入时的分发包内还含官方 Word 模板 `附件3："华为杯"第二十二届……论文模板.doc`。

## 收录了什么，没收录什么

| 文件 | 处置 | 理由 |
|---|---|---|
| `gmcmthesis.cls` | 收录到 `paper/` | 编译必需 |
| `gmcm.bst` | 收录到 `paper/` | 书目样式，编译必需 |
| `figures/logo.pdf`、`figures/title.pdf` | 收录到 `paper/figures/` | 文档类硬编码 `\includegraphics{logo}` 与 `{title}`，缺失即编译失败 |
| `example.tex`、`example.pdf` | 收录到本目录 | 上游用法与目标版式的参照，不编译 |
| `figures/gongzhonghao*.png` | **未收录** | latexstudio 的公众号二维码，属推广物料，不应出现在比赛工程里 |
| `figures/image1-4.pdf`、`fig.png`、`logo2*.pdf` | **未收录** | 示例插图，与本队论文无关 |
| `makefiles.sh`、`#delete-temp-files.bat`、`digest.lock` | **未收录** | 上游构建脚本，本仓库用 `make paper-ci` |

## 校验和

```text
769a484ecfe4c2e5abb5d3d65cfd404e7325fdbf236ed12b25d2707cea177df9  gmcmthesis.cls
cfd2ed609cfc7c7d5c2c2f4d84ee5f1a2300510cc22f5c3f6cf67d81e82ae03e  gmcm.bst
a382e4fa022f4d97984807756f36076552489d3ec26530126c58587572046632  figures/logo.pdf
19eee18de63633104dc4829439700fd30a7279549dfa12f71fd7d8f76d158bd7  figures/title.pdf
4b9cdbb0b05e6c6ddee982ceae7215efa307f6bce9514889a7af0ce0f4a7b929  upstream/example.tex
```

## 2026 年怎么替换

当届官方格式发布后：

1. 取新版 gmcmthesis（或当届官方指定模板），替换 `paper/gmcmthesis.cls`、`gmcm.bst`、`figures/`；
2. 用新的 `example.tex`/`example.pdf` 覆盖本目录，并更新上面的版本与校验和；
3. 核对 `\baominghao`/`\schoolname`/`\membera` 等元信息宏是否改名，改了就同步 `paper/config/paper-profile.tex`；
4. 更新 `paper/official/<year>/manifest.yaml` 与 `writing/official/<year>/`；
5. 跑 `make paper-ci` 与 `make qa`，并**人工打开 PDF 与官方 Word 模板逐页对照**。

第 5 步不能省。脚本只查得出「编得过、有摘要有关键词有参考文献、没有页眉」，
查不出字号、行距、页边距、封面字段是否符合当届要求。

## 边界

社区模板**不是官方来源**。它跟进得快、排版成熟，所以适合日常写作；但比赛日以
组委会发布的当届格式规范和 Word 模板为准，两者冲突时以官方为准。
