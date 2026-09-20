"""LV2 逐笔数据访问层。

从 7z 归档按需抽取单只股票的三个 GBK 编码 CSV（行情 / 逐笔委托 / 逐笔成交），
解析为统一的逐笔事件流（委托 / 成交 / 撤单），并提供汇总统计、订单追踪、
盘口快照与分时数据。支持深交所（.SZ）与上交所（.SH）两种编码约定。
"""

from __future__ import annotations

import csv
import io
import json
import os
import struct
import threading
from collections import OrderedDict
from functools import lru_cache

import py7zr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA_DIR = os.path.join(ROOT, "data-lv2")
CACHE_DIR = os.path.join(ROOT, "cache")

PRICE_SCALE = 10000.0  # 原始价格为 元 * 10000

os.makedirs(CACHE_DIR, exist_ok=True)

_archive_lock = threading.Lock()
_index_lock = threading.Lock()


def list_dates() -> list[str]:
    """扫描 data-lv2/*.7z，返回升序交易日列表（文件名即 YYYYMMDD）。"""
    ds = []
    try:
        for fn in os.listdir(DATA_DIR):
            if fn.endswith(".7z") and fn[:-3].isdigit():
                ds.append(fn[:-3])
    except OSError:
        pass
    ds.sort()
    return ds


DATES = list_dates()
DEFAULT_DATE = DATES[-1] if DATES else "20260918"
TRADE_DATE = DEFAULT_DATE  # 兼容旧引用：默认（最新）交易日


def _norm_date(date: str | None) -> str:
    return date if date in DATES else DEFAULT_DATE


def _archive_path(date: str) -> str:
    return os.path.join(DATA_DIR, f"{date}.7z")


def prev_date(date: str) -> str | None:
    d = _norm_date(date)
    i = DATES.index(d)
    return DATES[i - 1] if i > 0 else None


def next_date(date: str) -> str | None:
    d = _norm_date(date)
    i = DATES.index(d)
    return DATES[i + 1] if i < len(DATES) - 1 else None


# --------------------------------------------------------------------------- #
# 归档索引 / 抽取
# --------------------------------------------------------------------------- #
def _build_index(date: str) -> dict:
    """扫描某日归档，建立 code -> [成员文件名] 索引，缓存到磁盘。"""
    index: dict[str, list[str]] = {}
    with _archive_lock:
        with py7zr.SevenZipFile(_archive_path(date), "r") as a:
            for f in a.list():
                if f.is_directory:
                    continue
                parts = f.filename.split("/")
                if len(parts) >= 3 and parts[1]:
                    index.setdefault(parts[1], []).append(f.filename)
    date_dir = os.path.join(CACHE_DIR, date)
    os.makedirs(date_dir, exist_ok=True)
    ipath = os.path.join(date_dir, "_index.json")
    tmp = ipath + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(index, fh)
    os.replace(tmp, ipath)
    return index


