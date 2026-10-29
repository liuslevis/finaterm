"""量化「旧实现会崩溃」的标的数：任何价格/数量超出 int32 都会让
`data._encode_stock` 的 ``array.array("i")`` 抛 OverflowError，导致该股票永久不可读。

在已建的 Parquet 数据集上直接判定，不需要再跑旧实现。
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from app.parquet_store import Store  # noqa: E402
from app.paths import parquet_default  # noqa: E402

I32_MAX = 2**31 - 1
I32_MIN = -(2**31)

# 旧实现 _encode_stock 里用 array("i") 的列
COLS = {
    "orders": ["price", "qty"],
    "trades": ["price", "qty"],
    "quotes": ["last", "high", "low", "open", "prev_close"]
    + [f"ask_px{i}" for i in range(1, 11)] + [f"ask_qty{i}" for i in range(1, 11)]
    + [f"bid_px{i}" for i in range(1, 11)] + [f"bid_qty{i}" for i in range(1, 11)],
}


def main():
    root = parquet_default()
    st = Store(root).open()
    dates = st.dates
    print(f"数据集 {root}  交易日 {len(dates)} 个: {dates}")
    out = {}
    for date in dates:
        per_table: dict[str, set] = {}
        for table, cols in COLS.items():
            bad: set[str] = set()
            for sh in range(st.n_shards()):
                p = st.table_path(date, table, sh)
                if not os.path.exists(p):
                    continue
                t = pq.read_table(p, columns=["code"] + cols)
                mask = None
                for c in cols:
                    a = t.column(c)
                    m = pc.or_(pc.less(a, I32_MIN), pc.greater(a, I32_MAX))
                    mask = m if mask is None else pc.or_(mask, m)
                if mask is None:
                    continue
                n = int(pc.sum(pc.cast(mask, "int64")).as_py() or 0)
                if n:
                    bad |= set(pc.unique(t.filter(mask).column("code")).to_pylist())
            if bad:
                per_table[table] = bad
        allbad = set().union(*per_table.values()) if per_table else set()
        out[date] = {"total_codes": len(st.list_codes(date)),
                     "broken_codes": len(allbad),
                     "by_table": {k: len(v) for k, v in per_table.items()},
                     "sample": sorted(allbad)[:12]}
        print(f"  {date}: 标的 {out[date]['total_codes']:>5}，旧实现会崩溃 "
              f"{len(allbad):>3} 只  {out[date]['by_table']}")
        if allbad:
            print(f"    样例 {sorted(allbad)[:8]}")

    path = os.path.join(HFQ, "snapshot", "old_path_overflow.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({"int32_max": I32_MAX, "dates": out}, fh, indent=2,
                  ensure_ascii=False)
    print(f"\n明细 -> {path}")


if __name__ == "__main__":
    main()
