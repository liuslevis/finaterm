r"""把 data-lv2/*.7z 转成按月/周分区的 Parquet 列存。

流程（每个交易日）
    1. 整档解压到临时目录（solid 归档一次性顺序解压最快）
    2. 按 universe 顺序逐只股票读 GBK CSV，映射为紧凑整数列
    3. 按 code 分片写 orders / trades / quotes（zstd-3 + 字典编码）
    4. 写当日标的清单与日线目录（catalog）
    5. 更新 manifest，原子替换

可断点续跑：manifest 已记录的交易日默认跳过。

用法
    python hfq/scripts/build_parquet.py --all
    python hfq/scripts/build_parquet.py --dates 20260901 20260902
    python hfq/scripts/build_parquet.py --codes 001301.SZ 600967.SH --dates 20260901
    python hfq/scripts/build_parquet.py --universe-only
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
HFQ = os.path.dirname(HERE)
sys.path.insert(0, HFQ)

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import pyarrow as pa  # noqa: E402
import pyarrow.compute as pc  # noqa: E402
import pyarrow.csv as pacsv  # noqa: E402
import pyarrow.parquet as pq  # noqa: E402
import py7zr  # noqa: E402

from app.parquet_store import (  # noqa: E402
    CATALOG_SCHEMA, DEFAULT_ROOT, ORDERS_SCHEMA, PRICE_SCALE, QUOTES_SCHEMA,
    SCHEMA_VERSION, TRADES_SCHEMA, WRITE_OPTS, Store, _DICT_COLS,
)

from app.paths import archive_dir  # noqa: E402

DATA_DIR = archive_dir()

ORDERS_W = 11        # 逐笔委托.csv 实际列宽
TRADES_W = 13        # 逐笔成交.csv
QUOTES_W = 67        # 行情.csv
ORDERS_MIN = 10      # 原 CSV 解析要求的字段数
TRADES_MIN = 12
QUOTES_MIN = 58

# 原解析用到的列下标
O_IDX = dict(code=0, exch=1, date=2, t=3, order_no=4, exch_order_no=5,
             order_type=6, order_code=7, price=8, qty=9)
T_IDX = dict(code=0, exch=1, date=2, t=3, trade_no=4, trade_code=5,
             order_code=6, side=7, price=8, qty=9, sell_seq=10, buy_seq=11)
_Q_SIMPLE = dict(code=0, exch=1, date=2, t=3, last=4, vol=5, amt=6, num=7,
                 cum_vol=11, cum_amt=12, high=13, low=14, open=15, prev_close=16,
                 wavg_ask=57, wavg_bid=58, ask_total=59, bid_total=60)


def log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------- #
# universe
# --------------------------------------------------------------------------- #
def archive_path(date: str) -> str:
    return os.path.join(DATA_DIR, f"{date}.7z")


def list_archives() -> list[str]:
    if not os.path.isdir(DATA_DIR):
        return []
    return sorted(fn[:-3] for fn in os.listdir(DATA_DIR)
                  if fn.endswith(".7z") and fn[:-3].isdigit())


def scan_codes(date: str) -> list[str]:
    """读取归档成员名，返回当日股票代码（不落盘）。"""
    codes = set()
    with py7zr.SevenZipFile(archive_path(date), "r") as a:
        for f in a.list():
            if f.is_directory:
                continue
            parts = f.filename.replace("\\", "/").split("/")
            if len(parts) >= 3 and parts[1]:
                codes.add(parts[1])
    return sorted(codes)


def load_universe(store: Store, dates: list[str], force: bool = False) -> list[str]:
    if store.exists() and not force:
        try:
            return store.manifest()["universe"]
        except Exception:  # noqa: BLE001
            pass
    uni = set()
    for i, d in enumerate(dates, 1):
        c = scan_codes(d)
        uni.update(c)
        log(f"  universe scan {d}  +{len(c):>5}  (累计 {len(uni)})")
    return sorted(uni)


# --------------------------------------------------------------------------- #
# CSV -> 紧凑列
# --------------------------------------------------------------------------- #
def _body(path: str) -> bytes:
    """跳过 GBK 表头，返回数据段字节（数据行是纯 ASCII）。"""
    with open(path, "rb") as fh:
        raw = fh.read()
    i = raw.find(b"\n")
    return raw[i + 1:] if i >= 0 else b""


def _read_table(path: str, width: int, int_cols: set[int],
                include: list[int] | None = None) -> tuple[pa.Table, str]:
    """读 GBK CSV 为 arrow 表。

    快路径：表头之下的数据段是纯 ASCII，直接用 pyarrow.csv 多线程解析
    （实测比 pandas 快约 16 倍，数值逐值一致）。若遇到非纯 ASCII、字段数
    异常或空值等边界，回退到 pandas 逐列 coerce，保证不中断。

    整数列按 **uint64** 解析：源数据里存在把负数写成无符号的形式
    （如委托价格 ``2^64 - 10000``，实为 -1.00 元的市价委托哨兵）。
    uint64 全部装得下，再由 :func:`_i64` 按二补码还原成 int64。
    """
    names = [f"c{i}" for i in range(width)]
    use = include if include is not None else list(range(width))
    types = {f"c{i}": (pa.uint64() if i in int_cols else pa.string()) for i in use}
    body = _body(path)
    if not body.strip():
        # 只有表头的空 CSV：直接返回空表，不必走回退路径
        return pa.table({f"c{i}": pa.array([], type=types[f"c{i}"]) for i in use}), "arrow"
    try:
        t = pacsv.read_csv(
            pa.BufferReader(body),
            read_options=pacsv.ReadOptions(column_names=names, use_threads=True),
            parse_options=pacsv.ParseOptions(delimiter=","),
            convert_options=pacsv.ConvertOptions(
                column_types=types, include_columns=[f"c{i}" for i in use],
                strings_can_be_null=False, null_values=[]),
        )
        return t, "arrow"
    except Exception as e:  # noqa: BLE001
        log(f"    回退 pandas 解析（{path}: {type(e).__name__}: {e}）")
        return _read_table_pandas(path, width, int_cols, use), "pandas"


def _read_table_pandas(path: str, width: int, int_cols: set[int],
                       use: list[int]) -> pa.Table:
    names = [f"c{i}" for i in range(width)]
    df = pd.read_csv(path, encoding="gbk", header=None, skiprows=1, names=names,
                     usecols=range(width), dtype=str,
                     keep_default_na=False, na_values=[], na_filter=False,
                     engine="c")
    arrays = {}
    for i in use:
        col = df[f"c{i}"]
        if i in int_cols:
            v = pd.to_numeric(col, errors="coerce").fillna(0).to_numpy(dtype=np.float64)
            arrays[f"c{i}"] = pa.array(v.astype(np.int64), type=pa.int64())
        else:
            arrays[f"c{i}"] = pa.array(col.to_numpy(dtype=object), type=pa.string())
    return pa.table(arrays)


def _i64(t: pa.Table, name: str) -> np.ndarray:
    """取整数列。uint64 经 ``astype(int64)`` 按二补码还原负数哨兵。"""
    a = t.column(name).to_numpy(zero_copy_only=False)
    if a.dtype == np.uint64:
        return a.astype(np.int64)
    return a.astype(np.int64, copy=False)


def _str(t: pa.Table, name: str, strip: bool = False):
    a = t.column(name)
    if isinstance(a, pa.ChunkedArray):
        a = a.combine_chunks()
    if strip:
        a = pc.utf8_trim_whitespace(a)
    return a


def parse_orders(path: str) -> dict:
    ints = {O_IDX[k] for k in ("t", "order_no", "exch_order_no", "price", "qty")}
    use = sorted({O_IDX["t"], O_IDX["order_no"], O_IDX["exch_order_no"],
                  O_IDX["order_type"], O_IDX["order_code"],
                  O_IDX["price"], O_IDX["qty"]})
    t, eng = _read_table(path, ORDERS_W, ints, use)
    return {
        "n": t.num_rows, "engine": eng,
        "t": _i64(t, f"c{O_IDX['t']}"),
        "order_no": _i64(t, f"c{O_IDX['order_no']}"),
        "exch_order_no": _i64(t, f"c{O_IDX['exch_order_no']}"),
        "price": _i64(t, f"c{O_IDX['price']}"),
        "qty": _i64(t, f"c{O_IDX['qty']}"),
        "order_type": _str(t, f"c{O_IDX['order_type']}"),
        "order_code": _str(t, f"c{O_IDX['order_code']}"),
    }


def parse_trades(path: str) -> dict:
    ints = {T_IDX[k] for k in ("t", "trade_no", "price", "qty",
                               "sell_seq", "buy_seq")}
    use = sorted({T_IDX["t"], T_IDX["trade_no"], T_IDX["trade_code"],
                  T_IDX["order_code"], T_IDX["side"], T_IDX["price"],
                  T_IDX["qty"], T_IDX["sell_seq"], T_IDX["buy_seq"]})
    t, eng = _read_table(path, TRADES_W, ints, use)
    return {
        "n": t.num_rows, "engine": eng,
        "t": _i64(t, f"c{T_IDX['t']}"),
        "trade_no": _i64(t, f"c{T_IDX['trade_no']}"),
        "price": _i64(t, f"c{T_IDX['price']}"),
        "qty": _i64(t, f"c{T_IDX['qty']}"),
        "sell_seq": _i64(t, f"c{T_IDX['sell_seq']}"),
        "buy_seq": _i64(t, f"c{T_IDX['buy_seq']}"),
        # 原解析对这两列做了 strip()
        "trade_code": _str(t, f"c{T_IDX['trade_code']}", strip=True),
        "side": _str(t, f"c{T_IDX['side']}", strip=True),
        "order_code": _str(t, f"c{T_IDX['order_code']}"),
    }


_QUOTE_SIMPLE_IDX = ("t", "last", "cum_vol", "cum_amt",
                     "high", "low", "open", "prev_close")
_LADDER_IDX = [17 + i for i in range(10)] + [27 + i for i in range(10)] + \
              [37 + i for i in range(10)] + [47 + i for i in range(10)]


def parse_quotes(path: str) -> dict:
    ints = {_Q_SIMPLE[k] for k in _QUOTE_SIMPLE_IDX} | set(_LADDER_IDX)
    use = sorted(ints)
    t, eng = _read_table(path, QUOTES_W, ints, use)
    out = {"t": _i64(t, f"c{_Q_SIMPLE['t']}"), "engine": eng}
    for k in _QUOTE_SIMPLE_IDX:
        if k != "t":
            out[k] = _i64(t, f"c{_Q_SIMPLE[k]}")
    for i in range(10):
        out[f"ask_px{i+1}"] = _i64(t, f"c{17 + i}")
        out[f"ask_qty{i+1}"] = _i64(t, f"c{27 + i}")
        out[f"bid_px{i+1}"] = _i64(t, f"c{37 + i}")
        out[f"bid_qty{i+1}"] = _i64(t, f"c{47 + i}")
    return {"n": t.num_rows, "cols": out}


_CLIP_WARNED: set[str] = set()


def int32(a: np.ndarray, what: str = "") -> np.ndarray:
    lo, hi = -2**31, 2**31 - 1
    if a.size:
        mn, mx = int(a.min()), int(a.max())
        if (mn < lo or mx > hi) and what not in _CLIP_WARNED:
            _CLIP_WARNED.add(what)
            log(f"    警告: {what} 超出 int32 范围 [{mn}, {mx}]，已截断")
    return np.clip(a, lo, hi).astype(np.int32)


def _sarr(a) -> pa.Array:
    if isinstance(a, pa.ChunkedArray):
        a = a.combine_chunks()
    if not isinstance(a, pa.Array):
        a = pa.array(a, type=pa.string())
    return a


def _eq_str(a, target: str) -> np.ndarray:
    """str 列 == target 的布尔数组（字典列走索引比较）。"""
    c = _sarr(a)
    if isinstance(c, pa.DictionaryArray):
        vals = c.dictionary.to_pylist()
        if target not in vals:
            return np.zeros(len(c), dtype=bool)
        return c.indices.to_numpy(zero_copy_only=False) == vals.index(target)
    return pc.equal(c, target).to_numpy(zero_copy_only=False)


# --------------------------------------------------------------------------- #
# 写盘
# --------------------------------------------------------------------------- #
def build_tables(stocks: dict, codes: list[str]) -> dict:
    """把一批股票的解析结果拼成三张 arrow 表（code 列已在每块内）。"""
    o_parts, t_parts, q_parts = [], [], []
    for code in codes:
        s = stocks.get(code)
        if not s:
            continue
        o = s["orders"]
        if o and o["n"]:
            o_parts.append(pa.table({
                "code": pa.array([code] * o["n"], type=pa.string()),
                "t": int32(o["t"], "orders.t"), "order_no": o["order_no"].astype(np.int64),
                "exch_order_no": o["exch_order_no"].astype(np.int64),
                "order_type": _sarr(o["order_type"]),
                "order_code": _sarr(o["order_code"]),
                "price": o["price"], "qty": o["qty"],
            }, schema=ORDERS_SCHEMA))
        t = s["trades"]
        if t and t["n"]:
            t_parts.append(pa.table({
                "code": pa.array([code] * t["n"], type=pa.string()),
                "t": int32(t["t"], "trades.t"), "trade_no": t["trade_no"].astype(np.int64),
                "trade_code": _sarr(t["trade_code"]),
                "order_code": _sarr(t["order_code"]),
                "side": _sarr(t["side"]),
                "price": t["price"], "qty": t["qty"],
                "sell_seq": t["sell_seq"].astype(np.int64),
                "buy_seq": t["buy_seq"].astype(np.int64),
            }, schema=TRADES_SCHEMA))
        q = s["quotes"]
        if q and q["n"]:
            d = {"code": pa.array([code] * q["n"], type=pa.string())}
            for k, v in q["cols"].items():
                if k == "engine":
                    continue
                d[k] = v.astype(np.int64)
            q_parts.append(pa.table(d, schema=QUOTES_SCHEMA))
    return {
        "orders": pa.concat_tables(o_parts) if o_parts else ORDERS_SCHEMA.empty_table(),
        "trades": pa.concat_tables(t_parts) if t_parts else TRADES_SCHEMA.empty_table(),
        "quotes": pa.concat_tables(q_parts) if q_parts else QUOTES_SCHEMA.empty_table(),
    }


def write_shard(path: str, table: pa.Table, table_name: str) -> int:
    """写一个分片。调用方按 universe 顺序（即 code 升序）填充，行序已满足
    row-group 统计剪枝所需，因此无需再排序。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    pq.write_table(table, tmp, **WRITE_OPTS,
                   use_dictionary=_DICT_COLS[table_name])
    os.replace(tmp, path)
    return table.num_rows


