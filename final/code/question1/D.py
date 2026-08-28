import time
from datetime import datetime
from pathlib import Path

import chinese_calendar as cc
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.cluster import hierarchy
from scipy.stats import zscore
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import adjusted_rand_score, silhouette_score
from matplotlib.patches import Patch


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results"
FIG = ROOT / "figures"
LOG_DIR = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATE0 = "2020-07-01"
DATE1 = "2023-06-30"
n_day_min = 60
k_lo, k_hi = 3, 10
sil_min = 0.15
n_boot = 50
boot_frac = 0.8
DEBUG = True

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

FEATS = ["售出天数占比", "有售日均销量", "有售日变异系数", "周末偏置",
         "节假日脉冲", "总销量占比"]


def load():
  df = pd.read_csv(OUT / "item_daily_sales.csv", encoding="utf-8-sig")
  df["销售日期"] = pd.to_datetime(df["销售日期"])
  return df


def feats(df):
  idx = pd.date_range(DATE0, DATE1, freq="D")
  q = df.pivot(index="销售日期", columns="单品编码",
               values="净销量").reindex(idx).fillna(0.0)
  info = df.drop_duplicates("单品编码").set_index("单品编码")[
    ["单品名称", "分类编码", "分类名称"]]
  n_day = (q > 0).sum()
  cols = n_day[n_day >= n_day_min].index
  q = q[cols]
  n = q.shape[1]
  mu = np.zeros(n)
  cv = np.zeros(n)
  for i, c in enumerate(cols):
    x = q[c].values
    xp = x[x > 0]
    mu[i] = xp.mean()
    cv[i] = xp.std() / mu[i] if mu[i] > 0 else 0.0
  wd = (q.index.weekday >= 5)
  hd = np.array([cc.is_holiday(d.date()) for d in q.index])
  wk = (q[wd].mean() / q[~wd].mean() - 1).values
  hl = (q[hd].mean() / q[~hd].mean() - 1).values
  sh = q.sum().values / q.sum().sum()
  f = pd.DataFrame({
    "售出天数占比": (n_day[cols] / len(idx)).values,
    "有售日均销量": mu,
    "有售日变异系数": cv,
    "周末偏置": wk,
    "节假日脉冲": hl,
    "总销量占比": sh,
  }, index=cols)
  return f, info.loc[cols]


def pick_k(z):
  lnk = hierarchy.linkage(z, method="ward")
  rows = [(k, silhouette_score(z, hierarchy.fcluster(
    lnk, t=k, criterion="maxclust"))) for k in range(k_lo, k_hi + 1)]
  best = max(rows, key=lambda r: r[1])[0]
  return lnk, rows, best


def stability(z, best, seed=7):
  rng = np.random.default_rng(seed)
  full = hierarchy.fcluster(hierarchy.linkage(z, method="ward"),
                            t=best, criterion="maxclust")
  ari = []
  for _ in range(n_boot):
    idx = rng.choice(len(z), size=int(len(z) * boot_frac), replace=False)
    sub = AgglomerativeClustering(n_clusters=best,
                                  linkage="ward").fit_predict(z[idx])
    ari.append(adjusted_rand_score(full[idx], sub))
  return np.mean(ari)


def name_cluster(fm):
  p, cv, wk, mu = (fm["售出天数占比"], fm["有售日变异系数"],
                   fm["周末偏置"], fm["有售日均销量"])
  if p >= 0.6 and cv <= 0.8:
    return "高频平稳型"
  if p < 0.3:
    if wk >= 0.35:
      return "低频脉冲型"
    return "低频稀疏型"
  if cv >= 1.2:
    return "高波动型"
  if wk >= 0.15:
    if mu >= 15:
      return "高量周末脉冲型"
    return "周末脉冲型"
  return "中频均衡型"


def fig_dend(lnk, lab, names):
  fig, ax = plt.subplots(figsize=(10, 6))
  d = hierarchy.dendrogram(lnk, ax=ax, no_labels=True)

  leaves = np.array(d["leaves"])
  ks = np.unique(lab)
  cmap = plt.get_cmap("tab10")
  colors = {k: cmap(i % 10) for i, k in enumerate(ks)}
  ax.scatter(np.arange(len(leaves)), np.zeros(len(leaves)), s=18,
             c=[colors[lab[i]] for i in leaves], zorder=3)
  handles = [Patch(color=colors[k], label=f"簇{k} {names[k]}") for k in ks]
  ax.legend(handles=handles, fontsize=8, loc="upper right")
  ax.set_xlabel("单品", fontsize=9)
  ax.set_ylabel("距离", fontsize=9)
  fig.tight_layout()
  fig.savefig(FIG / "q1_dendrogram.pdf")
  plt.close(fig)


