# 问题三主流程: 候选集 -> 弹性 -> 网格 -> MIP -> 灵敏度

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import Bounds, LinearConstraint, milp
from scipy.sparse import coo_matrix


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results"
FIG = ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
DATE0 = "2020-07-01"
DATE1 = "2023-06-30"
K = 11
K7 = 7
NMIN = 14
M0 = 30
LO = 27
HI = 33
MINQ = 2.5
RHOS = [0.5, 1.0, 1.5]
EXACT = [27, 30, 33]
DEBUG = True

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def d2i(s):
  return (pd.Timestamp(s) - pd.Timestamp(DATE0)).days


def load():
  df = pd.read_csv(OUT / "item_daily_full.csv", encoding="utf-8-sig")
  df["日期"] = pd.to_datetime(df["销售日期"])
  df["d"] = (df["日期"] - pd.Timestamp(DATE0)).dt.days
  names = df.drop_duplicates("单品编码").set_index("单品编码")["单品名称"].to_dict()
  el = pd.read_csv(OUT / "q2_elasticity.csv", encoding="utf-8-sig")
  Bcat = dict(zip(el["分类编码"], el["价格弹性"]))
  return df, names, Bcat


def cand(df):
  # 候选集与基准需求/参考价/批发价/损耗率
  w = df[(df["d"] >= d2i("2023-06-24")) & (df["d"] <= d2i("2023-06-30"))]
  g = w.groupby("单品编码").agg(
    名称=("单品名称", "first"), 品类=("分类编码", "first"),
    品类名=("分类名称", "first"), 销量=("净销量", "sum"),
    天数=("净销量", "count"), 批发=("批发价", "mean"),
    损耗=("损耗率", "mean"), 损耗c=("平均损耗率", "mean"))
  g = g[g["销量"] / 7 >= 0.5]
  g["d"] = g["销量"] / 7
  g["W"] = g["批发"]
  g["L"] = g["损耗"] / 100
  g["Lc"] = g["损耗c"] / 100
  g["low"] = g["天数"] < 3
  amt = w.assign(amt=w["净销量"] * w["均价"])
  p0 = amt.groupby("单品编码").apply(
    lambda x: x["amt"].sum() / max(x["净销量"].sum(), 1e-9))
  g["p0"] = p0
  g["mx"] = df.groupby("单品编码")["净销量"].max()
  w4 = df[(df["d"] >= d2i("2023-06-03")) & (df["d"] <= d2i("2023-06-30"))]
  d4 = w4.groupby("单品编码")["净销量"].mean()
  tmp = w4[w4["均价"] > 0]
  pp = tmp.groupby("单品编码")["均价"].apply(
    lambda x: pd.Series([np.percentile(x, 5), np.percentile(x, 95)])).unstack()
  pp.columns = ["p5", "p95"]
  g = g.join(pp)
  g["d"] = g["d"].fillna(d4)
  g["p0"] = g["p0"].fillna(
    w4.assign(amt=w4["净销量"] * w4["均价"]).groupby("单品编码").apply(
      lambda x: x["amt"].sum() / max(x["净销量"].sum(), 1e-9)))
  g["W"] = g["W"].fillna(df.groupby("单品编码")["批发价"].mean())
  g["p5"] = g["p5"].fillna(g["p0"])
  g["p95"] = g["p95"].fillna(g["p0"])
  for code in g.index[g["low"]]:
    if code in d4.index:
      g.loc[code, "d"] = d4[code]
  return g


def beta(df, g, Bcat):
  # 单品弹性回归 + Shrinkage 收缩 + 兜底
  rows = []
  for code, r in g.iterrows():
    sub = df[(df["单品编码"] == code) & (df["净销量"] > 0) &
             (df["均价"] > 0)].sort_values("d")
    y = np.log(sub["净销量"].values)
    p = sub["均价"].values
    d = sub["d"].values
    wd = sub["日期"].dt.weekday.to_numpy()
    mo = sub["日期"].dt.month.to_numpy()
    X = np.column_stack([
      np.log(p), d,
      (wd[:, None] == np.arange(1, 7)).astype(float),
      (mo[:, None] == np.arange(2, 13)).astype(float),
      np.ones(len(d)),
    ])
    try:
      fit = sm.OLS(y, X).fit()
      raw = float(fit.params[0])
    except Exception:
      raw = np.nan
    N = int((np.diff(p) != 0).sum())
    cat = Bcat[r["品类"]]
    if N < NMIN or not np.isfinite(raw):
      b, u = cat, 1
    else:
      w = N / (N + M0)
      b = w * raw + (1 - w) * cat
      u = 0
      if b > 0:
        b, u = cat, 1
    rows.append((code, raw, b, N, u, cat))
  return pd.DataFrame(rows, columns=["单品编码", "原始弹性", "收缩弹性",
                                     "有效样本量", "是否借用品类弹性",
                                     "品类弹性"]).set_index("单品编码")


