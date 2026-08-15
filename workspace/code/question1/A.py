# 任务A: 品类/单品销量分布拟合
# 输入 results/ 日销量表, 输出 results/ 拟合表与 figures/ 图

from datetime import datetime
from pathlib import Path
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results"
FIG = ROOT / "figures"
LOG_DIR = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
t = 1096
n_day_min = 60
dists = {"lognorm": stats.lognorm, "gamma": stats.gamma}
k = {"lognorm": 2, "gamma": 2}
DEBUG = True

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def fit(x, name):
  d = dists[name]
  par = d.fit(x, floc=0)
  llf = np.sum(d.logpdf(x, *par))
  aic = 2 * k[name] - 2 * llf
  bic = k[name] * np.log(len(x)) - 2 * llf
  return par, llf, aic, bic


def par_str(name, par):
  if name == "lognorm":
    return f"s={par[0]:.4f}, loc={par[1]:.4f}, scale={par[2]:.4f}"
  return f"a={par[0]:.4f}, loc={par[1]:.4f}, scale={par[2]:.4f}"


def best_fit(x):
  best = None
  for name in dists:
    par, llf, aic, bic = fit(x, name)
    if best is None or aic < best[2]:
      best = (name, par, aic)
  return best


def dist_cat():
  df = pd.read_csv(OUT / "category_daily_sales.csv", encoding="utf-8-sig")
  rows = []
  for c, g in df.groupby("分类编码"):
    x = g["净销量"].values
    x = x[x > 0]
    if DEBUG:
      print("[debug] cat", c, "positive days:", len(x))
    res = []
    for name in dists:
      par, llf, aic, bic = fit(x, name)
      res.append((name, par, llf, aic, bic))
    best = min(res, key=lambda r: r[3])
    for name, par, llf, aic, bic in res:
      rows.append({"分类编码": c, "分类名称": g["分类名称"].iloc[0],
                   "分布": name, "参数": par_str(name, par),
                   "负对数似然": round(-llf, 3), "AIC": round(aic, 3),
                   "BIC": round(bic, 3),
                   "是否最优": "是" if name == best[0] else "否"})
  out = pd.DataFrame(rows)
  out.to_csv(OUT / "q1_dist_cat.csv", index=False, encoding="utf-8-sig")


def dist_item():
  df = pd.read_csv(OUT / "item_daily_sales.csv", encoding="utf-8-sig")
  df = df[df["净销量"] > 0]
  n = df.groupby("单品编码").agg(n=("净销量", "size"),
                                  name=("单品名称", "first"),
                                  cat=("分类名称", "first"))
  if DEBUG:
    print("[debug] items:", len(n))
    print("[debug] sale-day min/med/max:", n["n"].min(), n["n"].median(),
          n["n"].max())
  rows, qs = [], []
  for code, r in n.iterrows():
    x = df.loc[df["单品编码"] == code, "净销量"].values
    nd = int(r["n"])
    q = np.percentile(x, [50, 75, 90, 95, 99])
    qs.append({"单品编码": code, "单品名称": r["name"], "有效销售天数": nd,
               "P50": round(q[0], 3), "P75": round(q[1], 3),
               "P90": round(q[2], 3), "P95": round(q[3], 3),
               "P99": round(q[4], 3)})
    if nd < n_day_min:
      continue
    name, par, aic = best_fit(x)
    rows.append({"单品编码": code, "单品名称": r["name"], "分类名称": r["cat"],
                 "有效销售天数": nd, "售出概率": round(nd / t, 4),
                 "分布": name, "参数": par_str(name, par),
                 "AIC": round(aic, 3), "是否最优": "是"})
  pd.DataFrame(qs).to_csv(OUT / "q1_item_quantiles.csv", index=False,
                          encoding="utf-8-sig")
  pd.DataFrame(rows).to_csv(OUT / "q1_dist_item.csv", index=False,
                            encoding="utf-8-sig")
  if DEBUG:
    print("[debug] fitted:", len(rows), "sparse:", len(qs) - len(rows))
  return df


