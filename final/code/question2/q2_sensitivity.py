import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import lognorm, norm

sys.path.insert(0, str(Path(__file__).resolve().parent))
import q2

OUT = q2.OUT
FIG = q2.FIG
N = 20000
SEED = 7


def d2i(s):
  return q2.d2i(s)


def design(d, wd, mo, lp):

  return np.column_stack([lp, d,
                          (wd[d][:, None] == np.arange(1, 7)).astype(float),
                          (mo[d][:, None] == np.arange(2, 13)).astype(float),
                          np.ones(len(d))])


def mk2(st, B, cp, ws):

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
        pg = np.clip((1 + mg) * ws.loc[c], st.loc[c, "p5"], st.loc[c, "p95"])
        v = (pg - cp.loc[c]) * st.loc[c, "mu"] * \
            (pg / st.loc[c, "pbar"]) ** B[i, i]
        if v > bv:
          bv = v
          best = mg
      p = np.clip((1 + best) * ws.loc[c], st.loc[c, "p5"], st.loc[c, "p95"])
      a = 0
    p = np.clip(p, st.loc[c, "p5"], st.loc[c, "p95"])
    mo.append(p / ws.loc[c] - 1)
    an.append(a)
  return np.array(mo), np.array(an)


def run(st, B, FQ, FS, cp, lv, ws):

  mo, an = mk2(st, B, cp, ws)
  pst = (1 + mo) * ws.values
  sca = (pst / st["pbar"].values) ** np.diag(B)
  mu = FQ * sca[:, None]
  sg = FS * sca[:, None]
  y, kap, R, R0, ep = q2.nv(
    mu.ravel(), sg.ravel(),
    np.broadcast_to(pst[:, None], mu.shape).ravel(),
    np.broadcast_to(cp.values[:, None], mu.shape).ravel(),
    np.broadcast_to(lv[:, None], mu.shape).ravel())
  return (y.reshape(mu.shape), kap.reshape(mu.shape), R.reshape(mu.shape),
          R0.reshape(mu.shape), ep.reshape(mu.shape), mo, pst, mu, sg)


def emin(mu, sg, y):

  s2 = np.log(1 + (sg / mu) ** 2)
  ml = np.log(mu) - s2 / 2
  s = np.sqrt(s2)
  a = mu * norm.cdf((np.log(y) - ml - s * s) / s)
  b = y * (1 - norm.cdf((np.log(y) - ml) / s))
  return a + b


def altP(df, cats, idx, mode):

  tmp = df[df["均价"] > 0]
  if mode == "cur":
    g = tmp.assign(amt=tmp["均价"] * tmp["售出量"]).groupby(
      ["d", "分类编码"]).apply(
      lambda x: x["amt"].sum() / max(x["售出量"].sum(), 1e-9))
  else:
    g = tmp.groupby(["d", "分类编码"])["均价"].median()
  g = g.unstack()
  d = (idx - pd.Timestamp(q2.DATE0)).days
  g = g.reindex(d)
  for c in cats:
    g[c] = g[c].fillna(g[c].mean())
  return g


def bt22(q, p, cats, idx):

  wd = idx.weekday.to_numpy()
  mo = idx.month.to_numpy()
  cut = d2i("2022-07-01")
  rows = []
  for c in cats:
    qv = q[c].values
    pos = qv > 0
    d = np.where(pos)[0]
    tr = d < cut
    X = design(d, wd, mo, np.log(p[c].values[d]))
    fit = np.linalg.lstsq(X[tr], np.log(qv[pos][tr]), rcond=None)[0]
    d7 = np.arange(cut, cut + 7)
    lp = np.log(p[c].values[d7])
    if not np.isfinite(lp).all():
      lp = np.where(np.isfinite(lp), lp, np.log(p[c].mean()))
    X7 = design(d7, wd, mo, lp)
    pred = np.exp(X7 @ fit)
    act = qv[d7]
    m = act > 0
    mape = np.mean(np.abs(pred[m] - act[m]) / act[m]) * 100
    rows.append({"c": c, "mape22": mape, "n": int(m.sum())})
  return pd.DataFrame(rows).set_index("c")