def catalog_row(date_str: str, code: str, q: dict, n_events: int) -> dict:
    """复现 data.StockData._compute_basic 的字段。"""
    c = q["cols"]
    n = q["n"]
    prev_close = open_ = 0
    if n:
        nz_prev = np.nonzero(c["prev_close"])[0]
        if len(nz_prev):
            prev_close = int(c["prev_close"][nz_prev[-1]])
        nz_open = np.nonzero(c["open"])[0]
        if len(nz_open):
            open_ = int(c["open"][nz_open[-1]])
    last = high = low = cum_vol = cum_amt = 0
    if n:
        nz_last = np.nonzero(c["last"])[0]
        if len(nz_last):
            i = nz_last[-1]
            last = int(c["last"][i]); high = int(c["high"][i]); low = int(c["low"][i])
            cum_vol = int(c["cum_vol"][i]); cum_amt = int(c["cum_amt"][i])

    pc = prev_close / PRICE_SCALE
    lp = last / PRICE_SCALE
    change_pct = ((lp - pc) / pc * 100) if pc else 0.0
    limit_up = round(pc * 1.1, 2)
    limit_down = round(pc * 0.9, 2)
    hit_up = bool(high and high / PRICE_SCALE >= limit_up - 0.005)
    hit_dn = bool(low and low / PRICE_SCALE <= limit_down + 0.005)
    return {
        "date": int(date_str), "code": code,
        "open": open_, "high": high, "low": low, "close": last,
        "prev_close": prev_close, "change_pct": change_pct,
        "vol": cum_vol, "amt": cum_amt,
        "limit_up": int(round(limit_up * PRICE_SCALE)),
        "limit_down": int(round(limit_down * PRICE_SCALE)),
        "hit_limit_up": hit_up, "hit_limit_down": hit_dn,
        "records": int(n_events), "snapshots": int(n),
    }


