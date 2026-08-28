import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT.parent / "Problem"
OUT = ROOT / "results"
OUT.mkdir(parents=True, exist_ok=True)


def save(df, name):
  """保存为 utf-8-sig CSV."""
  df.to_csv(OUT / name, index=False, encoding="utf-8-sig")
  print(f"[save] {name}: {len(df)} 行")


def load_info():
  """读取附件 1 商品信息."""
  df = pd.read_excel(DATA / "附件1.xlsx")
  return df[["单品编码", "单品名称", "分类编码", "分类名称"]]


def load_loss():
  """读取附件 4 单品损耗率和分类平均损耗率."""
  it = pd.read_excel(DATA / "附件4.xlsx", sheet_name="Sheet1")
  it = it[["单品编码", "损耗率(%)"]].rename(columns={"损耗率(%)": "损耗率"})
  ct = pd.read_excel(DATA / "附件4.xlsx",
                     sheet_name="平均损耗率(%)_小分类编码_不同值")
  ct = ct.rename(columns={"小分类编码": "分类编码",
                          "平均损耗率(%)_小分类编码_不同值": "平均损耗率"})
  return it, ct[["分类编码", "平均损耗率"]]


def load_sales():
  """读取附件 2 销售流水, 构造净销量和打折拆分."""
  df = pd.read_excel(DATA / "附件2.xlsx")
  df = df.rename(columns={"销量(千克)": "销量", "销售单价(元/千克)": "销售单价"})
  df["销售日期"] = pd.to_datetime(df["销售日期"])
  ok = df["销售类型"] == "销售"
  df["净销量"] = np.where(ok, df["销量"], -df["销量"])
  df["售出量"] = np.where(ok, df["销量"], 0.0)
  df["销售额"] = np.where(ok, df["销量"] * df["销售单价"], 0.0)
  df["打折销量"] = np.where(ok & (df["是否打折销售"] == "是"), df["销量"], 0.0)
  df["正常销量"] = np.where(ok & (df["是否打折销售"] == "否"), df["销量"], 0.0)
  return df


def daily_item(s):
  """按单品-日聚合销量."""
  agg = s.groupby(["销售日期", "单品编码"], as_index=False).agg(
    净销量=("净销量", "sum"), 售出量=("售出量", "sum"), 销售额=("销售额", "sum"),
    打折销量=("打折销量", "sum"), 正常销量=("正常销量", "sum"),
    售出记录数=("售出量", "count"), 退货记录数=("净销量", lambda x: (x < 0).sum()))
  agg["均价"] = np.where(agg["售出量"] > 0, agg["销售额"] / agg["售出量"], np.nan)
  return agg


def daily_cat(s, info):
  """按品类-日聚合销量."""
  df = s.merge(info[["单品编码", "分类编码", "分类名称"]],
               on="单品编码", how="left")
  agg = df.groupby(["销售日期", "分类编码", "分类名称"], as_index=False).agg(
    净销量=("净销量", "sum"), 售出量=("售出量", "sum"), 销售额=("销售额", "sum"),
    打折销量=("打折销量", "sum"), 正常销量=("正常销量", "sum"),
    售出记录数=("售出量", "count"), 退货记录数=("净销量", lambda x: (x < 0).sum()),
    在售单品数=("单品编码", "nunique"))
  agg["均价"] = np.where(agg["售出量"] > 0, agg["销售额"] / agg["售出量"], np.nan)
  return agg


def daily_ws(w):
  """补全单品-日批发价, 先按单品前向填充再用单品均值补齐."""
  mean = w.groupby("单品编码")["批发价"].mean()
  codes = w["单品编码"].drop_duplicates()
  dates = pd.date_range(w["销售日期"].min(), w["销售日期"].max(), freq="D")
  grid = pd.DataFrame([(c, d) for c in codes for d in dates],
                      columns=["单品编码", "销售日期"])
  full = grid.merge(w, on=["单品编码", "销售日期"], how="left")
  full = full.sort_values(["单品编码", "销售日期"])
  full["批发价"] = full.groupby("单品编码")["批发价"].ffill()
  full["价格来源"] = np.where(full["批发价"].isna(), "缺失", "前向")
  bad = full["批发价"].isna()
  full.loc[bad, "批发价"] = full.loc[bad, "单品编码"].map(mean)
  full.loc[bad, "价格来源"] = "单品均值"
  return full


