# 计算结果

> 当前完成：数据读取与预处理（任务 1）、问题一分布拟合（任务 A）、
> 问题一季节分解（任务 B）、问题一协同变动网络（任务 C）、
> 问题一时序特征聚类（任务 D）。

## 运行环境

- Python 3.12（Codex 工作区运行时）
- pandas 3.0.1、numpy、openpyxl 3.1.5
- 脚本：`code/clean_data.py`，运行命令 `python code/clean_data.py`
- 问题一任务 A：Python 3.13.12（D:\Python3.13.12\python.exe）、
  pandas 3.0.2、scipy 1.17.1、matplotlib 3.10.8
- 脚本：`code/question1/A.py`，运行命令
  `D:\Python3.13.12\python.exe code\question1\A.py`
- 问题一任务 B：Python 3.13.12、statsmodels 0.14.6、scipy 1.17.1、
  matplotlib 3.10.8、pandas 3.0.2
- 脚本：`code/question1/B.py`，运行命令
  `D:\Python3.13.12\python.exe code\question1\B.py`
- 问题一任务 C：Python 3.13.12、numpy、pandas、scipy、networkx、
  matplotlib
- 脚本：`code/question1/C.py`，运行命令
  `D:\Python3.13.12\python.exe code\question1\C.py`
- 问题一任务 D：Python 3.13.12、numpy、pandas、scipy、sklearn、
  matplotlib、chinese-calendar
- 脚本：`code/question1/D.py`，运行命令
  `D:\Python3.13.12\python.exe code\question1\D.py`

## 数据读取与预处理

### 输入与口径

| 附件 | 内容 | 原始规模 |
| --- | --- | --- |
| 附件1 | 商品信息（251 单品、6 品类） | 251 × 4 |
| 附件2 | 销售流水（2020-07-01 ~ 2023-06-30） | 878,503 × 7 |
| 附件3 | 批发价格（2020-07-01 ~ 2023-06-30） | 55,982 × 3 |
| 附件4 | 损耗率（单品级 251 条 + 分类级 6 条） | 251 × 3 |

清洗口径：

- 退货按负销量并入当日净销量（净销量 = 售出 − 退货）；销售额、均价、打折拆分只用“销售”记录计算。
- 单品日批发价：按单品按日前向填充（ffill），仍缺失用单品历史均值补齐，并标记价格来源。
- 品类日批发价：等权均值 + 按当日售出量加权均值两种口径。
- 损耗率：单品级取自附件 4 Sheet1，分类级取自附件 4 分类表，与附件 1 分类编码对齐。

### 输出文件（results/，UTF-8 with BOM）

| 文件 | 行数 | 用途 |
| --- | --- | --- |
| item_info.csv | 251 | 单品信息 + 单品/分类损耗率 |
| item_daily_sales.csv | 46,599 | 单品日销量、均价、打折拆分 |
| category_daily_sales.csv | 6,474 | 品类日销量、均价、打折拆分 |
| item_daily_wholesale.csv | 274,845 | 单品日批发价（补齐后） |
| category_daily_wholesale.csv | 6,570 | 品类日批发价（均值/加权） |
| item_daily_full.csv | 46,599 | 单品日汇总（销量+价格+批发价+损耗率+加价率） |
| category_daily_full.csv | 6,474 | 品类日汇总 |
| data_profile.json | — | 校验摘要 |

`item_daily_full.csv` 与 `category_daily_full.csv` 是后续问题一至三建模的直接输入。

> 输出表头统一使用中文（如 `单品编码`、`净销量`、`批发价`），代码直接使用中文列名，不做二次映射。

## 约束与一致性校验

- 附件2 日期范围 2020-07-01 ~ 2023-06-30，与题面一致。
- 附件2 原始 878,503 行；退货 461 行；售出总量 471,275.839 kg，退货总量 299.921 kg。
- 有销售单品 246 个（附件1/3/4 为 251 个，5 个单品无销售记录，为新品或未售，选品时剔除）。
- 附件3 覆盖 251 个单品，价格补齐后单品×日 = 251 × 1095 = 274,845 行。
- 单品日批发价中“单品均值补齐”占 35.45%（早于首次有价日期的部分），为合理近似，后续模型灵敏度中考察。
- 单品日表仅 4 行（纯退货日）均价为空，属预期。

## 可复现运行方式

```bash
python code/clean_data.py
D:\Python3.13.12\python.exe code\question1\A.py
D:\Python3.13.12\python.exe code\question1\B.py
D:\Python3.13.12\python.exe code\question1\C.py
D:\Python3.13.12\python.exe code\question1\D.py
```

