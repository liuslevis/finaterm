"""V9: use V8 pre-touch order-book features as a bearish overlay on the ambush strategy.

Stage 1 relabels every V8 limit-up touch with the strategy's own horizon
(buy next open, exit after 3/5 sessions) and freezes July-only rules on the
whole limit-up universe, where samples are large. Stage 2 applies those frozen
rules to the existing dormant candidates with several overlay methods.
"""

from __future__ import annotations

import argparse
import json
import math

import numpy as np
import pandas as pd

from backtest import backtest_score, load_prices
from board_v8 import FEATURES as V8_FEATURES
from board_v8 import PANEL_PATH as V8_PANEL_PATH
from board_v8 import RULES_PATH as V8_RULES_PATH
from board_v8 import UNSELECTABLE_FEATURES, flag_mask
from optimize_score import (
    DATA_DIR,
    HERE,
    apply_weighted_model,
    load_panel,
    rank_panel,
    split_datasets,
)
from strategy import add_forward_returns, limit_up_rate, rounded_limit_price

TRAIN_FROM = "20260601"
TRAIN_THROUGH = "20260731"
TEST_THROUGH = "20260831"
DIAGNOSTIC_THROUGH = "20260930"
HORIZONS = ("3d", "1w")
TARGET = "next_open_1w_pct"
RIDGE_ALPHA = 0.05
VETO_QUANTILE = 2 / 3
PENALTY_WEIGHT = 0.5
MIN_RERANK_CANDIDATES = 3
COST_BPS_PER_SIDE = 15.0
SELECTABLE = tuple(f for f in V8_FEATURES if f not in UNSELECTABLE_FEATURES)
BASE_SCORES = ("current_model_score", "lv2_score_v7_fixed", "rule_only_unranked")
UNIVERSE_PATH = DATA_DIR / "ambush_v9_universe_labels.csv"
MODEL_PATH = HERE / "enhance_v9_model.json"


def universe_labels(panel: pd.DataFrame) -> pd.DataFrame:
    """Next-open 3D/1W labels for every touch, matching the strategy's entry."""
    prices = {}
    for code in panel["code"].unique():
        try:
            prices.update(load_prices([code]))
        except (RuntimeError, ValueError):
            continue
    calendar = pd.DatetimeIndex(pd.to_datetime(sorted(
        set().union(*(set(frame.index) for frame in prices.values()))
    )))
    rows = []
    for row in panel[["signal_date", "code", "name"]].to_dict("records"):
        out = {"signal_date": row["signal_date"], "code": row["code"]}
        history = prices.get(row["code"])
        if history is not None:
            add_forward_returns(out, history, pd.Timestamp(row["signal_date"]), calendar)
            later = history[history.index > row["signal_date"]]
            if len(later):
                bar = later.iloc[0]
                upper = rounded_limit_price(
                    bar["previous_close"], limit_up_rate(row["code"], str(row["name"]))
                )
                out["next_open_locked"] = bool(bar["open"] >= upper - 1e-8)
        rows.append(out)
    labels = pd.DataFrame(rows)
    keep = ["signal_date", "code", "next_open_locked"] + [
        f"{prefix}_{h}_{suffix}"
        for h in HORIZONS
        for prefix, suffix in (("next_open", "pct"), ("forward", "end_date"))
    ]
    return labels.reindex(columns=keep)


def period_of(date: str) -> str:
    if date <= TRAIN_THROUGH:
        return "train"
    return "test" if date <= TEST_THROUGH else "diagnostic"


def tradable_universe(panel: pd.DataFrame, labels: pd.DataFrame) -> pd.DataFrame:
    rows = panel.merge(labels, on=["signal_date", "code"], how="left")
    rows = rows[rows[TARGET].notna() & ~rows["next_open_locked"].fillna(True).astype(bool)]
    rows = rows.copy()
    rows["period"] = rows["signal_date"].map(period_of)
    return rows


def mature_train(rows: pd.DataFrame) -> pd.DataFrame:
    """July rows whose 1W label was observable by the end of July."""
    end = rows["forward_1w_end_date"].astype(str)
    return rows[(rows["period"] == "train") & (end <= TRAIN_THROUGH)]