# --------------------------------------------------------------------------- #
# 单日转换
# --------------------------------------------------------------------------- #
LOCK_NAME = ".build.lock"
LOCK_STALE = 1800  # 秒；单日转换约 10 分钟，超过 30 分钟视为残留


def acquire_lock(store: Store) -> str:
    """同一 root 只允许一个转换进程，避免并发写坏 manifest 与分片。"""
    os.makedirs(store.meta_dir, exist_ok=True)
    path = os.path.join(store.meta_dir, LOCK_NAME)
    for _ in range(2):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, f"pid={os.getpid()} at={int(time.time())}\n".encode())
            os.close(fd)
            return path
        except FileExistsError:
            try:
                age = time.time() - os.path.getmtime(path)
            except OSError:
                age = LOCK_STALE + 1
            if age > LOCK_STALE:
                log(f"发现过期构建锁（{age/60:.0f} 分钟），接管")
                try:
                    os.remove(path)
                except OSError:
                    pass
                continue
            raise SystemExit(
                f"另一个转换进程正在写 {store.root}\n"
                f"  锁文件 {path} 距今 {age/60:.1f} 分钟\n"
                f"  若确认没有进程在跑，删除该锁文件后重试。")
    raise SystemExit(f"无法获取构建锁: {path}")


def release_lock(path: str) -> None:
    try:
        os.remove(path)
    except OSError:
        pass


