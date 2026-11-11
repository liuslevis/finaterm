"""Brent 区间 v2（复制自 predictor/brent-regr/strategy_v2.py）。

BNO 单边做多：z-score 偏离 + 效率比震荡过滤；OPEC+ 会议 / 地缘风险 / OVX / 期限结构 任一触发即空仓。
10% 波动目标定仓、单笔上限 50%，收盘出信号、次日开盘成交，空仓现金按 13 周国债计息。
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from strategies.opec import next_meeting, opec_window

ID = "brent-v2"
NAME = "Brent 区间 v2"
DESC = "BNO 单边做多 · 震荡市逢低买、回均线卖 · OPEC+/地缘/OVX/期限结构开关 · 10% 波动目标"
START = "2026-11-10"
CAPITAL = 10_000
CALENDAR = "BNO"
DATA = ["BNO", "BZ=F", "^OVX", "^IRX"]
NEED_GPR = True
FEE = 0.0005
FRACTIONAL = False
CASH_YIELD = True

N, K, ER_M, ER_THR, STOP_Z, MAX_HOLD = 20, 1.5, 40, 0.3, 3.0, 20
TARGET_VOL, MAX_W = 0.10, 0.5
SWITCHES = {"opec": "OPEC+ 会议", "gpr": "地缘风险", "ovx": "OVX 波动", "curve": "期限结构 contango"}

SUPPORT = [
    {"key": "status", "label": "信号", "fmt": "text"},
    {"key": "close", "label": "BNO 收盘", "fmt": "usd"},
    {"key": "buy_px", "label": f"买入线 MA{N}−{K}σ", "fmt": "usd"},
    {"key": "ma", "label": f"卖出线 MA{N}", "fmt": "usd"},
    {"key": "stop_px", "label": f"止损线 MA{N}−{STOP_Z:g}σ", "fmt": "usd"},
    {"key": "z", "label": f"z-score（< −{K} 买）", "fmt": "num2"},
    {"key": "er", "label": f"效率比 ER{ER_M}（< {ER_THR} 为震荡）", "fmt": "num2"},
    {"key": "rv20", "label": "20 日实现波动", "fmt": "pct1"},
    {"key": "target_w", "label": "目标仓位", "fmt": "pct1"},
    {"key": "opec", "label": "开关 · OPEC+ 会议窗口", "fmt": "bool"},
    {"key": "next_opec", "label": "下次 OPEC+ 会议", "fmt": "text"},
    {"key": "gpr", "label": "开关 · 地缘风险 GPR", "fmt": "bool"},
    {"key": "gpr_val", "label": "GPR 7日均 / 90分位", "fmt": "text"},
    {"key": "ovx", "label": "开关 · OVX", "fmt": "bool"},
    {"key": "ovx_val", "label": "OVX / 80分位 / 5日变化", "fmt": "text"},
    {"key": "curve", "label": "开关 · contango", "fmt": "bool"},
    {"key": "roll60", "label": "60 日展期收益（>0 升水）", "fmt": "pct1"},
]


def prepare(market) -> pd.DataFrame:
    df = market["BNO"]
    idx = df.index
    px = df.Close
    ma, sd = px.rolling(N).mean(), px.rolling(N).std()
    z = (px - ma) / sd
    er = (px - px.shift(ER_M)).abs() / px.diff().abs().rolling(ER_M).sum()

    ovx = market["^OVX"].Close.reindex(idx).ffill()
    ovx_thr = ovx.rolling(250).quantile(0.8)
    ovx_chg = ovx / ovx.shift(5) - 1
    gpr = market.gpr.reindex(idx, method="ffill").shift(5)
    gpr_thr = gpr.rolling(250).quantile(0.9)
    bz = market["BZ=F"].Close.reindex(idx).ffill()
    roll60 = np.log(px).diff(60) - np.log(bz).diff(60)
    rv20 = np.log(px).diff().rolling(20).std() * np.sqrt(252)

    f = pd.DataFrame({
        "close": px, "ma": ma, "buy_px": ma - K * sd, "stop_px": ma - STOP_Z * sd, "z": z, "er": er,
        "rv20": rv20, "target_w": (TARGET_VOL / rv20).clip(upper=MAX_W),
        "opec": opec_window(idx), "gpr": gpr > gpr_thr,
        "ovx": (ovx > ovx_thr) | (ovx_chg > 0.2), "curve": roll60 <= 0,
        "gpr_v": gpr, "gpr_t": gpr_thr, "ovx_v": ovx, "ovx_t": ovx_thr, "ovx_c": ovx_chg, "roll60": roll60,
    }, index=idx)
    sig, status = _signal(f)
    f["sig"], f["status"] = sig, status
    return f


def _signal(f: pd.DataFrame):
    z, er = f.z.values, f.er.values
    names = [[SWITCHES[s] for s in SWITCHES if bool(f[s].iloc[i])] for i in range(len(f))]
    sig = np.zeros(len(f))
    status = [""] * len(f)
    cur, held = 0, 0
    for i in range(len(f)):
        if np.isnan(z[i]) or np.isnan(er[i]):
            status[i] = "数据不足"
            continue
        if cur:
            held += 1
            exit_reason = ("回到均线" if z[i] >= 0 else f"跌破止损 z≤−{STOP_Z:g}" if z[i] <= -STOP_Z
                           else f"持有满 {MAX_HOLD} 日" if held >= MAX_HOLD
                           else f"开关：{'、'.join(names[i])}" if names[i] else "")
            if exit_reason:
                cur, held = 0, 0
                status[i] = f"平仓：{exit_reason}"
            else:
                status[i] = f"持有第 {held} 日"
        elif -STOP_Z < z[i] <= -K and er[i] < ER_THR:
            if names[i]:
                status[i] = f"观望：买点被开关拦截（{'、'.join(names[i])}）"
            else:
                cur, held = 1, 0
                status[i] = f"开仓：z {z[i]:.2f} ≤ −{K}，ER {er[i]:.2f} < {ER_THR}"
        else:
            status[i] = ("观望：开关触发（" + "、".join(names[i]) + "）" if names[i]
                         else f"观望：ER {er[i]:.2f} ≥ {ER_THR}（趋势市）" if er[i] >= ER_THR
                         else f"观望：z {z[i]:.2f} 未到 −{K}")
        sig[i] = cur
    return sig, status


def contribution(day) -> float:
    return 0.0


def on_open(day, ctx, acct) -> list[dict]:
    return []


def on_close(day, ctx: pd.DataFrame, acct):
    row = ctx.loc[day]
    held = acct.shares("BNO") > 0
    orders = []
    if row.sig and not held and pd.notna(row.target_w):
        reason = row.status if row.status.startswith("开仓") else f"建仓（跟随已有信号，{row.status}）"
        orders.append({"symbol": "BNO", "side": "buy", "weight": round(float(row.target_w), 4), "reason": reason})
    elif not row.sig and held:
        orders.append({"symbol": "BNO", "side": "sell", "shares": "all", "reason": row.status})

    def num(x, nd):
        return None if pd.isna(x) else round(float(x), nd)

    support = {
        "status": row.status, "close": num(row.close, 2), "buy_px": num(row.buy_px, 2), "ma": num(row.ma, 2),
        "stop_px": num(row.stop_px, 2), "z": num(row.z, 3), "er": num(row.er, 3), "rv20": num(row.rv20, 4),
        "target_w": num(row.target_w, 4), "opec": int(bool(row.opec)), "next_opec": next_meeting(day),
        "gpr": int(bool(row.gpr)), "gpr_val": f"{row.gpr_v:.0f} / {row.gpr_t:.0f}",
        "ovx": int(bool(row.ovx)), "ovx_val": f"{row.ovx_v:.1f} / {row.ovx_t:.1f} / {row.ovx_c:+.0%}",
        "curve": int(bool(row.curve)), "roll60": num(row.roll60, 4),
    }
    return orders, support