def daily_rank_ic(rows: pd.DataFrame, feature: str, target: str = TARGET) -> dict:
    values = []
    for _, group in rows.groupby("signal_date"):
        pair = group[[feature, target]].dropna()
        if len(pair) >= 5 and pair[feature].nunique() > 1:
            values.append(pair[feature].rank().corr(pair[target].rank()))
    series = pd.Series(values, dtype=float).dropna()
    std = series.std(ddof=1)
    return {
        "samples": int(rows[feature].notna().sum()),
        "days": len(series),
        "daily_rank_ic_mean": series.mean(),
        "daily_rank_ic_t": series.mean() / std * math.sqrt(len(series)) if std > 0 else math.nan,
    }


def empirical_cdf(reference: pd.Series, values: pd.Series) -> pd.Series:
    """Percentile of ``values`` against a frozen reference sample; NaN -> 0.5."""
    sorted_ref = np.sort(reference.dropna().to_numpy())
    if not len(sorted_ref):
        return pd.Series(0.5, index=values.index)
    position = np.searchsorted(sorted_ref, values.to_numpy(dtype=float), side="right")
    result = pd.Series(position / len(sorted_ref), index=values.index)
    return result.where(values.notna(), 0.5)


def fit_ridge(train: pd.DataFrame, alpha: float = RIDGE_ALPHA) -> dict:
    """Ridge on frozen-percentile features against the day-centered target rank."""
    x = np.column_stack([empirical_cdf(train[f], train[f]) - 0.5 for f in SELECTABLE])
    rank = train.groupby("signal_date")[TARGET].rank(pct=True)
    y = (rank - rank.groupby(train["signal_date"]).transform("mean")).to_numpy()
    # Penalty on the per-sample covariance scale; percentile features have variance 1/12.
    weights = np.linalg.solve(x.T @ x / len(x) + alpha * np.eye(x.shape[1]), x.T @ y / len(x))
    return dict(zip(SELECTABLE, map(float, weights)))


def ridge_score(rows: pd.DataFrame, reference: pd.DataFrame, weights: dict) -> pd.Series:
    return sum(
        weight * (empirical_cdf(reference[feature], rows[feature]) - 0.5)
        for feature, weight in weights.items()
    )


def freeze_rules(train: pd.DataFrame) -> dict:
    ic = {f: daily_rank_ic(train, f)["daily_rank_ic_t"] for f in SELECTABLE}
    bear = min((f for f in ic if np.isfinite(ic[f])), key=ic.get)
    weights = fit_ridge(train)
    scores = ridge_score(train, train, weights)
    return {
        "version": "v9",
        "train_through": TRAIN_THROUGH,
        "train_universe_samples": int(len(train)),
        "target": TARGET,
        "train_daily_rank_ic_t": ic,
        "horizon_bear": {
            "feature": bear,
            "direction": "high",
            "threshold": float(train[bear].quantile(VETO_QUANTILE)),
        },
        "ridge": {
            "alpha": RIDGE_ALPHA,
            "weights": weights,
            "veto_below": float(scores.quantile(1 - VETO_QUANTILE)),
        },
        "v8_flags": json.loads(V8_RULES_PATH.read_text(encoding="utf-8"))["flags"],
        "penalty_weight": PENALTY_WEIGHT,
    }


def overlay_masks(rows: pd.DataFrame, rules: dict, reference: pd.DataFrame) -> dict[str, pd.Series]:
    """Bearish masks; True means the candidate should be avoided."""
    flags = rules["v8_flags"]
    ridge = ridge_score(rows, reference, rules["ridge"]["weights"])
    return {
        "v8_avoid": flag_mask(rows, flags["avoid_selected"]),
        "v8_combined": flag_mask(rows, flags["avoid_selected"])
        | flag_mask(rows, flags["weak_support"]),
        "v9_horizon": flag_mask(rows, rules["horizon_bear"]),
        "v9_ridge": (ridge <= rules["ridge"]["veto_below"]).fillna(False),
    }


def penalized_score(rows: pd.DataFrame, base: str, rules: dict, reference: pd.DataFrame) -> pd.Series:
    """Blend the base day-rank with the frozen-universe ridge percentile."""
    ridge = ridge_score(rows, reference, rules["ridge"]["weights"])
    ridge_pct = empirical_cdf(ridge_score(reference, reference, rules["ridge"]["weights"]), ridge)
    base_pct = rows.groupby("signal_date")[base].rank(pct=True).fillna(0.5)
    weight = rules["penalty_weight"]
    return (1 - weight) * base_pct + weight * ridge_pct


def rerank_without(rows: pd.DataFrame, base: str, avoid: pd.Series) -> pd.Series:
    """Drop vetoed names before ranking, so the remaining top half is bought."""
    return rows[base].where(~avoid)


