"""剖析 Parquet 读取路径的耗时构成，定位可优化热点。"""
from __future__ import annotations

import cProfile
import os
import pstats
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

os.environ["HFQ_PARQUET_DIR"] = os.path.join(HFQ, "cache", "_parity_ds")

import numpy as np  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from app import parquet_store as ps  # noqa: E402

DATE = "20260916"
CODE = "000001.SZ"
st = ps.Store(os.environ["HFQ_PARQUET_DIR"]).open()
shard, ui = st.shard_of(CODE)
print(f"{DATE} {CODE} shard={shard} universe_index={ui}")


def timed(label, fn, n=3):
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        r = fn()
        ts.append(time.perf_counter() - t0)
    print(f"  {label:<44} {min(ts)*1000:8.1f} ms (min/{n})")
    return r


op = st.table_path(DATE, "orders", shard)
tp = st.table_path(DATE, "trades", shard)
qp = st.table_path(DATE, "quotes", shard)
for p in (op, tp, qp):
    print(f"  {os.path.basename(p):<20} {os.path.getsize(p)/1024**2:7.2f} MB")

print("\n--- 分解 ---")
orders = timed("pq.read_table(orders, filter code)",
               lambda: pq.read_table(op, filters=[("code", "=", CODE)]))
trades = timed("pq.read_table(trades, filter code)",
               lambda: pq.read_table(tp, filters=[("code", "=", CODE)]))
quotes = timed("pq.read_table(quotes, filter code)",
               lambda: pq.read_table(qp, filters=[("code", "=", CODE)]))
print(f"    orders rows={orders.num_rows}  row_groups="
      f"{pq.ParquetFile(op).num_row_groups}")
print(f"    trades rows={trades.num_rows}")
print(f"    quotes rows={quotes.num_rows}")

is_sh = CODE.endswith(".SH")
eo = timed("_events_from_orders", lambda: ps._events_from_orders(orders, is_sh))
et = timed("_events_from_trades", lambda: ps._events_from_trades(trades, is_sh))


def cat():
    return {k: np.concatenate([eo[k], et[k]]) for k in eo}


ev = timed("concat", cat)
order = timed("argsort stable", lambda: np.argsort(ev["aseq"], kind="stable"))


def apply_order():
    return {k: v[order] for k, v in ev.items()}


ev2 = timed("apply order", apply_order)
dicts = timed("_to_event_dicts (python loop)", lambda: ps._to_event_dicts(ev2))
print(f"    events={len(dicts)}")
qs = timed("_quotes_from_table", lambda: ps._quotes_from_table(quotes))

timed("FULL load_stock", lambda: st.load_stock(CODE, DATE))

print("\n--- 字符串列开销 ---")
for name, t in (("order_type", orders), ("order_code", orders),
                ("trade_code", trades), ("side", trades)):
    r = timed(f"  col.to_pylist() {name}",
              lambda t=t, name=name: t.column(name).to_pylist(), n=5)

print("\n--- 字典列索引提取（候选优化） ---")
for name, t in (("order_type", orders), ("side", trades)):
    col = t.column(name)
    print(f"  {name}: type={col.type}")


def via_indices():
    out = {}
    for t, cols in ((orders, ("order_type", "order_code")),
                    (trades, ("trade_code", "side", "order_code"))):
        for c in cols:
            a = t.column(c)
            if hasattr(a, "indices"):
                idx = a.indices.to_numpy(zero_copy_only=False)
                out[c] = (idx, a.dictionary.to_pylist())
            else:
                out[c] = a.to_pylist()
    return out


timed("字典索引替代 to_pylist", via_indices, n=5)

print("\n--- cProfile: load_stock x3 ---")
pr = cProfile.Profile()
pr.enable()
for _ in range(3):
    st.load_stock(CODE, DATE)
pr.disable()
pstats.Stats(pr).sort_stats("cumulative").print_stats(18)
