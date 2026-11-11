"""通用模拟账户：逐个交易日增量记账，已写入的日期不再重算（多台电脑结果一致、git 合并干净）。

每个交易日 d 的顺序：
1. 现金按前一日 13 周国债利率计息（策略 CASH_YIELD=True 时）。
2. 入金：首日 CAPITAL + 策略 contribution(d)。
3. 开盘成交：上一交易日收盘产生的挂单 + 策略 on_open(d) 的订单，按 Open[d] 成交。
4. 收盘估值，更新时间加权收益 twr。
5. 策略 on_close(d) 产生下一开盘的挂单，并给出当日支持数据快照。

订单格式：{"symbol", "side": "buy"|"sell", 以及 "weight"（占当时净值）| "amount"（美元）| "shares"="all", "reason"}
"""
from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

STATE = Path(__file__).resolve().parent / "state"
NAV_COLS = ["date", "cash", "holdings", "nav", "flow", "invested", "twr"]
TRADE_COLS = ["date", "signal_date", "symbol", "side", "shares", "price", "amount", "fee", "reason"]


@dataclass
class Account:
    cash: float = 0.0
    holdings: dict[str, float] = field(default_factory=dict)
    invested: float = 0.0
    nav: float = 0.0
    twr: float = 1.0
    last_date: str | None = None
    pending: list[dict] = field(default_factory=list)

    def shares(self, symbol: str) -> float:
        return self.holdings.get(symbol, 0.0)


def _append_csv(path: Path, cols: list[str], rows: list[dict]) -> None:
    if not rows:
        return
    new = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore", lineterminator="\n")
        if new:
            w.writeheader()
        w.writerows(rows)


def _r(x: float, nd: int = 4) -> float:
    return round(float(x), nd)


def _fill(acct: Account, order: dict, day: str, open_px: float, fee_rate: float, fractional: bool) -> dict | None:
    sym, side = order["symbol"], order["side"]
    if side == "sell":
        shares = acct.shares(sym) if order.get("shares") == "all" else min(order["shares"], acct.shares(sym))
    elif "amount" in order:
        shares = order["amount"] / (open_px * (1 + fee_rate))
    else:
        shares = order["weight"] * acct.nav / open_px
    if side == "buy":
        shares = min(shares, acct.cash / (open_px * (1 + fee_rate)))
    shares = shares if fractional else math.floor(shares)
    shares = round(shares, 6)
    if shares <= 0:
        return None
    gross = shares * open_px
    fee = gross * fee_rate
    if side == "buy":
        acct.cash -= gross + fee
        acct.holdings[sym] = acct.shares(sym) + shares
    else:
        acct.cash += gross - fee
        left = acct.shares(sym) - shares
        acct.holdings = {k: v for k, v in {**acct.holdings, sym: left}.items() if v > 1e-9}
    return {"date": day, "signal_date": order.get("signal_date", day), "symbol": sym, "side": side,
            "shares": shares, "price": _r(open_px), "amount": _r(gross, 2), "fee": _r(fee, 2),
            "reason": order.get("reason", "")}


def run_strategy(strategy, market) -> int:
    """处理该策略所有尚未入账的已收盘交易日，返回新增天数。"""
    folder = STATE / strategy.ID
    folder.mkdir(parents=True, exist_ok=True)
    acct_path = folder / "account.json"
    acct = Account(**json.loads(acct_path.read_text())) if acct_path.exists() else Account()

    cal = market[strategy.CALENDAR]
    days = cal.index[cal.index >= pd.Timestamp(strategy.START)]
    if acct.last_date:
        days = days[days > pd.Timestamp(acct.last_date)]
    if len(days) == 0:
        _write_meta(strategy, folder)
        return 0

    ctx = strategy.prepare(market)
    irx = market["^IRX"].Close.reindex(cal.index).ffill() / 100 / 252
    nav_rows, trade_rows, sig_rows = [], [], []
    for d in days:
        day = d.date().isoformat()
        first = acct.last_date is None
        prev_nav = acct.nav
        if strategy.CASH_YIELD and not first and acct.cash > 0:
            prev = irx.loc[:d].iloc[:-1]
            acct.cash *= 1 + (prev.iloc[-1] if len(prev) and pd.notna(prev.iloc[-1]) else 0)
        flow = (strategy.CAPITAL if first else 0) + strategy.contribution(d)
        acct.cash += flow
        acct.invested += flow

        orders = acct.pending + strategy.on_open(d, ctx, acct)
        for o in orders:
            px = market[o["symbol"]].Open.get(d)
            if px is None or pd.isna(px):
                continue
            t = _fill(acct, o, day, float(px), strategy.FEE, strategy.FRACTIONAL)
            if t:
                trade_rows.append(t)

        value = sum(sh * float(market[s].Close.loc[:d].iloc[-1]) for s, sh in acct.holdings.items())
        acct.nav = acct.cash + value
        base = prev_nav + flow
        acct.twr *= acct.nav / base if base > 0 else 1
        acct.last_date = day

        pending, support = strategy.on_close(d, ctx, acct)
        acct.pending = [{**o, "signal_date": day} for o in pending]
        nav_rows.append({"date": day, "cash": _r(acct.cash, 2),
                         "holdings": ";".join(f"{k}={_r(v, 6)}" for k, v in sorted(acct.holdings.items())),
                         "nav": _r(acct.nav, 2), "flow": _r(flow, 2), "invested": _r(acct.invested, 2),
                         "twr": _r(acct.twr, 6)})
        sig_rows.append({"date": day, **support})

    _append_csv(folder / "nav.csv", NAV_COLS, nav_rows)
    _append_csv(folder / "trades.csv", TRADE_COLS, trade_rows)
    _append_csv(folder / "signals.csv", ["date"] + [f["key"] for f in strategy.SUPPORT], sig_rows)
    acct.cash, acct.nav, acct.invested = _r(acct.cash, 6), _r(acct.nav, 6), _r(acct.invested, 6)
    acct_path.write_text(json.dumps(acct.__dict__, ensure_ascii=False, indent=1) + "\n")
    _write_meta(strategy, folder)
    return len(days)


def _write_meta(strategy, folder: Path) -> None:
    meta = {"id": strategy.ID, "name": strategy.NAME, "desc": strategy.DESC, "start": strategy.START,
            "capital": strategy.CAPITAL, "support": strategy.SUPPORT}
    text = json.dumps(meta, ensure_ascii=False, indent=1) + "\n"
    path = folder / "meta.json"
    if not path.exists() or path.read_text(encoding="utf-8") != text:
        path.write_text(text, encoding="utf-8")
