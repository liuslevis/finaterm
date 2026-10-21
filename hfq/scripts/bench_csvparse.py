"""对比 GBK CSV 解析：pandas.read_csv vs pyarrow.csv（跳过表头后数据段为纯 ASCII）。

数据行只含数字/逗号/字母，中文仅出现在表头，因此可以跳过表头后直接交给
pyarrow.csv 多线程解析，避免整表按 GBK 解码。
"""
from __future__ import annotations

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.csv as pacsv  # noqa: E402

SRC = os.path.join(ROOT, "cache", "20260901", os.environ.get("BENCH_CODE", "001301.SZ"))


def timed(label, fn, n=3):
    ts = []
    r = None
    for _ in range(n):
        t0 = time.perf_counter()
        r = fn()
        ts.append(time.perf_counter() - t0)
    print(f"  {label:<46} {min(ts)*1000:8.1f} ms")
    return r


def body_of(path: str) -> bytes:
    with open(path, "rb") as fh:
        raw = fh.read()
    i = raw.find(b"\n")
    return raw[i + 1:]


def ascii_only(path: str) -> bool:
    with open(path, "rb") as fh:
        raw = fh.read()
    i = raw.find(b"\n")
    return all(b < 128 for b in raw[i + 1:])


def bench(name: str, width: int, types: dict[int, pa.DataType]):
    path = os.path.join(SRC, name)
    mb = os.path.getsize(path) / 1024**2
    print(f"--- {name}  {mb:.2f} MB ---")
    print(f"  数据段纯 ASCII: {ascii_only(path)}")

    names = [f"c{i}" for i in range(width)]

    def via_pandas():
        return pd.read_csv(path, encoding="gbk", header=None, skiprows=1,
                           names=names, usecols=range(width), dtype=str,
                           keep_default_na=False, na_values=[], na_filter=False,
                           engine="c")

    def via_arrow():
        body = body_of(path)
        return pacsv.read_csv(
            pa.BufferReader(body),
            read_options=pacsv.ReadOptions(column_names=names, use_threads=True),
            parse_options=pacsv.ParseOptions(delimiter=","),
            convert_options=pacsv.ConvertOptions(
                column_types={f"c{i}": t for i, t in types.items()},
                strings_can_be_null=False, null_values=[]),
        )

    df = timed("pandas read_csv(dtype=str)", via_pandas)
    tb = timed("pyarrow.csv.read_csv", via_arrow)
    print(f"    pandas rows={len(df):,}   arrow rows={tb.num_rows:,}")
    ok = len(df) == tb.num_rows
    print(f"    行数一致: {ok}")
    if ok:
        for i, t in types.items():
            if pa.types.is_integer(t):
                a = pd.to_numeric(df[f"c{i}"], errors="coerce").fillna(0).to_numpy("int64")
                b = tb.column(f"c{i}").to_numpy(zero_copy_only=False).astype("int64")
                if not np.array_equal(a, b):
                    bad = np.nonzero(a != b)[0][:5]
                    print(f"    ! c{i} 不一致 {len(bad)} 处 e.g. {bad} "
                          f"pandas={a[bad]} arrow={b[bad]}")
                    break
        else:
            print("    数值列逐值一致: True")


if __name__ == "__main__":
    bench("逐笔委托.csv", 11, {3: pa.int64(), 4: pa.int64(), 5: pa.int64(),
                              8: pa.int64(), 9: pa.int64()})
    bench("逐笔成交.csv", 13, {3: pa.int64(), 4: pa.int64(), 8: pa.int64(),
                              9: pa.int64(), 10: pa.int64(), 11: pa.int64()})
    qt = {3: pa.int64(), 4: pa.int64(), 5: pa.int64(), 6: pa.int64(), 7: pa.int64(),
          11: pa.int64(), 12: pa.int64(), 13: pa.int64(), 14: pa.int64(),
          15: pa.int64(), 16: pa.int64()}
    for i in range(17, 57):
        qt[i] = pa.int64()
    qt[57] = pa.int64(); qt[58] = pa.int64(); qt[59] = pa.int64(); qt[60] = pa.int64()
    bench("行情.csv", 67, qt)
