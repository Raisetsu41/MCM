# 问题二画图: 读输出 CSV, 生成 4 张图
# 输入 results/q2_*.csv, 输出 figures/q2_*.pdf

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "results"
FIG = ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
plt.rcParams["axes.unicode_minus"] = False


def load(name):
  return pd.read_csv(OUT / name, encoding="utf-8-sig")


def fig_fit(e, sc):
  fig, axs = plt.subplots(2, 3, figsize=(15, 9))
  for ax, (_, r) in zip(axs.ravel(), e.iterrows()):
    g = sc[sc["分类编码"] == r["分类编码"]]
    ax.scatter(g["ln价格"], g["ln销量"], s=4, alpha=0.4, color="#4C72B0")
    x = np.linspace(g["ln价格"].min(), g["ln价格"].max(), 50)
    ax.plot(x, r["截距"] + r["价格弹性"] * x, color="#D62728", lw=1.5)
    ax.text(0.04, 0.96, f"{r['分类名称']}  beta={r['价格弹性']:.3f} "
            f"t={r['t值']:.2f} R2={r['R2']:.3f}",
            transform=ax.transAxes, va="top", fontsize=8)
    ax.set_xlabel("ln价格", fontsize=8)
    ax.set_ylabel("ln销量", fontsize=8)
  fig.tight_layout()
  fig.savefig(FIG / "q2_elasticity_fit.pdf")
  plt.close(fig)


def fig_forecast(f, raw):
  fig, axs = plt.subplots(2, 3, figsize=(15, 9))
  for ax, (_, r) in zip(axs.ravel(), f.groupby("分类编码").first().iterrows()):
    g = f[f["分类编码"] == r.name]
    h = raw[raw["分类编码"] == r.name].tail(60)
    ax.plot(pd.to_datetime(h["销售日期"]), h["净销量"], color="#4C72B0",
            lw=1.0, label="历史")
    d = pd.to_datetime(g["日期"])
    ax.plot(d, g["基准需求"], "o-", color="#D62728", lw=1.2, label="预测")
    ax.fill_between(d, g["基准需求"] - g["需求标准差"],
                    g["基准需求"] + g["需求标准差"], color="#D62728",
                    alpha=0.2)
    ax.text(0.04, 0.96, r["分类名称"], transform=ax.transAxes, va="top",
            fontsize=8)
    ax.set_xlabel("日期", fontsize=8)
    ax.set_ylabel("净销量(kg)", fontsize=8)
    ax.legend(fontsize=7)
  fig.tight_layout()
  fig.savefig(FIG / "q2_forecast.pdf")
  plt.close(fig)


def fig_price(e, rp):
  fig, axs = plt.subplots(2, 3, figsize=(15, 9))
  for ax, (_, r) in zip(axs.ravel(), e.iterrows()):
    p = np.linspace(r["参考价"] * 0.5, r["参考价"] * 2.0, 80)
    prof = (p - r["有效成本"]) * r["参考需求"] * (p / r["参考价"]) ** \
        r["价格弹性"]
    ax.plot(p, prof, color="#4C72B0", lw=1.5)
    pstar = rp[rp["分类编码"] == r["分类编码"]]["最优售价"].iloc[0]
    ax.axvline(pstar, color="#D62728", ls="--", lw=1.2)
    ax.text(0.04, 0.96, f"{r['分类名称']}  P*={pstar:.2f}",
            transform=ax.transAxes, va="top", fontsize=8)
    ax.set_xlabel("售价(元/kg)", fontsize=8)
    ax.set_ylabel("期望利润(元)", fontsize=8)
  fig.tight_layout()
  fig.savefig(FIG / "q2_price_curve.pdf")
  plt.close(fig)


def fig_repl(rp):
  fig, axs = plt.subplots(2, 3, figsize=(15, 9))
  for ax, (c, g) in zip(axs.ravel(), rp.groupby("分类编码")):
    ax.bar(range(7), g["补货量"], 0.6, color="#4C72B0", label="补货量")
    ax2 = ax.twinx()
    ax2.plot(range(7), g["最优售价"], "o-", color="#D62728", lw=1.3,
             label="最优售价")
    ax2.set_ylabel("售价(元/kg)", fontsize=8)
    ax.set_xticks(range(7))
    ax.set_xticklabels(g["日期"].str[5:], fontsize=7, rotation=30)
    ax.set_ylabel("补货量(kg)", fontsize=8)
    ax.text(0.04, 0.96, g["分类名称"].iloc[0], transform=ax.transAxes,
            va="top", fontsize=8)
    ax.legend(fontsize=7, loc="upper left")
    ax2.legend(fontsize=7, loc="upper right")
  fig.tight_layout()
  fig.savefig(FIG / "q2_replenishment.pdf")
  plt.close(fig)


def main():
  e = load("q2_elasticity.csv")
  f = load("q2_forecast.csv")
  rp = load("q2_replenishment.csv")
  sc = load("q2_scatter.csv")
  raw = pd.read_csv(OUT / "category_daily_full.csv", encoding="utf-8-sig")
  raw["销售日期"] = pd.to_datetime(raw["销售日期"])
  fig_fit(e, sc)
  fig_forecast(f, raw)
  fig_price(e, rp)
  fig_repl(rp)
  print("[save] q2_elasticity_fit.pdf / q2_forecast.pdf / "
        "q2_price_curve.pdf / q2_replenishment.pdf")


if __name__ == "__main__":
  main()