清洗脚本自动从 `../Problem/` 读取附件，输出写入 `results/`；任务 A 脚本
至任务 D 脚本读取 `results/` 汇总表，输出写入 `results/`、`figures/` 与
`code/question1/outputs/`。

## 问题一结果

### 任务 A：品类与单品销量分布拟合

方法：

- 品类级：对 6 个品类的正日净销量分别拟合 lognorm 与 gamma（固定
  loc=0），按 AIC 选型，BIC 作为交叉核对；
- 单品级：两阶段模型，阶段一为售出概率（有效销售天数/1095），阶段二为
  正销量分布（lognorm 或 gamma 按 AIC 选优）；有效销售天数 >= 60 的单品
  才做参数拟合，其余只输出经验分位数 P50/P75/P90/P95/P99。

关键数值：

- 品类级最优分布：gamma 在 4 个品类最优，lognorm 在 2 个品类最优；

| 分类编码 | 分类名称 | 最优分布 | AIC |
| --- | --- | --- | --- |
| 1011010101 | 花叶类 | gamma | 12444.912 |
| 1011010201 | 花菜类 | gamma | 9548.503 |
| 1011010402 | 水生根茎类 | gamma | 9898.119 |
| 1011010501 | 茄类 | gamma | 8059.611 |
| 1011010504 | 辣椒类 | lognorm | 11037.887 |
| 1011010801 | 食用菌 | lognorm | 10841.520 |

- 单品级：有售单品 246 个，132 个满足 60 天门槛进入参数拟合
  （gamma 81 个、lognorm 51 个），114 个稀疏单品只给分位数；
  5 个单品无销售记录，不参与分布分析；
- 拟合单品的有效销售天数范围 61~1076，售出概率范围 0.0557~0.9826。

输出文件（results/ 与 figures/）：

| 文件 | 行数 | 说明 |
| --- | --- | --- |
| q1_dist_cat.csv | 12 | 6 品类 x 2 分布的参数、负对数似然、AIC、BIC、最优标记 |
| q1_dist_item.csv | 132 | 单品两阶段拟合参数与 AIC |
| q1_item_quantiles.csv | 246 | 单品经验分位数 P50/P75/P90/P95/P99 |
| q1_dist_cat_qq.pdf | - | 品类最优分布 QQ 图（6 面板，图内无大标题） |
| q1_dist_item_sample.pdf | - | 高频/中频/稀疏代表单品拟合对比图 |
| code/question1/outputs/A.log | - | 运行日志（时间、最优分布计数） |

校验：

- 选型以 AIC/BIC 为准；K-S 检验在参数估计后 p 值偏保守且大样本下几乎
  必然拒绝，仅用 QQ 图做图形诊断；
- 单品 60 天门槛与 draft/question1/A.md 任务 A 一致；
- 输入核对：品类日表 6,474 行、单品日表 46,599 行，净销量全部为正，
  与 data_profile.json 一致。

### 任务 B：STL 季节分解

方法：

- 每品类按完整日历（T = 1095 天）补零，共 6,570 个品类-日（补零 96 个）；
- 使用 statsmodels STL（period=7、robust=True）分解为趋势、季节、残差；
- 按方差分解计算季节强度与趋势强度；
- 年季节用月度聚合，旺季取 4-10 月、淡季取 11-3 月，输出旺季比值。

关键数值：

- 季节强度介于 0.1729 至 0.2616，趋势强度介于 0.5135 至 0.6268；
- 旺季比值大于 1 的品类：花叶类 1.0945、花菜类 1.0089、茄类 1.5412；
  水生根茎类 0.6462、辣椒类 0.8696、食用菌 0.6343，淡季销量更高；
- 季节强度、趋势强度与旺季比值独立重算最大偏差 5 x 10^-5。

输出文件（results/ 与 figures/）：

| 文件 | 行数 | 说明 |
| --- | --- | --- |
| q1_stl_fit.csv | 6,570 | 每品类逐日净销量、趋势、季节、残差 |
| q1_seasonal_strength.csv | 6 | 季节强度、趋势强度、旺季/淡季均值与比值 |
| q1_monthly_mean.csv | 72 | 品类 x 月份平均日销量 |
| q1_stl.pdf | - | 6 品类 STL 三分量图（6 面板，图内无大标题） |
| q1_monthly_mean.pdf | - | 月度均值柱状图（4-10 月高亮） |
| code/question1/outputs/B.log | - | 运行日志（时间、强度与比值） |

校验：

- 分解表无缺失值，行数 6 x 1095 = 6,570 与完整日历一致；
- 强度与比值独立重算一致（偏差由数值舍入引起）；
- 结论：旺季假设仅对花叶类、花菜类、茄类成立。