def _extract(store: Store, src: str, temp: str, targets: list[str] | None,
             date_str: str) -> None:
    """解压归档到 temp；py7zr 偶发路径校验失败时清理重试，再失败则全量解压。"""
    temp = os.path.abspath(temp)
    attempts = [targets, targets, None]
    last: Exception | None = None
    for i, tg in enumerate(attempts):
        try:
            if i:
                shutil.rmtree(temp, ignore_errors=True)
                os.makedirs(temp, exist_ok=True)
                log(f"[{date_str}] 解压重试 #{i} "
                    f"({'targets' if tg else 'extractall'})")
            with py7zr.SevenZipFile(src, "r") as a:
                if tg is None:
                    a.extractall(path=temp)
                else:
                    a.extract(path=temp, targets=tg)
            return
        except Exception as e:  # noqa: BLE001
            last = e
    raise RuntimeError(f"{date_str} 解压失败: {last}")


def convert_date(store: Store, date_str: str, temp_root: str,
                 only_codes: list[str] | None = None,
                 keep_temp: bool = False,
                 reuse_temp: bool = False) -> dict:
    t_start = time.perf_counter()
    src = archive_path(date_str)
    if not os.path.exists(src):
        raise FileNotFoundError(src)
    temp = os.path.abspath(os.path.join(temp_root, date_str))
    inner = os.path.join(temp, date_str)
    base = inner if os.path.isdir(inner) else temp

    # 断点续跑：临时目录已有解压结果时跳过解压
    can_reuse = (reuse_temp and os.path.isdir(base)
                 and any(os.path.isdir(os.path.join(base, d)) for d in os.listdir(base)))
    if can_reuse:
        log(f"[{date_str}] 复用已解压临时目录 {base}")
        t_extract = 0.0
    else:
        shutil.rmtree(temp, ignore_errors=True)
        os.makedirs(temp, exist_ok=True)
        log(f"[{date_str}] 解压 {os.path.getsize(src)/1024**3:.2f} GB -> {temp}")
        t0 = time.perf_counter()
        if only_codes:
            # 只取指定标的，避免整档解压（solid 归档仍会解压途经块，但快于全量）
            wanted = set(only_codes)
            with py7zr.SevenZipFile(src, "r") as a:
                targets = [f.filename for f in a.list()
                           if not f.is_directory
                           and f.filename.replace("\\", "/").split("/")[1] in wanted]
            _extract(store, src, temp, targets, date_str)
        else:
            _extract(store, src, temp, None, date_str)
        t_extract = time.perf_counter() - t0
        base = inner if os.path.isdir(inner) else temp
    raw_bytes = sum(os.path.getsize(os.path.join(dp, f))
                    for dp, _, fs in os.walk(temp) for f in fs)
    log(f"[{date_str}] 待转换数据 {raw_bytes/1024**3:.2f} GB / {t_extract:.1f}s "
        f"({raw_bytes/1024**3/t_extract*60:.1f} GB/min)" if t_extract
        else f"[{date_str}] 待转换数据 {raw_bytes/1024**3:.2f} GB（复用）")

    present = sorted(d for d in os.listdir(base) if os.path.isdir(os.path.join(base, d)))
    if only_codes:
        present = [c for c in present if c in set(only_codes)]
    log(f"[{date_str}] 标的 {len(present)}")

    # 清掉该交易日已有的分片：中断重跑时，若本次某分片没有数据就不会写文件，
    # 上一次次优或残缺的分片会残留下来被读取。manifest 未记录完成前这样做是安全的。
    old_dir = os.path.dirname(store.table_path(date_str, "orders", 0))
    if os.path.isdir(old_dir):
        n_old = sum(len(fs) for _, _, fs in os.walk(old_dir))
        shutil.rmtree(old_dir, ignore_errors=True)
        log(f"[{date_str}] 清理旧分片 {n_old} 个: {old_dir}")

    m = store._m
    total_rows = {"orders": 0, "trades": 0, "quotes": 0}
    cat_rows = []
    produced = []

    t_parse_all = 0.0
    nsh = store.n_shards()
    for shard in range(nsh):
        want = store.shard_codes(shard)
        have = [c for c in want if c in set(present)]
        if not have:
            continue
        if shard % 4 == 0:
            # 心跳：解析阶段可能连续几分钟没有输出，靠它区分「在跑」和「卡死」
            log(f"[{date_str}] 进度 分片 {shard}/{nsh}  "
                f"已用 {time.perf_counter()-t_start:.0f}s")
        stocks = {}
        for code in have:
            d = os.path.join(base, code)
            po = os.path.join(d, "逐笔委托.csv")
            pt = os.path.join(d, "逐笔成交.csv")
            pqf = os.path.join(d, "行情.csv")
            if not (os.path.exists(po) and os.path.exists(pt)):
                continue
            t0 = time.perf_counter()
            orders = parse_orders(po)
            trades = parse_trades(pt)
            quotes = parse_quotes(pqf) if os.path.exists(pqf) else {"n": 0, "cols": {}}
            t_parse_all += time.perf_counter() - t0
            n_events = _count_events(orders, trades, code)
            stocks[code] = {"orders": orders, "trades": trades, "quotes": quotes}
            if quotes["n"]:
                cat_rows.append(catalog_row(date_str, code, quotes, n_events))
            produced.append(code)
        tables = build_tables(stocks, want)
        for name in ("orders", "trades", "quotes"):
            if tables[name].num_rows:
                total_rows[name] += write_shard(
                    store.table_path(date_str, name, shard), tables[name], name)
        del stocks, tables

    # 当日清单
    cpath = store.codes_path(date_str)
    os.makedirs(os.path.dirname(cpath), exist_ok=True)
    tmp = cpath + ".tmp"
    pq.write_table(pa.table({"code": pa.array(sorted(produced), type=pa.string())}),
                   tmp, **WRITE_OPTS, use_dictionary=["code"])
    os.replace(tmp, cpath)

    # 日线目录
    cat_path = store.catalog_path(date_str)
    os.makedirs(os.path.dirname(cat_path), exist_ok=True)
    tmp = cat_path + ".tmp"
    pq.write_table(pa.Table.from_pylist(cat_rows, schema=CATALOG_SCHEMA),
                   tmp, **WRITE_OPTS, use_dictionary=["code"])
    os.replace(tmp, cat_path)

    elapsed = time.perf_counter() - t_start
    # 注：不在这里遍历整个数据集统计体积——D: 是慢盘，且该值原本未被使用；
    # 总体积由 _print_summary 在最后统计一次，单日体积只统计本日文件。
    day_bytes = sum(
        os.path.getsize(store.table_path(date_str, t, sh))
        for t in ("orders", "trades", "quotes")
        for sh in range(store.n_shards())
        if os.path.exists(store.table_path(date_str, t, sh)))
    if os.path.exists(store.catalog_path(date_str)):
        day_bytes += os.path.getsize(store.catalog_path(date_str))
    if not keep_temp:
        shutil.rmtree(temp, ignore_errors=True)

    log(f"[{date_str}] 完成 {len(produced)} 只  rows={total_rows}  "
        f"解压 {t_extract:.0f}s  解析 {t_parse_all:.0f}s  总 {elapsed:.0f}s")
    return {
        "codes": len(produced), "rows": total_rows,
        "archive_bytes": os.path.getsize(src),
        "raw_bytes": raw_bytes,
        "extract_seconds": round(t_extract, 1),
        "parse_seconds": round(t_parse_all, 1),
        "total_seconds": round(elapsed, 1),
        "parquet_bytes": day_bytes,
        "partition": store.table_path(date_str, "orders", 0).split(os.sep)[-3],
        "built_at": int(time.time()),
        # 用 --codes 只转了一部分标的时为 True：清单/日线需回退到归档口径
        "partial": bool(only_codes),
    }


