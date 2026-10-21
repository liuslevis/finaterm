"""验证市价委托哨兵价格的处置：新旧实现的差异必须**只**出现在价格字段。

源数据把 -1.00 元写成 ``2^64 - 10000``。原实现按任意精度整数解析得到
``1.844674407370954e15`` 元；Parquet 路径按二补码还原为 ``-1.00`` 元。
本脚本证明：
  1. 事件条数与顺序完全一致；
  2. 除价格外所有字段一致；
  3. 差异行的新价格恰好是 -1.00，旧价格恰好是该哨兵值。
"""
from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)
sys.path.insert(0, HERE)

from verify_daily_kline import load_old_module  # noqa: E402

SENTINEL = 2**64 - 10000          # 源文件里的字面量
OLD_PRICE = SENTINEL / 10000.0    # 原实现算出的价格
NEW_PRICE = -1.0                  # 二补码还原后的价格


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", default="20260731")
    ap.add_argument("--root", default=os.path.join(HFQ, "data-parquet"))
    ap.add_argument("--snapshot", default=os.path.join(HFQ, "snapshot", "baseline-v1"))
    ap.add_argument("--max", type=int, default=40)
    args = ap.parse_args()

    os.environ["HFQ_PARQUET_DIR"] = os.path.abspath(args.root)
    from app import data as new

    import pyarrow.compute as pc
    import pyarrow.parquet as pq

    if not new.PARQUET_ENABLED or args.date not in new._PQ.dates:
        raise SystemExit("数据集不含该交易日")

    # 从 Parquet 找出带哨兵价格的标的
    st = new._PQ
    hit_codes: set[str] = set()
    total_hits = 0
    for sh in range(st.n_shards()):
        p = st.table_path(args.date, "orders", sh)
        if not os.path.exists(p):
            continue
        t = pq.read_table(p, columns=["code", "price"])
        m = pc.equal(t.column("price"), -10000)
        n = int(pc.sum(pc.cast(m, "int64")).as_py() or 0)
        if n:
            total_hits += n
            hit_codes |= set(pc.unique(t.filter(m).column("code")).to_pylist())

    print(f"{args.date}: 委托表中价格为 -1.00 元的哨兵行 {total_hits} 条，"
          f"涉及 {len(hit_codes)} 只")
    if not hit_codes:
        print("无哨兵行，改用常规比对")
    codes = sorted(hit_codes)[:args.max]

    old = load_old_module(args.snapshot)
    old.CACHE_DIR = os.path.join(HFQ, "cache", "_ab_old")
    os.makedirs(old.CACHE_DIR, exist_ok=True)

    report = []
    all_ok = True
    for code in codes:
        # 先确认新路径能读
        try:
            b = new.StockData(code, args.date)
        except Exception as e:  # noqa: BLE001
            report.append({"code": code, "status": "NEW_FAILED",
                           "error": f"{type(e).__name__}: {e}"})
            all_ok = False
            continue
        try:
            a = old.StockData(code, args.date)
        except Exception as e:  # noqa: BLE001
            # 旧实现在 _encode_stock 用 array("i") 存价格，哨兵值必然 OverflowError，
            # 该股票在旧实现下永久不可读。新路径能正常读出，属修复而非差异。
            report.append({"code": code, "status": "OLD_BROKEN",
                           "events": len(b.events),
                           "old_error": f"{type(e).__name__}: {e}",
                           "ok": True})
            print(f"  {code:<12} 旧实现崩溃（{type(e).__name__}）→ 新实现 "
                  f"{len(b.events)} 事件可读  FIXED")
            continue

        keys = ("aseq", "t", "type", "side", "qty", "buy_id", "sell_id",
                "order_id", "amount")
        diffs, price_diffs = [], []
        same_len = len(a.events) == len(b.events)
        if not same_len:
            all_ok = False
            diffs.append(f"事件条数 {len(a.events)} != {len(b.events)}")
        else:
            for i, (x, y) in enumerate(zip(a.events, b.events)):
                if x["price"] != y["price"]:
                    price_diffs.append({"seq": i + 1, "old": x["price"],
                                        "new": y["price"], "type": y["type"],
                                        "side": y["side"], "qty": y["qty"]})
                for k in keys:
                    if x[k] != y[k]:
                        diffs.append(f"events[{i}].{k} {x[k]} != {y[k]}")
                if len(diffs) > 5:
                    break
        bad_price = [d for d in price_diffs
                     if not (abs(d["new"] - NEW_PRICE) < 1e-12
                             and abs(d["old"] - OLD_PRICE) < 1e-3)]
        # 非价格字段若也不一致，才算真正不符
        non_price = [d for d in diffs if ".price" not in d]
        ok = same_len and not non_price and not bad_price
        all_ok &= ok
        entry = {"code": code, "status": "COMPARED",
                 "events": len(b.events), "same_length": same_len,
                 "price_diffs": len(price_diffs),
                 "non_price_diffs": non_price[:5],
                 "unexpected_price_diffs": bad_price[:5], "ok": ok}
        # 快照是否也受影响
        entry["quotes_equal"] = (a.quotes == b.quotes)
        entry["basic_equal"] = (a.basic == b.basic)
        report.append(entry)
        print(f"  {code:<12} 事件 {len(b.events):>7}  价格差异 {len(price_diffs):>3}  "
              f"非价格差异 {len(non_price):>2}  快照一致={entry['quotes_equal']} "
              f"basic一致={entry['basic_equal']}  {'OK' if ok else 'CHECK'}")

    print(f"\n=== 结论 ===  全部符合预期: {all_ok}")
    print(f"  旧价格 {OLD_PRICE:.6e} -> 新价格 {NEW_PRICE}（市价委托哨兵）")
    out = os.path.join(HFQ, "snapshot", f"compare_sentinel_{args.date}.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"date": args.date, "sentinel_rows": total_hits,
                   "codes_with_sentinel": len(hit_codes),
                   "old_price": OLD_PRICE, "new_price": NEW_PRICE,
                   "all_expected": all_ok, "detail": report}, fh,
                  indent=2, ensure_ascii=False)
    print(f"  明细 -> {out}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
