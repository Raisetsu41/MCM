# 问题一任务D：单品销售时序特征的层次聚类

## 一、建模思路

单品在销售频率、销量水平、波动幅度与日历响应上存在系统性差异。本文从
日频时序中提取六维特征刻画每个单品，经标准化后以 Ward 层次聚类分组；
簇数由 silhouette 指标确定，并以 80% 抽样重复聚类计算 ARI 评估稳定性。
聚类结果可作为问题三差异化选品与定价的分组依据。

## 二、数据与统计口径

输入：results/item_daily_sales.csv。

统计口径：

- 完整观测期 2020-07-01 至 2023-06-30，共 $T=1095$ 天；
- 单品日销量按完整日历补零；
- 有效销售天数 $n_i \ge 60$ 的单品进入聚类（共 132 个）；
- 节假日集合 $H$ 取中国法定节假日（含调休），由 chinese-calendar
  提供。

## 三、方法

### 3.1 时序特征定义

对每个单品 $i$ 定义六维特征：

$$\mathrm{售出天数占比}\quad p_i=\frac{n_i}{T}$$

$$\mathrm{有售日均销量}\quad \mu_i=\frac{1}{n_i}\sum_{q_{it}>0}q_{it}$$

$$\mathrm{有售日变异系数}\quad \mathrm{CV}_i=\frac{1}{\mu_i}
\sqrt{\frac{1}{n_i}\sum_{q_{it}>0}(q_{it}-\mu_i)^2}$$

$$\mathrm{周末偏置}\quad w_i=\frac{\bar q_{i,\mathrm{weekend}}}
{\bar q_{i,\mathrm{weekday}}}-1$$

$$\mathrm{节假日脉冲}\quad h_i=\frac{\bar q_{i,\mathrm{holiday}}}
{\bar q_{i,\mathrm{non-holiday}}}-1$$

$$\mathrm{总销量占比}\quad s_i=\frac{\sum_t q_{it}}
{\sum_j\sum_t q_{jt}}$$

其中均值均基于补零后的完整日序列计算，变异系数仅基于正销量样本，
避免零值膨胀失真。

### 3.2 标准化与层次聚类

对六维特征做 z-score 标准化，再计算欧式距离并采用 Ward 最小方差法
层次聚类，输出树状图。

### 3.3 簇数选择与稳定性

对 $k\in\{3,\dots,10\}$ 分别计算 silhouette 系数，取 silhouette 最大且
不小于 0.15 的 $k$。稳定性评估：随机抽取 80% 单品重复聚类 50 次，
以 adjusted rand index（ARI）度量抽样结果与全量聚类的一致性，
取平均值报告。

## 四、结果

132 个单品的最优簇数为 $k=5$，对应 silhouette 系数 0.2583；50 次
80% 抽样聚类的平均 ARI 为 0.4567，聚类结构基本稳定。

| 簇 | 单品数 | 售出天数占比 | 有售日均销量 | 有售日变异系数 | 周末偏置 | 节假日脉冲 | 总销量占比 | 建议命名 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| 1 | 13 | 0.3236 | 27.4374 | 0.6927 | 0.3466 | 0.3544 | 0.0207 | 高量周末脉冲型 |
| 2 | 7 | 0.8384 | 20.7024 | 0.7215 | 0.4876 | 0.5192 | 0.0414 | 高频平稳型 |
| 3 | 55 | 0.2053 | 4.7746 | 0.7616 | 0.2129 | 0.2126 | 0.0025 | 低频稀疏型 |
| 4 | 34 | 0.1908 | 6.1442 | 0.7681 | 0.5531 | 0.5963 | 0.0028 | 低频脉冲型 |
| 5 | 23 | 0.5631 | 7.3427 | 1.0807 | 0.3617 | 0.4005 | 0.0091 | 周末脉冲型 |

