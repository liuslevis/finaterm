"""大样本一致性扫描：Parquet 路径 vs 原始 CSV 解析路径，逐字段比对。

覆盖全部市场/板块分组，并显式包含历史上行情.csv 出现 int64 溢出的基金代码。
原始实现来自快照副本；预先把解压好的 CSV 放进它的缓存目录以跳过 7z 抽取。
"""
from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)
sys.path.insert(0, HERE)

from verify_daily_kline import load_old_module  # noqa: E402
from app.paths import parquet_default  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260901")
    ap.add_argument("--root", default=parquet_default())
    ap.add_argument("--snapshot", default=os.path.join(HFQ, "snapshot", "baseline-v1"))
    ap.add_argument("--csv-src", default=os.path.join(HFQ, "cache", "_scan"),
                    help="已解压的 CSV 目录（<date>/<code>/*.csv），用于免抽取")
    ap.add_argument("--n", type=int, default=120)
    ap.add_argument("--seed", type=int, default=20260901)
    ap.add_argument("--json-out", default=os.path.join(HFQ, "snapshot", "compare_sweep.json"))
    args = ap.parse_args()

    os.environ["HFQ_PARQUET_DIR"] = os.path.abspath(args.root)
    from app import data as new  # noqa: E402

    if not new.PARQUET_ENABLED or args.date not in new._PQ.dates:
        raise SystemExit("Parquet 数据集不可用")

    old = load_old_module(args.snapshot)
    old.CACHE_DIR = os.path.join(HFQ, "cache", "_ab_old")
    os.makedirs(old.CACHE_DIR, exist_ok=True)

    codes = new._PQ.list_codes(args.date)
    by_board: dict[str, list[str]] = {}
    for c in codes:
        by_board.setdefault(c[:3], []).append(c)

    # 1) 历史溢出代码  2) 每个前缀分组抽样  3) 随机补充
    picks: list[str] = [c for c in ("160119.SZ", "160140.SZ", "160216.SZ")
                        if c in set(codes)]
    rng = random.Random(args.seed)
    per_group = max(1, args.n // max(len(by_board), 1))
    for pre in sorted(by_board):
        g = by_board[pre]
        picks += rng.sample(g, min(per_group, len(g)))
    rest = [c for c in codes if c not in set(picks)]
    picks += rng.sample(rest, max(0, min(args.n - len(picks), len(rest))))
    picks = list(dict.fromkeys(picks))
    print(f"{args.date} 共 {len(codes)} 只，抽查 {len(picks)} 只，"
          f"覆盖 {len(by_board)} 个代码前缀分组")

    src_base = os.path.join(args.csv_src, args.date)
    ok = fail = err = 0
    fails = []
    t0 = time.perf_counter()
    for i, code in enumerate(picks, 1):
        # 预置 CSV，让旧实现跳过 7z 抽取
        dst = os.path.join(old.CACHE_DIR, args.date, code)
        src = os.path.join(src_base, code)
        if os.path.isdir(src) and not os.path.isdir(dst):
            os.makedirs(dst, exist_ok=True)
            for n in ("行情.csv", "逐笔委托.csv", "逐笔成交.csv"):
                p = os.path.join(src, n)
                if os.path.exists(p):
                    shutil.copy2(p, os.path.join(dst, n))
        try:
            a = old.StockData(code, args.date)
            b = new.StockData(code, args.date)
        except Exception as e:  # noqa: BLE001
            err += 1
            fails.append({"code": code, "error": f"{type(e).__name__}: {e}"})
            continue

        def fp(sd):
            return [[e["aseq"], e["t"], e["type"], e["side"], e["price"],
                     e["qty"], e["buy_id"], e["sell_id"], e["order_id"],
                     e["amount"]] for e in sd.events]

        def qfp(sd):
            return [[q["t"], q["last"], q["cum_vol"], q["cum_amt"], q["high"],
                     q["low"], q["open"], q["prev_close"], q["asks"], q["bids"]]
                    for q in sd.quotes]

        diffs = []
        if len(a.events) != len(b.events):
            diffs.append(f"events {len(a.events)} != {len(b.events)}")
        elif fp(a) != fp(b):
            k = next(j for j, (x, y) in enumerate(zip(fp(a), fp(b))) if x != y)
            diffs.append(f"events[{k}] {fp(a)[k]} != {fp(b)[k]}")
        if len(a.quotes) != len(b.quotes):
            diffs.append(f"quotes {len(a.quotes)} != {len(b.quotes)}")
        elif qfp(a) != qfp(b):
            k = next(j for j, (x, y) in enumerate(zip(qfp(a), qfp(b))) if x != y)
            diffs.append(f"quotes[{k}] {qfp(a)[k]} != {qfp(b)[k]}")
        if a.basic != b.basic:
            for k in sorted(set(a.basic) | set(b.basic)):
                if a.basic.get(k) != b.basic.get(k):
                    diffs.append(f"basic.{k} {a.basic.get(k)} != {b.basic.get(k)}")
        if diffs:
            fail += 1
            fails.append({"code": code, "diffs": diffs[:6]})
        else:
            ok += 1
        if i % 20 == 0:
            print(f"  {i}/{len(picks)}  OK={ok} FAIL={fail} ERR={err}  "
                  f"{time.perf_counter()-t0:.0f}s")
        # 清掉旧实现的 bin 缓存，避免磁盘膨胀
        for n in os.listdir(dst) if os.path.isdir(dst) else []:
            if n.startswith("_cache_v"):
                os.remove(os.path.join(dst, n))

    dt = time.perf_counter() - t0
    print(f"\n=== 结论（{args.date}）===")
    print(f"  抽查 {len(picks)} 只：逐字段一致 {ok}，不一致 {fail}，异常 {err}  "
          f"耗时 {dt:.0f}s")
    for f in fails[:10]:
        print(f"  ! {f['code']}: {f.get('diffs') or f.get('error')}")

    with open(args.json_out, "w", encoding="utf-8") as fh:
        json.dump({"date": args.date, "checked": len(picks), "ok": ok,
                   "fail": fail, "error": err, "seconds": round(dt, 1),
                   "codes": picks, "failures": fails}, fh,
                  indent=2, ensure_ascii=False)
    print(f"明细 -> {args.json_out}")
    return 0 if (fail == 0 and err == 0) else 1


if __name__ == "__main__":
    raise SystemExit(main())
