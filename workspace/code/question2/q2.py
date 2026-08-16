# 问题二主流程: 数据 -> 弹性 -> 定价 -> 预测 -> 报童

import ctypes
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.optimize import differential_evolution


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results"
FIG = ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
DATE0 = "2020-07-01"
DATE1 = "2023-06-30"
DEBUG = True

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False

_lib = ctypes.CDLL(str(Path(__file__).resolve().parent / "nv.dll"))
_f64 = np.ctypeslib.ndpointer(dtype=np.float64, ndim=1, flags="C_CONTIGUOUS")
_lib.newsvendor_batch.restype = None
_lib.newsvendor_batch.argtypes = [_f64] * 5 + [ctypes.c_int] + [_f64] * 5


def nv(mu, sg, p, c, l):
  # 批量报童补货, 返回 y/kappa/R/R0/期望利润
  mu = np.ascontiguousarray(mu, dtype=np.float64)
  sg = np.ascontiguousarray(sg, dtype=np.float64)
  p = np.ascontiguousarray(p, dtype=np.float64)
  c = np.ascontiguousarray(c, dtype=np.float64)
  l = np.ascontiguousarray(l, dtype=np.float64)
  n = len(mu)
  y = np.empty(n)
  kap = np.empty(n)
  r = np.empty(n)
  r0 = np.empty(n)
  ep = np.empty(n)
  _lib.newsvendor_batch(mu, sg, p, c, l, n, y, kap, r, r0, ep)
  return y, kap, r, r0, ep


def d2i(s):
  return (pd.Timestamp(s) - pd.Timestamp(DATE0)).days


def load():
  df = pd.read_csv(OUT / "item_daily_full.csv", encoding="utf-8-sig")
  df["日期"] = pd.to_datetime(df["销售日期"])
  df["d"] = (df["日期"] - pd.Timestamp(DATE0)).dt.days
  names = df.drop_duplicates("分类编码").set_index("分类编码")["分类名称"].to_dict()
  return df, names


def agg(df):
  win = df[(df["d"] >= d2i("2022-07-01")) & (df["d"] <= d2i("2023-06-30"))]
  iq = win.groupby("单品编码")["净销量"].sum()
  cq = win.groupby("分类编码")["净销量"].sum()
  cat = df.drop_duplicates("单品编码").set_index("单品编码")["分类编码"]
  w = (iq / cat.map(cq)).fillna(0)

  def one(g):
    sw = g["w"].sum()
    return pd.Series({
      "Q": g["净销量"].sum(),
      "P": (g["均价"] * g["w"]).sum() / sw if sw > 0 else np.nan,
      "W": (g["批发价"] * g["w"]).sum() / sw if sw > 0 else np.nan,
      "L": g["平均损耗率"].mean() / 100,
    })

  tmp = df[df["均价"] > 0].copy()
  tmp["w"] = tmp["单品编码"].map(w)
  tab = tmp.groupby(["d", "分类编码"]).apply(one).unstack()
  idx = pd.date_range(DATE0, DATE1)
  d = (idx - pd.Timestamp(DATE0)).days
  q = df.groupby(["d", "分类编码"])["净销量"].sum().unstack().reindex(d).fillna(0)
  p = tab["P"].reindex(d).fillna(tab["P"].mean())
  w = tab["W"].reindex(d).fillna(tab["W"].mean())
  l = tab["L"].mean()
  return list(q.columns), idx, q, p, w, l


def stat(q, p, w, l, names):
  # 每品类均值/分位数/成本与最近一周批发价
  rows = []
  for c in q.columns:
    qv = q[c].values
    pos = qv > 0
    qq, pp = qv[pos], p[c].values[pos]
    wv = w[c].values[pos]
    m = qq.mean()
    wb = w[c].iloc[d2i("2023-06-24"):].mean()
    wb = wb if not np.isnan(wb) else w[c].mean()
    rows.append({
      "c": c, "name": names[c], "mu": m, "sd": qq.std(ddof=0),
      "pbar": pp.mean(), "p5": np.percentile(pp, 5),
      "p95": np.percentile(pp, 95), "m5": np.percentile(pp / wv - 1, 5),
      "m95": np.percentile(pp / wv - 1, 95), "W": wb, "L": l[c],
    })
  return pd.DataFrame(rows).set_index("c")


