"""row_group_size 权衡实验：文件体积 vs 单股票过滤读耗时。"""
from __future__ import annotations

import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

import pyarrow.parquet as pq  # noqa: E402

from app.parquet_store import Store, WRITE_OPTS, _DICT_COLS  # noqa: E402
from app.paths import parquet_default  # noqa: E402

ROOT = parquet_default()
DATE = "20260901"
TMP = os.path.join(HFQ, "cache", "_rgtest")
os.makedirs(TMP, exist_ok=True)

st = Store(ROOT).open()
CASES = [("159119.SZ", 8), ("600525.SH", 27)]
SIZES = [262_144, 131_072, 65_536, 32_768, 16_384]

print(f"{'table':<8}{'rg_size':>9}{'MB':>9}{'rg':>6}{'rows/rg':>10}"
      f"{'filter_ms':>11}{'rows':>8}")
for code, shard in CASES:
    print(f"--- {code} shard={shard:03d} ---")
    for table in ("orders", "trades", "quotes"):
        src = st.table_path(DATE, table, shard)
        t = pq.read_table(src)
        for rg in SIZES:
            out = os.path.join(TMP, f"{table}-{rg}.parquet")
            opts = dict(WRITE_OPTS)
            opts["row_group_size"] = rg
            pq.write_table(t, out, **opts, use_dictionary=_DICT_COLS[table])
            # 预热
            pq.read_table(out, filters=[("code", "=", code)])
            best = 1e9
            for _ in range(3):
                t0 = time.perf_counter()
                r = pq.read_table(out, filters=[("code", "=", code)])
                best = min(best, time.perf_counter() - t0)
            md = pq.ParquetFile(out).metadata
            print(f"{table:<8}{rg:>9}{os.path.getsize(out)/1024**2:>9.1f}"
                  f"{md.num_row_groups:>6}{md.num_rows//max(md.num_row_groups,1):>10,}"
                  f"{best*1000:>11.1f}{r.num_rows:>8,}")
        del t

shutil.rmtree(TMP, ignore_errors=True)
