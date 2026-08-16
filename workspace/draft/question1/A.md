# 问题一任务A：蔬菜类商品销售量的分布规律

## 一、建模思路

本部分仅刻画品类与单品的分布规律，相互关系分析在后续任务中展开。

品类日销量为连续正值，分布呈右偏长尾，故选用对数正态分布
（lognormal）与伽马分布（gamma）两类连续分布拟合，并以 AIC/BIC
选型。单品日销量存在大量无销售日，直接拟合单峰连续分布将严重失真，
故采用两阶段模型：第一阶段以售出概率刻画"当日是否销售"，第二阶段
以连续分布刻画"有销售日的条件销量分布"。有效销售天数较少的稀疏
单品，参数估计不可靠，仅报告经验分位数。

## 二、数据与统计口径

本部分使用清洗后的日销量汇总表：

| 文件 | 内容 |
| --- | --- |
| results/category_daily_sales.csv | 品类日销量（6 品类，6,474 个品类-日） |
| results/item_daily_sales.csv | 单品日销量（246 个有售单品，46,599 个单品-日） |

统计口径：

- 完整观测期 2020-07-01 至 2023-06-30，共 $T = 1095$ 天；
- 分布拟合仅使用正销量样本 $q > 0$；
- 单品有效销售天数 $n_i$ 为该单品产生销售的天数；
- 全部净销量为正值（品类最小日销量 0.252 kg）。

## 三、品类日销量的分布拟合

### 3.1 候选分布

对数正态分布：若一个变量的对数服从正态分布，则该变量服从对数正态
分布，记为 $X \sim \mathrm{LogNormal}(s, \mathrm{loc}, \mathrm{scale})$，
其密度函数为

$$f(x)=\frac{1}{(x-\mathrm{loc})\,s\sqrt{2\pi}}\exp\left(-\frac{[\ln((x-\mathrm{loc})/\mathrm{scale})]^2}{2s^2}\right),\quad x>\mathrm{loc}$$

其中 $s$ 为对数标准差，$\mathrm{scale}=e^\mu$（$\mu$ 为对数均值），
$\mathrm{loc}$ 为位置参数（支撑下界）。当 $\mathrm{loc}=0$ 时，
$\ln X \sim N(\ln \mathrm{scale}, s^2)$，且
$E[X]=\mathrm{scale}\cdot e^{s^2/2}$，
$\mathrm{Var}(X)=\mathrm{scale}^2(e^{s^2}-1)e^{s^2}$。

伽马分布：记为 $X \sim \mathrm{Gamma}(a, \mathrm{loc}, \mathrm{scale})$，
其密度函数为

$$f(x)=\frac{(x-\mathrm{loc})^{a-1}e^{-(x-\mathrm{loc})/\mathrm{scale}}}{\Gamma(a)\,\mathrm{scale}^a},\quad x>\mathrm{loc}$$

其中 $a$ 为形状参数，$\mathrm{scale}$ 为尺度参数，$\mathrm{loc}$ 为位置
参数。当 $\mathrm{loc}=0$ 时，$E[X]=a\cdot\mathrm{scale}$，
$\mathrm{Var}(X)=a\cdot\mathrm{scale}^2$。

两类分布均固定 $\mathrm{loc}=0$，使支撑为 $(0, \infty)$，与销量下界为 0
相符；固定 loc 亦避免位置参数自由估计带来的无意义平移。两个候选分布的
自由参数个数相同（均为 2），模型选择准则可直接比较。

### 3.2 参数估计与模型选择

设某品类正销量样本为 $x_1, \dots, x_n$，密度函数为 $f(x; \theta)$。
参数 $\theta$ 由最大似然估计（MLE）得到：

$$L(\theta)=\prod_{i=1}^{n} f(x_i;\theta),\qquad \mathrm{LLF}=\ln L(\hat\theta)=\sum_{i=1}^{n}\ln f(x_i;\hat\theta)$$

其中 $\hat\theta=\arg\max_\theta \mathrm{LLF}$ 为最大似然估计，负对数
似然 $\mathrm{NLL}=-\mathrm{LLF}$。AIC 与 BIC 在拟合优度基础上引入
参数复杂度惩罚，取值越小表示模型越优：

$$\mathrm{AIC}=2k-2\mathrm{LLF},\qquad \mathrm{BIC}=k\ln n-2\mathrm{LLF}$$

其中 $k$ 为自由参数个数（此处均为 2），$n$ 为正销量天数。本文以 AIC
进行正式选型，以 BIC 交叉核对。

### 3.3 拟合结果

各品类正销量天数分别为 1085、1084、1085、1050、1085、1085，合计 6,474。
AIC 选型结果：花叶类、花菜类、水生根茎类、茄类为伽马分布，辣椒类、
食用菌为对数正态分布；AIC 与 BIC 选型完全一致。独立重算 AIC 与输出
结果的偏差不超过 $5\times 10^{-4}$，可归因于输出数值保留三位小数。

| 品类 | 最优分布 | AIC |
| --- | --- | --- |
| 花叶类 | gamma | 12444.912 |
| 花菜类 | gamma | 9548.503 |
| 水生根茎类 | gamma | 9898.119 |
| 茄类 | gamma | 8059.611 |
| 辣椒类 | lognorm | 11037.887 |
| 食用菌 | lognorm | 10841.520 |

