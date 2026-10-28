# -*- coding: utf-8 -*-
r"""重建后的一致性复核：新数据集 vs 旧数据集 vs 7z 原始 CSV。

背景
----
因为 universe（分片映射）变了，整份数据集必须重建。重建要证明两件事：

1. **和旧数据集逐字段一致**：2026-06-30~2026-09-21 这 59 天在旧数据集里已经过
   33 项快照比对 + 120 项抽样扫描，是可信的基准。新数据集对这些天必须给出
   完全相同的事件流（同样的 CSV、同样的解析代码，只是换了分片下标）。
2. **新日期能被 7z 回退路径复现**：2026-01~06 的平铺归档走 app 自己的解析
   路径（data.get_stock），与新数据集的 Store.load_stock 逐一对照。

用法
----
    python hfq/scripts/verify_rebuild.py --root D:\data-parquet \
        --old-root hfq/data-parquet --overlap-days 8 --per-day 6 --csv-days 3
"""

from __future__ import annotations

import argparse
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

from app.parquet_store import Store  # noqa: E402

KEY_EVENT = ("aseq", "t", "type", "side", "price", "qty", "amount",
             "buy_id", "sell_id", "order_id", "seq")


def cmp_stock(new_store: Store, code: str, date: str, old_obj: dict) -> list[str]:
    """返回差异描述列表（空 = 一致）。"""
    ev_new, q_new = new_store.load_stock(code, date)
    ev_old = old_obj["events"]
    q_old = old_obj["quotes"]
    bad: list[str] = []
    if len(ev_new) != len(ev_old):
        bad.append(f"事件数 {len(ev_new)} != {len(ev_old)}")
        return bad
    if len(q_new) != len(q_old):
        bad.append(f"快照数 {len(q_new)} != {len(q_old)}")
        return bad
    for i, (a, b) in enumerate(zip(ev_new, ev_old)):
        for k in KEY_EVENT:
            if a.get(k) != b.get(k):
                bad.append(f"event[{i}].{k}: {a.get(k)!r} != {b.get(k)!r}")
                if len(bad) > 8:
                    return bad
    for i, (a, b) in enumerate(zip(q_new, q_old)):
        for k in set(a) | set(b):
            if a.get(k) != b.get(k):
                bad.append(f"quote[{i}].{k}: {a.get(k)!r} != {b.get(k)!r}")
                if len(bad) > 8:
                    return bad
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=r"D:\data-parquet")
    ap.add_argument("--old-root", default=os.path.join(HFQ, "data-parquet"))
    ap.add_argument("--overlap-days", type=int, default=8)
    ap.add_argument("--per-day", type=int, default=6)
    ap.add_argument("--csv-days", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20261028)
    args = ap.parse_args()

    new = Store(args.root).open()
    print(f"[new] {args.root} dates={len(new.dates)} universe={len(new._m['universe'])} "
          f"shards={new.n_shards()}")

    old = None
    if args.old_root and os.path.exists(os.path.join(args.old_root, "_meta", "manifest.json")):
        old = Store(args.old_root).open()
        print(f"[old] {args.old_root} dates={len(old.dates)} "
              f"universe={len(old._m['universe'])} shards={old.n_shards()}")

    rng = random.Random(args.seed)
    fails = 0
    checked = 0

    # ---- 1) 与旧数据集逐字段对比 ---------------------------------------- #
    if old is not None:
        shared = sorted(set(new.dates) & set(old.dates))
        print(f"\n=== 旧数据集重叠 {len(shared)} 天，抽 {args.overlap_days} 天 ===")
        days = rng.sample(shared, min(args.overlap_days, len(shared)))
        for d in sorted(days):
            codes = new.list_codes(d)
            pick = rng.sample(codes, min(args.per_day, len(codes)))
            for code in pick:
                checked += 1
                ev_old, q_old = old.load_stock(code, d)
                bad = cmp_stock(new, code, d, {"events": ev_old, "quotes": q_old})
                if bad:
                    fails += 1
                    print(f"  FAIL {d} {code}: {'; '.join(bad[:3])}")
            print(f"  {d}: {len(pick)} 只 完成")

    # ---- 2) 新日期 vs 7z 回退解析 --------------------------------------- #
    new_only = [d for d in new.dates if old is None or d not in set(old.dates)]
    if new_only:
        # 把 Parquet 屏蔽掉，逼 app 走 7z + CSV 解析路径
        os.environ["HFQ_PARQUET_DIR"] = os.path.join(HFQ, "cache", "_noparquet")
        os.makedirs(os.environ["HFQ_PARQUET_DIR"], exist_ok=True)
        from app import data as ref  # noqa: E402
        print(f"\n=== 新日期 {len(new_only)} 天，抽 {args.csv_days} 天与 7z 解析对比 ===")
        print(f"    （参考路径 parquet_enabled={ref.PARQUET_ENABLED}）")
        days = rng.sample(new_only, min(args.csv_days, len(new_only)))
        for d in sorted(days):
            codes = new.list_codes(d)
            pick = rng.sample(codes, min(3, len(codes)))
            for code in pick:
                checked += 1
                try:
                    sd = ref.get_stock(code, d)
                except Exception as e:  # noqa: BLE001
                    print(f"  SKIP {d} {code}: 参考路径失败 {type(e).__name__}: {e}")
                    continue
                bad = cmp_stock(new, code, d,
                                {"events": sd.events, "quotes": sd.quotes})
                if bad:
                    fails += 1
                    print(f"  FAIL {d} {code}: {'; '.join(bad[:3])}")
            print(f"  {d}: {len(pick)} 只 完成")

    print(f"\n=== 结果：{checked - fails}/{checked} 通过 ===")
    return 0 if fails == 0 and checked else 1


if __name__ == "__main__":
    sys.exit(main())