def ols(q, p, cats, idx):
  # 品类 Log-Log 弹性回归
  wd = idx.weekday.to_numpy()
  mo = idx.month.to_numpy()
  B = np.zeros((len(cats), len(cats)))
  rows = []
  sc = []
  for i, c in enumerate(cats):
    qv = q[c].values
    pos = qv > 0
    d = np.where(pos)[0]
    X = np.column_stack([
      np.log(p.values[d]), d,
      (wd[d][:, None] == np.arange(1, 7)).astype(float),
      (mo[d][:, None] == np.arange(2, 13)).astype(float),
      np.ones(len(d)),
    ])
    y = np.log(qv[pos])
    fit = sm.OLS(y, X).fit()
    res = y - X @ fit.params
    B[i] = fit.params[:len(cats)]
    rows.append({"c": c, "beta": fit.params, "b0": fit.params[i],
                 "t": fit.tvalues[i], "r2": fit.rsquared,
                 "mse": fit.mse_resid, "res": res})
    sc.append(pd.DataFrame({"ln价格": np.log(p[c].values[pos]), "ln销量": y}))
  sc = pd.concat(sc, keys=cats)
  sc.index.names = ["分类编码", "i"]
  return B, pd.DataFrame(rows).set_index("c"), sc.reset_index().drop(columns=["i"])


def mk(st, B):
  # 最优加价率: 题面成本加成口径, 网格按夹逼后价格评估
  cp = st["W"] / (1 - st["L"])
  mo = []
  an = []
  for i, c in enumerate(st.index):
    E = abs(B[i, i])
    if E > 1:
      p = E / (E - 1) * cp.loc[c]
      a = 1
    else:
      g = np.linspace(st.loc[c, "m5"], st.loc[c, "m95"], 201)
      best = g[0]
      bv = -1e100
      for mg in g:
        pg = np.clip((1 + mg) * st.loc[c, "W"],
                     st.loc[c, "p5"], st.loc[c, "p95"])
        v = (pg - cp.loc[c]) * st.loc[c, "mu"] * \
            (pg / st.loc[c, "pbar"]) ** B[i, i]
        if v > bv:
          bv = v
          best = mg
      p = np.clip((1 + best) * st.loc[c, "W"],
                  st.loc[c, "p5"], st.loc[c, "p95"])
      a = 0
    p = np.clip(p, st.loc[c, "p5"], st.loc[c, "p95"])
    mo.append(p / st.loc[c, "W"] - 1)
    an.append(a)
  return np.array(mo), np.array(an)


def jp(st, B):
  # 联合定价: 交叉弹性 + 差分进化, 独立基准用同一价格可行域
  cp = st["W"].values / (1 - st["L"].values)
  pbar = st["pbar"].values
  mu = st["mu"].values
  n = len(mu)
  lo = st["p5"].values
  hi = st["p95"].values

  def prof(p):
    s = 0.0
    for i in range(n):
      s += (p[i] - cp[i]) * mu[i] * np.prod((p / pbar) ** B[i])
    return -s

  res = differential_evolution(prof, list(zip(lo, hi)), seed=7, tol=1e-8)
  pj = res.x
  pib = np.zeros(n)
  pi_i = np.zeros(n)
  for i in range(n):
    g = np.linspace(lo[i], hi[i], 201)
    v = (g - cp[i]) * mu[i] * (g / pbar[i]) ** B[i, i]
    pib[i] = g[np.argmax(v)]
    pi_i[i] = v.max()
  pi_j = np.array([(pj[i] - cp[i]) * mu[i] * np.prod((pj / pbar) ** B[i])
                   for i in range(n)])
  return pj, pib, pi_i, pi_j


def fc(el, st, cats):
  # 参考价处外推未来 7 天基准需求
  FQ = []
  FS = []
  for c in cats:
    qb = []
    sg = []
    for k in range(7):
      d = 1095 + k
      row = np.r_[np.log(st["pbar"].values), d,
                  ((d + 2) % 7 == np.arange(1, 7)).astype(float),
                  (np.arange(2, 13) == 7).astype(float), 1.0]
      lp = row @ el.loc[c, "beta"]
      q = np.exp(lp + el.loc[c, "mse"] / 2)
      qb.append(q)
      sg.append(q * np.sqrt(np.exp(el.loc[c, "mse"]) - 1))
    FQ.append(qb)
    FS.append(sg)
  return np.array(FQ), np.array(FS)


def bt(q, p, cats, idx):
  # 后 28 天滚动回测, 返回每品类 MAPE
  wd = idx.weekday.to_numpy()
  mo = idx.month.to_numpy()
  rows = []
  for c in cats:
    qv = q[c].values
    pos = qv > 0
    d = np.where(pos)[0]
    X = np.column_stack([
      np.log(p.values[d]), d,
      (wd[d][:, None] == np.arange(1, 7)).astype(float),
      (mo[d][:, None] == np.arange(2, 13)).astype(float),
      np.ones(len(d)),
    ])
    fit = sm.OLS(np.log(qv[pos]), X).fit()
    te = d >= d[-1] - 27
    pred = np.exp(X[te] @ fit.params)
    mape = np.mean(np.abs(pred - qv[d[te]]) / qv[d[te]]) * 100
    rows.append({"c": c, "mape": mape, "n": int(te.sum())})
  return pd.DataFrame(rows).set_index("c")


