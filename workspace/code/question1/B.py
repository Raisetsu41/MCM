# 任务B: 品类日销量 STL 季节分解
# 输入 results/category_daily_sales.csv, 输出分解表与两张图

from datetime import datetime
from pathlib import Path
import time

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import STL


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results"
FIG = ROOT / "figures"
LOG_DIR = Path(__file__).resolve().parent / "outputs"
OUT.mkdir(parents=True, exist_ok=True)
FIG.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
PERIOD = 7
DATE0 = "2020-07-01"
DATE1 = "2023-06-30"
PEAK = [4, 5, 6, 7, 8, 9, 10]
DEBUG = True

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def load():
  df = pd.read_csv(OUT / "category_daily_sales.csv", encoding="utf-8-sig")
  df["销售日期"] = pd.to_datetime(df["销售日期"])
  return df


def full_daily(df):
  idx = pd.date_range(DATE0, DATE1, freq="D")
  out = []
  for c, g in df.groupby("分类编码"):
    s = g.set_index("销售日期")["净销量"].reindex(idx, fill_value=0.0)
    d = pd.DataFrame({"销售日期": idx, "净销量": s.values})
    d["分类编码"] = c
    d["分类名称"] = g["分类名称"].iloc[0]
    out.append(d)
  return pd.concat(out, ignore_index=True)


def decomp(s):
  res = STL(s, period=PERIOD, robust=True).fit()
  return res.trend, res.seasonal, res.resid


def strength(t, s, r):
  fs = max(0.0, 1 - np.var(r) / np.var(s + r))
  ft = max(0.0, 1 - np.var(r) / np.var(t + r))
  return fs, ft


def monthly(g):
  m = g.assign(月份=g["销售日期"].dt.month)
  return m.groupby("月份")["净销量"].mean()


def fig_stl(full, rows, dec):
  fig, axs = plt.subplots(2, 3, figsize=(15, 8), sharex=True)
  for ax, (c, g) in zip(axs.ravel(), full.groupby("分类编码")):
    d = g["销售日期"]
    t, se, r = dec[c]
    ax.plot(d, t, color="C0", lw=1.2, label="趋势")
    ax.plot(d, se, color="C1", lw=1.0, label="季节")
    ax.plot(d, r, color="C2", lw=0.7, alpha=0.7, label="残差")
    info = rows.loc[rows["分类编码"] == c].iloc[0]
    ax.text(0.03, 0.96,
            f"{info['分类名称']}  F_s={info['季节强度']:.2f} "
            f"F_t={info['趋势强度']:.2f}",
            transform=ax.transAxes, va="top", fontsize=8)
    ax.set_xlabel("日期", fontsize=8)
    ax.set_ylabel("销量(千克)", fontsize=8)
  handles, labels = axs.ravel()[0].get_legend_handles_labels()
  fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=9)
  fig.tight_layout(rect=[0, 0.04, 1, 1])
  fig.savefig(FIG / "q1_stl.pdf")
  plt.close(fig)


def fig_month(full):
  fig, axs = plt.subplots(2, 3, figsize=(14, 8))
  for ax, (c, g) in zip(axs.ravel(), full.groupby("分类编码")):
    mm = monthly(g)
    colors = ["#D62728" if i in PEAK else "#4C72B0" for i in mm.index]
    ax.bar(mm.index, mm.values, color=colors, alpha=0.85)
    ax.set_xticks(range(1, 13))
    ax.set_xlabel("月份", fontsize=9)
    ax.set_ylabel("平均日销量(千克)", fontsize=9)
    ax.text(0.03, 0.96, g["分类名称"].iloc[0],
            transform=ax.transAxes, va="top", fontsize=8)
  fig.tight_layout()
  fig.savefig(FIG / "q1_monthly_mean.pdf")
  plt.close(fig)


def main():
  t0 = time.time()
  df = load()
  full = full_daily(df)
  missing = len(full) - len(df)
  if DEBUG:
    print("[debug] total missing days:", missing)
  dec = {}
  stl_rows, str_rows, m_rows = [], [], []
  for c, g in full.groupby("分类编码"):
    s = g["净销量"].reset_index(drop=True)
    t, se, r = decomp(s)
    dec[c] = (t, se, r)
    fs, ft = strength(t, se, r)
    miss_c = 1095 - len(df[df["分类编码"] == c])
    d = g[["销售日期", "分类编码", "分类名称"]].reset_index(drop=True)
    d["净销量"] = s.values
    d["趋势"] = t.values
    d["季节"] = se.values
    d["残差"] = r.values
    stl_rows.append(d)
    mm = monthly(g)
    peak = mm[mm.index.isin(PEAK)].mean()
    off = mm[~mm.index.isin(PEAK)].mean()
    ratio = peak / off
    if DEBUG:
      print("[debug]", g["分类名称"].iloc[0],
            "missing:", miss_c,
            "F_s=%.4f F_t=%.4f ratio=%.4f" % (fs, ft, ratio))
    str_rows.append({"分类编码": c, "分类名称": g["分类名称"].iloc[0],
                     "季节强度": round(fs, 4), "趋势强度": round(ft, 4),
                     "旺季平均日销量": round(peak, 3),
                     "淡季平均日销量": round(off, 3),
                     "旺季比值": round(ratio, 4)})
    for mo, v in mm.items():
      m_rows.append({"分类编码": c, "分类名称": g["分类名称"].iloc[0],
                     "月份": int(mo), "平均日销量": round(v, 3)})
  stl = pd.concat(stl_rows, ignore_index=True)
  stl[["净销量", "趋势", "季节", "残差"]] = \
    stl[["净销量", "趋势", "季节", "残差"]].round(3)
  strength_df = pd.DataFrame(str_rows)
  month_df = pd.DataFrame(m_rows)
  stl.to_csv(OUT / "q1_stl_fit.csv", index=False, encoding="utf-8-sig")
  strength_df.to_csv(OUT / "q1_seasonal_strength.csv", index=False,
                     encoding="utf-8-sig")
  month_df.to_csv(OUT / "q1_monthly_mean.csv", index=False,
                  encoding="utf-8-sig")
  fig_stl(full, strength_df, dec)
  fig_month(full)
  if DEBUG:
    print("[debug] stl rows:", len(stl),
          "nan:", int(stl.isna().sum().sum()))
    print("[debug] F_s range:", strength_df["季节强度"].min(),
          strength_df["季节强度"].max())
    print("[debug] F_t range:", strength_df["趋势强度"].min(),
          strength_df["趋势强度"].max())
    print("[debug] monthly rows:", len(month_df))
    print("[debug] elapsed: %.1fs" % (time.time() - t0))
  lines = [
    f"run_time={datetime.now().isoformat(timespec='seconds')}",
    f"missing_days={missing}",
    f"seasonal_strength={strength_df['季节强度'].tolist()}",
    f"trend_strength={strength_df['趋势强度'].tolist()}",
    f"peak_ratio={strength_df['旺季比值'].tolist()}",
    f"monthly_rows={len(month_df)}",
  ]
  (LOG_DIR / "B.log").write_text("\n".join(lines) + "\n", encoding="utf-8")
  print("[save] q1_stl_fit.csv / q1_seasonal_strength.csv / "
        "q1_monthly_mean.csv")
  print("[save] q1_stl.pdf / q1_monthly_mean.pdf")
  print("[save] outputs/B.log")


if __name__ == "__main__":
  main()
