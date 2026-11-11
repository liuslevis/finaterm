"""行情下载与缓存。只返回已收盘的交易日，盘中 K 线一律丢弃。"""
from __future__ import annotations

import io
import json
import time
import urllib.request
from datetime import datetime, time as dtime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / ".cache"
GPR_URL = "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls"
GPR_MAX_AGE = 12 * 3600

# A 股指数用腾讯行情（Yahoo 的 000300.SS 长区间只返回当天一根），代码形如 sh000300
TENCENT_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={sym},day,{start},{end},640,qfq"
US_SESSION = ("America/New_York", dtime(16, 30))
CN_SESSION = ("Asia/Shanghai", dtime(15, 30))


def is_cn(symbol: str) -> bool:
    return symbol[:2] in ("sh", "sz") and symbol[2:].isdigit()


def session_complete(symbol: str, day: pd.Timestamp, now: datetime | None = None) -> bool:
    """收盘后留 30 分钟让数据源落定，之前的当日 K 线视为盘中数据。"""
    tz, cutoff = CN_SESSION if is_cn(symbol) else US_SESSION
    local = (now or datetime.now(ZoneInfo("UTC"))).astimezone(ZoneInfo(tz))
    return day.date() < local.date() or (day.date() == local.date() and local.time() >= cutoff)


def _cache_path(symbol: str) -> Path:
    return CACHE / "prices" / f"{symbol.replace('^', '').replace('=', '_')}.csv"


def fetch_tencent(symbol: str, start: str) -> pd.DataFrame:
    rows = []
    for year in range(int(start[:4]), datetime.now().year + 1):
        url = TENCENT_URL.format(sym=symbol, start=f"{year}-01-01", end=f"{year}-12-31")
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())["data"][symbol]
        rows += data.get("qfqday") or data.get("day") or []
    df = pd.DataFrame([r[:5] for r in rows], columns=["Date", "Open", "Close", "High", "Low"])
    df = df.set_index(pd.to_datetime(df.pop("Date"))).astype(float)
    return df[df.index >= pd.Timestamp(start)][["Open", "High", "Low", "Close"]]


def fetch_prices(symbols: list[str], start: str, cn_start: str | None = None) -> dict[str, pd.DataFrame]:
    import yfinance as yf

    (CACHE / "prices").mkdir(parents=True, exist_ok=True)
    us = [s for s in symbols if not is_cn(s)]
    raw = yf.download(us, start=start, auto_adjust=True, group_by="ticker", progress=False, threads=True)
    out = {}
    for sym in symbols:
        try:
            df = fetch_tencent(sym, cn_start or start) if is_cn(sym) else raw[sym][["Open", "High", "Low", "Close"]]
            df = df.dropna(subset=["Close"])
        except Exception:
            df = pd.DataFrame()
        path = _cache_path(sym)
        if df.empty and path.exists():
            df = pd.read_csv(path, index_col=0, parse_dates=True)
        if df.empty:
            raise RuntimeError(f"no price data for {sym}")
        df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
        df = df[[session_complete(sym, d) for d in df.index]]
        df.to_csv(path)
        out[sym] = df
    return out


def fetch_gpr() -> pd.Series:
    """Caldara-Iacoviello 地缘风险日度指数（7 日均值），每周更新。"""
    path = CACHE / "gpr_daily.csv"
    if not path.exists() or time.time() - path.stat().st_mtime > GPR_MAX_AGE:
        try:
            req = urllib.request.Request(GPR_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                xls = pd.read_excel(io.BytesIO(resp.read()), engine="calamine")
            xls[["date", "GPRD_MA7"]].to_csv(path, index=False)
        except Exception:
            if not path.exists():
                raise
    g = pd.read_csv(path, parse_dates=["date"]).set_index("date").GPRD_MA7
    return g.dropna()


class Market:
    def __init__(self, symbols: list[str], start: str, need_gpr: bool, cn_start: str | None = None):
        self.prices = fetch_prices(sorted(set(symbols)), start, cn_start)
        self.gpr = fetch_gpr() if need_gpr else None

    def __getitem__(self, symbol: str) -> pd.DataFrame:
        return self.prices[symbol]
