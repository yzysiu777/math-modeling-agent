# LaTeX 排版片段库

比赛期间不要现查语法。这里每一段都能**直接复制进 `paper/sections/*.tex`**，
在本仓库的论文工程里编得过 —— `make snippet-check` 会把它们全部抽出来实际编译一遍，
所以这份文档不会烂掉。

想看这些元素排出来是什么样：

```bash
make paper-example    # 编译上游完整示例，12 页
```

源码在 `paper/upstream/example.tex`，可以直接抄。但注意它比本仓库多加载了
`mdframed`、`subfig`、`colortbl` —— 抄那部分要自己 `\usepackage`。

---

## 图表的共同约定

**每张图表的标题都要能自洽**（不看正文也知道它在说什么），并写明来源实验 ID。
写作手核数字时按这个 ID 去 `q<k>/outputs/figures/manifest.md` 追溯。

```text
\caption{不同容量下的最优总成本（EXP-OPT-002）}
```

`\label` 统一前缀：表 `tab:`、图 `fig:`、公式 `eq:`、算法 `alg:`。

---

## 三线表

建模论文的默认表格样式。不要画竖线。

<!-- snippet: booktabs -->
```latex
\begin{table}[H]
  \centering
  \caption{候选路线在统一口径下的比较（EXP-OPT-001 至 EXP-OPT-003）}
  \label{tab:route-comparison}
  \begin{tabular}{lccc}
    \toprule
    路线 & 目标值 & 求解时间/s & 可行性 \\
    \midrule
    M-01 贪心   & 4.00 & 0.001 & 可行 \\
    M-02 枚举   & 4.00 & 0.012 & 可行（真值） \\
    M-03 整数规划 & 4.00 & 0.240 & 可行 \\
    \bottomrule
  \end{tabular}
\end{table}
```

---

## 跨行跨列与单元格换行

`\multirow` 跨行、`\multicolumn` 跨列、`\makecell` 在单元格内换行。

<!-- snippet: multirow -->
```latex
\begin{table}[H]
  \centering
  \caption{分场景的服务水平与成本}
  \label{tab:scenario}
  \begin{tabular}{clcc}
    \toprule
    \multirow{2}{*}{场景} & \multirow{2}{*}{说明}
      & \multicolumn{2}{c}{结果} \\
    \cmidrule(lr){3-4}
      & & 成本 & \makecell{服务率\\(\%)} \\
    \midrule
    \multirow{2}{*}{低需求} & 基准 & 8.0  & 100 \\
                            & 扰动 & 8.4  & 98  \\
    高需求                  & 基准 & 18.0 & 92  \\
    \bottomrule
  \end{tabular}
\end{table}
```

---

## 长表格跨页

数据字典、符号表这类超过一页的表用 `longtable`，不要用 `table` 硬塞。

<!-- snippet: longtable -->
```latex
\begin{longtable}{llp{0.45\textwidth}}
  \caption{符号说明}\label{tab:symbols} \\
  \toprule
  符号 & 单位 & 含义 \\
  \midrule
  \endfirsthead
  \multicolumn{3}{l}{\small 续表~\thetable} \\
  \toprule
  符号 & 单位 & 含义 \\
  \midrule
  \endhead
  \bottomrule
  \endfoot
  $x_{ij}$ & --   & 需求点 $j$ 是否由服务点 $i$ 承担的 0-1 变量 \\
  $c_{ij}$ & 元   & 需求点 $j$ 由服务点 $i$ 承担的单位成本 \\
  $u_i$    & 件   & 服务点 $i$ 的容量上限 \\
\end{longtable}
```

---

## 伪代码

`algorithm` + `algpseudocode` 已由 `style/modeling-paper.sty` 统一加载并汉化
（`\Require` 显示为「输入：」，`\Ensure` 为「输出：」）—— 不要在自己章节里再
`\renewcommand`，否则同一篇论文会出现「输入/Require」混用。

<!-- snippet: algorithm -->
```latex
\begin{algorithm}[H]
  \caption{容量约束下的贪心分配}
  \label{alg:greedy}
  \begin{algorithmic}[1]
    \Require 成本矩阵 $C$，容量向量 $u$，需求集合 $D$
    \Ensure 分配方案 $A$ 与总成本 $z$
    \State $A \gets \emptyset$，$z \gets 0$
    \For{每个需求 $j \in D$（按最小可行成本升序）}
      \State $i^\ast \gets \arg\min_{i:\,u_i > 0} c_{ij}$
      \If{不存在这样的 $i^\ast$}
        \State \Return 不可行
      \EndIf
      \State $A \gets A \cup \{(i^\ast, j)\}$；$u_{i^\ast} \gets u_{i^\ast} - 1$
      \State $z \gets z + c_{i^\ast j}$
    \EndFor
    \State \Return $A,\ z$
  \end{algorithmic}
\end{algorithm}
```