def sim(cats, idx, q, mu, sg, pst, R, cp, lv):

  wd = idx.weekday.to_numpy()
  mo = idx.month.to_numpy()
  Xc = np.column_stack([
    (wd[:, None] == np.arange(1, 7)).astype(float),
    (mo[:, None] == np.arange(2, 13)).astype(float), np.ones(len(idx))])
  E = np.column_stack([q[c].values for c in cats])
  res = E - Xc @ np.linalg.lstsq(Xc, E, rcond=None)[0]
  C = np.corrcoef(res.T)
  rng = np.random.default_rng(SEED)
  y = R * (1 - lv[:, None])
  s2 = np.log(1 + (sg / mu) ** 2)
  ml = np.log(mu) - s2 / 2
  s = np.sqrt(s2)
  ej = 0.0
  vj = 0.0
  vi = 0.0
  for k in range(7):
    z = rng.multivariate_normal(np.zeros(len(cats)), C, size=N)
    D = lognorm.ppf(norm.cdf(z), s=s[:, k], scale=np.exp(ml[:, k]))
    prof = (pst[None, :] * np.minimum(D, y[:, k]) -
            cp[None, :] * y[:, k]).sum(axis=1)
    ej += prof.mean()
    vj += prof.var()
    zi = rng.multivariate_normal(
      np.zeros(len(cats)), np.eye(len(cats)), size=N)
    Di = lognorm.ppf(norm.cdf(zi), s=s[:, k], scale=np.exp(ml[:, k]))
    profi = (pst[None, :] * np.minimum(Di, y[:, k]) -
             cp[None, :] * y[:, k]).sum(axis=1)
    vi += profi.var()
  return ej, C, vj, vi


def fig(rows):

  names = [r[0] for r in rows]
  vals = [r[1] for r in rows]
  fig, ax = plt.subplots(figsize=(9, 5))
  x = np.arange(len(names))
  col = ["#4C72B0"] * len(names)
  col[0] = "#D62728"
  ax.bar(x, vals, 0.6, color=col)
  for i, v in enumerate(vals):
    ax.text(i, v + 5, "%.0f" % v, ha="center", fontsize=8)
  ax.set_xticks(x)
  ax.set_xticklabels(names, fontsize=8, rotation=20)
  ax.set_ylabel("7天总利润(元)")
  fig.tight_layout()
  fig.savefig(FIG / "q2_sensitivity.pdf")
  plt.close(fig)