def grid(g, K=K):
  ps = {}
  for code, r in g.iterrows():
    lo = min(r["p5"], r["p0"])
    hi = max(r["p95"], r["p0"])
    arr = np.unique(np.append(np.linspace(lo, hi, K), r["p0"]))
    if len(arr) < K:
      arr = np.pad(arr, (0, K - len(arr)), mode="edge")
    else:
      arr = arr[:K]
    ps[code] = arr
  return ps


def grid_q(g, K, w4):
  # 分位数网格: 近 4 周日售价等概率分位 + 参考价
  ps = {}
  for code, r in g.iterrows():
    v = w4.loc[w4["单品编码"] == code, "均价"].values
    v = v[v > 0]
    if len(v) == 0:
      arr = np.full(K, r["p0"])
    else:
      arr = np.unique(
        np.append(np.quantile(v, np.linspace(0.05, 0.95, K)), r["p0"]))
    if len(arr) < K:
      arr = np.pad(arr, (0, K - len(arr)), mode="edge")
    else:
      arr = arr[:K]
    ps[code] = arr
  return ps


def demand(d, p0, beta, ps, bs=1.0):
  return d[:, None] * (ps / p0[:, None]) ** (beta[:, None] * bs)


def mip(g, el, ps, rho, cov=True, exact_n=None, bs=1.0, ws=1.0, ms=1.0,
        lc=False):
  codes = list(g.index)
  n = len(codes)
  K = len(ps[codes[0]])
  V = 2 + 3 * K
  P = np.array([ps[c] for c in codes])
  D = demand(g["d"].values, g["p0"].values, el["收缩弹性"].values, P, bs)
  Lv = g["Lc"].values if lc else g["L"].values
  M = np.maximum(3 * g["mx"].values, MINQ)
  M = np.maximum(M, D[:, 0] * 1.05)
  if ms != 1.0:
    M = M * ms
  cp = g["W"].values * ws / (1 - Lv)
  gam = np.maximum(0, g["p0"].values - cp) * rho
  nv = n * V
  c = np.zeros(nv)
  lb = np.zeros(nv)
  ub = np.ones(nv)
  integ = np.zeros(nv)
  for i in range(n):
    base = i * V
    integ[base] = 1
    integ[base + 1:base + 1 + K] = 1
    ub[base + 1 + K] = M[i]
    ub[base + 2 + K:base + 2 + 2 * K] = D[i].max()
    ub[base + 2 + 2 * K:base + 1 + 3 * K] = D[i].max()
    c[base + 1 + K] = g["W"].values[i] * ws
    c[base + 2 + K:base + 2 + 2 * K] = -P[i]
    c[base + 2 + 2 * K:base + 1 + 3 * K] = gam[i]
  rows, cols, data, clb, cub = [], [], [], [], []
  row = 0

  def add(cols_, vals, lb_, ub_):
    nonlocal row
    for col_, val_ in zip(cols_, vals):
      rows.append(row)
      cols.append(col_)
      data.append(val_)
    clb.append(lb_)
    cub.append(ub_)
    row += 1

  for i in range(n):
    base = i * V
    y, q = base, base + 1 + K
    add([y, q], [MINQ, -1.0], -np.inf, 0)
    add([q, y], [1.0, -M[i]], -np.inf, 0)
    add(list(range(base + 1, base + 1 + K)) + [y], [1.0] * K + [-1.0], 0, 0)
    zs = list(range(base + 2 + K, base + 2 + 2 * K))
    add(zs + [q], [1.0] * K + [-(1 - Lv[i])], -np.inf, 0)
    for j in range(K):
      xj = base + 1 + j
      zj = base + 2 + K + j
      uj = base + 2 + 2 * K + j
      add([zj, uj, xj], [1.0, 1.0, -D[i, j]], 0, 0)
  ycols = [i * V for i in range(n)]
  add(ycols, [-1.0] * n, -np.inf, -LO)
  add(ycols, [1.0] * n, -np.inf, HI)
  if exact_n is not None:
    add(ycols, [1.0] * n, exact_n, exact_n)
  if cov:
    for cname in g["品类"].unique():
      idx = [i for i, c in enumerate(codes) if g.loc[c, "品类"] == cname]
      add([i * V for i in idx], [-1.0] * len(idx), -np.inf, -1)
  A = coo_matrix((data, (rows, cols)), shape=(len(clb), nv)).tocsr()
  res = milp(c, integrality=integ, bounds=Bounds(lb, ub),
             constraints=LinearConstraint(A, np.array(clb), np.array(cub)),
             options={"time_limit": 60})
  x = res.x
  y = np.array([x[i * V] for i in range(n)])
  sel = np.where(y > 0.5)[0]
  q = np.array([x[i * V + 1 + K] for i in range(n)])
  sold = np.zeros(n)
  short = np.zeros(n)
  dem = np.zeros(n)
  rev = np.zeros(n)
  price = np.zeros(n)
  for i in range(n):
    j = int(np.argmax(x[i * V + 1:i * V + 1 + K]))
    price[i] = P[i, j]
    dem[i] = D[i, j] if y[i] > 0.5 else 0
    sold[i] = x[i * V + 2 + K + j]
    short[i] = x[i * V + 2 + 2 * K + j]
    rev[i] = price[i] * sold[i]
  cost = q * g["W"].values * ws
  pen = short * gam
  net = rev - cost - pen
  fr = sold.sum() / max(dem.sum(), 1e-9)
  return {"codes": codes, "sel": sel, "y": y, "q": q, "price": price,
          "sold": sold, "short": short, "dem": dem, "rev": rev,
          "cost": cost, "pen": pen, "net": net, "fr": fr, "M": M,
          "D1": D[:, 0], "Lv": Lv,
          "status": res.status, "fun": res.fun,
          "gap": getattr(res, "mip_gap", None),
          "nodes": getattr(res, "mip_node_count", None)}