聚类标签与独立重算的 Ward 聚类结果完全一致，特征值最大偏差约
$10^{-14}$（浮点精度），ARI 重算结果一致，全部输出无缺失值。

## 五、图表说明

图 1（q1_dendrogram.pdf）为 Ward 层次聚类树状图，展示单品逐级合并的
层次结构。

图 2（q1_silhouette.pdf）为 $k\in\{3,\dots,10\}$ 的 silhouette 曲线，
红色虚线标出最优簇数 $k=5$。

图 3（q1_cluster_profile.pdf）为各簇标准化特征均值曲线，反映簇间的
特征差异，与表 1 的画像相互印证。

图表均输出为 PDF 矢量格式，图内不设大标题，图题由论文正文给出。

## 六、结论

单品可按日频时序特征划分为高频平稳、高量周末脉冲、低频稀疏、低频脉冲
与周末脉冲五类。高频平稳类适合作为稳定主销单品，脉冲类可用于节假日与
周末备货，低频稀疏类在选品与定价时需谨慎处理。该分组可直接为问题三
提供候选单品集合与差异化定价依据。

## 七、实现说明

- 脚本：code/question1/D.py；
- 运行环境：Python 3.13（numpy、pandas、scipy、sklearn、matplotlib、
  chinese-calendar）；
- 运行命令：`D:\Python3.13.12\python.exe code\question1\D.py`；
- 输出文件：results/q1_item_cluster.csv、results/q1_cluster_profile.csv、
  results/q1_cluster_k.csv、figures/q1_dendrogram.pdf、
  figures/q1_silhouette.pdf、figures/q1_cluster_profile.pdf、
  code/question1/outputs/D.log。

## 八、文献依据

| 推论/方法 | 支撑文献 | 具体支撑点 |
| --- | --- | --- |
| 日频时序特征聚类 | [10] | 特征化时序聚类框架 |
| 周末/节假日日历特征 | [11][15] | 日历变量进入回归与特征建模 |
| Ward 层次聚类 | [23][24] | Ward 准则及其算法实现 |
| 标准化后欧式距离 | [25] | 尺度差异影响距离度量 |
| silhouette 选簇数 | [26] | 轮廓系数作为内部验证指标 |
| ARI 稳定性评估 | [27] | 划分一致性校正指标 |

## 九、参考文献（编号沿用主参考文献表，仅列本文引用条目）

[10] Wang X, Smith K, Hyndman R. Characteristic-based clustering for time
series data[J]. Data Mining and Knowledge Discovery, 2006, 13(3): 335-364.
doi:10.1007/s10618-005-0039-x

[11] Hyndman R J, Athanasopoulos G. Forecasting: Principles and Practice[M].
2nd ed. Melbourne: OTexts, 2018. https://otexts.com/fpp2/

[15] Wooldridge J M. Econometric Analysis of Cross Section and Panel
Data[M]. 2nd ed. Cambridge, MA: MIT Press, 2010.

[23] Ward J H. Hierarchical grouping to optimize an objective function[J].
Journal of the American Statistical Association, 1963, 58(301): 236-244.
doi:10.1080/01621459.1963.10500845

[24] Murtagh F, Legendre P. Ward's hierarchical agglomerative clustering
method: Which algorithms implement Ward's criterion?[J].
Journal of Classification, 2014, 31(3): 274-295.
doi:10.1007/s00357-014-9161-z

[25] Kaufman L, Rousseeuw P J. Finding Groups in Data: An Introduction to
Cluster Analysis[M]. New York: Wiley, 1990.

[26] Rousseeuw P J. Silhouettes: A graphical aid to the interpretation and
validation of cluster analysis[J]. Journal of Computational and Applied
Mathematics, 1987, 20: 53-65. doi:10.1016/0377-0427(87)90125-7

[27] Hubert L, Arabie P. Comparing partitions[J].
Journal of Classification, 1985, 2(1): 193-218. doi:10.1007/BF01908075