def fig_sil(rows, best):
  ks = [r[0] for r in rows]
  ss = [r[1] for r in rows]
  fig, ax = plt.subplots(figsize=(8, 5))
  ax.plot(ks, ss, "o-", color="#4C72B0")
  ax.axvline(best, color="#D62728", ls="--", lw=1)
  ax.set_xlabel("簇数 k", fontsize=9)
  ax.set_ylabel("silhouette", fontsize=9)
  fig.tight_layout()
  fig.savefig(FIG / "q1_silhouette.pdf")
  plt.close(fig)


def fig_profile(z, lab, names):
  fig, ax = plt.subplots(figsize=(9, 6))
  x = np.arange(len(FEATS))
  for k in np.unique(lab):
    m = z[lab == k].mean(axis=0)
    ax.plot(x, m, "o-", label=f"簇{k} {names[k]}")
  ax.set_xticks(x)
  ax.set_xticklabels(FEATS, fontsize=8, rotation=20, ha="right")
  ax.set_ylabel("特征 z 均值", fontsize=9)
  ax.legend(fontsize=8)
  fig.tight_layout()
  fig.savefig(FIG / "q1_cluster_profile.pdf")
  plt.close(fig)


def main():
  t0 = time.time()
  df = load()
  f, info = feats(df)
  z = zscore(f.values)
  lnk, rows, best = pick_k(z)
  lab = hierarchy.fcluster(lnk, t=best, criterion="maxclust")
  ari = stability(z, best)
  out = f.reset_index().rename(columns={"index": "单品编码"})
  out["单品名称"] = info["单品名称"].values
  out["分类编码"] = info["分类编码"].values
  out["分类名称"] = info["分类名称"].values
  out["簇标签"] = lab
  out = out[["单品编码", "单品名称", "分类编码", "分类名称"] + FEATS
            + ["簇标签"]]
  out.to_csv(OUT / "q1_item_cluster.csv", index=False, encoding="utf-8-sig")
  prof = []
  for k in np.unique(lab):
    sub = out[out["簇标签"] == k]
    fm = sub[FEATS].mean()
    top = sub.sort_values("总销量占比", ascending=False).head(3)[
      "单品名称"].tolist()
    prof.append({"簇标签": int(k), "单品数": len(sub),
                 **{c: round(v, 4) for c, v in fm.items()},
                 "典型单品名称": "/".join(top),
                 "建议命名": name_cluster(fm)})
  prof_df = pd.DataFrame(prof)
  prof_df.to_csv(OUT / "q1_cluster_profile.csv", index=False,
                 encoding="utf-8-sig")
  k_df = pd.DataFrame(rows, columns=["候选k", "silhouette值"])
  k_df["稳定性ARI"] = np.nan
  k_df.loc[k_df["候选k"] == best, "稳定性ARI"] = round(ari, 4)
  k_df.to_csv(OUT / "q1_cluster_k.csv", index=False, encoding="utf-8-sig")
  names = dict(zip(prof_df["簇标签"], prof_df["建议命名"]))
  fig_dend(lnk, lab, names)
  fig_sil(rows, best)
  fig_profile(z, lab, names)
  if DEBUG:
    print("[debug] items:", len(f))
    print("[debug] chosen k:", best, "silhouette:",
          round([s for k, s in rows if k == best][0], 4), "ARI:", round(ari, 4))
    print("[debug] cluster sizes:", np.bincount(lab)[1:].tolist())
    print("[debug] nan total:", int(out.isna().sum().sum()
                                    + prof_df.isna().sum().sum()))
    print("[debug] elapsed: %.1fs" % (time.time() - t0))
  lines = [
    f"run_time={datetime.now().isoformat(timespec='seconds')}",
    f"items={len(f)} k={best}",
    f"silhouette={round([s for k, s in rows if k == best][0], 4)} "
    f"ari={round(ari, 4)}",
    f"cluster_sizes={np.bincount(lab)[1:].tolist()}",
  ]
  (LOG_DIR / "D.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
  print("[save] q1_item_cluster.csv / q1_cluster_profile.csv / "
        "q1_cluster_k.csv")
  print("[save] q1_dendrogram.pdf / q1_silhouette.pdf / "
        "q1_cluster_profile.pdf")
  print("[save] outputs/D.log")


if __name__ == "__main__":
  main()
