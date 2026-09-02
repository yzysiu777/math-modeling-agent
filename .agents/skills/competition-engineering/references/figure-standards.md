# 绘图规范

图是评委停留时间最长的地方。一张字太小、中文乱码、配色刺眼的图，会拖累背后正确的
模型。

Python 和 MATLAB 生成的图必须**视觉一致** —— 同字体、同字号、同配色、同线宽。
读者不该看得出哪张图是哪种语言画的。

## 硬性要求

| 项 | 要求 |
|---|---|
| 格式 | 每图同时导出 `<FIG-ID>.pdf`（矢量，入 LaTeX）和 `<FIG-ID>.png`（300 dpi，预览） |
| 字体 | 中文用思源黑体 / 黑体 / Songti，英文数字用 Times New Roman 或 DejaVu Serif |
| 最小字号 | 正文 9 pt 等效；坐标轴刻度不小于 8 pt |
| 尺寸 | 单栏图宽 8–9 cm，双栏 16–17 cm；不要画完再缩放 |
| 坐标轴 | 必须有标签和单位，例如「运行时间 / s」 |
| 图例 | 不遮挡数据；系列 ≤ 6 个，超过考虑换图型 |
| 线宽 | 主线 1.2–1.5 pt，网格线 0.5 pt 且浅色 |
| 分辨率 | 位图 300 dpi；能矢量就矢量 |
| 图内标题 | **不写**。标题归 LaTeX 的 `\caption`，图里再写一遍就是重复 |
| 多图对比 | 控制变量：只变一个因素，其余坐标范围、配色、字号、图例位置全部统一 |

第三次实测里这三条全没做到：全英文标签、只出 PNG、`dpi=200`，而且每个子图 `set_title`
之外还加了 `fig.suptitle` 写整段结论——那是图题该干的事，印在图里既挤又与 caption 冲突。
出图前读一遍本文件，不要凭印象画。

## 清洗前后对比图

清洗完成后，为**清洗真正改变了的关键变量**各出一张两栏图：左「清洗前」右「清洗后」，
两栏共用同一坐标范围、同一配色、同一字号，否则读者看到的差异有一半来自坐标轴。

没被清洗改动的变量不出这类图。八个变量出八张两栏图是图墙，不是证据 ——
它会把真正有问题的那两三个稀释掉。

配一份 `outputs/data/cleaning_summary.json`：变量、剔除条数、剔除规则、剩余条数、
关键统计量前后对照。论文的数据预处理一节直接用它渲染成表。

**出图之后要看一眼。**哨兵值混进统计量是这类错误里最常见的一种，而它在直方图上是
一根孤立的柱子，看一眼就能发现 —— 只生成不检查，图就白出了。

## 中文乱码

这是最高频的问题，两边都要显式设字体。

**Python**：

```python
import matplotlib
matplotlib.rcParams.update({
    "font.sans-serif": ["Songti SC", "Heiti SC", "Source Han Sans SC", "SimHei"],
    "axes.unicode_minus": False,          # 负号显示为方块的根因
    "font.size": 10,
    "axes.labelsize": 10,
    "xtick.labelsize": 9, "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "lines.linewidth": 1.3,
    "axes.grid": True, "grid.linewidth": 0.5, "grid.alpha": 0.3,
    "figure.dpi": 300, "savefig.bbox": "tight",
})
```

`axes.unicode_minus` 不设，负号会显示成方块 —— 常被忽略。

**MATLAB**：

```matlab
set(groot, 'defaultAxesFontName', 'Songti SC');
set(groot, 'defaultTextFontName', 'Songti SC');
set(groot, 'defaultAxesFontSize', 9);
set(groot, 'defaultLineLineWidth', 1.3);
set(groot, 'defaultAxesGridAlpha', 0.3);
set(groot, 'defaultAxesBox', 'on');
```

## 配色

色盲安全，灰度打印仍可区分。默认序列（Okabe-Ito）：

```text
#0072B2  蓝     #E69F00  橙     #009E73  绿
#CC79A7  粉     #56B4E9  浅蓝   #D55E00  朱红
#F0E442  黄     #000000  黑
```

**Python**：

```python
PALETTE = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00"]
matplotlib.rcParams["axes.prop_cycle"] = matplotlib.cycler(color=PALETTE)
```

**MATLAB**：

```matlab
PALETTE = [0 114 178; 230 159 0; 0 158 115; 204 121 167; 86 180 233; 213 94 0]/255;
set(groot, 'defaultAxesColorOrder', PALETTE);
```

多系列时**颜色之外再加一个通道**（线型或标记），保证黑白打印可读。

顺序型数据（热力图、等高线）用 `viridis` / `cividis`，不要用 `jet` ——
`jet` 会制造不存在的边界。

## 图型选择

| 要表达 | 用 | 不要用 |
|---|---|---|
| 类别比较 | 条形图 | 3D 柱状图、饼图 |
| 构成比例 | 堆叠条形图 | 饼图（>3 类时无法比较） |
| 趋势 | 折线图 | 平滑曲线掩盖离散点 |
| 分布 | 箱线图、小提琴图、直方图 | 只报均值 |
| 相关 | 散点图 + 拟合线（标注 R² 与样本量） | 只画拟合线 |
| 收敛 | 折线图，纵轴常用对数 | 线性轴挤在一起看不出后期 |
| 帕累托前沿 | 散点 + 阶梯线，标注非支配点 | 直接连线 |

**明令禁止**：3D 饼图、任何 3D 装饰效果、无必要的双 Y 轴（两个量纲不同的量强行叠在
一张图上，几乎总是误导）、截断纵轴放大差异（必须截断时明确标注断点）。

## 图注与标注

- 图题自洽：不看正文也能看懂这张图在说什么；
- 关键点标数值（最优解、拐点、异常点）；
- 误差棒要说明代表什么（标准差、标准误还是置信区间）；
- 有随机性的结果标注重复次数；
- 对照实验在图上标出用的是同一切分/同一实例集。

编程手写事实描述即可（「12 个实例上的运行时间对比」），写作手会改成论文语言 ——
但**不会改数值**。

## 保存

**Python**：

```python
for ext in ("pdf", "png"):
    fig.savefig(OUT / f"figures/{FIG_ID}.{ext}", dpi=300, bbox_inches="tight")
```

**MATLAB**：

```matlab
exportgraphics(fig, fullfile(figDir, [figId '.pdf']), 'ContentType', 'vector');
exportgraphics(fig, fullfile(figDir, [figId '.png']), 'Resolution', 300);
```

用 `exportgraphics` 而不是 `saveas`/`print` —— 它默认裁掉多余白边，且矢量输出更干净。

## 重跑纪律

**数据一变，对应图立刻在 `figures/manifest.md` 标 `stale` 并重跑脚本。**

绘图脚本读 `outputs/data/` 的文件，不重新计算数值 —— 这样重跑只是几秒钟的事。

**永远不要手工修图。** 手改的图无法复现，数据更新后无法同步，C3 独立审核一查
就露。要改就改脚本。