def net_pct(gross: pd.Series, cost_bps: float) -> pd.Series:
    fee = cost_bps / 10_000
    return ((1 + gross / 100) * (1 - fee) / (1 + fee) - 1) * 100


def candidate_label_table(splits: dict, masks: dict, cost_bps: float) -> pd.DataFrame:
    records = []
    for split, frame in splits.items():
        for method, avoid in masks.items():
            avoid = avoid.reindex(frame.index).fillna(False).astype(bool)
            for horizon in HORIZONS:
                column = f"next_open_{horizon}_pct"
                net = net_pct(frame[column], cost_bps)
                records.append({
                    "split": split, "method": method, "horizon": horizon,
                    "candidates": int(net.notna().sum()),
                    "avoided": int((avoid & net.notna()).sum()),
                    "mean_all_pct": net.mean(),
                    "mean_kept_pct": net[~avoid].mean(),
                    "mean_avoided_pct": net[avoid].mean(),
                    "win_kept_pct": (net[~avoid].dropna() > 0).mean() * 100,
                    "win_avoided_pct": (net[avoid].dropna() > 0).mean() * 100,
                })
    return pd.DataFrame(records)


def shuffled_within_day(allow: pd.Series, dates: pd.Series, rng: np.random.Generator) -> pd.Series:
    """Placebo mask: same number of vetoes per signal day, random names."""
    shuffled = allow.copy()
    for _, index in allow.groupby(dates).groups.items():
        shuffled.loc[index] = rng.permutation(allow.loc[index].to_numpy())
    return shuffled.astype(bool)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--relabel", action="store_true", help="Recompute universe 3D/1W labels")
    parser.add_argument("--cost-bps-per-side", type=float, default=COST_BPS_PER_SIDE)
    parser.add_argument("--placebo-runs", type=int, default=200)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    v8 = pd.read_csv(V8_PANEL_PATH, dtype={"code": str, "signal_date": str})
    if args.relabel or not UNIVERSE_PATH.exists():
        universe_labels(v8).to_csv(UNIVERSE_PATH, index=False, encoding="utf-8-sig")
    labels = pd.read_csv(UNIVERSE_PATH, dtype={
        "code": str, "signal_date": str,
        **{f"forward_{h}_end_date": str for h in HORIZONS},
    })
    universe = tradable_universe(v8, labels)
    train = mature_train(universe)
    rules = freeze_rules(train)
    MODEL_PATH.write_text(json.dumps(rules, indent=2), encoding="utf-8")

    universe_masks = overlay_masks(universe, rules, train)
    ic_rows = []
    for pool, pool_mask in (("all", universe.index == universe.index), ("dormant_pool", universe["dormant_pool"].astype(bool))):
        scored = universe[pool_mask].copy()
        scored["v9_ridge_score"] = ridge_score(scored, train, rules["ridge"]["weights"])
        for period, group in scored.groupby("period"):
            for feature in (*SELECTABLE, "v9_ridge_score"):
                for horizon in HORIZONS:
                    ic_rows.append({
                        "pool": pool, "period": period, "feature": feature, "horizon": horizon,
                        **daily_rank_ic(group, feature, f"next_open_{horizon}_pct"),
                    })
    universe_ic = pd.DataFrame(ic_rows)
    universe_ic.to_csv(DATA_DIR / "ambush_v9_universe_ic.csv", index=False, encoding="utf-8-sig")
    universe_flags = candidate_label_table(
        {p: g for p, g in universe.groupby("period")}, universe_masks, args.cost_bps_per_side
    )
    universe_flags.to_csv(DATA_DIR / "ambush_v9_universe_flags.csv", index=False, encoding="utf-8-sig")

    panel = load_panel(TRAIN_FROM, DIAGNOSTIC_THROUGH)
    eligible = rank_panel(panel[panel["launch_detected"] & panel["data_quality_valid"]].copy())
    model = json.loads((HERE / "lv2_score_model.json").read_text(encoding="utf-8"))
    eligible["current_model_score"] = apply_weighted_model(eligible, model["production_weights"])
    eligible["rule_only_unranked"] = 1.0
    eligible = eligible.merge(
        v8[["signal_date", "code", *SELECTABLE]], on=["signal_date", "code"], how="left",
        validate="one_to_one",
    )
    masks = overlay_masks(eligible, rules, train)
    _, test, diagnostic = split_datasets(
        eligible, TRAIN_FROM, TRAIN_THROUGH, TEST_THROUGH, DIAGNOSTIC_THROUGH
    )
    in_train = eligible[eligible["signal_date"] <= TRAIN_THROUGH]
    splits = {"train": in_train, "test": test, "diagnostic": diagnostic}
    candidate_labels = candidate_label_table(splits, masks, args.cost_bps_per_side)
    candidate_labels.to_csv(DATA_DIR / "ambush_v9_candidate_labels.csv", index=False, encoding="utf-8-sig")

    prices = load_prices(eligible["code"])
    calendar = sorted(set().union(*(set(frame.index) for frame in prices.values())))
    windows = {
        "train": (TRAIN_FROM, TRAIN_THROUGH),
        "test": ("20260801", TEST_THROUGH),
        "diagnostic": ("20260901", DIAGNOSTIC_THROUGH),
        "post_train": ("20260801", DIAGNOSTIC_THROUGH),
    }
    records = []
    for base in BASE_SCORES:
        variants = {"baseline": (base, None)}
        for name, avoid in masks.items():
            eligible[f"allow_{name}"] = ~avoid
            variants[f"veto_{name}"] = (base, f"allow_{name}")
        for name in ("v8_avoid", "v9_ridge"):
            column = f"{base}__rerank_{name}"
            eligible[column] = rerank_without(eligible, base, masks[name])
            variants[f"rerank_{name}"] = (column, None)
        column = f"{base}__penalty"
        eligible[column] = penalized_score(eligible, base, rules, train)
        variants["penalty_v9_ridge"] = (column, None)
        for variant, (score, entry_mask) in variants.items():
            for split, (start, through) in windows.items():
                frame = eligible[(eligible["signal_date"] >= start) & (eligible["signal_date"] <= through)]
                metrics, _ = backtest_score(
                    frame, score, prices, calendar, start, through,
                    cost_bps_per_side=args.cost_bps_per_side, entry_mask_column=entry_mask,
                )
                records.append({"base": base, "variant": variant, "split": split, **metrics})
    portfolio = pd.DataFrame(records)
    portfolio.to_csv(DATA_DIR / "ambush_v9_portfolio_evaluation.csv", index=False, encoding="utf-8-sig")

    # A veto keeps cash, which alone cuts losses when the base strategy loses money.
    rng = np.random.default_rng(9)
    placebo = []
    for method in ("v8_avoid", "v8_combined"):
        for base in BASE_SCORES:
            for split, (start, through) in windows.items():
                frame = eligible[(eligible["signal_date"] >= start) & (eligible["signal_date"] <= through)].copy()
                frame["allow"] = ~masks[method].loc[frame.index]
                real = backtest_score(
                    frame, base, prices, calendar, start, through,
                    cost_bps_per_side=args.cost_bps_per_side, entry_mask_column="allow",
                )[0]["net_return_pct"]
                sims = []
                for _ in range(args.placebo_runs):
                    frame["placebo"] = shuffled_within_day(frame["allow"], frame["signal_date"], rng)
                    sims.append(backtest_score(
                        frame, base, prices, calendar, start, through,
                        cost_bps_per_side=args.cost_bps_per_side, entry_mask_column="placebo",
                    )[0]["net_return_pct"])
                sims = np.asarray(sims)
                placebo.append({
                    "method": method, "base": base, "split": split, "real_net_return_pct": real,
                    "placebo_mean_pct": sims.mean(), "placebo_p": (sims >= real).mean(),
                })
    placebo = pd.DataFrame(placebo)
    placebo.to_csv(DATA_DIR / "ambush_v9_placebo.csv", index=False, encoding="utf-8-sig")

    print(f"rules={json.dumps({k: rules[k] for k in ('horizon_bear', 'ridge')}, indent=1)}")
    print("\n== universe IC (1w) ==")
    print(universe_ic[(universe_ic.horizon == "1w")].pivot_table(
        index=["pool", "feature"], columns="period", values="daily_rank_ic_t"
    ).round(2).to_string())
    print("\n== universe flags (1w) ==")
    print(universe_flags[universe_flags.horizon == "1w"].round(2).to_string(index=False))
    print("\n== candidate labels (1w) ==")
    print(candidate_labels[candidate_labels.horizon == "1w"].round(2).to_string(index=False))
    print("\n== portfolio net_return_pct ==")
    print(portfolio.pivot_table(
        index=["base", "variant"], columns="split", values="net_return_pct"
    ).round(2).to_string())
    print("\n== veto vs same-count random veto ==")
    print(placebo.round(3).to_string(index=False))


if __name__ == "__main__":
    main()
