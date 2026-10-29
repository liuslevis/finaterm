"""LV2 数据的 Parquet 列存层。

把 data-lv2/*.7z 里的 GBK CSV 转成按月/周分区的 Parquet，并提供与
`data.py` 中二进制缓存完全等价的读取结果（同一套事件流/快照语义）。

目录布局
--------
    <root>/_meta/manifest.json             schema 版本、分区频率、universe、分片参数
    <root>/_meta/codes/<date>.parquet      当日标的清单
    <root>/<freq>/<part>/date=<date>/      orders/trades/quotes 分片文件
    <root>/catalog/<freq>/<part>/catalog.parquet
        日线目录（每个 date×code 一行的 OHLCV 汇总），供跨日 K 线直接扫描

其中 freq 为 ``month=YYYY-MM`` 或 ``week=YYYY-Www``。分片号由 code 在
universe 中的序号整除 shard_size 得到，跨交易日稳定，因此按 code 查询
只需打开 1 个文件并借助 row-group 统计剪枝。
"""

from __future__ import annotations

import bisect
import json
import os
import time
from datetime import date as _date
from typing import Iterable

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .paths import parquet_default

PRICE_SCALE = 10000.0
SCHEMA_VERSION = 4
# 默认根目录与其余调用方共用同一套解析（HFQ_PARQUET_DIR → D:\data-parquet）。
# 不要在这里再拼仓库内路径：那是已删除的迁移前旧数据集。
DEFAULT_ROOT = parquet_default()
FREQS = ("month", "week")
TABLES = ("orders", "trades", "quotes")
CATALOG_TABLE = "catalog"

_LADDER = 10

# --------------------------------------------------------------------------- #
# 列定义
# --------------------------------------------------------------------------- #
_STR = pa.string()
_I32 = pa.int32()
_I64 = pa.int64()

ORDERS_SCHEMA = pa.schema([
    ("code", _STR),
    ("t", _I32),                 # HHMMSSmmm
    ("order_no", _I64),          # 委托编号
    ("exch_order_no", _I64),     # 交易所委托号（即 aseq）
    ("order_type", _STR),        # 委托类型 A/D/0/...
    ("order_code", _STR),        # 委托代码 B/S/...
    ("price", _I64),             # 元 × 10000（区间内存在 999,999 元级别报价）
    ("qty", _I64),
])

TRADES_SCHEMA = pa.schema([
    ("code", _STR),
    ("t", _I32),
    ("trade_no", _I64),          # 成交编号
    ("trade_code", _STR),        # 成交代码（SZ 的 "C" 表示撤单）
    ("order_code", _STR),
    ("side", _STR),              # BS标志
    ("price", _I64),
    ("qty", _I64),
    ("sell_seq", _I64),          # 叫卖序号
    ("buy_seq", _I64),           # 叫买序号
])

# 仅保留 data.py 实际消费的字段。原 CSV 的第 5/6 列（成交量/成交额 增量）
# 与 57..60 列（加权叫价、叫卖/叫买总量）未被应用使用，且在 16xxxx.SZ 基金
# 上有厂商写入的越界值（2^64 - n），一并剔除。
# 价格/数量统一用 int64：实测比 int32 只多 3% 体积，但能容下 999,999 元级报价
# 与 22 亿股级挂单，避免截断合法数据。
_QUOTE_COLS = (
    [("t", _I32), ("last", _I64), ("cum_vol", _I64), ("cum_amt", _I64),
     ("high", _I64), ("low", _I64), ("open", _I64), ("prev_close", _I64)]
    + [(f"ask_px{i}", _I64) for i in range(1, _LADDER + 1)]
    + [(f"ask_qty{i}", _I64) for i in range(1, _LADDER + 1)]
    + [(f"bid_px{i}", _I64) for i in range(1, _LADDER + 1)]
    + [(f"bid_qty{i}", _I64) for i in range(1, _LADDER + 1)]
)
QUOTES_SCHEMA = pa.schema([("code", _STR)] + _QUOTE_COLS)

