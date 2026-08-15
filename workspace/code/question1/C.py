# 任务C: 去季节相关性与协同变动网络
# 输入 results/item_daily_sales.csv, 输出相关表/网络表与两张图

import time
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx
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
DATE0 = "2020-07-01"
DATE1 = "2023-06-30"
n_day_min = 60
r_th = 0.4
fdr_q = 0.05
ths = [0.3, 0.4, 0.5]
DEBUG = True

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def load():
  df = pd.read_csv(OUT / "item_daily_sales.csv", encoding="utf-8-sig")
  df["销售日期"] = pd.to_datetime(df["销售日期"])
  return df


def wide(df):
  idx = pd.date_range(DATE0, DATE1, freq="D")
  q = df.pivot(index="销售日期", columns="单品编码",
               values="净销量").reindex(idx).fillna(0.0)
  info = df.drop_duplicates("单品编码").set_index("单品编码")[
    ["单品名称", "分类编码", "分类名称"]]
  return q, info


def design(d):
  wd = d["销售日期"].dt.weekday
  mo = d["销售日期"].dt.month
  x = pd.get_dummies(wd, prefix="w", drop_first=True).astype(float)
  x = pd.concat([x, pd.get_dummies(mo, prefix="m",
                                    drop_first=True).astype(float)], axis=1)
  x["c"] = 1.0
  return x.values


def resid(q, x):
  r = np.empty_like(q, dtype=float)
  for i in range(q.shape[1]):
    b, _, _, _ = np.linalg.lstsq(x, q[:, i], rcond=None)
    r[:, i] = q[:, i] - x @ b
  return r


def sp(r):
  rank = np.apply_along_axis(stats.rankdata, 0, r)
  with np.errstate(invalid="ignore", divide="ignore"):
    rho = np.corrcoef(rank, rowvar=False)
  n = r.shape[0]
  with np.errstate(divide="ignore", invalid="ignore"):
    t = rho * np.sqrt((n - 2) / (1 - rho ** 2))
  p = 2 * stats.t.sf(np.abs(t), n - 2)
  np.fill_diagonal(p, 1.0)
  return rho, p


def bh(p):
  m = len(p)
  order = np.argsort(p)
  q = np.empty(m)
  q[order] = p[order] * m / np.arange(1, m + 1)
  q = np.minimum.accumulate(q[::-1])[::-1]
  return q


def cat_heat():
  df = pd.read_csv(OUT / "category_daily_sales.csv", encoding="utf-8-sig")
  df["销售日期"] = pd.to_datetime(df["销售日期"])
  q = df.pivot(index="销售日期", columns="分类名称",
               values="净销量").reindex(pd.date_range(DATE0, DATE1),
                                        ).fillna(0.0)
  d = pd.DataFrame({"销售日期": q.index})
  rho, _ = sp(resid(q.values, design(d)))
  fig, ax = plt.subplots(figsize=(7, 6))
  im = ax.imshow(rho, cmap="RdBu_r", vmin=-1, vmax=1)
  ax.set_xticks(range(6))
  ax.set_yticks(range(6))
  ax.set_xticklabels(q.columns, fontsize=8, rotation=45, ha="right")
  ax.set_yticklabels(q.columns, fontsize=8)
  for i in range(6):
    for j in range(6):
      ax.text(j, i, f"{rho[i, j]:.2f}", ha="center", va="center", fontsize=7)
  fig.colorbar(im, ax=ax, label="相关系数")
  fig.tight_layout()
  fig.savefig(FIG / "q1_corr_heatmap_cat.pdf")
  plt.close(fig)
  return rho


def fig_net(sub, info):
  g = nx.Graph()
  for _, r in sub.iterrows():
    g.add_edge(int(r["单品A编码"]), int(r["单品B编码"]),
               sign=np.sign(r["相关系数"]))
  fig, ax = plt.subplots(figsize=(12, 9))
  pos = nx.spring_layout(g, k=0.5, seed=1, weight=None)
  pe = [(u, v) for u, v, d in g.edges(data=True) if d["sign"] > 0]
  ne = [(u, v) for u, v, d in g.edges(data=True) if d["sign"] < 0]
  nx.draw_networkx_edges(g, pos, edgelist=pe, edge_color="#D62728",
                         alpha=0.5, ax=ax)
  nx.draw_networkx_edges(g, pos, edgelist=ne, edge_color="#4C72B0",
                         alpha=0.5, ax=ax)
  deg = dict(g.degree())
  sizes = [100 + 30 * deg[n] for n in g.nodes()]
  nx.draw_networkx_nodes(g, pos, node_size=sizes, node_color="#C9D6E8",
                         edgecolors="gray", ax=ax)
  top = sorted(deg, key=deg.get, reverse=True)[:10]
  labels = {n: info.loc[n, "单品名称"] for n in top if n in info.index}
  nx.draw_networkx_labels(g, pos, labels, font_size=7, ax=ax)
  ax.axis("off")
  fig.tight_layout()
  fig.savefig(FIG / "q1_corr_network.pdf")
  plt.close(fig)