## 四、单品日销量的两阶段分布

### 4.1 模型设定

令 $Y_t = \mathbf{1}\{q_t > 0\}$ 表示第 $t$ 日是否销售，则
$Y_t \sim \mathrm{Bernoulli}(p_i)$。正销量的条件分布为
$q_t \mid Y_t = 1 \sim f(q; \theta_i)$，其中 $f$ 取对数正态或伽马分布，
按 AIC 选优。单品日销量的整体分布为混合分布：

$$f(q)=(1-p_i)\,\delta_0(q)+p_i\,f(q;\theta_i),\quad q\ge 0$$

其中 $\delta_0$ 为 0 点的点质量，$f(q; \theta_i)$ 为条件正销量密度。

售出概率取经验频率 $p_i = n_i / T$，即该单品日销售指示变量的最大似然
估计；条件分布参数 $\theta_i$ 由正销量样本的最大似然估计得到。

### 4.2 样本筛选与经验分位数

参数估计需要足够的正销量样本，故仅对 $n_i \ge 60$ 的单品进行拟合；
$n_i < 60$ 的稀疏单品只报告经验分位数。分位数的定义为

$$Q_\tau=\inf\{x: F(x)\ge\tau\},\quad \tau\in(0,1)$$

经验分位数由排序样本线性插值得到（numpy 默认口径）。$\tau=0.5$、$0.9$、
$0.99$ 对应的分位数（即输出表中的 P50、P90、P99）分别表示 50%、90%、
99% 的销售日销量不超过该值，用于描述中位水平与极端高峰日。

### 4.3 拟合结果

246 个有售单品中，132 个进入参数拟合（伽马 81 个、对数正态 51 个），
有效销售天数介于 61 至 1076 天，售出概率介于 0.0557 至 0.9826；114 个
稀疏单品仅报告经验分位数；另有 5 个单品无销售记录，不参与分析。经验
分位数、有效销售天数与售出概率均经独立重算校验，与输出结果一致
（最大偏差 $5\times 10^{-4}$，为舍入误差）。

## 五、图表说明

图 1（q1_dist_cat_qq.pdf）为各品类最优分布的 QQ 图。设 $F^{-1}(p)$ 与
$F_n^{-1}(p)$ 分别为理论分布与样本的经验分位数函数，QQ 图绘制
$(F^{-1}(p), F_n^{-1}(p))$ 在 $p \in (0, 1)$ 上的散点；点列越贴近直线
$y = x$，经验分布与理论分布越一致。各品类中部拟合良好、两端略有偏离，
说明分布主体可由所选分布近似。

图 2（q1_dist_item_sample.pdf）为代表性单品（高频、中频、稀疏各 2 个）
的拟合对比图：直方图为正销量样本的经验密度估计，曲线为最优分布密度。
该图直观展示高频单品分布较集中、稀疏单品波动较大的差异。

图表均输出为 PDF 矢量格式，图内不设大标题，图题由论文正文给出。

## 六、结论

品类日销量可由伽马或对数正态分布近似，其中 4 个品类的最优分布为伽马
分布，2 个品类为对数正态分布；单品日销量采用"售出概率 + 条件正销量
分布"的两阶段模型刻画零膨胀特征，稀疏单品以经验分位数描述。全部结果
经独立重算校验，可作为论文中分布规律部分的数值依据。

## 七、实现说明

- 脚本：code/question1/A.py；
- 运行环境：Python 3.13（scipy 1.17、matplotlib 3.10、pandas 3.0）；
- 运行命令：`D:\Python3.13.12\python.exe code\question1\A.py`；
- 输出文件：results/q1_dist_cat.csv、results/q1_dist_item.csv、
  results/q1_item_quantiles.csv、figures/q1_dist_cat_qq.pdf、
  figures/q1_dist_item_sample.pdf、code/question1/outputs/A.log。

## 八、文献依据

| 推论/方法 | 文献 | 具体支撑点 |
| --- | --- | --- |
| 品类日销量用 lognormal/gamma 拟合 | [8] | 库存需求常用连续分布刻画 |
| AIC/BIC 选型 | [1][2] | 似然-复杂度权衡[1]；维度惩罚[2] |
| 单品两阶段模型处理零膨胀 | [5] | 两阶段模型刻画超额零 |
| 稀疏单品只给经验分位数 | [4] | 小样本下参数估计与检验不可靠 |

## 九、参考文献（编号沿用主参考文献表，仅列本文引用条目）

[1] Akaike H. A new look at the statistical model identification[J].
IEEE Transactions on Automatic Control, 1974, 19(6): 716-723.
doi:10.1109/TAC.1974.1100705

[2] Schwarz G. Estimating the dimension of a model[J].
The Annals of Statistics, 1978, 6(2): 461-464.
doi:10.1214/aos/1176344136

[4] D'Agostino R B, Stephens M A. Goodness-of-Fit Techniques[M].
New York: Marcel Dekker, 1986.

[5] Mullahy J. Specification and testing of some modified count data
models[J]. Journal of Econometrics, 1986, 33(3): 341-365.
doi:10.1016/0304-4076(86)90002-3

[8] Silver E A, Pyke D F, Thomas D J. Inventory and Production Management
in Supply Chains[M]. 4th ed. Boca Raton: CRC Press, 2016.