def daily_cat_ws(ws, item, info):
  """按品类-日聚合批发价, 输出均值与销量加权."""
  df = ws.merge(info[["单品编码", "分类编码", "分类名称"]], on="单品编码")
  df = df.merge(item[["销售日期", "单品编码", "售出量"]],
                on=["销售日期", "单品编码"], how="left")
  df["售出量"] = df["售出量"].fillna(0.0)
  agg = df.groupby(["销售日期", "分类编码", "分类名称"], as_index=False).agg(
    批发价均值=("批发价", "mean"), 覆盖单品数=("单品编码", "nunique"),
    售出量=("售出量", "sum"))
  df["加权值"] = df["批发价"] * df["售出量"]
  w = df.groupby(["销售日期", "分类编码"])[["加权值", "售出量"]].sum()
  w = w.reset_index()
  w["批发价加权"] = np.where(w["售出量"] > 0, w["加权值"] / w["售出量"], np.nan)
  agg = agg.merge(w[["销售日期", "分类编码", "批发价加权"]],
                  on=["销售日期", "分类编码"])
  agg["批发价加权"] = agg["批发价加权"].fillna(agg["批发价均值"])
  return agg


def profile(info, s, w, item, cat, ws):
  """输出数据质量与口径校验摘要."""
  sold = s.loc[s["销售类型"] == "销售", "销量"].sum()
  back = s.loc[s["销售类型"] == "退货", "销量"].sum()
  return {
    "商品数": int(len(info)),
    "品类数": int(info["分类编码"].nunique()),
    "流水行数": int(len(s)),
    "退货行数": int((s["销售类型"] == "退货").sum()),
    "售出总量_kg": round(float(sold), 3),
    "退货总量_kg": round(float(back), 3),
    "流水日期范围": [str(s["销售日期"].min().date()),
                    str(s["销售日期"].max().date())],
    "有销售商品数": int(s["单品编码"].nunique()),
    "批发价行数": int(len(w)),
    "批发价日期范围": [str(w["销售日期"].min().date()),
                    str(w["销售日期"].max().date())],
    "有价商品数": int(w["单品编码"].nunique()),
    "损耗率商品数": int(info["损耗率"].notna().sum()),
    "损耗率均值_%": round(float(info["损耗率"].mean()), 4),
    "单品日表行数": int(len(item)),
    "品类日表行数": int(len(cat)),
    "批发价日表行数": int(len(ws)),
    "均值补齐行数": int((ws["价格来源"] == "单品均值").sum()),
    "均值补齐占比_%": round(100 * (ws["价格来源"] == "单品均值").mean(), 4),
  }


def main():
  """执行完整清洗流程."""
  print("=" * 60)
  print("任务 1: 数据清洗与聚合")
  print("=" * 60)

  info = load_info()
  loss, loss_c = load_loss()
  info = info.merge(loss, on="单品编码").merge(loss_c, on="分类编码")
  save(info, "item_info.csv")

  s = load_sales()
  item = daily_item(s).merge(info, on="单品编码", how="left")
  save(item, "item_daily_sales.csv")

  cat = daily_cat(s, info).merge(loss_c, on="分类编码", how="left")
  save(cat, "category_daily_sales.csv")

  w = pd.read_excel(DATA / "附件3.xlsx").rename(columns={"日期": "销售日期",
                                                       "批发价格(元/千克)": "批发价"})
  w["销售日期"] = pd.to_datetime(w["销售日期"])
  ws = daily_ws(w)
  save(ws, "item_daily_wholesale.csv")

  cat_ws = daily_cat_ws(ws, item, info)
  save(cat_ws, "category_daily_wholesale.csv")

  full = item.merge(ws[["销售日期", "单品编码", "批发价"]],
                    on=["销售日期", "单品编码"], how="left")
  full["加价率"] = full["均价"] / full["批发价"] - 1
  save(full, "item_daily_full.csv")

  cat_full = cat.merge(cat_ws[["销售日期", "分类编码", "批发价均值", "批发价加权"]],
                       on=["销售日期", "分类编码"], how="left")
  cat_full["加价率"] = cat_full["均价"] / cat_full["批发价加权"] - 1
  save(cat_full, "category_daily_full.csv")

  pro = profile(info, s, w, item, cat, ws)
  with (OUT / "data_profile.json").open("w", encoding="utf-8") as f:
    json.dump(pro, f, ensure_ascii=False, indent=2)
  print("\n[校验]")
  print(json.dumps(pro, ensure_ascii=False, indent=2))
  print("\n任务 1 完成: 结果已写入 results/")


if __name__ == "__main__":
  sys.exit(main())