def sample_codes(df):
  n = df.groupby("单品编码")["净销量"].size()
  hi = n.nlargest(2).index.tolist()
  mid = n.iloc[(n - n.median()).abs().argsort()[:2]].index.tolist()
  sp = n[n < n_day_min].nlargest(2).index.tolist()
  return hi + mid + sp


def qq_cat():
  df = pd.read_csv(OUT / "category_daily_sales.csv", encoding="utf-8-sig")
  fig, axs = plt.subplots(2, 3, figsize=(12, 8))
  for ax, (c, g) in zip(axs.ravel(), df.groupby("分类编码")):
    x = g["净销量"].values
    x = x[x > 0]
    name, par, aic = best_fit(x)
    stats.probplot(x, dist=dists[name], sparams=par, plot=ax)
    ax.set_xlabel("理论分位数", fontsize=9)
    ax.set_ylabel("样本分位数", fontsize=9)
    ax.text(0.04, 0.96, f"{g['分类名称'].iloc[0]}  {name} AIC={aic:.1f}",
            transform=ax.transAxes, va="top", fontsize=8)
  fig.tight_layout()
  fig.savefig(FIG / "q1_dist_cat_qq.pdf")
  plt.close(fig)


def fig_item(df):
  codes = sample_codes(df)
  fig, axs = plt.subplots(2, 3, figsize=(14, 8))
  for ax, code in zip(axs.ravel(), codes):
    g = df[df["单品编码"] == code]
    x = g["净销量"].values
    nd = len(x)
    ax.hist(x, bins=30, density=True, alpha=0.6, color="#4C72B0",
            label=f"{g['单品名称'].iloc[0]}  n={nd}")
    if nd >= n_day_min:
      name, par, aic = best_fit(x)
      xs = np.linspace(x.min(), x.max(), 200)
      ax.plot(xs, dists[name].pdf(xs, *par), color="C3", lw=1.5,
              label=f"{name} AIC={aic:.1f}")
    ax.set_xlabel("日净销量(千克)", fontsize=9)
    ax.set_ylabel("密度", fontsize=9)
    ax.legend(fontsize=8)
  fig.tight_layout()
  fig.savefig(FIG / "q1_dist_item_sample.pdf")
  plt.close(fig)


def main():
  t0 = time.time()
  dist_cat()
  df = dist_item()
  qq_cat()
  fig_item(df)
  c = pd.read_csv(OUT / "q1_dist_cat.csv", encoding="utf-8-sig")
  it = pd.read_csv(OUT / "q1_dist_item.csv", encoding="utf-8-sig")
  qt = pd.read_csv(OUT / "q1_item_quantiles.csv", encoding="utf-8-sig")
  if DEBUG:
    print("[debug] cat rows:", len(c))
    print("[debug] winners:", c.loc[c["是否最优"] == "是", "分布"].tolist())
    print("[debug] item fitted:", len(it), "sparse:",
          len(qt) - len(it), "no-sale:", 251 - len(qt))
    print("[debug] nd range:", it["有效销售天数"].min(),
          it["有效销售天数"].max())
    print("[debug] nan total:", int(c.isna().sum().sum()
                                    + it.isna().sum().sum()
                                    + qt.isna().sum().sum()))
    print("[debug] elapsed: %.1fs" % (time.time() - t0))
  lines = [
    f"run_time={datetime.now().isoformat(timespec='seconds')}",
    f"cat_winner={c.loc[c['是否最优']=='是', '分布'].tolist()}",
    f"item_fitted={len(it)} "
    f"gamma={len(it[it['分布']=='gamma'])} "
    f"lognorm={len(it[it['分布']=='lognorm'])}",
    f"item_quantiles={len(qt)}",
  ]
  (LOG_DIR / "A.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
  print("[save] q1_dist_cat.csv / q1_dist_item.csv / q1_item_quantiles.csv")
  print("[save] q1_dist_cat_qq.pdf / q1_dist_item_sample.pdf")
  print("[save] outputs/A.log")


if __name__ == "__main__":
  main()