def fig(st, el, B, sc, q, idx, FQ, FS, pst, R, ep, names, dts):
  # 输出 4 张论文图
  cats = list(st.index)
  for ax, (c, r) in zip(
      plt.subplots(2, 3, figsize=(15, 9))[1].ravel(), el.iterrows()):
    g = sc[sc["分类编码"] == c]
    x = g["ln价格"].values
    yp = r["res"] + r["b0"] * x
    ax.scatter(x, yp, s=4, alpha=0.4, color="#4C72B0")
    xs = np.linspace(x.min(), x.max(), 50)
    ax.plot(xs, r["b0"] * xs, color="#D62728", lw=1.5)
    ax.text(0.04, 0.96, f"{names[c]}  beta={r['b0']:.3f} "
            f"t={r['t']:.2f} R2={r['r2']:.3f}",
            transform=ax.transAxes, va="top", fontsize=8)
    ax.set_xlabel("ln价格", fontsize=8)
    ax.set_ylabel("ln销量(去日历效应)", fontsize=8)
  plt.tight_layout()
  plt.savefig(FIG / "q2_elasticity_fit.pdf")
  plt.close()
  fig, axs = plt.subplots(2, 3, figsize=(15, 9))
  for ax, (i, c) in zip(axs.ravel(), enumerate(cats)):
    h = q[c].iloc[-60:]
    ax.plot(idx[-60:], h.values, color="#4C72B0", lw=1.0, label="历史")
    d = pd.to_datetime(dts)
    ax.plot(d, FQ[i], "o-", color="#D62728", lw=1.2, label="预测")
    ax.fill_between(d, FQ[i] - FS[i], FQ[i] + FS[i], color="#D62728", alpha=0.2)
    ax.text(0.04, 0.96, names[c], transform=ax.transAxes, va="top", fontsize=8)
    ax.set_xlabel("日期", fontsize=8)
    ax.set_ylabel("净销量(kg)", fontsize=8)
    ax.legend(fontsize=7)
  plt.tight_layout()
  plt.savefig(FIG / "q2_forecast.pdf")
  plt.close()
  fig, axs = plt.subplots(2, 3, figsize=(15, 9))
  for ax, (i, c) in zip(axs.ravel(), enumerate(cats)):
    p = np.linspace(st.loc[c, "pbar"] * 0.5, st.loc[c, "pbar"] * 2.0, 80)
    prof = (p - st.loc[c, "W"] / (1 - st.loc[c, "L"])) * st.loc[c, "mu"] * \
        (p / st.loc[c, "pbar"]) ** B[i, i]
    ax.axvspan(st.loc[c, "p5"], st.loc[c, "p95"], color="#4C72B0", alpha=0.08)
    ax.plot(p, prof, color="#4C72B0", lw=1.5)
    ax.axvline(pst[i], color="#D62728", ls="--", lw=1.2)
    ax.text(0.04, 0.96, f"{names[c]}  P*={pst[i]:.2f}",
            transform=ax.transAxes, va="top", fontsize=8)
    ax.set_xlabel("售价(元/kg)", fontsize=8)
    ax.set_ylabel("期望利润(元)", fontsize=8)
  plt.tight_layout()
  plt.savefig(FIG / "q2_price_curve.pdf")
  plt.close()
  fig, axs = plt.subplots(2, 3, figsize=(15, 9))
  for ax, (i, c) in zip(axs.ravel(), enumerate(cats)):
    ax.bar(range(7), R[i], 0.6, color="#4C72B0", label="补货量")
    ax2 = ax.twinx()
    ax2.plot(range(7), pst[i] * np.ones(7), "o-", color="#D62728", lw=1.3,
             label="最优售价")
    ax2.set_ylabel("售价(元/kg)", fontsize=8)
    ax.set_xticks(range(7))
    ax.set_xticklabels([d[5:] for d in dts], fontsize=7, rotation=30)
    ax.set_ylabel("补货量(kg)", fontsize=8)
    ax.text(0.04, 0.96, names[c], transform=ax.transAxes, va="top", fontsize=8)
  plt.tight_layout()
  plt.savefig(FIG / "q2_replenishment.pdf")
  plt.close()