CATALOG_SCHEMA = pa.schema([
    ("date", _I32), ("code", _STR),
    ("open", _I64), ("high", _I64), ("low", _I64), ("close", _I64),
    ("prev_close", _I64), ("change_pct", pa.float64()),
    ("vol", _I64), ("amt", _I64),
    ("limit_up", _I64), ("limit_down", _I64),
    ("hit_limit_up", pa.bool_()), ("hit_limit_down", pa.bool_()),
    ("records", _I64), ("snapshots", _I64),
])

SCHEMAS = {"orders": ORDERS_SCHEMA, "trades": TRADES_SCHEMA, "quotes": QUOTES_SCHEMA}
# 低基数列走字典编码
_DICT_COLS = {
    "orders": ["code", "order_type", "order_code"],
    "trades": ["code", "trade_code", "order_code", "side"],
    "quotes": ["code"],
}
# 读取时以字典页返回的列（避免逐行物化字符串）
_READ_DICT = {
    "orders": ["code", "order_type", "order_code"],
    "trades": ["code", "trade_code", "order_code", "side"],
}

# 分片内按 code 升序写入，row_group_size 决定单股票查询的剪枝粒度。
# 实测 256k -> 65k：文件体积几乎不变（+0.5%），单股票过滤读快 2x 左右；
# 再小到 16k 时 row-group 数量过多，footer 统计扫描反而拖慢。
WRITE_OPTS = dict(compression="zstd", compression_level=3, row_group_size=65_536,
                  write_statistics=True)


# --------------------------------------------------------------------------- #
# 分区 / 路径
# --------------------------------------------------------------------------- #
def partition_key(date_str: str, freq: str) -> str:
    d = _date(int(date_str[:4]), int(date_str[4:6]), int(date_str[6:8]))
    if freq == "month":
        return f"month={d.year:04d}-{d.month:02d}"
    if freq == "week":
        iso = d.isocalendar()
        return f"week={iso.year:04d}-W{iso.week:02d}"
    raise ValueError(f"未知分区频率: {freq}")


