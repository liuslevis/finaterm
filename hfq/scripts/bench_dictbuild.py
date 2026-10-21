"""微基准：字典列解码与事件字典构造的最快写法。"""
from __future__ import annotations

import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

import numpy as np  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.compute as pc  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402

from app import parquet_store as ps  # noqa: E402

ROOT = os.path.join(HFQ, "cache", "_parity_ds")
DATE, CODE = "20260916", "000001.SZ"
st = ps.Store(ROOT).open()
shard, _ = st.shard_of(CODE)
op = st.table_path(DATE, "orders", shard)

N = 261697


def timed(label, fn, n=5):
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        r = fn()
        ts.append(time.perf_counter() - t0)
    print(f"  {label:<52} {min(ts)*1000:8.1f} ms")
    return r


print("--- 字符串列解码 ---")
t0 = timed("read_table 无 read_dictionary", lambda: pq.read_table(op, filters=[("code", "=", CODE)]))
t1 = timed("read_table + read_dictionary=[order_type,order_code]",
           lambda: pq.read_table(op, filters=[("code", "=", CODE)],
                                 read_dictionary=["order_type", "order_code"]))
for name in ("order_type", "order_code"):
    print(f"    {name}: plain={t0.column(name).type}  dict={t1.column(name).type}")

col = t1.column("order_type")
if isinstance(col, pa.ChunkedArray):
    col = col.combine_chunks()
print(f"    has indices: {hasattr(col, 'indices')}")

t2 = timed("dictionary_encode 后取 indices（对比）",
           lambda: pc.dictionary_encode(
               pq.read_table(op, filters=[("code", "=", CODE)]).column("order_type")))

print("\n--- 事件字典构造 ---")
n = 261697
rng = np.random.default_rng(0)
aseq = np.sort(rng.integers(1, 10**9, n)).astype(np.int64)
tarr = rng.integers(91500000, 150000000, n).astype(np.int32)
typ = rng.integers(0, 3, n).astype(np.int8)
price = rng.integers(1, 10**6, n).astype(np.int32)
qty = rng.integers(100, 10**5, n).astype(np.int32)
buy = rng.integers(0, 10**9, n).astype(np.int64)
sell = rng.integers(0, 10**9, n).astype(np.int64)
oid = rng.integers(0, 10**9, n).astype(np.int64)
amount = rng.random(n) * 100
sib = rng.integers(0, 2, n).astype(np.int8)


def approach_a():
    """现状：逐元素 numpy 索引 + 字面量 dict。"""
    type_names = np.array(["委托", "成交", "撤单"], dtype=object)
    out = []
    for i in range(n):
        p = float(price[i]) / 10000.0
        et = type_names[typ[i]]
        q = int(qty[i])
        out.append({
            "aseq": int(aseq[i]), "t": int(tarr[i]), "type": et,
            "side": "买" if sib[i] else "卖",
            "price": p, "qty": q, "amount": float(amount[i]),
            "buy_id": int(buy[i]), "sell_id": int(sell[i]),
            "order_id": int(oid[i]), "seq": i + 1,
        })
    return out


def approach_b():
    """先 tolist()，再 zip + dict()。"""
    a = aseq.tolist(); tt = tarr.tolist(); ty = typ.tolist()
    pr = price.tolist(); qy = qty.tolist(); bu = buy.tolist()
    se = sell.tolist(); oi = oid.tolist(); am = amount.tolist()
    sb = sib.tolist()
    names = ("委托", "成交", "撤单")
    types = [names[x] for x in ty]
    sides = ["买" if x else "卖" for x in sb]
    prices = [x / 10000.0 for x in pr]
    seqs = range(1, n + 1)
    keys = ("aseq", "t", "type", "side", "price", "qty", "amount",
            "buy_id", "sell_id", "order_id", "seq")
    return [dict(zip(keys, row)) for row in
            zip(a, tt, types, sides, prices, qy, am, bu, se, oi, seqs)]


def approach_c():
    """tolist() + 列表推导内联 dict 字面量。"""
    a = aseq.tolist(); tt = tarr.tolist(); ty = typ.tolist()
    pr = price.tolist(); qy = qty.tolist(); bu = buy.tolist()
    se = sell.tolist(); oi = oid.tolist(); am = amount.tolist()
    sb = sib.tolist()
    return [{
        "aseq": a[i], "t": tt[i], "type": ("委托", "成交", "撤单")[ty[i]],
        "side": "买" if sb[i] else "卖", "price": pr[i] / 10000.0,
        "qty": qy[i], "amount": am[i], "buy_id": bu[i], "sell_id": se[i],
        "order_id": oi[i], "seq": i + 1,
    } for i in range(n)]


ra = timed("A 现状（numpy 逐元素索引）", approach_a)
rb = timed("B tolist + dict(zip)", approach_b)
rc = timed("C tolist + 推导式 + 字面量", approach_c)
assert len(ra) == len(rb) == len(rc) == n
assert ra[0] == rb[0] == rc[0], (ra[0], rb[0], rc[0])

print("\n--- 盘口快照 ---")
qp = st.table_path(DATE, "quotes", shard)
qt = timed("read_table(quotes) filter", lambda: pq.read_table(qp, filters=[("code", "=", CODE)]))
nq = qt.num_rows
qc = {c: qt.column(c).to_numpy(zero_copy_only=False) for c in qt.column_names if c != "code"}


def quotes_current():
    out = []
    for j in range(nq):
        out.append({
            "t": int(qc["t"][j]), "last": float(qc["last"][j]) / 10000.0,
            "cum_vol": int(qc["cum_vol"][j]), "cum_amt": int(qc["cum_amt"][j]),
            "high": float(qc["high"][j]) / 10000.0,
            "low": float(qc["low"][j]) / 10000.0,
            "open": float(qc["open"][j]) / 10000.0,
            "prev_close": float(qc["prev_close"][j]) / 10000.0,
            "asks": [[float(qc[f"ask_px{k}"][j]) / 10000.0,
                      int(qc[f"ask_qty{k}"][j])] for k in range(1, 11)],
            "bids": [[float(qc[f"bid_px{k}"][j]) / 10000.0,
                      int(qc[f"bid_qty{k}"][j])] for k in range(1, 11)],
        })
    return out


def quotes_fast():
    L = {k: v.tolist() for k, v in qc.items()}
    return [{
        "t": L["t"][j], "last": L["last"][j] / 10000.0,
        "cum_vol": L["cum_vol"][j], "cum_amt": L["cum_amt"][j],
        "high": L["high"][j] / 10000.0, "low": L["low"][j] / 10000.0,
        "open": L["open"][j] / 10000.0, "prev_close": L["prev_close"][j] / 10000.0,
        "asks": [[L[f"ask_px{k}"][j] / 10000.0, L[f"ask_qty{k}"][j]] for k in range(1, 11)],
        "bids": [[L[f"bid_px{k}"][j] / 10000.0, L[f"bid_qty{k}"][j]] for k in range(1, 11)],
    } for j in range(nq)]


qa = timed("quotes 现状", quotes_current)
qb = timed("quotes tolist", quotes_fast)
assert qa[0] == qb[0]
print(f"    quotes rows={nq}")
