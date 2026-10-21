"""测量 price/qty 用 int64 的存储代价（相对 int32），决定 schema 取值。"""
from __future__ import annotations

import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from app.parquet_store import (  # noqa: E402
    ORDERS_SCHEMA, QUOTES_SCHEMA, TRADES_SCHEMA, WRITE_OPTS, _DICT_COLS, Store,
)

ROOT = os.path.join(HFQ, "data-parquet")
DATE = "20260630"
TMP = os.path.join(HFQ, "cache", "_i64test")
os.makedirs(TMP, exist_ok=True)

st = Store(ROOT).open()

WIDEN = {"orders": ["price", "qty"],
         "trades": ["price", "qty"],
         "quotes": ["last", "high", "low", "open", "prev_close"]
         + [f"ask_px{i}" for i in range(1, 11)]
         + [f"ask_qty{i}" for i in range(1, 11)]
         + [f"bid_px{i}" for i in range(1, 11)]
         + [f"bid_qty{i}" for i in range(1, 11)]}

SCHEMAS = {"orders": ORDERS_SCHEMA, "trades": TRADES_SCHEMA, "quotes": QUOTES_SCHEMA}

print(f"{'table':<8}{'shard':>6}{'rows':>12}{'int32 MB':>11}{'int64 MB':>11}{'delta':>9}")
tot32 = tot64 = 0
for shard in (0, 8, 20, 27, 35):
    for table in ("orders", "trades", "quotes"):
        src = st.table_path(DATE, table, shard)
        if not os.path.exists(src):
            continue
        t = pq.read_table(src)
        # 1) 原样（int32）
        p32 = os.path.join(TMP, f"{table}-{shard}-i32.parquet")
        pq.write_table(t, p32, **WRITE_OPTS, use_dictionary=_DICT_COLS[table])
        # 2) 加宽到 int64
        cols = []
        for f in SCHEMAS[table]:
            if f.name in WIDEN[table]:
                cols.append(pa.field(f.name, pa.int64()))
            else:
                cols.append(f)
        wide = pa.schema(cols)
        idx = {n: i for i, n in enumerate(t.column_names)}
        arrays = []
        for f in wide:
            c = t.column(f.name)
            arrays.append(c.cast(pa.int64()) if f.type == pa.int64() else c)
        t64 = pa.Table.from_arrays(arrays, schema=wide)
        p64 = os.path.join(TMP, f"{table}-{shard}-i64.parquet")
        pq.write_table(t64, p64, **WRITE_OPTS, use_dictionary=_DICT_COLS[table])
        s32, s64 = os.path.getsize(p32), os.path.getsize(p64)
        tot32 += s32
        tot64 += s64
        print(f"{table:<8}{shard:>6}{t.num_rows:>12,}{s32/1024**2:>11.2f}"
              f"{s64/1024**2:>11.2f}{s64/s32:>9.2f}x")
        del t, t64

print(f"\n合计  int32 {tot32/1024**2:.1f} MB  int64 {tot64/1024**2:.1f} MB  "
      f"{tot64/tot32:.2f}x")
print(f"按此比例推算全天：4.35 GB -> {4.35*tot64/tot32:.2f} GB")
shutil.rmtree(TMP, ignore_errors=True)
