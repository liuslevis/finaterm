"""Evaluate the LLM factor against QQQ forward returns, side by side with baselines.

What is reported, for each horizon h in {1, 3, 7} trading days:

* Pearson IC and Spearman (rank) IC, with a block-bootstrap CI and a
  block-permutation p-value (iid tests are invalid: h-day forward returns
  overlap, so residuals are strongly autocorrelated).
* Newey-West t-statistic on the OLS slope, lag = h-1.
* Directional hit rate + Wilson CI + binomial p, against the "always up" base rate.
* Top/bottom half mean forward return, i.e. a crude long-short spread.
* Partial IC controlling for what was already knowable at 10:30 ET on the show
  date (5-day momentum and the overnight gap the show itself discussed).
* Placebo: tomorrow's score against today's forward return (must be ~0).
* IC decay over 1..10 day forward returns.

Baselines that must be beaten: 5/20-day momentum, the overnight gap, the ordinal
"pre-open tape" the show describes, and a naive sentiment word-count.

Writes ``reports/metrics.json`` and ``reports/ic_table.md``.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from common import FILES, REPORTS

HORIZONS = (1, 3, 7)
BOOT = 3000
SEED = 20261030

# name -> column template ({h} substituted) ; horizon-independent columns keep {h} unused
PREDICTORS: dict[str, str] = {
    "llm_p(2p-1)": "score_{h}d",
    "llm_logit": "logit_{h}d",
    "llm_sentiment": "sentiment",
    "lexicon_net": "lex_net",
    "brief_composite": "brf_composite",
    "brief_sentiment": "brf_sentiment",
    "momentum_5d": "mom5",
    "momentum_20d": "mom20",
    "preopen_tape": "preopen_move_score",
    "overnight_gap": "gap",
}


# ---------------------------------------------------------------- statistics
def newey_west_slope(y: np.ndarray, x: np.ndarray, lag: int) -> tuple[float, float, float]:
    n = len(y)
    X = np.column_stack([np.ones(n), x])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y - X @ beta
    xtx_inv = np.linalg.inv(X.T @ X)
    s = np.zeros((2, 2))
    for t in range(n):
        u = X[t] * resid[t]
        s += np.outer(u, u)
    lag = max(0, min(lag, n - 1))
    for l in range(1, lag + 1):
        w = 1.0 - l / (lag + 1.0)
        gamma = np.zeros((2, 2))
        for t in range(l, n):
            gamma += np.outer(X[t] * resid[t], X[t - l] * resid[t - l])
        s += w * (gamma + gamma.T)
    cov = xtx_inv @ s @ xtx_inv
    se = float(np.sqrt(max(cov[1, 1], 1e-18)))
    return float(beta[1]), se, float(beta[1] / se)


def block_bootstrap_ci(x: np.ndarray, y: np.ndarray, block: int = 5,
                       n_boot: int = BOOT, seed: int = SEED) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    n = len(x)
    if n < 6:
        return (np.nan, np.nan)
    n_blocks = int(np.ceil(n / block))
    out = []
    for _ in range(n_boot):
        starts = rng.integers(0, n, n_blocks)
        idx = np.concatenate([(np.arange(s, s + block)) % n for s in starts])[:n]
        xb, yb = x[idx], y[idx]
        if np.std(xb) > 1e-12 and np.std(yb) > 1e-12:
            out.append(np.corrcoef(xb, yb)[0, 1])
    if not out:
        return (np.nan, np.nan)
    return tuple(float(v) for v in np.percentile(out, [2.5, 97.5]))


def block_permutation_p(x: np.ndarray, y: np.ndarray, block: int = 5,
                        n_perm: int = BOOT, seed: int = SEED) -> float:
    observed = float(np.corrcoef(x, y)[0, 1])
    rng = np.random.default_rng(seed + 1)
    n = len(y)
    n_blocks = int(np.ceil(n / block))
    hits = 0
    for _ in range(n_perm):
        order = rng.permutation(n_blocks)
        idx: list[int] = []
        for b in order:
            idx.extend(range(b * block, min((b + 1) * block, n)))
        yy = y[np.array(idx[:n])]
        if np.std(yy) > 1e-12:
            if abs(float(np.corrcoef(x, yy)[0, 1])) >= abs(observed):
                hits += 1
    return (hits + 1) / (n_perm + 1)


def wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (float(centre - half), float(centre + half))


def partial_corr(x: np.ndarray, y: np.ndarray, controls: np.ndarray) -> float:
    n = len(x)
    C = np.column_stack([np.ones(n)] + [c for c in controls.T])
    bx = np.linalg.lstsq(C, x, rcond=None)[0]
    by = np.linalg.lstsq(C, y, rcond=None)[0]
    rx, ry = x - C @ bx, y - C @ by
    if np.std(rx) < 1e-12 or np.std(ry) < 1e-12:
        return float("nan")
    return float(np.corrcoef(rx, ry)[0, 1])


def ic_block(panel: pd.DataFrame, col: str, h: int, *, deep: bool = False) -> dict:
    sub = panel.dropna(subset=[col, f"r{h}"]).copy()
    n = len(sub)
    if n < 8:
        return {"n": n, "note": "too few observations"}
    x = sub[col].to_numpy(float)
    y = sub[f"r{h}"].to_numpy(float)
    if np.std(x) < 1e-12:
        return {"n": n, "note": "degenerate score"}

    pearson, p_pearson = stats.pearsonr(x, y)
    spearman, p_spearman = stats.spearmanr(x, y)
    slope, se, t_nw = newey_west_slope(y, x, lag=h - 1)
    lo, hi = block_bootstrap_ci(x, y)

    up = y > 0
    hit = int(np.sum((x > 0) == up))
    wlo, whi = wilson_ci(hit, n)

    med = np.median(x)
    top = sub.loc[x > med, f"r{h}"]
    bottom = sub.loc[x <= med, f"r{h}"]
    spread = float(top.mean() - bottom.mean()) if len(top) and len(bottom) else np.nan

    out = {
        "n": n,
        "pearson": round(float(pearson), 3),
        "p_pearson": round(float(p_pearson), 4),
        "spearman": round(float(spearman), 3),
        "p_spearman": round(float(p_spearman), 4),
        "slope": round(slope, 5),
        "t_nw": round(t_nw, 2),
        "ci95": [round(lo, 3), round(hi, 3)],
        "hit_rate": round(hit / n, 3),
        "base_up_rate": round(float(up.mean()), 3),
        "hi_half_mean_pct": round(float(top.mean()) * 100, 3),
        "lo_half_mean_pct": round(float(bottom.mean()) * 100, 3),
        "ls_spread_pct": round(float(spread) * 100, 3),
    }
    if deep:
        out["p_perm_block"] = round(block_permutation_p(x, y), 4)
        out["hit_ci95"] = [round(wlo, 3), round(whi, 3)]
        ctrl = sub[["mom5", "preopen_move_score"]].fillna(0.0).to_numpy(float)
        out["partial_pearson"] = round(partial_corr(x, y, ctrl), 3)
        out["partial_spearman"] = round(
            float(stats.spearmanr(
                pd.Series(x).rank() - np.polyval(np.polyfit(np.arange(n), pd.Series(x).rank(), 1), np.arange(n)),
                pd.Series(y).rank() - np.polyval(np.polyfit(np.arange(n), pd.Series(y).rank(), 1), np.arange(n)),
            ).statistic), 3)
    return out


def ic_decay(panel: pd.DataFrame, col: str, prices: pd.DataFrame, max_lag: int = 10) -> list[dict]:
    dates = list(prices["date"])
    index_of = {d: i for i, d in enumerate(dates)}
    closes = prices["close"].to_numpy(float)
    last = len(dates) - 1
    out = []
    for lag in range(1, max_lag + 1):
        xs, ys = [], []
        for row in panel.dropna(subset=[col]).itertuples(index=False):
            i = index_of.get(row.entry_date)
            if i is None or i + lag > last:
                continue
            xs.append(getattr(row, col))
            ys.append(closes[i + lag] / closes[i] - 1.0)
        if len(xs) < 8 or np.std(xs) < 1e-12:
            out.append({"lag": lag, "n": len(xs), "ic": None})
            continue
        out.append({"lag": lag, "n": len(xs), "ic": round(float(np.corrcoef(xs, ys)[0, 1]), 3)})
    return out


def trading_sim(panel: pd.DataFrame, col: str) -> dict:
    sub = panel.dropna(subset=[col, "r1"]).copy().sort_values("entry_date")
    if len(sub) < 10:
        return {"n": int(len(sub)), "note": "too few"}
    med = np.median(sub[col])
    sub["pos"] = (sub[col] > med).astype(float)
    sub["strat"] = sub["pos"] * sub["r1"]
    total = float((1 + sub["strat"]).prod() - 1)
    bench = float((1 + sub["r1"]).prod() - 1)
    sd = sub["strat"].std()
    sharpe = float(sub["strat"].mean() / sd * np.sqrt(252)) if sd and sd > 0 else float("nan")
    return {
        "n": int(len(sub)),
        "exposure": round(float(sub["pos"].mean()), 3),
        "total_return_pct": round(total * 100, 2),
        "benchmark_pct": round(bench * 100, 2),
        "sharpe_annualised": round(sharpe, 2) if sharpe == sharpe else None,
    }


def power_note(n: int) -> dict:
    """How many observations would be needed to detect a given IC at 80% power."""
    def n_for(ic: float, power: float = 0.8, alpha: float = 0.05) -> int:
        z_a = stats.norm.ppf(1 - alpha / 2)
        z_b = stats.norm.ppf(power)
        return int(np.ceil(((z_a + z_b) / np.arctanh(ic)) ** 2 + 3))

    se_at_n = 1.0 / np.sqrt(max(n - 3, 1))
    return {
        "current_n": n,
        "se_of_ic_at_current_n": round(float(se_at_n), 3),
        "n_for_ic_0.1": n_for(0.1),
        "n_for_ic_0.2": n_for(0.2),
        "n_for_ic_0.3": n_for(0.3),
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default=str(FILES["panel"]))
    ap.add_argument("--out", default=str(REPORTS / "metrics.json"))
    args = ap.parse_args()
    panel = pd.read_csv(args.panel)
    prices = pd.read_csv(FILES["prices"])
    panel["show_date"] = pd.to_datetime(panel["show_date"]).dt.strftime("%Y-%m-%d")
    panel["entry_date"] = pd.to_datetime(panel["entry_date"]).dt.strftime("%Y-%m-%d")

    results: dict = {
        "n_episodes": int(panel["n_episodes"].sum()),
        "n_dates": int(len(panel)),
        "date_range": [panel["show_date"].min(), panel["show_date"].max()],
        "horizons": list(HORIZONS),
        "table": {},
        "detail": {},
        "placebo": {},
        "diagnostics": {},
        "decay": {},
        "trading": {},
        "power": power_note(len(panel)),
    }

    print(f"panel: {len(panel)} dates, {results['n_episodes']} episodes, "
          f"{results['date_range'][0]}..{results['date_range'][1]}")

    rows = []
    for name, template in PREDICTORS.items():
        results["table"][name] = {}
        for h in HORIZONS:
            col = template.format(h=h)
            if col not in panel.columns:
                continue
            deep = name in {"llm_p(2p-1)", "llm_sentiment"}
            block = ic_block(panel, col, h, deep=deep)
            results["table"][name][f"{h}d"] = block
            if "pearson" not in block:
                continue
            rows.append({
                "predictor": name,
                "h": h,
                "n": block["n"],
                "pearson": block["pearson"],
                "p": block["p_pearson"],
                "spearman": block["spearman"],
                "t_nw": block["t_nw"],
                "ci95": f"[{block['ci95'][0]}, {block['ci95'][1]}]",
                "hit": block["hit_rate"],
                "ls_pct": block["ls_spread_pct"],
            })
            print(f"{name:16s} h={h}  n={block['n']:3d}  r={block['pearson']:+.3f} "
                  f"(p={block['p_pearson']:.3f})  rho={block['spearman']:+.3f}  "
                  f"t_nw={block['t_nw']:+.2f}  hit={block['hit_rate']:.2f}  ls={block['ls_spread_pct']:+.2f}%")

    # placebo: tomorrow's score against today's return
    p = panel.sort_values("show_date").reset_index(drop=True)
    p["next_score_1d"] = p["score_1d"].shift(-1)
    results["placebo"]["next_score_vs_today_r1"] = ic_block(p.dropna(subset=["next_score_1d"]), "next_score_1d", 1)
    print("placebo (next score vs today's r1):",
          json.dumps(results["placebo"]["next_score_vs_today_r1"], ensure_ascii=False))

    # is the factor just slow-moving persistence?  AR(1) + IC of the daily change
    order = panel.sort_values("show_date").reset_index(drop=True)
    order["dscore_1d"] = order["score_1d"].diff()
    order["lag_score_1d"] = order["score_1d"].shift(1)
    ar1 = order.dropna(subset=["lag_score_1d"])
    if len(ar1) > 5:
        results["persistence"] = {
            "ar1_of_score": round(float(stats.pearsonr(ar1["lag_score_1d"], ar1["score_1d"]).statistic), 3),
            "mean_abs_daily_change": round(float(order["dscore_1d"].abs().mean()), 4),
        }
    results["table"]["llm_dscore"] = {"1d": ic_block(order.dropna(subset=["dscore_1d"]), "dscore_1d", 1)}
    print("persistence:", json.dumps(results.get("persistence", {})))

    # stability: first half vs second half of the sample
    half = len(order) // 2
    first, second = order.iloc[:half], order.iloc[half:]
    results["split"] = {}
    for label, part in (("first_half", first), ("second_half", second)):
        results["split"][label] = {
            "n_dates": int(len(part)),
            "range": [part["show_date"].min(), part["show_date"].max()] if len(part) else None,
            "ic": {},
        }
        for h in HORIZONS:
            col = f"score_{h}d"
            if col in part.columns:
                results["split"][label]["ic"][f"{h}d"] = ic_block(part, col, h)
    print("split:", json.dumps({k: v["n_dates"] for k, v in results["split"].items()}))


    diag = {}
    for target in ("ret_0", "gap", "mom5"):
        sub = panel.dropna(subset=["score_1d", target])
        if len(sub) > 5:
            diag[f"corr_score_vs_{target}"] = round(float(stats.spearmanr(sub["score_1d"], sub[target]).statistic), 3)
    results["diagnostics"] = diag
    print("diagnostics:", json.dumps(diag))

    for name, template in PREDICTORS.items():
        col = template.format(h=1)
        if col in panel.columns:
            results["decay"][name] = ic_decay(panel, col, prices, max_lag=10)

    for name in ("llm_p(2p-1)", "llm_sentiment"):
        col = "score_1d" if name.startswith("llm_p") else "sentiment"
        results["trading"][name] = trading_sim(panel, col)

    Path(args.out).write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    table = pd.DataFrame(rows)
    md = ["| predictor | h | n | Pearson IC | p | Rank IC | NW t | boot 95% CI | hit rate | top-bottom (pp) |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        md.append(f"| {r['predictor']} | {r['h']}d | {r['n']} | {r['pearson']:+.3f} | {r['p']:.3f} | "
                  f"{r['spearman']:+.3f} | {r['t_nw']:+.2f} | {r['ci95']} | {r['hit']:.2f} | {r['ls_pct']:+.2f} |")
    (Path(args.out).with_name("ic_table_" + Path(args.out).stem.replace("metrics_", "") + ".md")).write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())



