"""对比 parquet 编码策略：默认字典/PLAIN vs 显式 DELTA_BINARY_PACKED 序号列。"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

SRC = os.path.join(ROOT, "cache", "20260901", os.environ.get("BENCH_CODE", "001301.SZ"))
COLS = ["code", "exch", "date", "t", "trade_no", "trade_code",
        "order_code", "side", "price", "qty", "sell_seq", "buy_seq"]
INT = {"t", "trade_no", "price", "qty", "sell_seq", "buy_seq"}
STR = {"code", "exch", "date", "trade_code", "order_code", "side"}

df = pd.read_csv(os.path.join(SRC, "逐笔成交.csv"), encoding="gbk", header=None,
                 skiprows=1, names=COLS, usecols=list(range(len(COLS))),
                 dtype={c: "int64" for c in COLS if c in INT},
                 keep_default_na=False, na_values=[""])
for c in COLS:
    if c in STR:
        df[c] = df[c].astype("category")
    elif c in INT:
        df[c] = df[c].fillna(0).astype("int64")

t = pa.Table.from_pandas(df, preserve_index=False)
srcmb = os.path.getsize(os.path.join(SRC, "逐笔成交.csv")) / 1024**2
tmp = os.path.join(ROOT, "cache", "_pqtest")
os.makedirs(tmp, exist_ok=True)


def run(tag, **kw):
    p = os.path.join(tmp, f"enc-{tag}.parquet")
    pq.write_table(t, p, **kw)
    sz = os.path.getsize(p) / 1024**2
    print(f"  {tag:<28} {sz:7.3f} MB   {srcmb/sz:6.2f}x")
    return sz


print(f"source csv {srcmb:.2f} MB, {len(df):,} rows")
base = dict(compression="zstd", compression_level=3, row_group_size=256_000,
            use_dictionary=["code", "trade_code", "order_code", "side"])
run("default(zstd3+dict)", **base)
run("delta-seq", column_encoding={
    "t": "DELTA_BINARY_PACKED", "trade_no": "DELTA_BINARY_PACKED",
    "sell_seq": "DELTA_BINARY_PACKED", "buy_seq": "DELTA_BINARY_PACKED",
}, **base)
run("delta+delta-price-qty", column_encoding={
    "t": "DELTA_BINARY_PACKED", "trade_no": "DELTA_BINARY_PACKED",
    "sell_seq": "DELTA_BINARY_PACKED", "buy_seq": "DELTA_BINARY_PACKED",
    "price": "DELTA_BINARY_PACKED", "qty": "DELTA_BINARY_PACKED",
}, **base)
run("default norg", compression="zstd", compression_level=3,
    use_dictionary=["code", "trade_code", "order_code", "side"])
run("snappy", compression="snappy", row_group_size=256_000,
    use_dictionary=["code", "trade_code", "order_code", "side"])