def main():
  t0 = time.time()
  df = load()
  q, info = wide(df)
  n_day = (q > 0).sum()
  cols = n_day[n_day >= n_day_min].index
  q = q[cols]
  info = info.loc[cols]
  d = pd.DataFrame({"销售日期": q.index})
  x = design(d)
  rho, p = sp(resid(q.values, x))
  iu = np.triu_indices(rho.shape[0], 1)
  rf, pf = rho[iu], p[iu]
  qf = bh(pf)
  h1 = q.index <= "2021-12-31"
  h2 = ~h1
  rho1, p1 = sp(resid(q[h1].values, design(d.loc[h1])))
  rho2, p2 = sp(resid(q[h2].values, design(d.loc[h2])))
  r1f, r2f = rho1[iu], rho2[iu]
  p1f, p2f = p1[iu], p2[iu]
  stable = ((np.sign(rf) == np.sign(r1f)) & (np.sign(rf) == np.sign(r2f))
            & (p1f < 0.05) & (p2f < 0.05))
  main = (np.abs(rf) >= r_th) & (qf < fdr_q)
  edges = pd.DataFrame({
    "单品A编码": q.columns[iu[0][main]],
    "单品A名称": info.loc[q.columns[iu[0][main]], "单品名称"].values,
    "单品B编码": q.columns[iu[1][main]],
    "单品B名称": info.loc[q.columns[iu[1][main]], "单品名称"].values,
    "相关系数": np.round(rf[main], 4),
    "p值": np.round(pf[main], 6),
    "FDR_q值": np.round(qf[main], 6),
    "符号": np.where(rf[main] > 0, "正", "负"),
    "是否稳健边": np.where(stable[main], "是", "否"),
  })
  edges.to_csv(OUT / "q1_corr_edges.csv", index=False, encoding="utf-8-sig")
  thr_rows = []
  for th in ths:
    m1 = np.abs(rf) >= th
    thr_rows.append({"阈值": th, "边数": int(m1.sum()),
                     "正边数": int((m1 & (rf > 0)).sum()),
                     "负边数": int((m1 & (rf < 0)).sum()),
                     "稳健边数": int((m1 & stable).sum())})
  thr = pd.DataFrame(thr_rows)
  thr.to_csv(OUT / "q1_corr_threshold.csv", index=False,
             encoding="utf-8-sig")
  sub = edges[edges["是否稳健边"] == "是"]
  if len(sub):
    g = nx.Graph()
    for _, r in sub.iterrows():
      g.add_edge(int(r["单品A编码"]), int(r["单品B编码"]),
                 sign=np.sign(r["相关系数"]))
    deg = nx.degree_centrality(g)
    bc = nx.betweenness_centrality(g)
    pos_cnt = {}
    neg_cnt = {}
    for _, r in sub.iterrows():
      for node in (int(r["单品A编码"]), int(r["单品B编码"])):
        if r["符号"] == "正":
          pos_cnt[node] = pos_cnt.get(node, 0) + 1
        else:
          neg_cnt[node] = neg_cnt.get(node, 0) + 1
    top = pd.DataFrame({
      "单品编码": list(deg.keys()),
      "单品名称": [info.loc[n, "单品名称"] for n in deg],
      "度中心度": np.round(list(deg.values()), 4),
      "介数中心度": np.round([bc[n] for n in deg], 6),
      "正边数": [pos_cnt.get(n, 0) for n in deg],
      "负边数": [neg_cnt.get(n, 0) for n in deg],
    }).sort_values("度中心度", ascending=False)
    top.to_csv(OUT / "q1_network_top.csv", index=False, encoding="utf-8-sig")
    fig_net(sub, info)
  else:
    pd.DataFrame(columns=["单品编码", "单品名称", "度中心度", "介数中心度",
                          "正边数", "负边数"]).to_csv(
      OUT / "q1_network_top.csv", index=False, encoding="utf-8-sig")
  rho_cat = cat_heat()
  if DEBUG:
    print("[debug] items kept:", len(cols))
    print("[debug] pairs tested:", len(rf))
    print("[debug] main edges:", len(edges),
          "stable:", int(stable.sum()))
    print("[debug] threshold table:\n", thr.to_string(index=False))
    print("[debug] cat corr:\n",
          np.round(rho_cat, 3))
    print("[debug] nan total:", int(edges.isna().sum().sum()
                                    + thr.isna().sum().sum()))
    print("[debug] elapsed: %.1fs" % (time.time() - t0))
  lines = [
    f"run_time={datetime.now().isoformat(timespec='seconds')}",
    f"items={len(cols)} pairs={len(rf)}",
    f"main_edges={len(edges)} stable={int(stable.sum())}",
    f"edges_by_threshold={thr['边数'].tolist()}",
    f"stable_by_threshold={thr['稳健边数'].tolist()}",
  ]
  (LOG_DIR / "C.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
  print("[save] q1_corr_edges.csv / q1_network_top.csv / "
        "q1_corr_threshold.csv")
  print("[save] q1_corr_heatmap_cat.pdf / q1_corr_network.pdf")
  print("[save] outputs/C.log")


if __name__ == "__main__":
  main()
