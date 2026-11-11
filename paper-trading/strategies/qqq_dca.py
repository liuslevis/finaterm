"""QQQ 定投：每个美股交易日开盘买入 $10（碎股、零佣金）。"""
from __future__ import annotations

import pandas as pd

ID = "qqq-dca"
NAME = "QQQ 定投"
DESC = "每个美股交易日开盘买入 $10 QQQ（碎股、零佣金）"
START = "2026-09-10"
CAPITAL = 0
CALENDAR = "QQQ"
DATA = ["QQQ", "^IRX"]
NEED_GPR = False
FEE = 0.0
FRACTIONAL = True
CASH_YIELD = False
DAILY = 10.0

SUPPORT = [
    {"key": "close", "label": "QQQ 收盘", "fmt": "usd"},
    {"key": "invested", "label": "累计投入", "fmt": "usd"},
    {"key": "shares", "label": "持有份额", "fmt": "num4"},
    {"key": "avg_cost", "label": "平均成本", "fmt": "usd"},
    {"key": "value", "label": "市值", "fmt": "usd"},
    {"key": "pnl", "label": "浮动盈亏", "fmt": "usd"},
    {"key": "pnl_pct", "label": "盈亏 / 投入", "fmt": "pct2"},
    {"key": "vs_avg", "label": "现价相对成本", "fmt": "pct2"},
    {"key": "buys", "label": "已定投次数", "fmt": "int"},
]


def prepare(market) -> pd.DataFrame:
    return market["QQQ"]


def contribution(day) -> float:
    return DAILY


def on_open(day, ctx, acct) -> list[dict]:
    return [{"symbol": "QQQ", "side": "buy", "amount": DAILY, "reason": f"定投 ${DAILY:g}"}]


def on_close(day, ctx: pd.DataFrame, acct):
    close = float(ctx.Close.loc[day])
    sh = acct.shares("QQQ")
    value = sh * close
    spent = acct.invested - acct.cash
    avg = spent / sh if sh else None
    return [], {
        "close": round(close, 2), "invested": round(acct.invested, 2), "shares": round(sh, 6),
        "avg_cost": round(avg, 2) if avg else None, "value": round(value, 2),
        "pnl": round(acct.nav - acct.invested, 2),
        "pnl_pct": round(acct.nav / acct.invested - 1, 5) if acct.invested else None,
        "vs_avg": round(close / avg - 1, 5) if avg else None,
        "buys": round(acct.invested / DAILY),
    }
