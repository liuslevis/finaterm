"""李大霄 A股顶/底预测 准确率(precision) / 召回率(recall) 回测.

Inputs : sh000001.csv (上证综指日线, akshare), calls.csv (人工整理的带日期预测)
Outputs: out/*.png, out/calls_scored.csv, out/pivots.csv, out/summary.json
Run from this directory (repo-root akshare/ clone shadows the pip package).
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = Path(__file__).parent
OUT = HERE / "out"
OUT.mkdir(exist_ok=True)
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False

H = 250          # 评估期: 约12个月交易日
TOL = 0.03       # 点位守住容差
WIN = 60         # 拐点匹配: 喊话最多早于拐点60交易日(约3个月)
LAG = 20         # 拐点匹配: 喊话最多晚于拐点20交易日(约1个月)
PX_TOL = 0.10    # 拐点匹配价格容差
START, END = "2012-01-01", "2026-10-30"


def load_index():
    if not (HERE / "sh000001.csv").exists():
        import akshare as ak
        ak.stock_zh_index_daily(symbol="sh000001").to_csv(HERE / "sh000001.csv", index=False)
    df = pd.read_csv(HERE / "sh000001.csv", parse_dates=["date"]).set_index("date")
    return df.loc["2010-01-01":END]


def zigzag(df, thr):
    """High/low zigzag. Returns confirmed pivots [(date, type, price)]; last leg dropped."""
    hi, lo, idx = df.high.values, df.low.values, df.index
    piv, trend = [], 0
    ext_i, ext_p = 0, hi[0]
    lo_i, lo_p, hi_i, hi_p = 0, lo[0], 0, hi[0]
    for i in range(1, len(df)):
        if trend == 0:
            if hi[i] > hi_p: hi_i, hi_p = i, hi[i]
            if lo[i] < lo_p: lo_i, lo_p = i, lo[i]
            if hi_p / lo_p - 1 >= thr:
                trend = 1 if lo_i < hi_i else -1
                piv.append((lo_i, "bottom", lo_p) if trend == 1 else (hi_i, "top", hi_p))
                ext_i, ext_p = (hi_i, hi_p) if trend == 1 else (lo_i, lo_p)
        elif trend == 1:
            if hi[i] > ext_p: ext_i, ext_p = i, hi[i]
            elif lo[i] <= ext_p * (1 - thr):
                piv.append((ext_i, "top", ext_p)); trend, ext_i, ext_p = -1, i, lo[i]
        else:
            if lo[i] < ext_p: ext_i, ext_p = i, lo[i]
            elif hi[i] >= ext_p * (1 + thr):
                piv.append((ext_i, "bottom", ext_p)); trend, ext_i, ext_p = 1, i, hi[i]
    return pd.DataFrame([(idx[i], t, p) for i, t, p in piv], columns=["date", "type", "price"])


def score_calls(df, calls, pivots, win=WIN):
    dates = df.index
    rows = []
    for c in calls.itertuples():
        i = dates.searchsorted(pd.Timestamp(c.date))  # 首个 >= 发言日的交易日
        i = min(i, len(dates) - 1)
        ref = df.close.iloc[max(i - 1, 0)] if dates[i] > pd.Timestamp(c.date) else df.close.iloc[i]
        level = c.level if pd.notna(c.level) else round(ref)
        fwd = df.iloc[i + 1:i + 1 + H]
        n = len(fwd)
        mature = n >= H
        bottom = c.type == "bottom"
        if bottom:
            worst = fwd.low.min() if n else np.nan
            breach = worst < level * (1 - TOL)
            exc = worst / level - 1
        else:
            worst = fwd.high.max() if n else np.nan
            breach = worst > level * (1 + TOL)
            exc = worst / level - 1
        # A 点位守住: 已破=错; 未破但不足12个月=待定
        hold = 0 if breach else (1 if mature else np.nan)
        # B 拐点匹配: 只与"下一个"同类拐点比较(允许滞后LAG日)，不能跨过它去匹配更远的拐点
        same = pivots[pivots.type == c.type]
        pos = dates.searchsorted(same.date)
        nxt = np.flatnonzero(pos >= i - LAG)
        tp, mp = 0, ""
        if len(nxt):
            k = nxt[0]
            if pos[k] - i <= win and abs(same.price.iloc[k] / ref - 1) <= PX_TOL:
                tp, mp = 1, same.date.iloc[k].date().isoformat()
        # C 方向正确 (12个月远期收益)
        r6 = df.close.iloc[i + 125] / ref - 1 if i + 125 < len(df) else np.nan
        r12 = df.close.iloc[i + H] / ref - 1 if i + H < len(df) else np.nan
        dir_ok = np.nan if np.isnan(r12) else int((r12 > 0) if bottom else (r12 < 0))
        rows.append(dict(id=c.id, date=c.date, type=c.type, name=c.name, level=level, ref_close=round(ref, 1),
                         worst_12m=round(worst, 1), worst_vs_level=round(exc, 4), A_hold=hold,
                         B_turn=tp, matched_pivot=mp,
                         r6=r6, r12=r12, C_dir=dir_ok, confidence=c.confidence, ex_post=c.ex_post))
    return pd.DataFrame(rows)


def recall(sc, pivots):
    """真实拐点被'召回' = 至少有一条同类喊话按B规则匹配到它."""
    out = []
    for p in pivots.itertuples():
        d = p.date.date().isoformat()
        m = sc[(sc.type == p.type) & (sc.matched_pivot == d)]
        out.append(dict(date=d, type=p.type, price=round(p.price, 1), called=int(len(m) > 0), by=";".join(m.id)))
    return pd.DataFrame(out)


def base_rates(df):
    """Naive caller: 每天宣称'近20日低点(高点)就是底(顶)'，点位守住12个月的概率 & 12个月收益>0 概率."""
    s = df.loc[START:]
    lo20, hi20 = df.low.rolling(20).min(), df.high.rolling(20).max()
    fl = df.low[::-1].rolling(H, min_periods=H).min()[::-1].shift(-1)
    fh = df.high[::-1].rolling(H, min_periods=H).max()[::-1].shift(-1)
    r12 = df.close.shift(-H) / df.close - 1
    m = s.index[s.index.isin(fl.dropna().index)]
    dd = df.close / df.high.rolling(250).max() - 1
    md = m[dd[m] <= -0.15]  # 条件基准: 距1年高点回撤>=15%的日子(李大霄喊底的典型情境)
    return dict(
        dd15_days=int(len(md)),
        dd15_bottom_hold=float((fl[md] >= lo20[md] * (1 - TOL)).mean()),
        dd15_up12=float((r12[md] > 0).mean()),
        dd15_mean_r12=float(r12[md].mean()),
        bottom_hold=float((fl[m] >= lo20[m] * (1 - TOL)).mean()),
        top_hold=float((fh[m] <= hi20[m] * (1 + TOL)).mean()),
        up12=float((r12[m] > 0).mean()),
        down12=float((r12[m] < 0).mean()),
        mean_r12=float(r12[m].mean()),
    )


def events(sc):
    """同类型、相隔<=60交易日的连续喊话合并为一个事件；以首次喊话衡量点位，任一命中计拐点."""
    sc = sc.sort_values("date").reset_index(drop=True)
    ev, last = [], {}  # last[type] = (date of latest call, event index)
    for r in sc.itertuples():
        d = pd.Timestamp(r.date)
        if r.type in last and (d - last[r.type][0]).days <= 90:
            k = last[r.type][1]; ev[k].append(r)
        else:
            ev.append([r]); k = len(ev) - 1
        last[r.type] = (d, k)
    out = []
    for g in ev:
        f = g[0]
        out.append(dict(first=f.id, ids=";".join(x.id for x in g), type=f.type, date=f.date, n=len(g),
                        A_hold_first=f.A_hold, B_turn_any=int(any(x.B_turn for x in g)), C_dir_first=f.C_dir))
    return pd.DataFrame(out)


def prf(prec, rec):
    return 2 * prec * rec / (prec + rec) if prec + rec else 0.0


def main():
    df = load_index()
    calls = pd.read_csv(HERE / "calls.csv", encoding="utf-8-sig", dtype={"level": float})
    piv = {thr: zigzag(df, thr) for thr in (0.15, 0.20)}
    for k in piv:
        piv[k] = piv[k][(piv[k].date >= START) & (piv[k].date <= END)].reset_index(drop=True)
    sc = score_calls(df, calls, piv[0.20])
    sc15 = score_calls(df, calls, piv[0.15])
    sc["B_turn15"] = sc15.B_turn
    sc.to_csv(OUT / "calls_scored.csv", index=False, encoding="utf-8-sig")
    ev = events(sc)
    ev.to_csv(OUT / "events.csv", index=False, encoding="utf-8-sig")

    summary = {"params": dict(H=H, TOL=TOL, WIN=WIN, LAG=LAG, PX_TOL=PX_TOL, start=START, end=END)}
    for t in ("bottom", "top", "all"):
        s = sc if t == "all" else sc[sc.type == t]
        e = ev if t == "all" else ev[ev.type == t]
        summary[t] = dict(
            n_calls=len(s),
            A_hold=[int(s.A_hold.sum()), int(s.A_hold.notna().sum())],
            B_turn20=[int(s.B_turn.sum()), len(s)],
            B_turn15=[int(s.B_turn15.sum()), len(s)],
            C_dir=[int(s.C_dir.sum()), int(s.C_dir.notna().sum())],
            mean_r12=float(s.r12.mean()), median_r12=float(s.r12.median()),
            n_events=len(e),
            ev_A_hold_first=[int(e.A_hold_first.sum()), int(e.A_hold_first.notna().sum())],
            ev_B_turn_any=[int(e.B_turn_any.sum()), len(e)],
            ev_C_dir_first=[int(e.C_dir_first.sum()), int(e.C_dir_first.notna().sum())],
        )
    rec = {}
    for thr in (0.15, 0.20):
        for w in (WIN, 120):
            r = recall(score_calls(df, calls, piv[thr], w), piv[thr])
            r.to_csv(OUT / f"recall_zz{int(thr*100)}_w{w}.csv", index=False, encoding="utf-8-sig")
            rec[f"zz{int(thr*100)}_w{w}"] = {t: [int(r[r.type == t].called.sum()), int((r.type == t).sum())]
                                             for t in ("bottom", "top")} | {"all": [int(r.called.sum()), len(r)]}
    summary["recall"] = rec
    summary["base"] = b = base_rates(df)
    from scipy.stats import binom
    pv = lambda k, n, p: float(binom.sf(k - 1, n, p))
    summary["pvalues"] = {
        "bottom_A_vs_dd15": pv(*summary["bottom"]["A_hold"], b["dd15_bottom_hold"]),
        "bottom_C_vs_dd15": pv(*summary["bottom"]["C_dir"], b["dd15_up12"]),
        "bottom_evC_vs_dd15": pv(*summary["bottom"]["ev_C_dir_first"], b["dd15_up12"]),
        "top_C_vs_uncond": pv(*summary["top"]["C_dir"], b["down12"]),
        "top_evC_vs_uncond": pv(*summary["top"]["ev_C_dir_first"], b["down12"]),
    }
    for thr in piv:
        piv[thr].to_csv(OUT / f"pivots_zz{int(thr*100)}.csv", index=False, encoding="utf-8-sig")
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding="utf-8")
    charts(df, sc, piv[0.20], summary)
    print(json.dumps(summary, ensure_ascii=False, indent=1))
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
    print(sc[["id", "date", "name", "level", "ref_close", "worst_12m", "worst_vs_level", "A_hold", "B_turn", "B_turn15",
              "matched_pivot", "r12", "C_dir"]].to_string())
    print(ev.to_string())
    for k in ("zz20_w60", "zz15_w60"):
        print(k); print(pd.read_csv(OUT / f"recall_{k}.csv").to_string())


def charts(df, sc, piv, summary):
    s = df.loc["2011-06-01":]
    fig, ax = plt.subplots(figsize=(16, 7))
    ax.plot(s.index, s.close, color="#555", lw=0.8, label="上证综指 收盘")
    ax.plot(piv.date, piv.price, color="#999", lw=1, ls="--", label="20% zigzag 拐点")
    for r in sc.itertuples():
        d = pd.Timestamp(r.date); y = r.ref_close
        ok = r.A_hold == 1
        pend = pd.isna(r.A_hold)
        col = "#2a9d8f" if ok else ("#e9c46a" if pend else "#e63946")
        mk = "^" if r.type == "bottom" else "v"
        ax.scatter(d, y, marker=mk, s=90, color=col, edgecolor="k", zorder=5)
        ax.annotate(r.name.split("(")[0], (d, y), xytext=(0, -16 if r.type == "bottom" else 10),
                    textcoords="offset points", fontsize=7, ha="center", rotation=0)
    ax.scatter([], [], marker="^", color="#2a9d8f", edgecolor="k", label="点位守住12个月")
    ax.scatter([], [], marker="^", color="#e63946", edgecolor="k", label="点位被击穿(>3%)")
    ax.scatter([], [], marker="^", color="#e9c46a", edgecolor="k", label="待定(不足12个月)")
    ax.set_title("李大霄 顶/底喊话 vs 上证综指 (2012–2026.10)  ▲=底  ▼=顶")
    ax.legend(loc="upper left", fontsize=8); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(OUT / "fig1_calls_timeline.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(10, 5))
    b = sc[sc.type == "bottom"].sort_values("date")
    ax.barh(b.name, b.worst_vs_level * 100, color=["#2a9d8f" if v >= -TOL else "#e63946" for v in b.worst_vs_level])
    ax.axvline(-TOL * 100, color="k", ls=":")
    ax.set_xlabel("喊底后12个月内最低点 相对 所喊点位 (%)"); ax.invert_yaxis(); ax.grid(alpha=0.3, axis="x")
    ax.set_title("底部喊话：之后被击穿的幅度")
    fig.tight_layout(); fig.savefig(OUT / "fig2_bottom_breach.png", dpi=130); plt.close(fig)

    fig, ax = plt.subplots(figsize=(9, 5))
    labels, vals, base = [], [], summary["base"]
    for t, cn in (("bottom", "底"), ("top", "顶")):
        a, bb, c = summary[t]["A_hold"], summary[t]["B_turn20"], summary[t]["C_dir"]
        labels += [f"{cn}:点位守住", f"{cn}:拐点匹配", f"{cn}:12月方向"]
        vals += [a[0] / a[1], bb[0] / bb[1], c[0] / c[1]]
    # 底: 条件基准(回撤>=15%的日子)；顶: 无条件基准
    bases = [base["dd15_bottom_hold"], np.nan, base["dd15_up12"], base["top_hold"], np.nan, base["down12"]]
    x = np.arange(len(labels))
    ax.bar(x - 0.2, vals, 0.4, label="李大霄", color="#457b9d")
    ax.bar(x + 0.2, bases, 0.4, label="随机基准(底:回撤≥15%时每日喊; 顶:每日喊)", color="#ccc")
    ax.set_xticks(x, labels, rotation=20); ax.set_ylim(0, 1); ax.legend(); ax.grid(alpha=0.3, axis="y")
    ax.set_title("逐条喊话准确率 vs 随机基准")
    fig.tight_layout(); fig.savefig(OUT / "fig3_precision_vs_base.png", dpi=130); plt.close(fig)


if __name__ == "__main__":
    main()