def _count_events(orders: dict, trades: dict, code: str) -> int:
    """复现 data.py 过滤后的事件条数（用于 catalog.records），向量化实现。"""
    is_sh = code.endswith(".SH")
    oc = orders["order_code"]
    keep = _eq_str(oc, "B") | _eq_str(oc, "S")
    if is_sh:
        ot = orders["order_type"]
        keep &= _eq_str(ot, "A") | _eq_str(ot, "D")
    n = int(keep.sum())
    n += trades["n"] if trades["n"] else 0
    return n


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="7z -> Parquet 列存转换")
    ap.add_argument("--root", default=DEFAULT_ROOT)
    ap.add_argument("--freq", default="month", choices=["month", "week"])
    ap.add_argument("--shard-size", type=int, default=256)
    ap.add_argument("--dates", nargs="*", default=None)
    ap.add_argument("--codes", nargs="*", default=None)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--force", action="store_true", help="已转换的交易日也重建")
    ap.add_argument("--universe-only", action="store_true")
    ap.add_argument("--temp", default=os.path.join(HFQ, "cache", "_build"))
    ap.add_argument("--keep-temp", action="store_true")
    ap.add_argument("--reuse-temp", action="store_true",
                    help="临时目录已有解压结果时跳过解压（断点续跑）")
    args = ap.parse_args()

    all_dates = list_archives()
    if not all_dates:
        raise SystemExit(f"未找到归档: {DATA_DIR}")
    targets = args.dates or (all_dates if args.all else all_dates[-1:])
    log(f"归档 {len(all_dates)} 个 ({all_dates[0]}..{all_dates[-1]})，"
        f"本次目标 {len(targets)} 个: {targets[0]}..{targets[-1]}")
    log(f"输出 {args.root}  分区={args.freq}  分片={args.shard_size}")

    store = Store(args.root)
    if store.exists() and not args.force:
        m = store.manifest()
        if m.get("schema") != SCHEMA_VERSION:
            raise SystemExit(
                f"已有数据集 schema={m.get('schema')} 与当前 {SCHEMA_VERSION} 不符，"
                f"用 --force 重建")
        if m.get("freq") != args.freq or m.get("shard_size") != args.shard_size:
            raise SystemExit(
                f"已有数据集参数不同 (freq={m.get('freq')}, "
                f"shard={m.get('shard_size')})，用 --force 重建")
        store._m = m
        log(f"续跑：已有 {len(m['dates'])} 个交易日")
    else:
        if args.force and os.path.isdir(args.root):
            log("--force：清空输出目录")
            shutil.rmtree(args.root)
        os.makedirs(store.meta_dir, exist_ok=True)
        universe = load_universe(store, all_dates, force=True)
        log(f"universe {len(universe)} 只，分片数 "
            f"{(len(universe)+args.shard_size-1)//args.shard_size}")
        store._m = store.new_manifest(args.freq, universe, args.shard_size)
        store.save_manifest(store._m)
        if args.universe_only:
            log("仅构建 universe，退出")
            return

    if args.universe_only:
        log("universe 已存在，退出")
        return

    os.makedirs(args.temp, exist_ok=True)
    todo = [d for d in targets if args.force or d not in store._m["dates"]]
    log(f"待处理 {len(todo)}/{len(targets)} 个交易日")
    lock = acquire_lock(store)
    try:
        t_all = time.perf_counter()
        for i, d in enumerate(todo, 1):
            log(f"\n===== [{i}/{len(todo)}] {d} =====")
            info = convert_date(store, d, args.temp, args.codes,
                                args.keep_temp, args.reuse_temp)
            info["codes_list"] = len(store.list_codes(d))
            store._m["dates"][d] = info
            store.save_manifest(store._m)

        if len(todo) > 1:
            log(f"\n合计耗时 {(time.perf_counter()-t_all)/60:.1f} 分钟")
        _print_summary(store)
    finally:
        release_lock(lock)