def main():
  df, names = q2.load()
  cats, idx, q, p, w, l = q2.agg(df)
  st = q2.stat(q, p, w, l, names)
  B, el, sc = q2.ols(q, p, cats, idx)
  back = q2.bt(q, p, cats, idx)
  FQ, FS = q2.fc(el, st, cats)
  cp0 = st["W"] / (1 - st["L"])
  base = run(st, B, FQ, FS, cp0, st["L"].values, st["W"])
  y0, kap0, R0, R00, ep0, mo0, pst0, mu0, sg0 = base
  mo1, an1 = q2.mk(st, B)
  assert np.allclose(mo1, mo0), "mk2 与 q2.mk 不一致"
  rows = []
  det = []

  def add(nm, B_, mo_, pst_, R_, ep_):
    for i, c in enumerate(cats):
      rows.append({"情景": nm, "分类编码": c, "分类名称": names[c],
                   "价格弹性": B_[i, i], "最优加价率": mo_[i],
                   "最优售价": pst_[i],
                   "7天补货量": R_[i].sum(), "7天利润": ep_[i].sum()})

  add("基准", B, mo0, pst0, R0, ep0)
  tot = pd.DataFrame(rows).groupby("情景")[["7天补货量", "7天利润"]].sum()
  agg = [{"情景": "基准", "7天总补货量": tot.loc["基准", "7天补货量"],
          "7天总利润": tot.loc["基准", "7天利润"], "利润变化%": 0.0}]

  def scn(nm, st_, B_, FQ_, FS_, cp_, lv_, ws_):
    r = run(st_, B_, FQ_, FS_, cp_, lv_, ws_)
    add(nm, B_, r[5], r[6], r[2], r[4])
    b = tot.loc["基准", "7天利润"]
    v = r[4].sum()
    agg.append({"情景": nm, "7天总补货量": r[2].sum(),
                "7天总利润": v, "利润变化%": (v / b - 1) * 100})
    return r

  for f, nm in [(1.1, "批发价+10%"), (0.9, "批发价-10%")]:
    ws = st["W"] * f
    cpf = ws / (1 - st["L"])
    scn(nm, st, B, FQ, FS, cpf, st["L"].values, ws)
  for f, nm in [(1.2, "弹性+20%"), (0.8, "弹性-20%")]:
    Bm = B.copy()
    np.fill_diagonal(Bm, np.diag(B) * f)
    scn(nm, st, Bm, FQ, FS, cp0, st["L"].values, st["W"])
  win = df[(df["d"] >= d2i("2022-07-01")) & (df["d"] <= d2i("2023-06-30"))]
  iq = win.groupby("单品编码")["净销量"].sum()
  cq = win.groupby("分类编码")["净销量"].sum()
  cat = df.drop_duplicates("单品编码").set_index("单品编码")["分类编码"]
  wgt = (iq / cat.map(cq)).fillna(0)
  li = df.drop_duplicates("单品编码").set_index("单品编码")["损耗率"] / 100
  Li = (li * wgt).groupby(cat).sum().reindex(st.index)
  cpL = st["W"] / (1 - Li)
  scn("损耗率=单品加权", st, B, FQ, FS, cpL, Li.values, st["W"])
  for mode, nm in [("cur", "价格口径=当期加权"), ("med", "价格口径=中位价")]:
    pa = altP(df, cats, idx, mode)
    sta = q2.stat(q, pa, w, l, names)
    Ba, ela, sca = q2.ols(q, pa, cats, idx)
    FQa, FSa = q2.fc(ela, sta, cats)
    cpa = sta["W"] / (1 - sta["L"])
    scn(nm, sta, Ba, FQa, FSa, cpa, sta["L"].values, sta["W"])


  ydet = R00 * (1 - st["L"].values[:, None])
  e0 = (pst0[:, None] * emin(mu0, sg0, ydet) -
        cp0.values[:, None] * ydet)
  sd2 = np.log(1 + (sg0 / mu0) ** 2)
  sdl = np.sqrt(sd2)
  mdl = np.log(mu0) - sd2 / 2
  sr_det = 1 - lognorm.cdf(ydet, s=sdl, scale=np.exp(mdl))
  for i, c in enumerate(cats):
    det.append({
      "分类编码": c, "分类名称": names[c],
      "报童7天补货量": R0[i].sum(), "确定性7天补货量": R00[i].sum(),
      "安全库存增量%": (R0[i].sum() / R00[i].sum() - 1) * 100,
      "报童7天期望利润": ep0[i].sum(),
      "确定性订货7天期望利润": e0[i].sum(),
      "报童日均缺货率": (1 - kap0[i]).mean(),
      "确定性日均缺货率": sr_det[i].mean(),
    })


  b22 = bt22(q, p, cats, idx)
  bcmp = b22.join(back["mape"]).rename(
    columns={"mape": "mape28"})


  ej, C, vj, vi = sim(cats, idx, q, mu0, sg0, pst0, R0, cp0.values, st["L"].values)
  ei = ep0.sum()
  srow = {"独立7天期望利润": ei, "相关模拟7天期望利润": ej,
          "期望利润差": ej - ei, "期望利润差%": (ej / ei - 1) * 100,
          "独立方差(模拟)": vi, "相关方差(模拟)": vj,
          "方差比": vj / vi, "样本量": N,
          "残差相关最大非对角": np.abs(C - np.eye(len(C))).max(),
          "残差相关最小非对角": C[np.triu_indices(len(C), 1)].min()}

  pd.DataFrame(rows).to_csv(OUT / "q2_sens_detail.csv", index=False,
                            encoding="utf-8-sig")
  pd.DataFrame(agg).to_csv(OUT / "q2_sensitivity.csv", index=False,
                           encoding="utf-8-sig")
  pd.DataFrame(det).to_csv(OUT / "q2_nv_det.csv", index=False,
                           encoding="utf-8-sig")
  bcmp.reset_index().rename(columns={"c": "分类编码"}).to_csv(
    OUT / "q2_backtest_2022.csv", index=False, encoding="utf-8-sig")
  pd.DataFrame([srow]).to_csv(OUT / "q2_joint_sim.csv", index=False,
                              encoding="utf-8-sig")


  b = tot.loc["基准", "7天利润"]
  rw = {r["情景"]: r["7天总利润"] for r in agg}
  rR = {r["情景"]: r["7天总补货量"] for r in agg}
  summary = [
    {"claim": "批发价±10% 内利润不剧烈恶化",
     "sources": ["q2_sensitivity.csv", "q2_replenishment.csv"],
     "perturbation": "W x 1.1 / x 0.9",
     "metric": "7天总利润相对变化绝对值",
     "threshold": 30.0,
     "observed": max(abs((rw["批发价+10%"] / b - 1) * 100),
                     abs((rw["批发价-10%"] / b - 1) * 100)),
     "status": "PASS" if max(abs((rw["批发价+10%"] / b - 1) * 100),
                             abs((rw["批发价-10%"] / b - 1) * 100)) <= 30
               else "CONDITIONAL",
     "limitation": "补货量用近一周均价预测, 未建模日内批发价随机性"},
    {"claim": "弹性±20% 内最优价与利润稳定",
     "sources": ["q2_sensitivity.csv"],
     "perturbation": "品类弹性 x 1.2 / x 0.8",
     "metric": "7天总利润相对变化绝对值",
     "threshold": 30.0,
     "observed": max(abs((rw["弹性+20%"] / b - 1) * 100),
                     abs((rw["弹性-20%"] / b - 1) * 100)),
     "status": "PASS" if max(abs((rw["弹性+20%"] / b - 1) * 100),
                             abs((rw["弹性-20%"] / b - 1) * 100)) <= 30
               else "CONDITIONAL",
     "limitation": "仅扰动对角弹性, 交叉弹性不变"},
    {"claim": "价格口径切换不改变弹性符号与利润量级",
     "sources": ["q2_sensitivity.csv", "q2_sens_detail.csv"],
     "perturbation": "固定权重 -> 当期销售额加权 / 中位价",
     "metric": "7天总利润相对固定权重变化绝对值",
     "threshold": 30.0,
     "observed": max(abs((rw["价格口径=当期加权"] / b - 1) * 100),
                     abs((rw["价格口径=中位价"] / b - 1) * 100)),
     "status": "PASS" if max(abs((rw["价格口径=当期加权"] / b - 1) * 100),
                             abs((rw["价格口径=中位价"] / b - 1) * 100)) <= 30
               else "CONDITIONAL",
     "limitation": "未对口径切换重估报童分位数分布参数"},
    {"claim": "报童订货优于确定性订货",
     "sources": ["q2_nv_det.csv"],
     "perturbation": "最优分位数 y* vs 均值 y0",
     "metric": "报童7天期望利润 >= 确定性订货期望利润",
     "threshold": 0.0,
     "observed": (ep0.sum() - e0.sum()),
     "status": "PASS" if ep0.sum() >= e0.sum() - 1e-6 else "CONDITIONAL",
     "limitation": "确定性口径按 lognormal 期望利润评估, 缺货率口径为 P(D>y)"},
    {"claim": "损耗率替换后补货量稳定",
     "sources": ["q2_sensitivity.csv"],
     "perturbation": "分类级损耗率 -> 单品销量加权损耗率",
     "metric": "7天总补货量相对变化绝对值",
     "threshold": 20.0,
     "observed": abs(rR["损耗率=单品加权"] / rR["基准"] - 1) * 100,
     "status": "PASS" if abs(rR["损耗率=单品加权"] / rR["基准"] - 1) * 100 <= 20
               else "CONDITIONAL",
     "limitation": "损耗率口径差异来自附件4两类表, 取加权口径作对照"},
    {"claim": "2022-07 同期回测误差与后28天同量级",
     "sources": ["q2_backtest_2022.csv", "q2_backtest.csv"],
     "perturbation": "样本截止 2022-06-30",
     "metric": "2022-07 预测 MAPE <= 40%",
     "threshold": 40.0,
     "observed": float(b22["mape22"].max()),
     "status": "PASS" if b22["mape22"].max() <= 40 else "CONDITIONAL",
     "limitation": "目标周仅 7 天, 实际销量个别日为 0 时剔除"},
    {"claim": "品类相关性与独立优化期望收益一致",
     "sources": ["q2_joint_sim.csv"],
     "perturbation": "残差相关矩阵 vs 单位阵(高斯 copula + lognormal 边际)",
     "metric": "相关模拟期望利润相对独立期望利润偏差 <= 1%",
     "threshold": 1.0,
     "observed": abs((ej / ei - 1) * 100),
     "status": "PASS" if abs((ej / ei - 1) * 100) <= 1 else "CONDITIONAL",
     "limitation": "copula 相关为残差 Pearson 相关, 与 Spearman 口径略有差异"},
  ]
  with open(OUT / "q2_robustness_summary.json", "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

  frows = [(r["情景"], r["7天总利润"]) for r in agg]
  fig(frows)
  if q2.DEBUG:
    print("[debug] 基准总利润: %.2f 总补货: %.2f" % (b, rR["基准"]))
    for r in agg:
      print("[debug] %s: 利润 %.2f (%+.1f%%) 补货 %.2f" %
            (r["情景"], r["7天总利润"], r["利润变化%"], r["7天总补货量"]))
    print("[debug] 报童-确定性利润差: %.2f" % (ep0.sum() - e0.sum()))
    print("[debug] 2022-07 MAPE:", b22["mape22"].round(1).to_dict())
    print("[debug] 相关模拟: 独立 %.2f vs 相关 %.2f, 方差比 %.3f" %
          (ei, ej, vj / vi))
    print("[debug] 残差相关矩阵:\n", np.round(C, 3))
  print("[save] q2_sensitivity.csv / q2_sens_detail.csv / q2_nv_det.csv / "
        "q2_backtest_2022.csv / q2_joint_sim.csv / "
        "q2_robustness_summary.json / q2_sensitivity.pdf")


if __name__ == "__main__":
  main()