class Store:
    """一个 Parquet 数据集的读写入口。"""

    def __init__(self, root: str = DEFAULT_ROOT):
        self.root = root
        self._m: dict | None = None
        self._mtime: float = 0.0
        self._last_check: float = 0.0

    # --- 元数据 ----------------------------------------------------------- #
    @property
    def meta_dir(self) -> str:
        return os.path.join(self.root, "_meta")

    @property
    def manifest_path(self) -> str:
        return os.path.join(self.meta_dir, "manifest.json")

    def exists(self) -> bool:
        return os.path.exists(self.manifest_path)

    def manifest(self) -> dict:
        with open(self.manifest_path, encoding="utf-8") as fh:
            return json.load(fh)

    def save_manifest(self, m: dict) -> None:
        os.makedirs(self.meta_dir, exist_ok=True)
        tmp = self.manifest_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(m, fh, ensure_ascii=False)
        os.replace(tmp, self.manifest_path)

    def new_manifest(self, freq: str, universe: list[str], shard_size: int) -> dict:
        return {"schema": SCHEMA_VERSION, "freq": freq, "shard_size": shard_size,
                "universe": universe, "dates": {}, "tables": list(TABLES),
                "write_opts": {k: v for k, v in WRITE_OPTS.items()}}

    # --- universe / 分片 --------------------------------------------------- #
    def shard_of(self, code: str) -> tuple[int, int]:
        """返回 (shard_index, universe_index)；code 不在 universe 中返回 (-1,-1)。"""
        m = self._m
        i = bisect.bisect_left(m["universe"], code)
        if i >= len(m["universe"]) or m["universe"][i] != code:
            return -1, -1
        return i // m["shard_size"], i

    def n_shards(self) -> int:
        m = self._m
        return (len(m["universe"]) + m["shard_size"] - 1) // m["shard_size"]

    def shard_codes(self, shard: int) -> list[str]:
        m = self._m
        lo = shard * m["shard_size"]
        return m["universe"][lo:lo + m["shard_size"]]

    def table_path(self, date_str: str, table: str, shard: int) -> str:
        part = partition_key(date_str, self._m["freq"])
        return os.path.join(self.root, self._m["freq"], part, f"date={date_str}",
                            f"{table}-{shard:03d}.parquet")

    def codes_path(self, date_str: str) -> str:
        return os.path.join(self.meta_dir, "codes", f"{date_str}.parquet")

    def catalog_path(self, date_str: str) -> str:
        part = partition_key(date_str, self._m["freq"])
        return os.path.join(self.root, CATALOG_TABLE, self._m["freq"], part,
                            f"catalog-{date_str}.parquet")

    # --- 生命周期 --------------------------------------------------------- #
    def open(self) -> "Store":
        self._m = self.manifest()
        if self._m.get("schema") != SCHEMA_VERSION:
            raise ValueError(f"schema 版本不符: {self._m.get('schema')} != {SCHEMA_VERSION}")
        try:
            self._mtime = os.path.getmtime(self.manifest_path)
        except OSError:
            self._mtime = 0.0
        return self

    def maybe_reload(self, min_interval: float = 5.0) -> bool:
        """manifest 变化时重载（转换在后台持续追加交易日时用）。

        以 ``min_interval`` 秒为节流，避免每次请求都 stat 文件；schema 变化则忽略，
        保持当前可用数据集不被打断。返回是否真的重载了。
        """
        now = time.monotonic()
        if now - self._last_check < min_interval:
            return False
        self._last_check = now
        try:
            mtime = os.path.getmtime(self.manifest_path)
        except OSError:
            return False
        if not mtime or mtime == self._mtime:
            return False
        try:
            m = self.manifest()
        except (OSError, ValueError):
            return False
        if m.get("schema") != SCHEMA_VERSION:
            return False
        self._mtime = mtime
        self._m = m
        return True

    def __enter__(self):
        return self.open()

    def __exit__(self, *a):
        return False

    @property
    def dates(self) -> list[str]:
        return sorted(self._m["dates"])

    def is_partial(self, date_str: str) -> bool:
        """该交易日是否只转换了部分标的（--codes 子集构建）。"""
        info = self._m["dates"].get(date_str) or {}
        return bool(info.get("partial"))

    def all_complete(self) -> bool:
        """全部已建交易日均为全量构建（catalog 可作为唯一日线来源）。"""
        return not any(self.is_partial(d) for d in self._m["dates"])

    # --- 查询 ------------------------------------------------------------- #
    def list_codes(self, date_str: str) -> list[str]:
        p = self.codes_path(date_str)
        if not os.path.exists(p):
            return []
        return pq.read_table(p, columns=["code"]).column("code").to_pylist()

    def load_stock(self, code: str, date_str: str):
        """返回 (events, quotes)，与 data._decode_stock 的语义逐字段一致。"""
        shard, ui = self.shard_of(code)
        if ui < 0 or date_str not in self._m["dates"]:
            raise KeyError(f"未收录: {code} @ {date_str}")
        is_sh = code.endswith(".SH")

        op = self.table_path(date_str, "orders", shard)
        tp = self.table_path(date_str, "trades", shard)
        qp = self.table_path(date_str, "quotes", shard)
        if not os.path.exists(op) or not os.path.exists(tp):
            raise KeyError(f"未收录: {code} @ {date_str}")

        # read_dictionary：字符串列以字典页返回，避免逐行物化 Python str
        orders = pq.read_table(op, filters=[("code", "=", code)],
                               read_dictionary=_READ_DICT["orders"])
        trades = pq.read_table(tp, filters=[("code", "=", code)],
                               read_dictionary=_READ_DICT["trades"])
        quotes_t = (pq.read_table(qp, filters=[("code", "=", code)])
                    if os.path.exists(qp) else None)

        ev_orders = _events_from_orders(orders, is_sh)
        ev_trades = _events_from_trades(trades, is_sh)
        events = {k: np.concatenate([ev_orders[k], ev_trades[k]])
                  for k in ev_orders}
        # 稳定排序，复现 CSV 路径 raw_events.sort(key=aseq) 的结果
        order = np.argsort(events["aseq"], kind="stable")
        ev = {k: v[order] for k, v in events.items()}
        quotes = _quotes_from_table(quotes_t) if quotes_t is not None else []
        return _to_event_dicts(ev), quotes

    def read_catalog(self, code: str | None = None,
                     dates: Iterable[str] | None = None):
        """读日线目录；code 给定时只取该标的。"""
        import pyarrow.compute as pc
        want = set(dates) if dates is not None else set(self.dates)
        parts = []
        for d in sorted(want & set(self.dates)):
            p = self.catalog_path(d)
            if os.path.exists(p):
                parts.append(pq.read_table(p))
        if not parts:
            return pa.table({f.name: pa.array([], f.type) for f in CATALOG_SCHEMA})
        t = pa.concat_tables(parts)
        if code is not None:
            t = t.filter(pc.equal(t["code"], code))
        return t