def _print_summary(store: Store) -> None:
    m = store._m
    dates = sorted(m["dates"])
    print("\n=== 数据集概览 ===")
    print(f"  分区频率      {m['freq']}")
    print(f"  universe      {len(m['universe'])} 只")
    print(f"  交易日        {len(dates)} 个  {dates[0] if dates else '-'}.."
          f"{dates[-1] if dates else '-'}")
    tot_pq = sum(os.path.getsize(os.path.join(dp, f))
                 for dp, _, fs in os.walk(store.root) for f in fs
                 if f.endswith(".parquet"))
    tot_arc = sum(m["dates"][d]["archive_bytes"] for d in dates)
    tot_raw = sum(m["dates"][d]["raw_bytes"] for d in dates)
    print(f"  7z 归档       {tot_arc/1024**3:8.2f} GB")
    print(f"  CSV 解压      {tot_raw/1024**3:8.2f} GB")
    print(f"  Parquet       {tot_pq/1024**3:8.2f} GB  "
          f"({tot_raw/tot_pq if tot_pq else 0:.2f}x vs CSV, "
          f"{tot_arc/tot_pq if tot_pq else 0:.2f}x vs 7z)")
    if dates:
        print(f"  文件数        "
              f"{sum(1 for dp,_,fs in os.walk(store.root) for f in fs if f.endswith('.parquet'))}")
        print(f"  分区数        "
              f"{len({m['dates'][d]['partition'] for d in dates})}")


if __name__ == "__main__":
    main()
