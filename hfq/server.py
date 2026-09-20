"""hfq LV2 逐笔研究终端 —— 本地 HTTP 服务。

纯标准库实现（无第三方 Web 框架），提供 JSON API 与静态文件。
默认监听 127.0.0.1:8770，仅本机访问。

启动：  python -m hfq.server   或   python server.py
"""

from __future__ import annotations

import json
import os
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from app import data

HOST = os.environ.get("HFQ_HOST", "127.0.0.1")
PORT = int(os.environ.get("HFQ_PORT", "8770"))
HERE = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(HERE, "static")

MIME = {
    ".html": "text/html; charset=utf-8", ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
    ".ico": "image/x-icon",
}


def parse_time(s):
    """'HH:MM:SS.mmm' / 'HHMMSSmmm' -> int(HHMMSSmmm)，空返回 None。"""
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    if ":" in s or "." in s:
        s = s.replace(":", "").replace(".", "")
    try:
        return int(s.ljust(9, "0")[:9])
    except ValueError:
        return None


def slim(e):
    return {
        "seq": e["seq"], "time": data.fmt_time(e["t"]), "type": e["type"],
        "side": e["side"], "price": e["price"], "qty": e["qty"],
        "amount": round(e["amount"], 2), "aseq": e["aseq"],
        "buy_id": e["buy_id"], "sell_id": e["sell_id"],
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "hfq/1.0"

    def log_message(self, fmt, *args):  # 安静日志
        pass

    # --- 响应辅助 --------------------------------------------------------- #
    def _json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False, default=float).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _err(self, msg, status=400):
        self._json({"error": msg}, status)

    # --- 路由 ------------------------------------------------------------- #
    def do_GET(self):
        u = urlparse(self.path)
        path = u.path
        q = parse_qs(u.query)
        try:
            if path.startswith("/api/"):
                return self._api(path[5:], q)
            return self._static(path)
        except KeyError as e:
            self._err(f"未找到: {e}", 404)
        except Exception as e:
            traceback.print_exc()
            self._err(f"服务器错误: {e}", 500)

    def _get(self, q, key, default=None):
        v = q.get(key)
        return v[0] if v else default

    def _api(self, route, q):
        if route == "health":
            return self._json({"status": "ok", "service": "hfq-lv2", "date": data.TRADE_DATE})

        if route == "stocks":
            kw = (self._get(q, "kw", "") or "").upper()
            stocks = data.list_stocks()
            if kw:
                stocks = [s for s in stocks if kw in s["code"]]
            return self._json({"total": len(stocks), "stocks": stocks[:500]})

        code = self._get(q, "code")
        if not code:
            return self._err("缺少参数 code")

        if route == "basic":
            return self._json(data.get_stock(code).basic)

        if route == "events":
            sd = data.get_stock(code)
            ev = data.filter_events(
                sd,
                t_start=parse_time(self._get(q, "start")),
                t_end=parse_time(self._get(q, "end")),
                etype=self._get(q, "type", "全部"),
                min_qty=_iopt(self._get(q, "min_qty")),
                max_qty=_iopt(self._get(q, "max_qty")),
                min_amt=_fopt(self._get(q, "min_amt")),
                max_amt=_fopt(self._get(q, "max_amt")),
            )
            summary = data.summarize(ev)
            offset = int(self._get(q, "offset", "0"))
            limit = min(int(self._get(q, "limit", "500")), 5000)
            page = ev[offset:offset + limit]
            return self._json({
                "code": code, "total": len(ev), "offset": offset,
                "summary": summary, "events": [slim(e) for e in page],
            })

        if route == "ordermap":
            sd = data.get_stock(code)
            min_qty = _iopt(self._get(q, "min_qty"))
            buy, sell = [], []
            for e in sd.events:
                if e["type"] != "委托" or e["price"] <= 0:
                    continue
                if min_qty is not None and e["qty"] < min_qty:
                    continue
                rec = [e["t"] / 1.0, e["price"], e["qty"], e["order_id"]]
                (buy if e["side"] == "买" else sell).append(rec)
            return self._json({"code": code, "buy": buy, "sell": sell,
                               "basic": sd.basic})

        if route == "orderbook":
            sd = data.get_stock(code)
            t = parse_time(self._get(q, "t")) or 150000000
            return self._json(data.order_book_at(sd, t))

        if route == "ladder":
            return self._json({"code": code, "ladder": data.build_ladder(data.get_stock(code))})

        if route == "books":
            return self._json(data.all_books(data.get_stock(code)))

        if route == "intraday":
            return self._json(data.intraday(data.get_stock(code)))

        if route == "trades":
            sd = data.get_stock(code)
            ts = parse_time(self._get(q, "start"))
            te = parse_time(self._get(q, "end"))
            out = []
            for e in sd.events:
                if e["type"] != "成交":
                    continue
                if ts is not None and e["t"] < ts:
                    continue
                if te is not None and e["t"] > te:
                    continue
                out.append(slim(e))
            limit = min(int(self._get(q, "limit", "1000")), 20000)
            return self._json({"code": code, "total": len(out),
                               "trades": out[-limit:]})

        if route == "orders":
            sd = data.get_stock(code)
            side = self._get(q, "side")
            side = side if side in ("买", "卖") else None
            return self._json(data.list_orders(
                sd, side=side,
                t_start=parse_time(self._get(q, "start")),
                t_end=parse_time(self._get(q, "end")),
                limit=min(int(self._get(q, "limit", "800")), 5000)))

        if route == "locate":
            sd = data.get_stock(code)
            oid = _iopt(self._get(q, "order_id"))
            if oid is None:
                return self._err("缺少 order_id")
            return self._json(data.locate_order(sd, oid))

        if route == "track":
            sd = data.get_stock(code)
            oid = _iopt(self._get(q, "order_id"))
            if oid is None:
                return self._err("缺少 order_id")
            return self._json(data.track_order(sd, oid))

        if route == "region":
            sd = data.get_stock(code)
            ts = parse_time(self._get(q, "start"))
            te = parse_time(self._get(q, "end"))
            return self._json(_region_stats(sd, ts, te))

        return self._err(f"未知接口: {route}", 404)

    # --- 静态文件 --------------------------------------------------------- #
    def _static(self, path):
        if path == "/":
            path = "/index.html"
        path = path.lstrip("/")
        full = os.path.normpath(os.path.join(STATIC_DIR, path))
        if not full.startswith(STATIC_DIR) or not os.path.isfile(full):
            return self._err("未找到", 404)
        ext = os.path.splitext(full)[1].lower()
        with open(full, "rb") as fh:
            body = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", MIME.get(ext, "application/octet-stream"))
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _iopt(s):
    if s is None or s == "":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def _fopt(s):
    if s is None or s == "":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _region_stats(sd, ts, te):
    trades = [e for e in sd.events if e["type"] == "成交"
              and (ts is None or e["t"] >= ts) and (te is None or e["t"] <= te)]
    if not trades:
        return {"found": False}
    prices = [e["price"] for e in trades]
    vol = sum(e["qty"] for e in trades)
    amt = sum(e["amount"] for e in trades)  # 万
    start_p, end_p = prices[0], prices[-1]
    mx = max(trades, key=lambda e: e["qty"])
    return {
        "found": True,
        "start_time": data.fmt_time(trades[0]["t"]),
        "end_time": data.fmt_time(trades[-1]["t"]),
        "change_pct": ((end_p - start_p) / start_p * 100) if start_p else 0.0,
        "start_price": start_p, "high": max(prices), "low": min(prices),
        "end_price": end_p, "vol": vol, "amt": amt,
        "max_vol": mx["qty"], "max_vol_side": mx["side"], "count": len(trades),
    }


def main():
    print(f"hfq LV2 终端启动：http://{HOST}:{PORT}  (交易日 {data.TRADE_DATE})")
    print("首次加载某只股票会从归档抽取并解析，稍候几秒。")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    main()
