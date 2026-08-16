# 问题一任务C：品类与单品销售量的协同变动关系

## 一、建模思路

单品日销量同时受日历效应（星期、月份）与自身需求规律驱动，直接计算
相关系数会产生大量由共同季节因素导致的伪相关。本文先剔除星期与月份
效应取残差，再计算 Spearman 秩相关；以 BH-FDR 控制多重检验后按相关系数
阈值建边，并通过前后半样本检验筛选稳健边，最终以稳健边构建协同变动
网络并计算中心度。

## 二、数据与统计口径

输入：results/item_daily_sales.csv、results/category_daily_sales.csv。

统计口径：

- 完整观测期 2020-07-01 至 2023-06-30，共 $T=1095$ 天；
- 单品日销量按完整日历补零，有效销售天数 $n_i \ge 60$ 的单品进入分析
  （共 132 个）；
- 日历效应控制变量：星期虚拟变量（基准周一）与月份虚拟变量（基准 1 月），
  含截距项。

## 三、方法

### 3.1 日历效应残差

对每个单品 $i$ 拟合线性模型

$$q_{it}=\alpha_i+\sum_{k=1}^{6}\delta_k D^{\mathrm{wk}}_{kt}
+\sum_{m=1}^{11}\eta_m D^{\mathrm{mo}}_{mt}+\varepsilon_{it}$$

其中 $D^{\mathrm{wk}}_{kt}$ 与 $D^{\mathrm{mo}}_{mt}$ 分别为星期与月份
虚拟变量，参数由最小二乘估计。残差

$$e_{it}=q_{it}-\hat q_{it}$$

作为去日历效应后的销量序列。

### 3.2 Spearman 秩相关

对残差序列按日秩变换，取 Pearson 相关作为 Spearman 秩相关系数

$$r_{ij}=\mathrm{corr}\big(\mathrm{rank}(e_i),\,\mathrm{rank}(e_j)\big)$$

在原假设 $r_{ij}=0$ 下，

$$t=\frac{r_{ij}\sqrt{n-2}}{\sqrt{1-r_{ij}^2}}\sim t_{n-2}$$

双侧 $p$ 值为 $p=2\big(1-F_t(|t|;n-2)\big)$。

### 3.3 多重检验与建边

对全部 $m$ 个单品对的 $p$ 值做 BH-FDR 校正：

$$q_{(i)}=\min_{j\ge i}\left\{\frac{m}{j}p_{(j)}\right\}$$

其中 $p_{(1)}\le\cdots\le p_{(m)}$ 为排序后的 $p$ 值。建边条件为

$$|r_{ij}|\ge 0.4,\qquad q_{ij}<0.05$$

### 3.4 前后半样本稳定性检验

将样本按时间分为前半（2020-07-01 至 2021-12-31）与后半
（2022-01-01 至 2023-06-30），分别执行相同的残差化与秩相关检验。
若某条边在两半中均满足 $p<0.05$，且符号与全样本一致，则记为稳健边。

### 3.5 协同变动网络

以单品为节点、稳健边为边构建无向图，边权为相关系数，按符号区分正相关
与负相关；节点中心性采用度中心度与介数中心度。

## 四、结果

进入分析的 132 个单品共 8,646 个单品对。满足 $|r|\ge0.4$ 且
$q<0.05$ 的主边共 1,062 条，其中正相关 820 条、负相关 242 条；
通过前后半样本检验的稳健边 154 条，构成包含 51 个节点的协同变动网络。

相关系数阈值敏感性：

| 阈值 | 边数 | 正边数 | 负边数 | 稳健边数 |
| --- | ---: | ---: | ---: | ---: |
| 0.3 | 1848 | 1289 | 559 | 249 |
| 0.4 | 1062 | 820 | 242 | 154 |
| 0.5 | 523 | 456 | 67 | 81 |

品类级去季节残差的 Spearman 相关中，花叶类与食用菌（0.651）、花叶类与
辣椒类（0.636）、辣椒类与食用菌（0.638）相关较强；茄类与其余品类的
相关最弱（|r| 均小于 0.14）。