def get_index(date: str = DEFAULT_DATE) -> dict:
    date = _norm_date(date)
    ipath = os.path.join(CACHE_DIR, date, "_index.json")
    with _index_lock:
        if os.path.exists(ipath):
            try:
                with open(ipath, encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception:
                pass
        return _build_index(date)


def list_stocks(date: str = DEFAULT_DATE) -> list[dict]:
    idx = get_index(date)
    out = [{"code": c, "market": c.split(".")[-1]} for c in idx]
    out.sort(key=lambda x: x["code"])
    return out


def _stock_dir(code: str, date: str) -> str:
    return os.path.join(CACHE_DIR, date, code)


def ensure_extracted(code: str, date: str) -> str:
    """确保某只股票某日的 CSV 已抽取到本地缓存目录，返回该目录。"""
    date = _norm_date(date)
    dest = _stock_dir(code, date)
    needed = ["行情.csv", "逐笔委托.csv", "逐笔成交.csv"]
    if all(os.path.exists(os.path.join(dest, n)) for n in needed):
        return dest
    idx = get_index(date)
    members = idx.get(code)
    if not members:
        raise KeyError(f"未知代码: {code}")
    os.makedirs(dest, exist_ok=True)
    stage_root = os.path.join(CACHE_DIR, date, "_stage")
    with _archive_lock:
        with py7zr.SevenZipFile(_archive_path(date), "r") as a:
            a.extract(path=stage_root, targets=members)
    # 归档内路径为 <date>/<code>/<name>，移动到 cache/<date>/<code>/<name>
    staged = os.path.join(stage_root, date, code)
    for n in needed:
        src = os.path.join(staged, n)
        if os.path.exists(src):
            os.replace(src, os.path.join(dest, n))
    return dest


def _read_csv(path: str):
    with open(path, "r", encoding="gbk", errors="replace", newline="") as fh:
        yield from csv.reader(fh)


# --------------------------------------------------------------------------- #
# 时间 / 价格辅助
# --------------------------------------------------------------------------- #
def fmt_time(t: int) -> str:
    ms = t % 1000
    s = (t // 1000) % 100
    m = (t // 100000) % 100
    h = t // 10000000
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def _px(raw: str) -> float:
    try:
        return int(raw) / PRICE_SCALE
    except (ValueError, TypeError):
        return 0.0


def _int(raw: str) -> int:
    try:
        return int(raw)
    except (ValueError, TypeError):
        return 0


# --------------------------------------------------------------------------- #
# 解析 -> 统一事件流
# --------------------------------------------------------------------------- #
class StockData:
    """单只股票某交易日的全部解析结果。"""

    def __init__(self, code: str, date: str = DEFAULT_DATE):
        self.code = code
        self.date = _norm_date(date)
        self.market = code.split(".")[-1]
        self.events: list[dict] = []          # 统一逐笔事件（按 aseq 排序）
        self.quotes: list[dict] = []          # 行情快照（分时 / 盘口）
        self.basic: dict = {}
        self._by_order: dict[int, dict] = {}  # order_id -> 追踪聚合
        self._load()

    # --- 解析各文件 --------------------------------------------------------- #
    def _load(self):
        if not self._load_binary():
            self._parse_all()
            self._save_binary()
        self._index_orders()
        self._compute_basic()

    def _parse_all(self):
        """慢速路径：从 7z 抽取 + 解析 GBK CSV（首次访问某股票时执行一次）。"""
        d = ensure_extracted(self.code, self.date)
        self._parse_quotes(os.path.join(d, "行情.csv"))
        raw_events = []
        raw_events += self._parse_orders(os.path.join(d, "逐笔委托.csv"))
        raw_events += self._parse_trades(os.path.join(d, "逐笔成交.csv"))
        raw_events.sort(key=lambda e: e["aseq"])
        for i, e in enumerate(raw_events, 1):
            e["seq"] = i
        self.events = raw_events

    def _parse_orders(self, path: str) -> list[dict]:
        out = []
        rows = _read_csv(path)
        next(rows, None)  # header
        is_sh = self.market == "SH"
        for r in rows:
            if len(r) < 10:
                continue
            # 时间, 委托编号, 交易所委托号, 委托类型, 委托代码, 委托价格, 委托数量
            t = _int(r[3]); aseq = _int(r[5]); otype = r[6]; side_code = r[7]
            price = _px(r[8]); qty = _int(r[9])
            if side_code == "B":
                side = "买"
            elif side_code == "S":
                side = "卖"
            else:
                continue  # 过滤噪声委托代码
            if is_sh:
                # 上交所：A=新增委托，D=撤单
                if otype == "A":
                    etype = "委托"
                elif otype == "D":
                    etype = "撤单"
                    price = 0.0
                else:
                    continue
            else:
                etype = "委托"  # 深交所逐笔委托均为新增；撤单在逐笔成交中
            buy_id = aseq if side == "买" else 0
            sell_id = aseq if side == "卖" else 0
            out.append({
                "aseq": aseq, "t": t, "type": etype, "side": side,
                "price": price, "qty": qty, "amount": 0.0,
                "buy_id": buy_id, "sell_id": sell_id, "order_id": aseq,
            })
        return out

    def _parse_trades(self, path: str) -> list[dict]:
        out = []
        rows = _read_csv(path)
        next(rows, None)
        is_sh = self.market == "SH"
        for r in rows:
            if len(r) < 12:
                continue
            # 时间, 成交编号, 成交代码, BS标志, 成交价格, 成交数量, 叫卖序号, 叫买序号
            t = _int(r[3]); aseq = _int(r[4]); dcode = r[5].strip(); bs = r[7].strip()
            price = _px(r[8]); qty = _int(r[9])
            sell_seq = _int(r[10]); buy_seq = _int(r[11])
            is_cancel = (not is_sh) and dcode == "C"
            if is_cancel:
                if buy_seq:
                    side, buy_id, sell_id, oid = "买", buy_seq, 0, buy_seq
                else:
                    side, buy_id, sell_id, oid = "卖", 0, sell_seq, sell_seq
                out.append({
                    "aseq": aseq, "t": t, "type": "撤单", "side": side,
                    "price": 0.0, "qty": qty, "amount": 0.0,
                    "buy_id": buy_id, "sell_id": sell_id, "order_id": oid,
                })
            else:
                side = "买" if bs == "B" else ("卖" if bs == "S" else "")
                out.append({
                    "aseq": aseq, "t": t, "type": "成交", "side": side or "买",
                    "price": price, "qty": qty, "amount": price * qty / 1e4,
                    "buy_id": buy_seq, "sell_id": sell_seq, "order_id": 0,
                })
        return out

    def _parse_quotes(self, path: str):
        rows = _read_csv(path)
        header = next(rows, None)
        for r in rows:
            if len(r) < 58:
                continue
            t = _int(r[3])
            asks = [[_px(r[17 + i]), _int(r[27 + i])] for i in range(10)]
            bids = [[_px(r[37 + i]), _int(r[47 + i])] for i in range(10)]
            self.quotes.append({
                "t": t,
                "last": _px(r[4]),
                "cum_vol": _int(r[11]),
                "cum_amt": _int(r[12]),
                "high": _px(r[13]), "low": _px(r[14]),
                "open": _px(r[15]), "prev_close": _px(r[16]),
                "asks": asks, "bids": bids,
            })

    # --- 派生结构 ----------------------------------------------------------- #
    def _index_orders(self):
        for e in self.events:
            if e["type"] == "委托":
                self._by_order.setdefault(e["order_id"], {"orders": [], "trades": [], "cancels": []})["orders"].append(e)
        for e in self.events:
            if e["type"] == "成交":
                for oid in (e["buy_id"], e["sell_id"]):
                    if oid in self._by_order:
                        self._by_order[oid]["trades"].append(e)
            elif e["type"] == "撤单":
                if e["order_id"] in self._by_order:
                    self._by_order[e["order_id"]]["cancels"].append(e)
        # 逐笔委托聚合（供委托明细表：已成交 / 已撤单 / 剩余）
        self.orders_summary = []
        for oid, agg in self._by_order.items():
            o = agg["orders"][0]
            filled = sum(t["qty"] for t in agg["trades"])
            canceled = sum(c["qty"] for c in agg["cancels"])
            self.orders_summary.append({
                "t": o["t"], "order_id": oid, "side": o["side"],
                "price": o["price"], "qty": o["qty"],
                "filled": filled, "canceled": canceled,
                "remain": max(o["qty"] - filled - canceled, 0),
            })
        self.orders_summary.sort(key=lambda x: (x["t"], x["order_id"]))

    def _compute_basic(self):
        prev_close = high = low = open_ = last = 0.0
        cum_vol = cum_amt = 0
        for q in self.quotes:
            if q["prev_close"]:
                prev_close = q["prev_close"]
            if q["open"]:
                open_ = q["open"]
        for q in reversed(self.quotes):
            if q["last"]:
                last = q["last"]; high = q["high"]; low = q["low"]
                cum_vol = q["cum_vol"]; cum_amt = q["cum_amt"]
                break
        change_pct = ((last - prev_close) / prev_close * 100) if prev_close else 0.0
        limit_up = round(prev_close * 1.1, 2)
        limit_down = round(prev_close * 0.9, 2)
        self.basic = {
            "code": self.code, "date": self.date, "market": self.market,
            "open": open_, "prev_close": prev_close, "high": high, "low": low,
            "last": last, "change_pct": change_pct,
            "limit_up": limit_up, "limit_down": limit_down,
            "hit_limit_up": bool(high and high >= limit_up - 0.005),
            "hit_limit_down": bool(low and low <= limit_down + 0.005),
            "records": len(self.events),
            "cum_vol": cum_vol, "cum_amt": cum_amt,
            "turnover_rate": None, "prev_change_pct": None,
            "float_shares": None, "market_cap": None,
        }

    # --- 列式二进制缓存（避免重复的 7z 抽取 + GBK CSV 解析） --------------- #
    _TYPE_CODE = {"委托": 0, "成交": 1, "撤单": 2}
    _CODE_TYPE = {0: "委托", 1: "成交", 2: "撤单"}

    def _bin_path(self) -> str:
        return os.path.join(_stock_dir(self.code, self.date), f"_cache_v{_CACHE_VER}.bin")

    def _save_binary(self):
        try:
            data_bytes = _encode_stock(self.events, self.quotes)
            p = self._bin_path()
            tmp = p + ".tmp"
            with open(tmp, "wb") as fh:
                fh.write(data_bytes)
            os.replace(tmp, p)
        except OSError:
            pass  # 缓存写失败不影响功能

    def _load_binary(self) -> bool:
        p = self._bin_path()
        if not os.path.exists(p):
            return False
        try:
            with open(p, "rb") as fh:
                blob = fh.read()
            self.events, self.quotes = _decode_stock(blob)
            return True
        except (OSError, ValueError, struct.error):
            return False


# 缓存格式版本：结构变更时递增使旧缓存失效
_CACHE_VER = 1


def _encode_stock(events: list, quotes: list) -> bytes:
    import array
    n = len(events)
    cols = {
        "aseq": array.array("q", (e["aseq"] for e in events)),
        "t": array.array("i", (e["t"] for e in events)),
        "type": array.array("b", (StockData._TYPE_CODE.get(e["type"], 0) for e in events)),
        "side": array.array("b", (0 if e["side"] == "买" else 1 for e in events)),
        "price": array.array("i", (round(e["price"] * PRICE_SCALE) for e in events)),
        "qty": array.array("i", (e["qty"] for e in events)),
        "buy": array.array("q", (e["buy_id"] for e in events)),
        "sell": array.array("q", (e["sell_id"] for e in events)),
        "oid": array.array("q", (e["order_id"] for e in events)),
    }
    m = len(quotes)
    q_scalars = ["t", "last", "high", "low", "open", "prev_close"]
    qcols = {k: array.array("i", (round(q[k] * PRICE_SCALE) if k != "t" else q[k]
             for q in quotes)) for k in q_scalars}
    qcols["cum_vol"] = array.array("q", (q["cum_vol"] for q in quotes))
    qcols["cum_amt"] = array.array("q", (q["cum_amt"] for q in quotes))
    ladder = array.array("i")
    for q in quotes:
        for px, qy in q["asks"]:
            ladder.append(round(px * PRICE_SCALE)); ladder.append(qy)
        for px, qy in q["bids"]:
            ladder.append(round(px * PRICE_SCALE)); ladder.append(qy)
    out = bytearray()
    out += b"HFQ2" + struct.pack("<ii", _CACHE_VER, n)
    for k in ("aseq", "t", "type", "side", "price", "qty", "buy", "sell", "oid"):
        b = cols[k].tobytes()
        out += struct.pack("<Q", len(b)); out += b
    out += struct.pack("<i", m)
    for k in ("t", "last", "high", "low", "open", "prev_close", "cum_vol", "cum_amt"):
        b = qcols[k].tobytes()
        out += struct.pack("<Q", len(b)); out += b
    lb = ladder.tobytes()
    out += struct.pack("<Q", len(lb)); out += lb
    return bytes(out)


def _decode_stock(blob: bytes):
    import array
    mv = memoryview(blob)
    if bytes(mv[:4]) != b"HFQ2":
        raise ValueError("bad magic")
    ver, n = struct.unpack_from("<ii", mv, 4)
    if ver != _CACHE_VER:
        raise ValueError("version mismatch")
    off = 12

    def take(typ):
        nonlocal off
        (ln,) = struct.unpack_from("<Q", mv, off); off += 8
        a = array.array(typ); a.frombytes(mv[off:off + ln]); off += ln
        return a

    aseq = take("q"); t = take("i"); typ = take("b"); side = take("b")
    price = take("i"); qty = take("i"); buy = take("q"); sell = take("q"); oid = take("q")
    events = []
    ct = StockData._CODE_TYPE
    for i in range(n):
        p = price[i] / PRICE_SCALE
        et = ct[typ[i]]; qn = qty[i]
        events.append({
            "aseq": aseq[i], "t": t[i], "type": et,
            "side": "买" if side[i] == 0 else "卖",
            "price": p, "qty": qn,
            "amount": (p * qn / 1e4) if et == "成交" else 0.0,
            "buy_id": buy[i], "sell_id": sell[i], "order_id": oid[i], "seq": i + 1,
        })
    (m,) = struct.unpack_from("<i", mv, off); off += 4
    qt = take("i"); last = take("i"); high = take("i"); low = take("i")
    qopen = take("i"); prev = take("i"); cum_vol = take("q"); cum_amt = take("q")
    ladder = take("i")
    quotes = []
    for j in range(m):
        base = j * 40
        asks = [[ladder[base + 2 * k] / PRICE_SCALE, ladder[base + 2 * k + 1]] for k in range(10)]
        bids = [[ladder[base + 20 + 2 * k] / PRICE_SCALE, ladder[base + 20 + 2 * k + 1]] for k in range(10)]
        quotes.append({
            "t": qt[j], "last": last[j] / PRICE_SCALE,
            "cum_vol": cum_vol[j], "cum_amt": cum_amt[j],
            "high": high[j] / PRICE_SCALE, "low": low[j] / PRICE_SCALE,
            "open": qopen[j] / PRICE_SCALE, "prev_close": prev[j] / PRICE_SCALE,
            "asks": asks, "bids": bids,
        })
    return events, quotes


# 简单的 LRU 内存缓存（避免重复解析）
_MEM: "OrderedDict[str, StockData]" = OrderedDict()
_MEM_CAP = 12
_mem_lock = threading.Lock()


def get_stock(code: str) -> StockData:
    with _mem_lock:
        if code in _MEM:
            _MEM.move_to_end(code)
            return _MEM[code]
    sd = StockData(code)  # 解析在锁外进行
    with _mem_lock:
        _MEM[code] = sd
        _MEM.move_to_end(code)
        while len(_MEM) > _MEM_CAP:
            _MEM.popitem(last=False)
    return sd


# --------------------------------------------------------------------------- #
# 查询：筛选事件 + 汇总统计
# --------------------------------------------------------------------------- #
TYPE_FILTERS = {
    "全部": lambda e: True,
    "成交": lambda e: e["type"] == "成交",
    "全委托": lambda e: e["type"] == "委托",
    "委托买": lambda e: e["type"] == "委托" and e["side"] == "买",
    "委托卖": lambda e: e["type"] == "委托" and e["side"] == "卖",
    "全撤单": lambda e: e["type"] == "撤单",
    "撤买单": lambda e: e["type"] == "撤单" and e["side"] == "买",
    "撤卖单": lambda e: e["type"] == "撤单" and e["side"] == "卖",
}


def filter_events(sd: StockData, *, t_start=None, t_end=None, etype="全部",
                  min_qty=None, max_qty=None, min_amt=None, max_amt=None):
    pred = TYPE_FILTERS.get(etype, TYPE_FILTERS["全部"])
    res = []
    for e in sd.events:
        if t_start is not None and e["t"] < t_start:
            continue
        if t_end is not None and e["t"] > t_end:
            continue
        if not pred(e):
            continue
        if min_qty is not None and e["qty"] < min_qty:
            continue
        if max_qty is not None and e["qty"] > max_qty:
            continue
        if min_amt is not None or max_amt is not None:
            amt = e["amount"] or (e["price"] * e["qty"] / 1e4)  # 万元（委托按名义额）
            if min_amt is not None and amt < min_amt:
                continue
            if max_amt is not None and amt > max_amt:
                continue
        res.append(e)
    return res


def summarize(events) -> dict:
    buy_vol = buy_amt = sell_vol = sell_amt = 0.0
    for e in events:
        if e["type"] != "成交":
            continue
        if e["side"] == "买":
            buy_vol += e["qty"]; buy_amt += e["amount"]
        else:
            sell_vol += e["qty"]; sell_amt += e["amount"]
    tot_vol = buy_vol + sell_vol
    tot_amt = buy_amt + sell_amt  # 万元
    return {
        "count": len(events),
        "total_vol": tot_vol, "total_amt": tot_amt,
        "buy_vol": buy_vol, "buy_amt": buy_amt,
        "sell_vol": sell_vol, "sell_amt": sell_amt,
        "buy_sell_ratio": (buy_amt / sell_amt) if sell_amt else 0.0,
        "net_amt": buy_amt - sell_amt,
        "buy_pct": (buy_vol / tot_vol * 100) if tot_vol else 0.0,
        "buy_avg": (buy_amt * 1e4 / buy_vol) if buy_vol else 0.0,
        "sell_avg": (sell_amt * 1e4 / sell_vol) if sell_vol else 0.0,
    }


# --------------------------------------------------------------------------- #
# 盘口快照（就近时间）
# --------------------------------------------------------------------------- #
def order_book_at(sd: StockData, t: int) -> dict:
    import bisect
    ts = [q["t"] for q in sd.quotes]
    i = bisect.bisect_right(ts, t) - 1
    if i < 0:
        i = 0
    q = sd.quotes[i] if sd.quotes else None
    if not q:
        return {}
    tot_bid = sum(b[1] for b in q["bids"])
    tot_ask = sum(a[1] for a in q["asks"])
    denom = tot_bid + tot_ask
    return {
        "t": q["t"], "time": fmt_time(q["t"]), "last": q["last"],
        "asks": q["asks"], "bids": q["bids"],
        "total_bid": tot_bid, "total_ask": tot_ask,
        "committee_ratio": ((tot_bid - tot_ask) / denom * 100) if denom else 0.0,
        "committee_diff": tot_bid - tot_ask,
    }


def build_ladder(sd: StockData) -> list[dict]:
    """按价位聚合全天委托：累计委托买/卖量、已成交、已撤单。用于委托地图左侧阶梯。"""
    cache = getattr(sd, "_ladder", None)
    if cache is not None:
        return cache
    agg: dict[float, dict] = {}
    for o in sd.orders_summary:
        p = round(o["price"], 2)
        if p <= 0:
            continue
        a = agg.setdefault(p, {"price": p, "buy_vol": 0, "buy_cancel": 0,
                               "sell_vol": 0, "sell_cancel": 0})
        if o["side"] == "买":
            a["buy_vol"] += o["qty"]; a["buy_cancel"] += o["canceled"]
        else:
            a["sell_vol"] += o["qty"]; a["sell_cancel"] += o["canceled"]
    ladder = sorted(agg.values(), key=lambda x: x["price"], reverse=True)
    sd._ladder = ladder
    return ladder


def all_books(sd: StockData) -> dict:
    """全天十档快照的紧凑数组，供前端回放时本地二分查找（避免逐帧请求）。"""
    t, last, ap, aq, bp, bq = [], [], [], [], [], []
    for q in sd.quotes:
        t.append(q["t"]); last.append(q["last"])
        ap.append([a[0] for a in q["asks"]]); aq.append([a[1] for a in q["asks"]])
        bp.append([b[0] for b in q["bids"]]); bq.append([b[1] for b in q["bids"]])
    return {"t": t, "last": last, "ask_px": ap, "ask_qty": aq,
            "bid_px": bp, "bid_qty": bq}


# --------------------------------------------------------------------------- #
# 分时
# --------------------------------------------------------------------------- #
def intraday(sd: StockData) -> dict:
    pts = []
    prev_vol = 0
    for q in sd.quotes:
        if not q["last"]:
            continue
        vol = q["cum_vol"] - prev_vol
        prev_vol = q["cum_vol"]
        avg = (q["cum_amt"] / q["cum_vol"]) if q["cum_vol"] else q["last"]
        pts.append({"time": fmt_time(q["t"]), "t": q["t"], "price": q["last"],
                    "avg": round(avg, 3), "vol": max(vol, 0)})
    return {"prev_close": sd.basic.get("prev_close", 0.0), "points": pts}


# --------------------------------------------------------------------------- #
# 逐笔委托明细（已成交 / 已撤单 / 剩余）
# --------------------------------------------------------------------------- #
def list_orders(sd: StockData, side=None, t_start=None, t_end=None, limit=800, tail=True):
    res = []
    for o in sd.orders_summary:
        if side and o["side"] != side:
            continue
        if t_start is not None and o["t"] < t_start:
            continue
        if t_end is not None and o["t"] > t_end:
            continue
        res.append({
            "time": fmt_time(o["t"]), "order_id": o["order_id"], "side": o["side"],
            "price": o["price"], "qty": o["qty"], "filled": o["filled"],
            "canceled": o["canceled"], "remain": o["remain"],
        })
    total = len(res)
    page = res[-limit:] if tail else res[:limit]
    return {"total": total, "orders": page}


def locate_order(sd: StockData, order_id: int):
    """返回该委托号在主表中的序号与时间（用于定位）。"""
    for e in sd.events:
        if e["type"] == "委托" and e["order_id"] == order_id:
            return {"found": True, "seq": e["seq"], "time": fmt_time(e["t"]),
                    "t": e["t"], "side": e["side"]}
    return {"found": False}


# --------------------------------------------------------------------------- #
# 订单追踪
# --------------------------------------------------------------------------- #
def track_order(sd: StockData, order_id: int) -> dict:
    agg = sd._by_order.get(order_id)
    if not agg or not agg["orders"]:
        return {"found": False, "order_id": order_id}
    o = agg["orders"][0]
    life = [{"time": fmt_time(o["t"]), "type": "委托", "qty": o["qty"],
             "price": o["price"], "counter": ""}]
    filled = 0
    for tr in sorted(agg["trades"], key=lambda x: x["aseq"]):
        counter = tr["sell_id"] if o["side"] == "买" else tr["buy_id"]
        life.append({"time": fmt_time(tr["t"]), "type": "成交", "qty": tr["qty"],
                     "price": tr["price"], "counter": counter})
        filled += tr["qty"]
    canceled = 0
    for c in agg["cancels"]:
        life.append({"time": fmt_time(c["t"]), "type": "撤单", "qty": c["qty"],
                     "price": 0.0, "counter": ""})
        canceled += c["qty"]
    life.sort(key=lambda x: x["time"])
    status = "已撤单" if canceled else ("全部成交" if filled >= o["qty"] else
             ("部分成交" if filled else "未成交"))
    return {
        "found": True, "order_id": order_id, "side": o["side"],
        "total_qty": o["qty"], "order_price": o["price"],
        "filled_qty": filled, "canceled_qty": canceled,
        "status": status, "life": life,
    }