# --------------------------------------------------------------------------- #
# 列 -> 结构化数组（向量化）
# --------------------------------------------------------------------------- #
def _col(t, name) -> np.ndarray:
    return t.column(name).to_numpy(zero_copy_only=False)


def _arrow_col(t, name):
    c = t.column(name)
    if isinstance(c, pa.ChunkedArray):
        c = c.combine_chunks()
    return c


def _eq(t, name, target: str) -> np.ndarray:
    """列 == target 的布尔数组；字典列走索引比较，不物化字符串。"""
    c = _arrow_col(t, name)
    if pa.types.is_dictionary(c.type):
        vals = c.dictionary.to_pylist()
        try:
            k = vals.index(target)
        except ValueError:
            return np.zeros(len(c), dtype=bool)
        return c.indices.to_numpy(zero_copy_only=False) == k
    arr = np.asarray(c.to_pylist(), dtype=object)
    return arr == target


def _mask(d: dict) -> dict:
    """应用 keep 掩码，返回只含保留行的列字典。"""
    keep = d.pop("keep")
    return {k: v[keep] for k, v in d.items()}


def _events_from_orders(t, is_sh: bool) -> dict:
    n = t.num_rows
    t_arr = _col(t, "t").astype(np.int32, copy=False)
    aseq = _col(t, "exch_order_no").astype(np.int64, copy=False)
    price = _col(t, "price").astype(np.int64, copy=False)
    qty = _col(t, "qty").astype(np.int64, copy=False)

    # 类型码：0 委托 / 1 成交 / 2 撤单
    etype = np.zeros(n, dtype=np.int8)
    side_is_buy = np.zeros(n, dtype=np.int8)  # 1=买 0=卖

    is_buy = _eq(t, "order_code", "B")
    is_sell = _eq(t, "order_code", "S")
    valid_side = is_buy | is_sell
    if is_sh:
        # 上交所：A=新增委托，D=撤单；其余忽略
        is_a = _eq(t, "order_type", "A")
        is_d = _eq(t, "order_type", "D")
        keep = valid_side & (is_a | is_d)
        etype[is_d] = 2
        price = np.where(is_d, 0, price)
    else:
        # 深交所逐笔委托均为新增，撤单在逐笔成交中
        keep = valid_side
    side_is_buy[is_buy] = 1
    buy_id = np.where(is_buy, aseq, 0).astype(np.int64)
    sell_id = np.where(is_sell, aseq, 0).astype(np.int64)

    return _mask({
        "keep": keep, "aseq": aseq, "t": t_arr, "type": etype,
        "buy": buy_id, "sell": sell_id, "oid": aseq.copy(),
        "price": price.astype(np.int64), "qty": qty,
        "amount": np.zeros(n, dtype=np.float64), "side_is_buy": side_is_buy,
    })