---

## 单图与子图

子图用 `subcaption`，由 `style/modeling-paper.sty` 加载 —— 文档类里它是被注释掉的
（上游示例改用 `subfig`）。两者互斥：从 `example.tex` 抄子图代码要改写成下面的
`subfigure` 环境，不能直接 `\usepackage{subfig}`。

<!-- snippet: figures -->
```latex
\begin{figure}[H]
  \centering
  \includegraphics[width=0.6\textwidth]{example-image}
  \caption{总成本随容量的变化（EXP-OPT-002）}
  \label{fig:cost-capacity}
\end{figure}

\begin{figure}[H]
  \centering
  \begin{subfigure}[b]{0.46\textwidth}
    \centering
    \includegraphics[width=\textwidth]{example-image-a}
    \caption{基准场景}\label{fig:base}
  \end{subfigure}
  \hfill
  \begin{subfigure}[b]{0.46\textwidth}
    \centering
    \includegraphics[width=\textwidth]{example-image-b}
    \caption{扰动场景}\label{fig:perturbed}
  \end{subfigure}
  \caption{两种场景下的分配结果对比（EXP-HYB-001）}
  \label{fig:scenarios}
\end{figure}
```

图文件放 `q<k>/outputs/figures/`，编译时通过 `\graphicspath` 或相对路径引用；
**永远不要手工修图**，改图就重跑生成脚本。

---

## 公式

多行对齐用 `align`，需要引用的行才编号。

<!-- snippet: equations -->
```latex
\begin{align}
  \min_{x} \quad & \sum_{i \in S} \sum_{j \in D} c_{ij} x_{ij} \label{eq:objective} \\
  \text{s.t.} \quad
    & \sum_{i \in S} x_{ij} = 1, && \forall j \in D \label{eq:assign} \\
    & \sum_{j \in D} x_{ij} \le u_i, && \forall i \in S \label{eq:capacity} \\
    & x_{ij} \in \{0,1\}, && \forall i \in S,\ j \in D \nonumber
\end{align}

其中式~\eqref{eq:objective} 为总成本，约束~\eqref{eq:assign} 保证每个需求恰好被
服务一次，约束~\eqref{eq:capacity} 为容量上限。
```

**公式首次出现时必须定义其中每个符号**，且符号要与 `specs/` 里的规格一致。

---

## 代码附录

`listings` 样式已在 `style/modeling-paper.sty` 里统一定义（含中文注释支持）。
附录只放**关键入口**，不要把整个仓库贴进去。

> **不要用文档类自带的 `\begin{Matlab}{...}` / `\begin{Python}{...}` 环境。**
> 它们在环境内部写死了 `\fontspec{Courier New}` —— 那是 Windows/macOS 字体，
> 在 Linux 上直接编译失败，而且因为写在环境里，外部 `\lstset` 覆盖不掉。
> 上游示例用的就是它们，所以 `make paper-example` 只能在 macOS/Windows 上跑。
> 用下面的 `lstlisting` + 本仓库样式，换机器不会炸。

<!-- snippet: listings -->
```latex
\begin{lstlisting}[language=Python, caption={枚举求解与目标值独立复算入口}, label={lst:enumerate}]
def recompute_objective(assignment, cost):
    """独立重算目标值，不复用求解器的中间结果。"""
    return sum(cost[j][i] for i, j in assignment)
\end{lstlisting}

\begin{lstlisting}[language=Matlab, caption={场景生成与湍流强度计算}, label={lst:scenario}]
function tke = turbulence_intensity(u, v, w)
    % 由三分量脉动速度计算湍流动能
    tke = 0.5 * mean(u.^2 + v.^2 + w.^2);
end
\end{lstlisting}
```

---

## 引用

经典 BibTeX + `gmcm.bst`，顺序编码制。条目写进
`paper/bibliography/references.bib`，正文用 `\cite{}`。

<!-- snippet: citations -->
```latex
本文采用的格式依据见文献~\cite{cmathc2025format}；开赛公告见~\cite{cmathc2025notice}。
```

`urldate`、`langid` 这类 biblatex 专有字段会被静默忽略 —— 不报错，但也不显示。

---

## 交叉引用的写法

```text
表~\ref{tab:route-comparison}    图~\ref{fig:scenarios}
式~\eqref{eq:objective}          算法~\ref{alg:greedy}
```

`~` 是不断行空格，避免「表」和编号被拆到两行。

---

## 维护

新增片段必须带 `<!-- snippet: 名字 -->` 标记，`make snippet-check` 会抽取所有带标记的
代码块，拼进一份使用本仓库文档类与样式的文档实际编译。**编不过就是错的**，
不要只靠肉眼看。
