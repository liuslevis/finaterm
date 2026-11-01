"""Explanation study, stage 2 — does the show describe/explain the moves around it?

Windows (New York time), A = air date, P = previous trading session:

    prev      close(P-1) -> close(P)   fully known before the show; tested against the recap
    gap       close(P)   -> open(A)    futures during the show ≈ this window
    intraday  open(A)    -> close(A)   after the show (it ends 10:00); the show cannot see it
    ret0      close(P)   -> close(A)   = gap ⊕ intraday, "当日收盘"

Everything here is *contemporaneous* (explanation, not prediction), so the usual
look-ahead rules do not apply — but the date alignment does: A = title date − 1
calendar day.  The script also re-runs the key test on the title date to show how
much a one-day misalignment destroys.

Output: reports/explain_metrics.json + data/explain_panel.csv.
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict

import akshare as ak
import numpy as np
import pandas as pd
from scipy import stats

from common import DATA, FILES, REPORTS
from make_brief import numeric_features

EXPL = DATA / "explain"
RNG = np.random.default_rng(7)
MOVE_MAP = {"sharply_down": -2, "down": -1, "flat": 0, "up": 1, "sharply_up": 2}
DIR = {"up": 1, "down": -1, "flat": 0}


# ----------------------------------------------------------------- market data
def market() -> pd.DataFrame:
    cache = DATA / "explain_market.csv"
    if cache.is_file():
        return pd.read_csv(cache)
    qqq = pd.read_csv(FILES["prices"])[["date", "open", "close"]]
    qqq.columns = ["date", "qqq_open", "qqq_close"]
    spy = ak.stock_us_daily(symbol="SPY", adjust="")[["date", "open", "close"]]
    spy.columns = ["date", "spy_open", "spy_close"]
    ust = ak.bond_zh_us_rate(start_date="20260601")
    ust = ust.iloc[:, [0, 7, 9]]
    ust.columns = ["date", "us2y", "us10y"]
    brent = ak.futures_foreign_hist(symbol="OIL")[["date", "close"]].rename(columns={"close": "brent"})
    wti = ak.futures_foreign_hist(symbol="CL")[["date", "close"]].rename(columns={"close": "wti"})
    frames = [qqq, spy, ust, brent, wti]
    for f in frames:
        f["date"] = pd.to_datetime(f["date"]).dt.strftime("%Y-%m-%d")
    df = frames[0]
    for f in frames[1:]:
        df = df.merge(f, on="date", how="left")
    df = df[df["date"] >= "2026-06-01"].sort_values("date").reset_index(drop=True)
    df.to_csv(cache, index=False)
    return df


def windows(mkt: pd.DataFrame, air: str) -> dict | None:
    idx = mkt.index[mkt["date"] == air]
    if len(idx) == 0:
        return None
    i = int(idx[0])
    if i < 2:
        return None
    c, o = mkt["qqq_close"], mkt["qqq_open"]
    sc, so = mkt["spy_close"], mkt["spy_open"]
    p, pp = i - 1, i - 2
    return {
        "air_date": air,
        "prev_date": mkt["date"].iloc[p],
        "qqq_prev": c[p] / c[pp] - 1, "spy_prev": sc[p] / sc[pp] - 1,
        "qqq_gap": o[i] / c[p] - 1, "spy_gap": so[i] / sc[p] - 1,
        "qqq_intra": c[i] / o[i] - 1, "spy_intra": sc[i] / so[i] - 1,
        "qqq_ret0": c[i] / c[p] - 1, "spy_ret0": sc[i] / sc[p] - 1,
        "qqq_next": c[i + 1] / c[i] - 1 if i + 1 < len(mkt) else np.nan,
        "d10y_prev": (mkt["us10y"].iloc[p] - mkt["us10y"].iloc[pp]) * 100,
        "d2y_prev": (mkt["us2y"].iloc[p] - mkt["us2y"].iloc[pp]) * 100,
        "d10y_air": (mkt["us10y"].iloc[i] - mkt["us10y"].iloc[p]) * 100,
        "brent_prev": mkt["brent"].iloc[p] / mkt["brent"].iloc[pp] - 1,
        "wti_prev": mkt["wti"].iloc[p] / mkt["wti"].iloc[pp] - 1,
        "brent_air": mkt["brent"].iloc[i] / mkt["brent"].iloc[p] - 1,
    }


# ----------------------------------------------------------------- show data
def dir_of(block: dict | None) -> float:
    if not isinstance(block, dict):
        return np.nan
    return DIR.get(str(block.get("direction", "")).lower(), np.nan)


def num_of(block: dict | None, key: str = "pct") -> float:
    if not isinstance(block, dict):
        return np.nan
    v = block.get(key)
    try:
        v = float(v)
    except (TypeError, ValueError):
        return np.nan
    d = dir_of(block)
    # ASR/LLM sometimes drops the sign; trust the stated direction for the sign
    if d == d and d != 0 and v != 0 and np.sign(v) != d:
        v = abs(v) * d
    return v


def show_rows() -> list[dict]:
    episodes = pd.read_csv(FILES["episodes"])
    scores = pd.read_csv(DATA / "llm_scores_deepseek_brief_r2.csv")
    scores["preopen"] = scores["preopen_move"].map(MOVE_MAP)
    pre = scores.groupby("bvid")[["preopen", "sentiment", "p_up_1d"]].mean()
    rows = []
    for r in episodes.itertuples(index=False):
        path = EXPL / f"{r.bvid}.json"
        if not path.is_file():
            continue
        ex = json.loads(path.read_text(encoding="utf-8"))["extract"]
        brief = json.loads((DATA / "briefs" / f"{r.bvid}.json").read_text(encoding="utf-8"))["brief"]
        nf = numeric_features(brief)
        transcript = open(r.transcript, encoding="utf-8", errors="replace").read()
        ps, tm = ex.get("prev_session") or {}, ex.get("this_morning") or {}
        co = ex.get("cash_open") or {}
        rows.append({
            "bvid": r.bvid, "title_date": r.show_date, "title": r.title,
            "minutes": 5 * transcript.count("\n[") + 5 * transcript.startswith("["),
            "weekday_said": ex.get("air_weekday"),
            "prev_described": bool(ps.get("described")),
            "s_prev_spx_dir": dir_of(ps.get("spx")), "s_prev_spx_pct": num_of(ps.get("spx")),
            "s_prev_ndx_dir": dir_of(ps.get("nasdaq")), "s_prev_ndx_pct": num_of(ps.get("nasdaq")),
            "s_prev_10y_dir": dir_of(ps.get("ust10y")), "s_prev_10y_bp": num_of(ps.get("ust10y"), "bp"),
            "s_prev_oil_dir": dir_of(ps.get("oil")), "s_prev_oil_pct": num_of(ps.get("oil")),
            "prev_reasons": ps.get("reasons") or [], "prev_quote": ps.get("quote", ""),
            "s_fut_spx_dir": dir_of(tm.get("spx_fut")), "s_fut_spx_pct": num_of(tm.get("spx_fut")),
            "s_fut_ndx_dir": dir_of(tm.get("nasdaq_fut")), "s_fut_ndx_pct": num_of(tm.get("nasdaq_fut")),
            "s_fut_10y_dir": dir_of(tm.get("ust10y")), "s_fut_10y_bp": num_of(tm.get("ust10y"), "bp"),
            "s_fut_oil_dir": dir_of(tm.get("oil")), "s_fut_oil_pct": num_of(tm.get("oil")),
            "trajectory": tm.get("trajectory"), "fut_reasons": tm.get("reasons") or [],
            "fut_quote": tm.get("quote", ""),
            "open_observed": bool(co.get("observed")), "s_open_dir": dir_of(co),
            "brf_equity_futures": nf.get("brf_equity_futures", np.nan),
            "brf_composite": nf.get("brf_composite", np.nan),
            "brf_sentiment": nf.get("brf_sentiment", np.nan),
            "llm_preopen": pre["preopen"].get(r.bvid, np.nan),
            "llm_sentiment": pre["sentiment"].get(r.bvid, np.nan),
            "llm_p_up_1d": pre["p_up_1d"].get(r.bvid, np.nan),
        })
    return rows


def best_number(row: pd.Series, ndx: str, spx: str, scale: float = 1.0) -> float:
    """Nasdaq figure if spoken, else S&P figure × scale (QQQ beta to SPY ≈ 1.2)."""
    if row[ndx] == row[ndx]:
        return row[ndx]
    if row[spx] == row[spx]:
        return row[spx] * scale
    return np.nan


# ----------------------------------------------------------------- statistics
def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z * z / n
    mid = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (mid - half, mid + half)


def corr(x, y, reps: int = 5000) -> dict:
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    x, y = x[m], y[m]
    n = len(x)
    if n < 6 or np.std(x) == 0 or np.std(y) == 0:
        return {"n": int(n)}
    r = float(np.corrcoef(x, y)[0, 1])
    rho = float(stats.spearmanr(x, y)[0])
    # daily, non-overlapping windows -> iid permutation is the right null
    null = np.array([np.corrcoef(x, RNG.permutation(y))[0, 1] for _ in range(reps)])
    p = float((np.sum(np.abs(null) >= abs(r)) + 1) / (reps + 1))
    boots = []
    for _ in range(2000):
        k = RNG.integers(0, n, n)
        if np.std(x[k]) > 0 and np.std(y[k]) > 0:
            boots.append(np.corrcoef(x[k], y[k])[0, 1])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    slope = float(np.polyfit(x, y, 1)[0])
    return {"n": int(n), "r": r, "r2": r * r, "rho": rho, "p_perm": p,
            "ci": [float(lo), float(hi)], "slope": slope}


def hit(stated_dir, actual, flat_band: float = 0.0) -> dict:
    s, a = np.asarray(stated_dir, float), np.asarray(actual, float)
    m = np.isfinite(s) & np.isfinite(a) & (s != 0)
    n = int(m.sum())
    if n == 0:
        return {"n": 0}
    k = int(np.sum(np.sign(s[m]) == np.sign(a[m])))
    lo, hi = wilson(k, n)
    p = float(stats.binomtest(k, n, 0.5, alternative="greater").pvalue)
    return {"n": n, "hits": k, "rate": k / n, "ci": [lo, hi], "p_binom": p}


def mae(x, y) -> float:
    x, y = np.asarray(x, float), np.asarray(y, float)
    m = np.isfinite(x) & np.isfinite(y)
    return float(np.mean(np.abs(x[m] - y[m]))) if m.any() else np.nan


# ----------------------------------------------------------------- reasons audit
REASON_CHECK = {
    # category -> (market column on the PREVIOUS session, sign that "weighed" on stocks implies)
    "rates": ("d10y_prev", +1),       # rates weighed  => 10y up
    "fed": ("d2y_prev", +1),          # hawkish Fed weighed => 2y up
    "oil_energy": ("brent_prev", +1), # oil weighed => oil up
}


def audit_reasons(panel: pd.DataFrame, which: str) -> dict:
    out: dict = {"categories": Counter(), "checks": defaultdict(lambda: {"n": 0, "consistent": 0}),
                 "effect_vs_tape": {"n": 0, "consistent": 0}}
    tape = "qqq_prev" if which == "prev_reasons" else "qqq_gap"
    for row in panel.itertuples(index=False):
        reasons = getattr(row, which) or []
        signs = []
        for rsn in reasons:
            if not isinstance(rsn, dict):
                continue
            cat = rsn.get("category", "other")
            eff = {"lifted": -1, "weighed": +1}.get(rsn.get("effect"), 0)
            out["categories"][cat] += 1
            signs.append(-eff)
            if which == "prev_reasons" and cat in REASON_CHECK and eff:
                col, sgn = REASON_CHECK[cat]
                val = getattr(row, col)
                if val == val and val != 0:
                    out["checks"][cat]["n"] += 1
                    out["checks"][cat]["consistent"] += int(np.sign(val) == sgn * eff)
        actual = getattr(row, tape)
        net = np.sign(sum(signs)) if signs else 0
        if net and actual == actual:
            out["effect_vs_tape"]["n"] += 1
            out["effect_vs_tape"]["consistent"] += int(np.sign(actual) == net)
    out["categories"] = dict(out["categories"].most_common())
    out["checks"] = {k: {**v, "rate": v["consistent"] / v["n"] if v["n"] else None}
                     for k, v in out["checks"].items()}
    e = out["effect_vs_tape"]
    e["rate"] = e["consistent"] / e["n"] if e["n"] else None
    return out


# ----------------------------------------------------------------- main
def main() -> int:
    mkt = market()
    shows = pd.DataFrame(show_rows())
    shows["air_date"] = (pd.to_datetime(shows["title_date"]) - pd.Timedelta(days=1)).dt.strftime("%Y-%m-%d")
    shows["air_weekday"] = pd.to_datetime(shows["air_date"]).dt.day_name().str.lower()
    shows["weekday_ok"] = shows["weekday_said"].eq(shows["air_weekday"])

    def attach(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
        recs = [windows(mkt, d) or {"air_date": d} for d in df[date_col]]
        w = pd.DataFrame(recs).drop(columns=["air_date"])
        return pd.concat([df.reset_index(drop=True), w], axis=1)

    panel = attach(shows, "air_date")
    panel_title = attach(shows, "title_date")       # the (wrong) title-date alignment, for contrast

    for p in (panel, panel_title):
        p["s_prev_pct"] = p.apply(best_number, axis=1, args=("s_prev_ndx_pct", "s_prev_spx_pct", 1.2))
        p["s_fut_pct"] = p.apply(best_number, axis=1, args=("s_fut_ndx_pct", "s_fut_spx_pct", 1.2))
        p["s_prev_dir"] = p["s_prev_ndx_dir"].fillna(p["s_prev_spx_dir"])
        p["s_fut_dir"] = p["s_fut_ndx_dir"].fillna(p["s_fut_spx_dir"])

    panel.drop(columns=["prev_reasons", "fut_reasons"]).to_csv(DATA / "explain_panel.csv", index=False)

    # one row per air date for regressions (9/16 has two episodes)
    num_cols = [c for c in panel.columns if panel[c].dtype.kind in "fb" and c not in ("weekday_ok",)]
    daily = panel.groupby("air_date", as_index=False)[num_cols].mean()

    M: dict = {"n_episodes": int(len(panel)), "n_air_dates": int(daily["air_date"].nunique())}

    # §1 alignment
    M["alignment"] = {
        "weekday_said_matches_air_date": int(panel["weekday_ok"].sum()),
        "weekday_said_known": int(panel["weekday_said"].isin(
            ["monday", "tuesday", "wednesday", "thursday", "friday"]).sum()),
        "title_is_weekend": int(pd.to_datetime(panel["title_date"]).dt.dayofweek.ge(5).sum()),
        "air_date_is_trading_day": int(panel["qqq_gap"].notna().sum()),
        "fut_vs_gap_air": corr(panel["s_fut_pct"], panel["qqq_gap"]),
        "fut_vs_gap_title": corr(panel_title["s_fut_pct"], panel_title["qqq_gap"]),
        "prev_vs_ret_air": corr(panel["s_prev_pct"], panel["qqq_prev"]),
        "prev_vs_ret_title": corr(panel_title["s_prev_pct"], panel_title["qqq_prev"]),
    }

    # §2 previous session recap
    M["prev"] = {
        "described": int(panel["prev_described"].sum()),
        "dir_hit_qqq": hit(panel["s_prev_dir"], panel["qqq_prev"]),
        "dir_hit_spx_vs_spy": hit(panel["s_prev_spx_dir"], panel["spy_prev"]),
        "pct_vs_qqq": corr(panel["s_prev_pct"], panel["qqq_prev"] * 100),
        "spx_pct_vs_spy": corr(panel["s_prev_spx_pct"], panel["spy_prev"] * 100),
        "spx_pct_mae_pp": mae(panel["s_prev_spx_pct"], panel["spy_prev"] * 100),
        "ust10y_dir_hit": hit(panel["s_prev_10y_dir"], panel["d10y_prev"]),
        "ust10y_bp_vs_actual": corr(panel["s_prev_10y_bp"], panel["d10y_prev"]),
        "oil_dir_hit_brent": hit(panel["s_prev_oil_dir"], panel["brent_prev"]),
        "reasons": audit_reasons(panel, "prev_reasons"),
        "macro_explains_prev": {
            "d10y": corr(daily["d10y_prev"], daily["qqq_prev"]),
            "d2y": corr(daily["d2y_prev"], daily["qqq_prev"]),
            "brent": corr(daily["brent_prev"], daily["qqq_prev"]),
        },
    }
    # OLS of qqq_prev on the three macro moves: how much of the day's return is "explainable"
    sub = daily[["qqq_prev", "d10y_prev", "d2y_prev", "brent_prev"]].dropna()
    if len(sub) > 8:
        X = np.column_stack([np.ones(len(sub)), sub[["d10y_prev", "d2y_prev", "brent_prev"]].values])
        beta, *_ = np.linalg.lstsq(X, sub["qqq_prev"].values, rcond=None)
        fit = X @ beta
        ss = np.sum((sub["qqq_prev"] - sub["qqq_prev"].mean()) ** 2)
        r2 = 1 - np.sum((sub["qqq_prev"] - fit) ** 2) / ss
        k = X.shape[1] - 1
        M["prev"]["macro_ols"] = {"n": int(len(sub)), "r2": float(r2),
                                  "adj_r2": float(1 - (1 - r2) * (len(sub) - 1) / (len(sub) - k - 1)),
                                  "beta": dict(zip(["const", "d10y_bp", "d2y_bp", "brent"], map(float, beta)))}

    # §3 this morning -> gap, and same-day close
    feats = {
        "stated_fut_pct": "s_fut_pct",
        "stated_fut_dir": "s_fut_dir",
        "brief_equity_futures": "brf_equity_futures",
        "llm_preopen_tape": "llm_preopen",
        "brief_composite": "brf_composite",
        "brief_sentiment": "brf_sentiment",
        "llm_sentiment": "llm_sentiment",
        "llm_p_up_1d": "llm_p_up_1d",
    }
    M["same_day"] = {}
    for name, col in feats.items():
        M["same_day"][name] = {
            tgt: corr(daily[col], daily[f"qqq_{tgt}"])
            for tgt in ("prev", "gap", "intra", "ret0", "next")
        }
    M["same_day"]["fut_dir_hit_gap"] = hit(daily["s_fut_dir"], daily["qqq_gap"])
    M["same_day"]["fut_dir_hit_ret0"] = hit(daily["s_fut_dir"], daily["qqq_ret0"])
    M["same_day"]["fut_dir_hit_intra"] = hit(daily["s_fut_dir"], daily["qqq_intra"])
    M["same_day"]["fut_pct_mae_pp_gap"] = mae(daily["s_fut_pct"], daily["qqq_gap"] * 100)
    M["same_day"]["gap_explains_ret0"] = corr(daily["qqq_gap"], daily["qqq_ret0"])
    M["same_day"]["gap_vs_intra"] = corr(daily["qqq_gap"], daily["qqq_intra"])
    traj = {"improving": 1, "deteriorating": -1, "stable": 0}
    daily_traj = panel.assign(t=panel["trajectory"].map(traj)).groupby("air_date")["t"].mean()
    daily = daily.merge(daily_traj.rename("traj"), left_on="air_date", right_index=True, how="left")
    M["same_day"]["trajectory_vs_intra"] = corr(daily["traj"], daily["qqq_intra"])
    v = daily[["qqq_gap", "qqq_intra", "qqq_ret0"]].dropna()
    M["same_day"]["variance_share"] = {
        "var_gap": float(v["qqq_gap"].var()), "var_intra": float(v["qqq_intra"].var()),
        "var_ret0": float(v["qqq_ret0"].var()),
        "gap_share": float(v["qqq_gap"].var() / v["qqq_ret0"].var()),
    }
    # explained share of ret0 when the show's futures figure is used, vs perfect knowledge of the gap
    sub = daily[["s_fut_pct", "qqq_gap", "qqq_ret0"]].dropna()
    M["same_day"]["ret0_r2_from_show"] = corr(sub["s_fut_pct"], sub["qqq_ret0"]).get("r2")
    M["same_day"]["ret0_r2_from_true_gap"] = corr(sub["qqq_gap"], sub["qqq_ret0"]).get("r2")
    M["same_day"]["fut_reasons"] = audit_reasons(panel, "fut_reasons")

    # §4 show d+1 recaps close(d): coverage of every trading day in the window
    air = set(panel["air_date"])
    recap_of = dict(zip(panel["prev_date"], panel["air_date"]))
    sessions = mkt[(mkt["date"] >= min(air)) & (mkt["date"] <= max(air))]["date"].tolist()
    M["coverage"] = {
        "sessions_in_window": len(sessions),
        "sessions_with_show_same_day": sum(d in air for d in sessions),
        "sessions_recapped_next_day": sum(d in recap_of for d in sessions),
        "minutes_median": float(panel["minutes"].median()),
        "minutes_min": int(panel["minutes"].min()), "minutes_max": int(panel["minutes"].max()),
        "open_observed": int(panel["open_observed"].sum()),
        "open_dir_hit": hit(panel["s_open_dir"], panel["qqq_gap"]),
    }

    path = REPORTS / "explain_metrics.json"
    path.write_text(json.dumps(M, indent=2, default=float), encoding="utf-8")
    print(f"wrote {path}")
    print(json.dumps({k: M[k] for k in ("alignment",)}, indent=1, default=float)[:3000])
    return 0


if __name__ == "__main__":
    sys.exit(main())