def _events_from_trades(t, is_sh: bool) -> dict:
    n = t.num_rows
    t_arr = _col(t, "t").astype(np.int32, copy=False)
    aseq = _col(t, "trade_no").astype(np.int64, copy=False)
    price = _col(t, "price").astype(np.int64, copy=False)
    qty = _col(t, "qty").astype(np.int64, copy=False)
    sell_seq = _col(t, "sell_seq").astype(np.int64, copy=False)
    buy_seq = _col(t, "buy_seq").astype(np.int64, copy=False)

    is_cancel = (not is_sh) & _eq(t, "trade_code", "C")

    etype = np.where(is_cancel, 2, 1).astype(np.int8)
    has_buy = buy_seq != 0
    c_buy = np.where(has_buy, buy_seq, 0).astype(np.int64)
    c_sell = np.where(has_buy, 0, sell_seq).astype(np.int64)
    c_oid = np.where(has_buy, buy_seq, sell_seq).astype(np.int64)
    c_side_is_buy = has_buy.astype(np.int8)

    # 非撤单：CSV 语义为 B->买、S->卖、其余->买
    t_side_is_buy = (~_eq(t, "side", "S")).astype(np.int8)

    price_out = np.where(is_cancel, 0, price).astype(np.int64)
    buy_out = np.where(is_cancel, c_buy, buy_seq).astype(np.int64)
    sell_out = np.where(is_cancel, c_sell, sell_seq).astype(np.int64)
    oid_out = np.where(is_cancel, c_oid, 0).astype(np.int64)
    side_is_buy = np.where(is_cancel, c_side_is_buy, t_side_is_buy).astype(np.int8)

    amt = np.where(is_cancel, 0.0,
                   price_out.astype(np.float64) / PRICE_SCALE * qty / 1e4)
    return _mask({
        "keep": np.ones(n, dtype=bool), "aseq": aseq, "t": t_arr, "type": etype,
        "buy": buy_out, "sell": sell_out, "oid": oid_out,
        "price": price_out, "qty": qty,
        "amount": amt.astype(np.float64), "side_is_buy": side_is_buy,
    })


_TYPE_NAMES = ("委托", "成交", "撤单")


def _to_event_dicts(ev: dict) -> list[dict]:
    """结构化数组 -> data.py 约定的事件字典列表。

    先把 numpy 数组 ``tolist()`` 成原生 Python 对象，再在推导式里直接取下标，
    比逐元素 numpy 标量索引快约 1.8 倍（见 scripts/bench_dictbuild.py）。
    """
    a = ev["aseq"].tolist()
    t = ev["t"].tolist()
    ty = ev["type"].tolist()
    pr = ev["price"].tolist()
    qy = ev["qty"].tolist()
    bu = ev["buy"].tolist()
    se = ev["sell"].tolist()
    oi = ev["oid"].tolist()
    am = ev["amount"].tolist()
    sb = ev["side_is_buy"].tolist()
    names = _TYPE_NAMES
    scale = PRICE_SCALE
    return [{
        "aseq": a[i], "t": t[i], "type": names[ty[i]],
        "side": "买" if sb[i] else "卖",
        "price": pr[i] / scale, "qty": qy[i], "amount": am[i],
        "buy_id": bu[i], "sell_id": se[i], "order_id": oi[i], "seq": i + 1,
    } for i in range(len(a))]


def _quotes_from_table(t) -> list[dict]:
    L = {c: _col(t, c).tolist() for c in t.column_names if c != "code"}
    n = t.num_rows
    scale = PRICE_SCALE
    tt = L["t"]
    last, high, low, open_, prev = (L["last"], L["high"], L["low"],
                                    L["open"], L["prev_close"])
    cv, ca = L["cum_vol"], L["cum_amt"]
    # 把 40 条阶梯列提到局部变量，避免每格两次字典查找
    ap = [L[f"ask_px{k}"] for k in range(1, _LADDER + 1)]
    aq = [L[f"ask_qty{k}"] for k in range(1, _LADDER + 1)]
    bp = [L[f"bid_px{k}"] for k in range(1, _LADDER + 1)]
    bq = [L[f"bid_qty{k}"] for k in range(1, _LADDER + 1)]
    return [{
        "t": tt[j], "last": last[j] / scale, "cum_vol": cv[j], "cum_amt": ca[j],
        "high": high[j] / scale, "low": low[j] / scale,
        "open": open_[j] / scale, "prev_close": prev[j] / scale,
        "asks": [[ap[k][j] / scale, aq[k][j]] for k in range(_LADDER)],
        "bids": [[bp[k][j] / scale, bq[k][j]] for k in range(_LADDER)],
    } for j in range(n)]


__all__ = [
    "Store", "SCHEMAS", "SCHEMA_VERSION", "DEFAULT_ROOT", "TABLES", "FREQS",
    "partition_key", "ORDERS_SCHEMA", "TRADES_SCHEMA", "QUOTES_SCHEMA",
    "CATALOG_SCHEMA", "WRITE_OPTS", "_DICT_COLS", "PRICE_SCALE",
]