def main():
  df, names = load()
  cats, idx, q, p, w, l = agg(df)
  st = stat(q, p, w, l, names)
  B, el, sc = ols(q, p, cats, idx)
  back = bt(q, p, cats, idx)
  mo, an = mk(st, B)
  FQ, FS = fc(el, st, cats)
  cp = st["W"].values / (1 - st["L"].values)
  pst = (1 + mo) * st["W"].values
  pj, pib, pi_i, pi_j = jp(st, B)
  sca = (pst / st["pbar"].values) ** np.diag(B)
  mu = FQ * sca[:, None]
  sg = FS * sca[:, None]
  y, kap, R, R0, ep = nv(
    mu.ravel(), sg.ravel(),
    np.broadcast_to(pst[:, None], mu.shape).ravel(),
    np.broadcast_to(cp[:, None], mu.shape).ravel(),
    np.broadcast_to(st["L"].values[:, None], mu.shape).ravel())
  y = y.reshape(mu.shape)
  kap = kap.reshape(mu.shape)
  R = R.reshape(mu.shape)
  R0 = R0.reshape(mu.shape)
  ep = ep.reshape(mu.shape)
  dts = pd.date_range("2023-07-01", periods=7).strftime("%Y-%m-%d")
  e1, e2, e3 = [], [], []
  for i, c in enumerate(cats):
    e1.append({
      "分类编码": c, "分类名称": names[c], "价格弹性": B[i, i],
      "t值": el.loc[c, "t"], "R2": el.loc[c, "r2"],
      "截距": el.loc[c, "beta"][-1], "参考价": st.loc[c, "pbar"],
      "参考需求": st.loc[c, "mu"], "有效成本": cp[i],
      "加价率P5": st.loc[c, "m5"], "加价率P95": st.loc[c, "m95"],
      "最优加价率": mo[i], "是否解析解": an[i],
    })
    for k in range(7):
      e2.append({"分类编码": c, "分类名称": names[c], "日期": dts[k],
                 "基准需求": FQ[i, k], "需求标准差": FS[i, k],
                 "参考价": st.loc[c, "pbar"]})
      e3.append({"分类编码": c, "分类名称": names[c], "日期": dts[k],
                 "批发价": st.loc[c, "W"], "最优售价": pst[i],
                 "最优加价率": mo[i], "期望需求": mu[i, k],
                 "临界比": kap[i, k], "补货量": R[i, k],
                 "确定性补货量": R0[i, k], "期望利润": ep[i, k]})
  pd.DataFrame(e1).to_csv(OUT / "q2_elasticity.csv", index=False,
                          encoding="utf-8-sig")
  pd.DataFrame(e2).to_csv(OUT / "q2_forecast.csv", index=False,
                          encoding="utf-8-sig")
  pd.DataFrame(e3).to_csv(OUT / "q2_replenishment.csv", index=False,
                          encoding="utf-8-sig")
  pd.DataFrame({"分类编码": cats, "分类名称": [names[c] for c in cats],
                "7天总补货量": R.sum(axis=1), "7天总期望利润": ep.sum(axis=1)}
               ).to_csv(OUT / "q2_summary.csv", index=False,
                        encoding="utf-8-sig")
  pd.DataFrame({"分类编码": cats, "分类名称": [names[c] for c in cats],
                "独立最优价": np.round(pib, 3),
                "联合最优价": np.round(pj, 3),
                "独立利润": np.round(pi_i, 2),
                "联合利润": np.round(pi_j, 2)}
               ).to_csv(OUT / "q2_joint_pricing.csv", index=False,
                        encoding="utf-8-sig")
  sc.to_csv(OUT / "q2_scatter.csv", index=False, encoding="utf-8-sig")
  back.reset_index().rename(columns={"c": "分类编码"}).to_csv(
    OUT / "q2_backtest.csv", index=False, encoding="utf-8-sig")
  fig(st, el, B, sc, q, idx, FQ, FS, pst, R, ep, names, dts)
  if DEBUG:
    lp = np.log(p.values)
    lp = lp[~np.isnan(lp).any(axis=1)]
    print("[debug] cond(lnP): %.1f" % np.linalg.cond(np.corrcoef(lp.T)))
    print("[debug] 弹性:", np.round(np.diag(B), 4))
    print("[debug] t值:", el["t"].round(2).to_dict())
    print("[debug] MAPE:", back["mape"].round(1).to_dict())
    print("[debug] 独立定价总利润: %.2f 联合定价总利润: %.2f 提升: %.1f%%"
          % (pi_i.sum(), pi_j.sum(), (pi_j.sum() / pi_i.sum() - 1) * 100))
    print("[debug] 总补货: %.2f 总利润: %.2f" % (R.sum(), ep.sum()))
  print("[save] q2_elasticity.csv / q2_forecast.csv / "
        "q2_replenishment.csv / q2_summary.csv / q2_scatter.csv / "
        "q2_backtest.csv / q2_joint_pricing.csv")
  print("[save] q2_elasticity_fit.pdf / q2_forecast.pdf / "
        "q2_price_curve.pdf / q2_replenishment.pdf")


if __name__ == "__main__":
  main()
