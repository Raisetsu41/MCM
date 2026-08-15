"""验证附件2扫码间隔分布与伪购物篮重建可行性.

输入: ../Problem/附件2.xlsx, 输出: results/ 下间隔与伪篮统计 CSV.
运行: python code/scan_basket_check.py
"""

from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT.parent / "Problem" / "附件2.xlsx"
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)
WINS = [1, 2, 5, 10]


def load():
  """读取日期/扫码时间/单品编码/销售类型并转毫秒.""" 
  df = pd.read_excel(SRC, usecols=[0, 1, 2, 5])
  df.columns = ["日期", "时间", "单品编码", "销售类型"]
  df["日期"] = pd.to_datetime(df["日期"]).dt.normalize()
  df["单品编码"] = df["单品编码"].astype("int64")
  t = df["时间"].astype(str).str.split(":", expand=True)
  s = t[2].str.split(".", expand=True)
  ms = (t[0].astype(int) * 3600000 + t[1].astype(int) * 60000
        + s[0].astype(int) * 1000 + s[1].str[:3].fillna("0").astype(int))
  df["ms"] = ms
  return df[["日期", "ms", "单品编码", "销售类型"]]


def gap(df):
  """按日排序后计算相邻扫码间隔(毫秒).""" 
  d = df.sort_values(["日期", "ms"])
  return d.groupby("日期", sort=False)["ms"].diff().dropna().astype("int64")


def gap_row(df, tag):
  """汇总扫码间隔分布.""" 
  g = gap(df)
  q = {f"P{n}毫秒": round(g.quantile(n / 100), 3)
       for n in (1, 5, 10, 25, 50, 75, 90, 95, 99)}
  row = {"样本": tag, "间隔数": len(g), "均值毫秒": round(g.mean(), 3),
         "标准差毫秒": round(g.std(), 3), "最小毫秒": int(g.min()),
         **q, "最大毫秒": int(g.max())}
  for w in WINS:
    row[f"间隔小于等于{w}秒占比_%"] = round((g <= w * 1000).mean() * 100, 4)
  return row


def bid(df, win, gapm):
  """按窗口分桶或按间隔合并构造伪篮.""" 
  d = df.sort_values(["日期", "ms"])
  if gapm:
    diff = d.groupby("日期", sort=False)["ms"].diff().fillna(win * 1000 + 1)
    d["bid"] = (diff > win * 1000).cumsum()
  else:
    d["bid"] = d["日期"].astype(str) + "_" + (d["ms"] // (win * 1000)).astype(str)
  return d


def pairs(d, th):
  """统计多单品伪篮内的共现单品对及达到阈值的对数.""" 
  cnt = Counter()
  sz = d.groupby("bid")["bid"].transform("size")
  d = d[sz >= 2]
  for _, g in d.groupby("bid"):
    u = g["单品编码"].unique()
    if len(u) < 2:
      continue
    u.sort()
    for i in range(len(u)):
      for j in range(i + 1, len(u)):
        cnt[(u[i], u[j])] += 1
  vals = cnt.values()
  return len(cnt), (max(vals) if vals else 0), sum(v >= th for v in vals)


def stat_row(d, tag, win, method):
  """汇总伪篮规模与共现情况.""" 
  sz = d.groupby("bid")["单品编码"].agg(n="size", u="nunique")
  n = len(sz)
  mr = int((sz["n"] >= 2).sum())
  mi = int((sz["u"] >= 2).sum())
  cov = int(sz.loc[sz["n"] >= 2, "n"].sum())
  th = int(np.ceil(n * 0.005))
  pc, maxf, nok = pairs(d, th)
  return {"样本": tag, "伪篮方法": method, "窗口秒": win, "伪篮总数": n,
          "多行篮数": mr, "多行篮占比_%": round(mr / n * 100, 4),
          "多单品篮数": mi, "多单品篮占比_%": round(mi / n * 100, 4),
          "多行篮覆盖行数": cov,
          "多行篮覆盖行占比_%": round(cov / len(d) * 100, 4),
          "最大篮行数": int(sz["n"].max()),
          "最大篮单品数": int(sz["u"].max()),
          "共现单品对数": pc, "最高共现次数": maxf,
          "最高共现支持度_%": round(maxf / n * 100, 4),
          "达到0.005支持度的共现对数": nok,
          "支持度0.005所需共现数": th}


def size_row(d, tag, win, method):
  """输出伪篮规模分布.""" 
  vc = d.groupby("bid").size().value_counts().sort_index()
  return pd.DataFrame({"样本": tag, "伪篮方法": method, "窗口秒": win,
                       "篮内行数": vc.index, "篮数": vc.values,
                       "占比_%": (vc.values / len(d.groupby("bid")) * 100).round(4)})


def main():
  """运行验证并保存 CSV.""" 
  df = load()
  print(f"[load] 流水 {len(df)} 行")
  tags = [("全部流水", df), ("仅销售流水", df[df["销售类型"] == "销售"])]
  rows = [gap_row(d, t) for t, d in tags]
  pd.DataFrame(rows).to_csv(OUT / "scan_interval.csv", index=False,
                            encoding="utf-8-sig")
  print("[save] scan_interval.csv")
  bs, sd = [], []
  for t, d in tags:
    for w in WINS:
      for gapm, method in ((False, "分桶"), (True, "间隔合并")):
        db = bid(d, w, gapm)
        bs.append(stat_row(db, t, w, method))
        sd.append(size_row(db, t, w, method))
  pd.DataFrame(bs).to_csv(OUT / "basket_check.csv", index=False,
                          encoding="utf-8-sig")
  print("[save] basket_check.csv")
  pd.concat(sd, ignore_index=True).to_csv(OUT / "basket_size_dist.csv",
                                          index=False, encoding="utf-8-sig")
  print("[save] basket_size_dist.csv")


if __name__ == "__main__":
  main()
