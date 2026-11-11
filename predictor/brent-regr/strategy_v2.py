"""Brent 区间策略 v2：BNO 单边做多 + 小仓位 + 事件/基本面开关。

价格规则沿用 v1（z-score 偏离 + 效率比震荡过滤），参数取 v1 网格的中间值而非最优值。
在其上叠加（任一触发即空仓、且不开新仓）：
- opec : OPEC+ 会议前 2 ~ 会后 1 个交易日。
- gpr  : 地缘风险指数 GPR 7 日均值 > 过去 250 日 90 分位（滞后 5 个交易日，因 GPR 每周更新）。
- ovx  : 原油隐含波动率 OVX > 过去 250 日 80 分位，或 5 日涨幅 > 20%。
- curve: 期限结构。60 日展期收益 = BNO 对数收益 − BZ=F 对数收益（BZ=F 换月跳空即合约价差）；
         ≤ 0（contango，供给过剩）时不做多。
仓位：按 10% 年化波动目标，w = min(0.10 / 20日实现波动, 0.5)；空仓部分按 13 周国债利率计息。
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from backtest import IS_END, Params, indicators, stats
from common import DATA, load
from events import opec_window

COST = 0.0005
BASE = Params(n=20, k=1.5, er_m=40, er_thr=0.3, stop_z=3.0, max_hold=20)
TARGET_VOL, MAX_W = 0.10, 0.5
SWITCHES = ("opec", "gpr", "ovx", "curve")


def load_gpr(index: pd.DatetimeIndex) -> pd.Series:
    g = pd.read_csv(DATA / "gpr_daily.csv", parse_dates=["date"]).set_index("date").GPRD_MA7
    return g.reindex(index, method="ffill").shift(5)


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    idx = df.index
    ovx = load("OVX").Close.reindex(idx).ffill()
    gpr = load_gpr(idx)
    bz = load("BZ_F").Close.reindex(idx).ffill()
    roll60 = np.log(df.Close).diff(60) - np.log(bz).diff(60)
    rv20 = np.log(df.Close).diff().rolling(20).std() * np.sqrt(252)
    cash = load("IRX").Close.reindex(idx).ffill().fillna(0) / 100 / 252
    return pd.DataFrame({
        "opec": opec_window(idx),
        "gpr": gpr > gpr.rolling(250).quantile(0.9),
        "ovx": (ovx > ovx.rolling(250).quantile(0.8)) | (ovx / ovx.shift(5) - 1 > 0.2),
        "curve": roll60 <= 0,
        "roll60": roll60,
        "rv20": rv20,
        "cash": cash,
    }, index=idx)


def signal(ind: pd.DataFrame, p: Params, block: np.ndarray) -> np.ndarray:
    z, er = ind.z.values, ind.er.values
    out = np.zeros(len(z))
    cur, held = 0, 0
    for i in range(len(z)):
        if np.isnan(z[i]) or np.isnan(er[i]):
            continue
        if cur:
            held += 1
            if z[i] >= 0 or z[i] <= -p.stop_z or held >= p.max_hold or block[i]:
                cur, held = 0, 0
        elif not block[i] and er[i] < p.er_thr and -p.stop_z < z[i] <= -p.k:
            cur, held = 1, 0
        out[i] = cur
    return out


def run(df: pd.DataFrame, feat: pd.DataFrame, p: Params, switches=(), sized=True) -> pd.DataFrame:
    block = np.zeros(len(df), dtype=bool)
    for s in switches:
        block |= feat[s].fillna(False).values.astype(bool)
    sig = pd.Series(signal(indicators(df.Close, p), p, block), index=df.index)
    w = (TARGET_VOL / feat.rv20).clip(upper=MAX_W) if sized else pd.Series(1.0, index=df.index)
    # 仓位在开仓当天确定，持有期间不随波动再调整，避免额外换手
    entry_w = w.where((sig != 0) & (sig.shift(1).fillna(0) == 0))
    weight = (sig * entry_w.ffill()).fillna(0).where(sig != 0, 0)
    held = weight.shift(1).fillna(0)
    oo = (df.Open.shift(-1) / df.Open - 1).fillna(0)
    cash = feat.cash
    ret = held * oo + (1 - held) * cash - held.diff().abs().fillna(held.abs()) * COST
    return pd.DataFrame({"pos": held, "ret": ret, "excess": ret - cash, "bh": oo, "cash": cash})


def summarize(r: pd.DataFrame) -> dict:
    s = stats(r.ret, r.pos)
    ex = r.excess
    s["ExSharpe"] = round(ex.mean() * 252 / (ex.std() * np.sqrt(252)), 2)
    s["AvgW%"] = round(r.pos[r.pos != 0].mean() * 100, 1) if (r.pos != 0).any() else 0
    return s


def split(r: pd.DataFrame):
    return r.loc[:IS_END], r.loc["2019-01-01":]


def ablation(df, feat):
    configs = [
        ("v1 满仓无开关", (), False),
        ("+ 波动率定仓", (), True),
        ("+ opec", ("opec",), True),
        ("+ gpr", ("gpr",), True),
        ("+ ovx", ("ovx",), True),
        ("+ curve", ("curve",), True),
        ("+ opec+gpr+ovx", ("opec", "gpr", "ovx"), True),
        ("+ 全部开关", SWITCHES, True),
    ]
    rows = []
    for name, sw, sized in configs:
        r = run(df, feat, BASE, sw, sized)
        for label, part in zip(("IS", "OOS"), split(r)):
            s = summarize(part)
            rows.append({"config": name, "period": label, **{k: s[k] for k in
                         ("CAGR%", "MaxDD%", "ExSharpe", "Exposure%", "AvgW%", "Trades", "Win%")}})
    return pd.DataFrame(rows)


def benchmark(df, feat, avg_w: float):
    """与策略平均持仓相同权重的 BNO 常数仓位 + 现金，用来区分 alpha 和油价 beta。"""
    oo = (df.Open.shift(-1) / df.Open - 1).fillna(0)
    ret = avg_w * oo + (1 - avg_w) * feat.cash
    r = pd.DataFrame({"ret": ret, "excess": ret - feat.cash})
    out = {}
    for label, part in zip(("IS", "OOS"), split(r)):
        s = stats(part.ret)
        s["ExSharpe"] = round(part.excess.mean() / part.excess.std() * np.sqrt(252), 2)
        out[label] = s
    return out


def robustness(df, feat):
    """v1 全部价格参数组合：加开关前后 OOS 超额 Sharpe 的对比。"""
    grid = {"n": [10, 20, 40], "k": [1.0, 1.5, 2.0], "er_m": [40, 60, 120],
            "er_thr": [0.2, 0.3, 0.4, 1.01], "stop_z": [3.0], "max_hold": [10, 20]}
    rows = []
    for vals in itertools.product(*grid.values()):
        p = Params(*vals)
        row = dict(p.__dict__)
        for tag, sw in (("sized", ()), ("all", SWITCHES)):
            is_, oos = split(run(df, feat, p, sw, True))
            row[f"IS_{tag}"] = summarize(is_)["ExSharpe"]
            row[f"OOS_{tag}"] = summarize(oos)["ExSharpe"]
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    pd.set_option("display.width", 200)
    df = load("BNO")
    feat = build_features(df)

    print("开关触发占比（2010-06 起交易日）:")
    print((feat[list(SWITCHES)].mean() * 100).round(1).to_string())

    ab = ablation(df, feat)
    print("\n== 消融：逐个叠加 ==")
    print(ab.to_string(index=False))

    final = run(df, feat, BASE, SWITCHES, True)
    final.to_csv(DATA.parent / "v2_daily.csv")
    avg_w = final.pos.mean()
    print(f"\n== 同平均仓位 ({avg_w:.1%}) 的 BNO 常数持有基准 ==")
    for k, v in benchmark(df, feat, avg_w).items():
        print(f"  {k}: {v}")

    g = final.groupby(final.index.year)
    print("\n== v2 全部开关 分年 ==")
    print(pd.DataFrame({
        "v2%": g.ret.apply(lambda s: ((1 + s).prod() - 1) * 100),
        "cash%": g.cash.apply(lambda s: ((1 + s).prod() - 1) * 100),
        "BNO%": g.bh.apply(lambda s: ((1 + s).prod() - 1) * 100),
        "exposure%": g.pos.apply(lambda s: (s != 0).mean() * 100),
    }).round(1).to_string())

    rb = robustness(df, feat)
    rb.to_csv(DATA.parent / "v2_robustness.csv", index=False)
    print(f"\n== 稳健性：{len(rb)} 组价格参数，加全部开关前后 ==")
    for per in ("IS", "OOS"):
        a, b = rb[f"{per}_sized"], rb[f"{per}_all"]
        print(f"  {per}: 中位超额Sharpe {a.median():+.2f} → {b.median():+.2f}；开关改善的比例 {(b > a).mean():.0%}")

    plot(final, ab)


def plot(final, ab):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return
    df = load("BNO")
    feat = build_features(df)
    v1 = run(df, feat, BASE, (), False)
    sized = run(df, feat, BASE, (), True)
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot((1 + v1.ret).cumprod(), label="v1 full size, no switches", alpha=0.7)
    ax.plot((1 + sized.ret).cumprod(), label="vol-sized, no switches", alpha=0.7)
    ax.plot((1 + final.ret).cumprod(), label="v2 vol-sized + all switches", lw=2)
    ax.plot((1 + final.cash).cumprod(), label="T-bill cash", ls=":", color="k")
    ax.axvline(pd.Timestamp("2019-01-01"), color="grey", ls="--", lw=1)
    ax.legend(loc="upper left")
    ax.set_title("Brent range strategy v2 (BNO long-only)")
    fig.tight_layout()
    fig.savefig(DATA.parent / "equity_v2.png", dpi=120)


if __name__ == "__main__":
    main()