def solve(g, el, rho=1.0, K=K, qg=False, w4=None, cov=True, exact_n=None,
          bs=1.0, ws=1.0, ms=1.0, lc=False):
  # 基准 K=11; 非最优按 K=7 -> 放宽品类覆盖 顺序降级
  ps = grid_q(g, K, w4) if qg else grid(g, K)
  out = mip(g, el, ps, rho, cov, exact_n, bs, ws, ms, lc)
  lvl = 0
  if out["status"] != 0:
    lvl = 1
    if K != K7:
      ps = grid(g, K7)
      out = mip(g, el, ps, rho, cov, exact_n, bs, ws, ms, lc)
    if out["status"] != 0:
      lvl = 2
      ps = grid(g, K7)
      out = mip(g, el, ps, rho, False, exact_n, bs, ws, ms, lc)
      if out["status"] != 0:
        lvl = 3
  out["lvl"] = lvl
  out["ps"] = ps
  return out


def fig1(g, out):
  # 品类选中构成
  sel = out["sel"]
  sub = g.iloc[sel]
  cnt = sub["品类名"].value_counts()
  allc = g["品类名"].value_counts()
  fig, ax = plt.subplots(figsize=(8, 5))
  x = np.arange(len(allc))
  ax.bar(x - 0.2, allc.values, 0.4, color="#C9D6E8", label="候选")
  ax.bar(x + 0.2, cnt.reindex(allc.index).fillna(0).values, 0.4,
         color="#4C72B0", label="选中")
  ax.set_xticks(x)
  ax.set_xticklabels(allc.index, fontsize=9)
  ax.set_ylabel("单品数")
  ax.legend(fontsize=8)
  fig.tight_layout()
  fig.savefig(FIG / "q3_selection.pdf")
  plt.close(fig)


def fig2(rows):
  # rho-利润/满足率权衡
  fig, ax = plt.subplots(figsize=(8, 5))
  ax.plot([r["rho"] for r in rows], [r["net"] for r in rows], "o-",
          color="#4C72B0", label="总利润")
  ax.set_xlabel("缺货惩罚系数 rho")
  ax.set_ylabel("总利润(元)")
  ax.set_xticks([r["rho"] for r in rows])
  ax.set_ylim(670, 720)
  ax2 = ax.twinx()
  ax2.plot([r["rho"] for r in rows], [r["fr"] for r in rows], "s--",
           color="#D62728", label="满足率")
  ax2.set_ylabel("满足率")
  ax2.set_ylim(0.94, 1.02)
  ax.legend(fontsize=8, loc="upper left")
  ax2.legend(fontsize=8, loc="upper right")
  fig.tight_layout()
  fig.savefig(FIG / "q3_fr_tradeoff.pdf")
  plt.close(fig)


