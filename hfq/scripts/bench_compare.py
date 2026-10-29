"""A/B 基准：旧 7z 路径（冷/热） vs 新 Parquet 路径，含磁盘占用对比。

旧实现来自快照副本，缓存目录独立（cache/_ab_old），避免相互污染。
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import statistics
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)
sys.path.insert(0, HERE)

from verify_daily_kline import load_old_module  # noqa: E402
from app.paths import parquet_default  # noqa: E402


def dir_bytes(p: str) -> int:
    if not os.path.exists(p):
        return 0
    return sum(os.path.getsize(os.path.join(dp, f))
               for dp, _, fs in os.walk(p) for f in fs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260901")
    ap.add_argument("--snapshot", default=os.path.join(HFQ, "snapshot", "baseline-v1"))
    ap.add_argument("--root", default=parquet_default())
    ap.add_argument("--codes", nargs="*", default=None)
    ap.add_argument("--json-out", default=os.path.join(HFQ, "snapshot", "compare_perf.json"))
    args = ap.parse_args()

    os.environ["HFQ_PARQUET_DIR"] = os.path.abspath(args.root)
    from app import data as new

    if not new.PARQUET_ENABLED:
        raise SystemExit("Parquet 数据集不可用")
    if args.date not in new._PQ.dates:
        raise SystemExit(f"{args.date} 未转换")

    old = load_old_module(args.snapshot)
    old.CACHE_DIR = os.path.join(HFQ, "cache", "_ab_old")
    os.makedirs(old.CACHE_DIR, exist_ok=True)

    codes = args.codes
    if not codes:
        allc = new._PQ.list_codes(args.date)
        # 取中位规模附近的样本，避免只挑极端
        codes = [allc[0], allc[len(allc) // 4], allc[len(allc) // 2],
                 allc[3 * len(allc) // 4], allc[-1]]

    print(f"日期 {args.date}  样本 {len(codes)} 只: {codes}\n")
    rows = []
    for code in codes:
        rec = {"code": code}

        # --- 旧：冷（无 bin、无 CSV）---
        dst = os.path.join(old.CACHE_DIR, args.date, code)
        shutil.rmtree(dst, ignore_errors=True)
        shutil.rmtree(os.path.join(old.CACHE_DIR, args.date, "_stage"), ignore_errors=True)
        t0 = time.perf_counter()
        sd = old.StockData(code, args.date)
        rec["old_cold_s"] = round(time.perf_counter() - t0, 4)
        rec["events"] = len(sd.events)
        rec["quotes"] = len(sd.quotes)
        bin_path = os.path.join(dst, f"_cache_v{old._CACHE_VER}.bin")
        rec["bin_bytes"] = os.path.getsize(bin_path) if os.path.exists(bin_path) else 0
        rec["csv_bytes"] = sum(
            os.path.getsize(os.path.join(dst, n)) for n in
            ("行情.csv", "逐笔委托.csv", "逐笔成交.csv")
            if os.path.exists(os.path.join(dst, n)))

        # --- 旧：热（bin 缓存）---
        t0 = time.perf_counter()
        old.StockData(code, args.date)
        rec["old_warm_s"] = round(time.perf_counter() - t0, 4)

        # --- 新：Parquet（无任何缓存，清空内存 LRU）---
        new._MEM.clear()
        t0 = time.perf_counter()
        sd2 = new.StockData(code, args.date)
        rec["new_s"] = round(time.perf_counter() - t0, 4)
        rec["same_events"] = len(sd2.events) == len(sd.events)

        # --- 新：内存热（LRU 命中）---
        t0 = time.perf_counter()
        new.get_stock(code, args.date)
        rec["new_mem_s"] = round(time.perf_counter() - t0, 5)

        rows.append(rec)
        print(f"  {code:<12} 旧冷 {rec['old_cold_s']:7.3f}s  旧热 {rec['old_warm_s']:6.3f}s  "
              f"新 {rec['new_s']:6.3f}s  | bin {rec['bin_bytes']/1024**2:6.2f} MB  "
              f"csv {rec['csv_bytes']/1024**2:5.2f} MB")

    def med(k):
        return statistics.median(r[k] for r in rows)

    total_pq = dir_bytes(new._PQ.root)
    n_stocks = len(new._PQ.list_codes(args.date))
    m = new._PQ.manifest()
    info = m["dates"][args.date]
    # 全量 Parquet 体积要除以「全部交易日的 股票×日」总数，不能除以单日标的数
    stock_days = sum(v.get("codes", 0) for v in m["dates"].values()) or n_stocks
    print(f"\n=== 汇总（{args.date}，{n_stocks} 只）===")
    print(f"  耗时中位数   旧冷 {med('old_cold_s'):7.3f}s  旧热 {med('old_warm_s'):6.3f}s  "
          f"新 {med('new_s'):6.3f}s  内存命中 {med('new_mem_s')*1000:5.1f}ms")
    print(f"  事件数一致   {all(r['same_events'] for r in rows)}")
    print(f"\n  磁盘：")
    print(f"    7z 归档        {info['archive_bytes']/1024**3:8.2f} GB  "
          f"({info['archive_bytes']/n_stocks/1024**2:.2f} MB/只)")
    print(f"    CSV 解压合计   {info['raw_bytes']/1024**3:8.2f} GB  "
          f"({info['raw_bytes']/n_stocks/1024**2:.2f} MB/只)")
    print(f"    Parquet 合计   {total_pq/1024**3:8.2f} GB  "
          f"（{len(m['dates'])} 天 / {stock_days:,} 个股票×日，"
          f"{total_pq/stock_days/1024**2:.2f} MB/只/日）")
    print(f"    旧 bin 缓存    {med('bin_bytes')/1024**2:8.2f} MB/只（中位）")
    print(f"    旧 CSV 残留    {med('csv_bytes')/1024**2:8.2f} MB/只（中位）")
    print(f"    旧每只合计     {(med('bin_bytes')+med('csv_bytes'))/1024**2:8.2f} MB/只")

    out = {"date": args.date, "codes": codes, "rows": rows,
           "median": {k: med(k) for k in
                      ("old_cold_s", "old_warm_s", "new_s", "new_mem_s",
                       "bin_bytes", "csv_bytes")},
           "day": {"stocks": n_stocks, "archive_bytes": info["archive_bytes"],
                   "raw_bytes": info["raw_bytes"], "parquet_bytes": total_pq,
                   "extract_seconds": info["extract_seconds"],
                   "parse_seconds": info["parse_seconds"],
                   "total_seconds": info["total_seconds"]}}
    with open(args.json_out, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)
    print(f"\n明细 -> {args.json_out}")


if __name__ == "__main__":
    main()
