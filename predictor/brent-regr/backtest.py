"""Brent 区间（均值回归）策略回测。

价格序列：BNO（滚动持有 Brent 近月期货的 ETF，已包含换月收益）。
BZ=F 是未复权的近月拼接，换月跳空会制造虚假的均值回归，不用于信号与收益。

策略：
- 震荡识别：Kaufman 效率比 ER(m) = |P_t - P_{t-m}| / Σ|ΔP|，ER 低 = 来回走、没方向。
- 入场：z = (P - MA_n) / SD_n；z < -k 做多，z > k 做空（ETF 版只做多）；仅在 ER < er_thr 时开仓。
- 出场：z 回到 0（回归均线）、z 越过 ±stop_z（区间被突破）、持有超过 max_hold 天。
- 执行：t 日收盘出信号，t+1 日开盘成交，收益按开盘到开盘计算。

两种工具：
- futures：多空，收益 = BNO 收益 + 费率补回（近似裸期货滚动收益），单边成本 3bp。
- etf：仅做多 BNO，单边成本 5bp，空仓不计利息。
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass

import numpy as np
import pandas as pd

from common import DATA, load

IS_END = "2018-12-31"
BNO_FEE = 0.009 / 252
COST = {"futures": 0.0003, "etf": 0.0005}


@dataclass(frozen=True)
class Params:
    n: int = 20
    k: float = 1.5
    er_m: int = 60
    er_thr: float = 0.3
    stop_z: float = 3.5
    max_hold: int = 20


def indicators(px: pd.Series, p: Params) -> pd.DataFrame:
    ma = px.rolling(p.n).mean()
    sd = px.rolling(p.n).std()
    move = (px - px.shift(p.er_m)).abs()
    path = px.diff().abs().rolling(p.er_m).sum()
    return pd.DataFrame({"z": (px - ma) / sd, "er": move / path})


def positions(ind: pd.DataFrame, p: Params, allow_short: bool) -> np.ndarray:
    z, er = ind.z.values, ind.er.values
    pos = np.zeros(len(z))
    cur, held = 0, 0
    for i in range(len(z)):
        if np.isnan(z[i]) or np.isnan(er[i]):
            pos[i] = 0
            continue
        if cur != 0:
            held += 1
            back_to_mean = (cur > 0 and z[i] >= 0) or (cur < 0 and z[i] <= 0)
            broken = abs(z[i]) >= p.stop_z
            if back_to_mean or broken or held >= p.max_hold:
                cur, held = 0, 0
        if cur == 0 and er[i] < p.er_thr:
            if z[i] <= -p.k and z[i] > -p.stop_z:
                cur, held = 1, 0
            elif allow_short and z[i] >= p.k and z[i] < p.stop_z:
                cur, held = -1, 0
        pos[i] = cur
    return pos


def run(df: pd.DataFrame, p: Params, inst: str) -> pd.DataFrame:
    ind = indicators(df.Close, p)
    sig = pd.Series(positions(ind, p, allow_short=inst == "futures"), index=df.index)
    held = sig.shift(1).fillna(0)
    oo = df.Open.shift(-1) / df.Open - 1
    if inst == "futures":
        oo = oo + BNO_FEE
    gross = held * oo
    cost = held.diff().abs().fillna(held.abs()) * COST[inst]
    out = pd.DataFrame({"pos": held, "ret": (gross - cost).fillna(0), "bh": oo.fillna(0)})
    return out


def stats(ret: pd.Series, pos: pd.Series | None = None) -> dict:
    ret = ret.dropna()
    eq = (1 + ret).cumprod()
    yrs = len(ret) / 252
    vol = ret.std() * np.sqrt(252)
    d = {
        "CAGR%": (eq.iloc[-1] ** (1 / yrs) - 1) * 100,
        "Vol%": vol * 100,
        "Sharpe": ret.mean() * 252 / vol if vol > 0 else np.nan,
        "MaxDD%": (eq / eq.cummax() - 1).min() * 100,
    }
    if pos is not None:
        entries = (pos != 0) & (pos.shift(1).fillna(0) != pos)
        trade_id = entries.cumsum().where(pos != 0)
        tr = ret.groupby(trade_id).apply(lambda s: (1 + s).prod() - 1)
        d.update({
            "Exposure%": (pos != 0).mean() * 100,
            "Trades": int(entries.sum()),
            "Win%": (tr > 0).mean() * 100 if len(tr) else np.nan,
            "AvgTrade%": tr.mean() * 100 if len(tr) else np.nan,
        })
    return {k: round(v, 2) if isinstance(v, float) else v for k, v in d.items()}


GRID = {
    "n": [10, 20, 40],
    "k": [1.0, 1.5, 2.0],
    "er_m": [40, 60, 120],
    "er_thr": [0.2, 0.3, 0.4, 1.01],
    "stop_z": [3.0, 99.0],
    "max_hold": [10, 20],
}


def grid_search(df: pd.DataFrame, inst: str) -> pd.DataFrame:
    rows = []
    for vals in itertools.product(*GRID.values()):
        p = Params(*vals)
        r = run(df, p, inst)
        is_, oos = r.loc[:IS_END], r.loc[IS_END:].iloc[1:]
        s_is, s_oos = stats(is_.ret, is_.pos), stats(oos.ret, oos.pos)
        rows.append({**p.__dict__,
                     "IS_Sharpe": s_is["Sharpe"], "IS_CAGR%": s_is["CAGR%"], "IS_Trades": s_is["Trades"],
                     "OOS_Sharpe": s_oos["Sharpe"], "OOS_CAGR%": s_oos["CAGR%"], "OOS_MaxDD%": s_oos["MaxDD%"]})
    return pd.DataFrame(rows)


def yearly(r: pd.DataFrame) -> pd.DataFrame:
    g = r.groupby(r.index.year)
    return pd.DataFrame({
        "strat%": g.ret.apply(lambda s: ((1 + s).prod() - 1) * 100),
        "BNO%": g.bh.apply(lambda s: ((1 + s).prod() - 1) * 100),
        "exposure%": g.pos.apply(lambda s: (s != 0).mean() * 100),
    }).round(1)


def main():
    df = load("BNO")
    pd.set_option("display.width", 200)
    results = {}
    for inst in ("futures", "etf"):
        g = grid_search(df, inst)
        g.to_csv(DATA.parent / f"grid_{inst}.csv", index=False)
        g = g[g.IS_Trades >= 30]
        print(f"\n######## {inst}  共 {len(g)} 组参数（IS 交易≥30）########")
        print(f"OOS Sharpe>0 的比例: {(g.OOS_Sharpe > 0).mean():.0%}   "
              f"IS/OOS Sharpe 秩相关: {g.IS_Sharpe.corr(g.OOS_Sharpe, method='spearman'):+.2f}")
        print("按 ER 阈值分组的 OOS Sharpe 中位数（1.01=不过滤）:")
        print(g.groupby("er_thr")[["IS_Sharpe", "OOS_Sharpe"]].median().round(2).to_string())
        top = g.sort_values("IS_Sharpe", ascending=False).head(10)
        print("IS 最优 10 组:")
        print(top.to_string(index=False))

        best = Params(**{k: top.iloc[0][k] for k in Params.__dataclass_fields__})
        best = Params(int(best.n), best.k, int(best.er_m), best.er_thr, best.stop_z, int(best.max_hold))
        r = run(df, best, inst)
        results[inst] = (best, r)
        print(f"\n选定参数: {best}")
        for name, sl in (("IS 2010-2018", slice(None, IS_END)), ("OOS 2019-", slice("2019-01-01", None))):
            part = r.loc[sl]
            print(f"  {name:13} 策略 {stats(part.ret, part.pos)}")
            print(f"  {'':13} BNO持有 {stats(part.bh)}")
        print(yearly(r).to_string())

    plot(results)


def plot(results):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    fig, ax = plt.subplots(figsize=(11, 5))
    bh = None
    for inst, (p, r) in results.items():
        ax.plot((1 + r.ret).cumprod(), label=f"{inst} range strategy")
        bh = r.bh
    ax.plot((1 + bh).cumprod(), label="BNO buy & hold", alpha=0.6)
    ax.axvline(pd.Timestamp("2019-01-01"), color="grey", ls="--", lw=1)
    ax.text(pd.Timestamp("2019-02-01"), ax.get_ylim()[1] * 0.9, "out-of-sample →", color="grey")
    ax.set_yscale("log")
    ax.legend()
    ax.set_title("Brent range (mean-reversion) strategy vs BNO")
    fig.tight_layout()
    fig.savefig(DATA.parent / "equity.png", dpi=120)


if __name__ == "__main__":
    main()
