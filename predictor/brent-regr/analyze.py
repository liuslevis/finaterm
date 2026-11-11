"""Brent 是否存在区间震荡（均值回归）特征的统计检验。

检验项：
1. 方差比 VR(q)：VR<1 说明 q 日收益比随机游走更小 → 均值回归；VR>1 → 趋势。
2. 收益自相关：1/5/20 日收益与下一期同长度收益的相关系数。
3. Hurst 指数（按年滚动）：H<0.5 回归，H>0.5 趋势。
4. 价格偏离 N 日均线的 z-score 与未来 N 日收益的关系（区间策略的直接证据）。
"""
import numpy as np
import pandas as pd

from common import load


def variance_ratio(r: pd.Series, q: int) -> float:
    r = r.dropna()
    rq = r.rolling(q).sum().dropna()
    return rq.var() / (q * r.var())


def hurst(x: np.ndarray) -> float:
    lags = range(2, 50)
    tau = [np.std(x[lag:] - x[:-lag]) for lag in lags]
    return np.polyfit(np.log(list(lags)), np.log(tau), 1)[0]


def zscore_forward(px: pd.Series, n: int, h: int) -> pd.DataFrame:
    ma = px.rolling(n).mean()
    sd = px.rolling(n).std()
    z = (px - ma) / sd
    fwd = px.shift(-h) / px - 1
    df = pd.DataFrame({"z": z, "fwd": fwd}).dropna()
    bins = [-np.inf, -2, -1, 1, 2, np.inf]
    df["bucket"] = pd.cut(df.z, bins, labels=["<-2", "-2~-1", "-1~1", "1~2", ">2"])
    g = df.groupby("bucket", observed=True).fwd
    return pd.DataFrame({"n": g.size(), "mean_fwd%": g.mean() * 100, "hit_up%": g.apply(lambda s: (s > 0).mean() * 100)}).round(2)


def main(name: str = "BZ_F"):
    px = load(name).Close
    lp = np.log(px)
    r = lp.diff()

    print(f"== 方差比 VR(q)（全样本，{name}）==")
    for q in (2, 5, 10, 20, 60):
        print(f"  q={q:>3}: VR={variance_ratio(r, q):.3f}")

    print("\n== 收益自相关 corr(过去h日, 未来h日)，非重叠样本 ==")
    for h in (1, 5, 20):
        rh = lp.diff(h).iloc[::h]
        print(f"  h={h:>2}: {rh.autocorr():+.3f}  (n={rh.count()})")

    print("\n== 按年 Hurst 指数（log价格，滞后 2-50 日）==")
    yearly = lp.groupby(lp.index.year).apply(lambda s: hurst(s.values) if len(s) > 120 else np.nan)
    print(yearly.round(3).to_string())

    print("\n== 按年 VR(10) ==")
    vr = r.groupby(r.index.year).apply(lambda s: variance_ratio(s, 10))
    print(vr.round(3).to_string())

    for n, h in ((20, 10), (60, 20)):
        print(f"\n== z-score(相对{n}日均线) 分桶 → 未来{h}日收益 ==")
        print(zscore_forward(px, n, h).to_string())


if __name__ == "__main__":
    import sys
    main(sys.argv[1] if len(sys.argv) > 1 else "BZ_F")