独立重算校验：随机抽取 200 条主边重算相关系数与 FDR $q$ 值，相关系数
最大偏差 $5\times10^{-5}$，$q$ 值与 statsmodels 的 BH 校正结果一致；
全部输出无缺失值。

## 五、图表说明

图 1（q1_corr_heatmap_cat.pdf）为品类级去季节残差的 6x6 Spearman 相关
热图，格内标注相关系数，颜色越深表示相关越强。

图 2（q1_corr_network.pdf）为单品级协同变动网络：红色边表示正相关、
蓝色边表示负相关，节点大小与度数成正比，并标注中心度最高的 10 个单品。

图表均输出为 PDF 矢量格式，图内不设大标题，图题由论文正文给出。

## 六、结论

去除日历效应后，多数品类与单品销量呈正向同步变动，负相关边占比约
23%（242/1062），可作为潜在替代候选；茄类销量与其他品类相对独立。
替代与互补关系的最终判定需结合问题二的交叉价格弹性。

## 七、实现说明

- 脚本：code/question1/C.py；
- 运行环境：Python 3.13（numpy、pandas、scipy、networkx、matplotlib）；
- 运行命令：`D:\Python3.13.12\python.exe code\question1\C.py`；
- 输出文件：results/q1_corr_edges.csv、results/q1_network_top.csv、
  results/q1_corr_threshold.csv、figures/q1_corr_heatmap_cat.pdf、
  figures/q1_corr_network.pdf、code/question1/outputs/C.log。

## 八、文献依据

| 推论/方法 | 支撑文献 | 具体支撑点 |
| --- | --- | --- |
| 日历效应残差避免伪相关 | [13][14][15] | 时间序列伪相关[13][14]；虚拟变量回归[15] |
| Spearman 秩相关 | [12] | 秩相关定义与动机 |
| BH-FDR 多重检验 | [16] | FDR 控制方法 |
| 相关矩阵阈值建网 | [17][18] | 相关网络构建与弱边过滤 |
| 网络中心度 | [19][20] | 中心度度量与网络分析 |
| 正相关不等于互补/替代 | [21][22] | 替代与互补由交叉价格效应定义 |

## 九、参考文献（编号沿用主参考文献表，仅列本文引用条目）

[12] Spearman C. The proof and measurement of association between two
things[J]. American Journal of Psychology, 1904, 15(1): 72-101.
doi:10.2307/1412159

[13] Yule G U. Why do we sometimes get nonsense correlations between
time-series? A study in sampling and the nature of time-series[J].
Journal of the Royal Statistical Society, 1926, 89(1): 1-63.
doi:10.1111/j.2397-2335.1926.tb01829.x

[14] Granger C W J, Newbold P. Spurious regressions in econometrics[J].
Journal of Econometrics, 1974, 2(2): 111-120.
doi:10.1016/0304-4076(74)90034-7

[15] Wooldridge J M. Econometric Analysis of Cross Section and Panel
Data[M]. 2nd ed. Cambridge, MA: MIT Press, 2010.

[16] Benjamini Y, Hochberg Y. Controlling the false discovery rate:
A practical and powerful approach to multiple testing[J].
Journal of the Royal Statistical Society: Series B, 1995, 57(1): 289-300.
doi:10.1111/j.2517-6161.1995.tb02031.x

[17] Tumminello M, Aste T, Di Matteo T, et al. A tool for filtering
information in complex systems[J]. Proceedings of the National Academy of
Sciences, 2005, 102(30): 10421-10426. doi:10.1073/pnas.0500298102

[18] Mantegna R N. Hierarchical structure in financial markets[J].
The European Physical Journal B, 1999, 11(1): 193-197.
doi:10.1007/s100510050929

[19] Freeman L C. A set of measures of centrality based on betweenness[J].
Sociometry, 1977, 40(1): 35-41. doi:10.2307/3033543

[20] Wasserman S, Faust K. Social Network Analysis: Methods and
Applications[M]. Cambridge: Cambridge University Press, 1994.

[21] Deaton A, Muellbauer J. Economics and Consumer Behavior[M].
Cambridge: Cambridge University Press, 1980.

[22] Mas-Colell A, Whinston M D, Green J R. Microeconomic Theory[M].
New York: Oxford University Press, 1995.
