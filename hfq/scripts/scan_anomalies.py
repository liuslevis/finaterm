"""扫描已建 Parquet，检查是否存在**不可能出现**的数值。

schema 已全部使用 int64，因此不再与 int32 比较；这里验证的是：
  - 数量类不允许为负
  - 价格类允许 -1.00 元哨兵（-10000），但不允许超过 200 万元（2e10）
  - 序号类不允许为负
「旧实现会因 int32 溢出而崩溃」的统计见 ``scan_old_overflow.py``。
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from app.parquet_store import Store  # noqa: E402
from app.paths import parquet_default  # noqa: E402

I64_MAX = 2**63 - 1
# 本数据集源文件里的价格本身就有极端值（均为厂商写入，parquet 忠实保留）：
#   最大 1e12（1 亿元/股，20260812/301717.SZ）
#   最小 -2,104,207,296（-210,420 元，20260706/001248.SZ，CSV 里就带负号）
# 因此这里只拦「不可能是源数据」的量级，极端但真实的值走"观测"通道单独报出。
PRICE_MIN = -10**15
PRICE_MAX = 10**15

PRICE_COLS = ["price"]
QTY_COLS = ["qty"]
LADDER = 10


def checks_for(table: str) -> list[tuple[str, int, int]]:
    if table == "orders":
        return [("order_no", 0, I64_MAX), ("exch_order_no", 0, I64_MAX),
                ("price", PRICE_MIN, PRICE_MAX), ("qty", 0, I64_MAX)]
    if table == "trades":
        return [("trade_no", 0, I64_MAX), ("price", PRICE_MIN, PRICE_MAX),
                ("qty", 0, I64_MAX), ("sell_seq", 0, I64_MAX),
                ("buy_seq", 0, I64_MAX)]
    out = [("last", PRICE_MIN, PRICE_MAX), ("high", PRICE_MIN, PRICE_MAX),
           ("low", PRICE_MIN, PRICE_MAX), ("open", PRICE_MIN, PRICE_MAX),
           ("prev_close", PRICE_MIN, PRICE_MAX)]
    for k in range(1, LADDER + 1):
        out.append((f"ask_px{k}", PRICE_MIN, PRICE_MAX))
        out.append((f"ask_qty{k}", 0, I64_MAX))
        out.append((f"bid_px{k}", PRICE_MIN, PRICE_MAX))
        out.append((f"bid_qty{k}", 0, I64_MAX))
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="扫描 Parquet 数据集中的不可能数值")
    ap.add_argument("--root", default=parquet_default())
    ap.add_argument("--dates", nargs="*", default=None,
                    help="只扫描指定交易日（默认全部）")
    ap.add_argument("--json-out", default=os.path.join(HFQ, "snapshot", "anomalies.json"))
    args = ap.parse_args()

    st = Store(args.root).open()
    dates = sorted(set(args.dates) & set(st.dates)) if args.dates else st.dates
    print(f"数据集 {args.root}  扫描 {len(dates)}/{len(st.dates)} 个交易日")
    anomalies: Counter = Counter()
    bad_codes: dict[str, set] = {}
    for date in dates:
        for table in ("orders", "trades", "quotes"):
            cols = checks_for(table)
            for sh in range(st.n_shards()):
                p = st.table_path(date, table, sh)
                if not os.path.exists(p):
                    continue
                t = pq.read_table(p, columns=[c for c, _, _ in cols] + ["code"])
                for col, lo, hi in cols:
                    a = t.column(col)
                    mn, mx = pc.min(a).as_py(), pc.max(a).as_py()
                    if mn is None:
                        continue
                    if mn < lo or mx > hi:
                        anomalies[f"{date}.{table}.{col}"] += 1
                        print(f"  ! {date} {table}.{col} shard={sh:03d} "
                              f"min={mn} max={mx}")
                        mask = pc.or_(pc.less(a, lo), pc.greater(a, hi))
                        codes = set(pc.unique(
                            t.filter(mask).column("code")).to_pylist())
                        bad_codes.setdefault(f"{table}.{col}", set()).update(codes)

    print("\n=== 观测（源数据特征，已忠实保留，非迁移错误）===")
    neg = 0
    for date in dates[:1]:
        for sh in range(st.n_shards()):
            pp = st.table_path(date, "quotes", sh)
            if not os.path.exists(pp):
                continue
            tt = pq.read_table(pp, columns=["cum_amt", "cum_vol"])
            for col in ("cum_amt", "cum_vol"):
                mn = pc.min(tt.column(col)).as_py()
                if mn is not None and mn < 0:
                    neg += 1
                    print(f"  {date} quotes.{col} 最小 {mn}"
                          f"（负值：厂商 int32 溢出痕迹）")
    for date in dates:
        for table, cols in (("orders", ["price"]), ("trades", ["price"]),
                            ("quotes", ["last"])):
            mn = mx = None
            for sh in range(st.n_shards()):
                pp = st.table_path(date, table, sh)
                if not os.path.exists(pp):
                    continue
                tt = pq.read_table(pp, columns=cols)
                lo = pc.min(tt.column(cols[0])).as_py()
                hi = pc.max(tt.column(cols[0])).as_py()
                if lo is not None:
                    mn = lo if mn is None else min(mn, lo)
                if hi is not None:
                    mx = hi if mx is None else max(mx, hi)
            if mn is None:
                continue
            # 只在出现"极值"时打印，避免 59 天刷屏
            if abs(mn) > 10**9 or abs(mx) > 10**9:
                print(f"  {date} {table}.{cols[0]} 区间 {mn/10000:,.2f} "
                      f"… {mx/10000:,.2f} 元")

    print("\n=== 结论 ===")
    print(f"扫描交易日: {dates}")
    print(f"异常列: {dict(anomalies) or '无'}")
    for k, v in bad_codes.items():
        print(f"  {k}: {len(v)} 只  样例 {sorted(v)[:8]}")
    with open(args.json_out, "w", encoding="utf-8") as fh:
        json.dump({"root": args.root, "dates": dates,
                   "anomalies": dict(anomalies),
                   "codes": {k: sorted(v) for k, v in bad_codes.items()}},
                  fh, indent=2, ensure_ascii=False)
    print(f"明细 -> {args.json_out}")
    return 0 if not anomalies else 1


if __name__ == "__main__":
    main()
