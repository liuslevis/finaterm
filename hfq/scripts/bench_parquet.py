"""Parquet 可行性验证：解析速度、编码/压缩选择、体积与查询延迟。

在真实样本上对三种候选（7z 原样 / 各压缩编码的 parquet）做同口径测量。
"""
from __future__ import annotations

import io
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

CACHE = os.path.join(ROOT, "cache")
DATE = "20260901"
CODE = os.environ.get("BENCH_CODE", "001301.SZ")
SRC = os.path.join(CACHE, DATE, CODE)

ORD_COLS = ["code", "exch", "date", "t", "order_no", "exch_order_no",
            "order_type", "order_code", "price", "qty"]
TRD_COLS = ["code", "exch", "date", "t", "trade_no", "trade_code",
            "order_code", "side", "price", "qty", "sell_seq", "buy_seq"]
INT_COLS = {"t", "order_no", "exch_order_no", "price", "qty", "trade_no",
            "sell_seq", "buy_seq"}
STR_COLS = {"code", "exch", "date", "order_type", "order_code", "trade_code", "side"}


def read_csv(name, cols):
    t0 = time.perf_counter()
    df = pd.read_csv(
        os.path.join(SRC, name), encoding="gbk", header=None, skiprows=1,
        names=cols, usecols=list(range(len(cols))),
        dtype={c: "int64" for c in cols if c in INT_COLS},
        keep_default_na=False, na_values=[""],
    )
    for c in cols:
        if c in STR_COLS:
            df[c] = df[c].astype("category")
        elif c in INT_COLS:
            df[c] = df[c].fillna(0).astype("int64")
    return df, time.perf_counter() - t0


def bench(name, cols, tmp):
    print(f"--- {name} ---")
    df, dt_read = read_csv(name, cols)
    src_bytes = os.path.getsize(os.path.join(SRC, name))
    print(f"  read_csv(gbk)        {dt_read*1000:8.1f} ms   "
          f"{src_bytes/1024**2:.2f} MB  -> {src_bytes/1024**2/dt_read:6.1f} MB/s")
    print(f"  rows                 {len(df):,}")

    table = pa.Table.from_pandas(df, preserve_index=False)
    print(f"  arrow rows           {table.num_rows:,}")

    for comp, kwargs in [
        ("snappy", {}),
        ("zstd-1", {"compression": "zstd", "compression_level": 1}),
        ("zstd-3", {"compression": "zstd", "compression_level": 3}),
        ("zstd-9", {"compression": "zstd", "compression_level": 9}),
        ("gzip", {"compression": "gzip", "compression_level": 6}),
    ]:
        p = os.path.join(tmp, f"{name}.{comp}.parquet")
        t0 = time.perf_counter()
        pq.write_table(table, p, row_group_size=256_000,
                       use_dictionary=["code", "order_type", "order_code",
                                       "trade_code", "side"],
                       **kwargs)
        wdt = time.perf_counter() - t0
        sz = os.path.getsize(p)
        print(f"  write {comp:<8}      {wdt*1000:8.1f} ms   {sz/1024**2:7.2f} MB  "
              f"({src_bytes/sz:5.2f}x vs csv, {wdt and sz/1024**2/wdt:6.1f} MB/s)")

        t0 = time.perf_counter()
        back = pq.read_table(p)
        rdt = time.perf_counter() - t0
        assert back.num_rows == len(df), (back.num_rows, len(df))
        print(f"    read full          {rdt*1000:8.1f} ms  ({src_bytes/1024**2/rdt:6.1f} MB/s csv-equiv)")

        t0 = time.perf_counter()
        sub = pq.read_table(p, filters=[("code", "=", CODE)])
        fdt = time.perf_counter() - t0
        print(f"    read filtered      {fdt*1000:8.1f} ms  rows={sub.num_rows:,}")


if __name__ == "__main__":
    tmp = os.path.join(ROOT, "cache", "_pqtest")
    os.makedirs(tmp, exist_ok=True)
    bench("逐笔委托.csv", ORD_COLS, tmp)
    bench("逐笔成交.csv", TRD_COLS, tmp)