### 任务 C：去季节相关性与协同变动网络

方法：

- 单品日销量按完整日历补零，有效销售天数 >= 60 的单品进入分析
  （132 个）；
- 星期/月份虚拟变量 OLS 残差化，去除日历效应；
- 残差 Spearman 秩相关，BH-FDR 校正，|r| >= 0.4 且 q < 0.05 建边；
- 前后半样本（2020-07 至 2021-12、2022-01 至 2023-06）检验，稳健边
  构建协同变动网络并计算中心度。

关键数值：

- 共 8,646 个单品对；主边 1,062 条（正相关 820、负相关 242），
  稳健边 154 条，稳健网络包含 51 个节点；
- 阈值敏感性：0.3 阈值 1848 条边、0.4 阈值 1062 条、0.5 阈值 523 条，
  对应稳健边 249 / 154 / 81；
- 品类级相关较强组合：花叶类-食用菌 0.651、花叶类-辣椒类 0.636、
  辣椒类-食用菌 0.638；茄类与其他品类 |r| < 0.14；
- 独立重算抽样 200 条边，相关系数最大偏差 5 x 10^-5，q 值与
  statsmodels 的 BH 校正一致。

输出文件（results/ 与 figures/）：

| 文件 | 行数 | 说明 |
| --- | --- | --- |
| q1_corr_edges.csv | 1,062 | 主边：编码、名称、相关系数、p 值、FDR q 值、符号、是否稳健 |
| q1_network_top.csv | 51 | 稳健网络节点中心度与正/负边数 |
| q1_corr_threshold.csv | 3 | 阈值敏感性：0.3/0.4/0.5 边数与稳健边数 |
| q1_corr_heatmap_cat.pdf | - | 品类级 6x6 相关热图 |
| q1_corr_network.pdf | - | 单品级协同变动网络（红正蓝负） |
| code/question1/outputs/C.log | - | 运行日志 |

校验：全部输出无缺失值；抽样重算与阈值表核对一致。

### 任务 D：单品时序特征层次聚类

方法：

- 提取六维时序特征：售出天数占比、有售日均销量、有售日变异系数、
  周末偏置、节假日脉冲（chinese-calendar 法定节假日含调休）、
  总销量占比；
- 有效销售天数 >= 60 的 132 个单品，特征 z-score 标准化后取欧式距离，
  Ward 层次聚类；
- 簇数 k 在 3-10 扫描，取 silhouette 最大且不小于 0.15 的 k；
- 80% 抽样重复聚类 50 次，以平均 ARI 报告稳定性。

关键数值：

- 最优簇数 k = 5，silhouette 0.2583，稳定性 ARI 0.4567；
- 簇大小 13 / 7 / 55 / 34 / 23，命名分别为高量周末脉冲型、高频平稳型、
  低频稀疏型、低频脉冲型、周末脉冲型；
- 聚类标签与独立重算的 Ward 聚类完全一致，特征最大偏差约 1e-14。

输出文件（results/ 与 figures/）：

| 文件 | 行数 | 说明 |
| --- | --- | --- |
| q1_item_cluster.csv | 132 | 单品特征与簇标签 |
| q1_cluster_profile.csv | 5 | 簇画像与建议命名 |
| q1_cluster_k.csv | 8 | 候选 k 的 silhouette 与最优 k 的 ARI |
| q1_dendrogram.pdf | - | Ward 树状图 |
| q1_silhouette.pdf | - | silhouette 曲线（标注 k=5） |
| q1_cluster_profile.pdf | - | 各簇标准化特征均值曲线 |
| code/question1/outputs/D.log | - | 运行日志 |

校验：全部输出无缺失值；标签与特征独立重算一致。

## 问题二结果

待任务 3 完成后补充。

## 问题三结果

待任务 4 完成后补充。

## 灵敏度分析

待任务 5 完成后补充。

## 与建模报告的一致性说明

数据处理口径与建模稿（draft/ANALYSIS_0.md）第 2 节一致：退货并入净销量、
损耗率从补货侧补偿、批发价 ffill + 均值补齐。问题一任务 A 的方法与
draft/question1/A.md 完全一致（分布候选、AIC/BIC 选型、60 天单品门槛、
两阶段模型、经验分位数口径）；任务 B 的方法与 draft/question1/B.md
一致（STL 周季节、强度公式、月度聚合与旺季比值口径）；任务 C 与
draft/question1/C.md 一致（残差化、Spearman、FDR、稳健网络口径）；
任务 D 与 draft/question1/D.md 一致（六维特征、Ward、silhouette、
ARI 口径）。