def fig3(g, out):
  # 选中单品价格-订购量散点
  sel = out["sel"]
  sub = g.iloc[sel]
  fig, ax = plt.subplots(figsize=(9, 6))
  cats = sorted(sub["品类名"].unique())
  cmap = plt.get_cmap("tab10")
  for i, c in enumerate(cats):
    m = sub["品类名"] == c
    ax.scatter(out["price"][sel][m.values], out["q"][sel][m.values],
               s=40, color=cmap(i % 10), label=c)
  ax.set_xlabel("售价(元/kg)")
  ax.set_ylabel("订购量(kg)")
  ax.legend(fontsize=8)
  fig.tight_layout()
  fig.savefig(FIG / "q3_price_qty.pdf")
  plt.close(fig)


def main():
  df, names, Bcat = load()
  g = cand(df)
  el = beta(df, g, Bcat)
  w4 = df[(df["d"] >= d2i("2023-06-03")) & (df["d"] <= d2i("2023-06-30"))]
  out = solve(g, el)
  rows = []
  rows_rho = []
  for rho in RHOS:
    r = solve(g, el, rho=rho)
    rows.append({"情景": "rho=%.1f" % rho, "总利润": r["net"].sum(),
                 "满足率": r["fr"], "选中数": len(r["sel"]),
                 "求解状态": r["status"]})
    rows_rho.append({"rho": rho, "net": r["net"].sum(), "fr": r["fr"]})
  for k in EXACT:
    r = solve(g, el, exact_n=k)
    rows.append({"情景": "选品数=%d" % k, "总利润": r["net"].sum(),
                 "满足率": r["fr"], "选中数": len(r["sel"]),
                 "求解状态": r["status"]})
  for bs in [1.2, 0.8]:
    r = solve(g, el, bs=bs)
    rows.append({"情景": "弹性x%.1f" % bs, "总利润": r["net"].sum(),
                 "满足率": r["fr"], "选中数": len(r["sel"]),
                 "求解状态": r["status"]})
  for ws in [1.1, 0.9]:
    r = solve(g, el, ws=ws)
    rows.append({"情景": "批发价x%.1f" % ws, "总利润": r["net"].sum(),
                 "满足率": r["fr"], "选中数": len(r["sel"]),
                 "求解状态": r["status"]})
  for name, kw in [("损耗率=分类级", {"lc": True}), ("网格K=7", {"K": K7}),
                   ("网格分位数", {"qg": True, "w4": w4}),
                   ("大M放大50%", {"ms": 1.5})]:
    r = solve(g, el, **kw)
    rows.append({"情景": name, "总利润": r["net"].sum(),
                 "满足率": r["fr"], "选中数": len(r["sel"]),
                 "求解状态": r["status"]})
  sel = out["sel"]
  dec = pd.DataFrame({
    "单品编码": [g.index[i] for i in sel],
    "单品名称": [names[g.index[i]] for i in sel],
    "分类名称": [g.iloc[i]["品类名"] for i in sel],
    "售价": np.round(out["price"][sel], 3),
    "订购量": np.round(out["q"][sel], 3),
    "预计销量": np.round(out["sold"][sel], 3),
    "缺货量": np.round(out["short"][sel], 3),
    "需求": np.round(out["dem"][sel], 3),
    "批发价": np.round(g["W"].values[sel], 3),
    "损耗率": np.round(g["L"].values[sel], 4),
    "弹性": np.round(el["收缩弹性"].values[sel], 4),
    "参考价": np.round(g["p0"].values[sel], 3),
    "基准需求": np.round(g["d"].values[sel], 3),
    "低样本": [bool(g["low"].iloc[i]) for i in sel],
    "单品毛利": np.round(out["net"][sel], 2),
  })
  frc = {}
  for c in g["品类名"].unique():
    idx = [i for i in sel if g.iloc[i]["品类名"] == c]
    if idx:
      s = sum(out["sold"][i] for i in idx)
      d = sum(out["dem"][i] for i in idx)
      frc[c] = s / d if d > 0 else 1.0
  dec.insert(dec.columns.get_loc("单品毛利"), "品类满足率",
             [round(frc[g.iloc[i]["品类名"]], 4) for i in sel])
  dec.to_csv(OUT / "q3_decision.csv", index=False, encoding="utf-8-sig")
  el.reset_index().to_csv(OUT / "q3_elasticity.csv", index=False,
                          encoding="utf-8-sig")
  catsel = g.iloc[sel]["品类名"].value_counts()
  allcats = g["品类名"].value_counts()
  over = np.maximum(0, out["q"][sel] - out["sold"][sel] /
                    (1 - g["L"].values[sel]))
  ck = {
    "选品数达标": bool(LO <= len(sel) <= HI),
    "最小陈列达标": bool((out["q"][sel] >= MINQ - 1e-6).all()),
    "可售上限达标": bool((out["sold"][sel] <=
                       out["q"][sel] * (1 - g["L"].values[sel]) + 1e-6).all()),
    "价格网格内": bool(all(any(np.isclose(out["price"][i], p)
                          for p in out["ps"][g.index[i]]) for i in sel)),
    "品类覆盖达标": bool(len(set(g.iloc[sel]["品类"])) == len(g["品类"].unique())),
  }
  diag = pd.DataFrame([{
    "候选数": len(g), "选中数": len(sel), "求解状态": out["status"],
    "最优性gap": out["gap"], "节点数": out["nodes"], "降级层级": out["lvl"],
    "总需求": round(out["dem"].sum(), 2), "总销量": round(out["sold"].sum(), 2),
    "总缺货": round(out["short"].sum(), 2), "总收入": round(out["rev"].sum(), 2),
    "总成本": round(out["cost"].sum(), 2), "缺货惩罚": round(out["pen"].sum(), 2),
    "总利润": round(out["net"].sum(), 2), "满足率": round(out["fr"], 4),
    "超订量": round(float(over.sum()), 3),
    "超订成本": round(float((over * g["W"].values[sel]).sum()), 2),
    **ck, **{f"选中_{c}": int(catsel.get(c, 0)) for c in allcats.index},
  }])
  diag.to_csv(OUT / "q3_diagnostics.csv", index=False, encoding="utf-8-sig")
  pd.DataFrame(rows).to_csv(OUT / "q3_sensitivity.csv", index=False,
                            encoding="utf-8-sig")
  mb = pd.DataFrame({
    "单品编码": g.index,
    "大M": np.round(out["M"], 3),
    "最低档需求": np.round(out["D1"], 3),
    "可售上限需求": np.round(out["D1"] / (1 - g["L"].values), 3),
    "余量": np.round(out["M"] - out["D1"] / (1 - g["L"].values), 3),
  })
  mb.to_csv(OUT / "q3_mbound.csv", index=False, encoding="utf-8-sig")
  q2 = pd.read_csv(OUT / "q2_replenishment.csv", encoding="utf-8-sig")
  q2d = q2[q2["日期"] == "2023-07-01"].set_index("分类编码")
  q3v = g.iloc[sel][["品类", "品类名"]].copy()
  q3v["订购"] = out["q"][sel]
  q3v["可售"] = out["q"][sel] * (1 - g["L"].values[sel])
  gq = q3v.groupby("品类").agg(名称=("品类名", "first"),
                               订购合计=("订购", "sum"),
                               可售合计=("可售", "sum"))
  vs = gq.join(q2d[["补货量", "期望需求"]], how="left")
  vs.columns = ["分类名称", "Q3订购量合计", "Q3可售量合计", "Q2订购量", "Q2可售量"]
  vs["可售量比值"] = vs["Q3可售量合计"] / vs["Q2可售量"]
  vs.reset_index().rename(columns={"品类": "分类编码"}).to_csv(
    OUT / "q3_vs_q2.csv", index=False, encoding="utf-8-sig")
  fig1(g, out)
  fig2(rows_rho)
  fig3(g, out)
  if DEBUG:
    print("[debug] 候选数:", len(g), "选中数:", len(sel))
    print("[debug] 求解状态:", out["status"], "gap:", out["gap"],
          "节点数:", out["nodes"], "降级层级:", out["lvl"])
    print("[debug] 满足率: %.4f 总利润: %.2f" % (out["fr"], out["net"].sum()))
    print("[debug] 约束检查:", ck)
    print("[debug] 品类选中:", catsel.to_dict())
    print("[debug] 灵敏度行数:", len(rows))
  print("[save] q3_decision.csv / q3_elasticity.csv / q3_diagnostics.csv / "
        "q3_sensitivity.csv / q3_mbound.csv / q3_vs_q2.csv")
  print("[save] q3_selection.pdf / q3_fr_tradeoff.pdf / q3_price_qty.pdf")


if __name__ == "__main__":
  main()
