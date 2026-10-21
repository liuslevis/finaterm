"""Explore small, interpretable subgroups without fitting rules on test returns."""

from __future__ import annotations

import argparse
import itertools
import json

import numpy as np
import pandas as pd

from backtest import backtest_score, load_prices
from optimize_score import (
    DATA_DIR,
    HERE,
    apply_weighted_model,
    json_compatible,
    load_panel,
    rank_panel,
    split_datasets,
)

MEDIAN_FEATURES = {
    "turnover": "mean_turnover_20d_pct",
    "volume_ratio": "event_volume_ratio",
    "range": "range_60d_pct",
    "bottom": "bottom_percentile",
    "volatility": "mean_abs_return_20d_pct",
    "opening_fill": "opening_buy_fill_ratio_pct",
    "sell_cancel": "sell_cancel_ratio_pct",
    "sell_pressure": "gross_sell_float_ratio_pct",
    "buy_refill": "buy_refill_float_ratio_pct",
    "wash": "wash_trade_volume_pct",
    "flow": "delta_ratio_pct",
    "cap": "free_float_cap_billion",
    "amount": "event_amount_million",
    "absorption": "passive_sell_absorb_ratio_pct",
}
MIN_TRAIN_SAMPLES = 6
MIN_TRAIN_DATES = 3


def add_subset_features(panel: pd.DataFrame) -> pd.DataFrame:
    result = panel.copy()
    result["free_float_cap_billion"] = result["outstanding_share"] * result["event_close"] / 1e9
    result["event_amount_million"] = result["event_amount"] / 1e6
    result["closed_at_limit"] = result["event_close"] >= result["limit_up_price"] - 0.01
    result["board_20pct"] = result["code"].str.startswith(("300", "301", "688", "689"))
    result["shanghai"] = result["code"].str.endswith(".SH")
    return result


def build_rules(train: pd.DataFrame) -> list[dict]:
    atoms = {}
    for name, feature in MEDIAN_FEATURES.items():
        threshold = float(train[feature].median())
        if not np.isfinite(threshold):
            raise ValueError(f"No observed training values for {feature}")
        for side, operator in (("low", "le"), ("high", "gt")):
            atoms[f"{name}_{side}"] = {
                "feature": feature, "operator": operator, "threshold": threshold,
            }
    atoms.update({
        "flow_positive": {"feature": "delta_ratio_pct", "operator": "gt", "threshold": 0.0},
        "net_flow_positive": {
            "feature": "large_order_net_flow_pct", "operator": "gt", "threshold": 0.0,
        },
        "sealed": {"feature": "closed_at_limit", "operator": "eq", "threshold": True},
        "unsealed": {"feature": "closed_at_limit", "operator": "eq", "threshold": False},
        "main_board": {"feature": "board_20pct", "operator": "eq", "threshold": False},
        "growth_board": {"feature": "board_20pct", "operator": "eq", "threshold": True},
        "shanghai": {"feature": "shanghai", "operator": "eq", "threshold": True},
        "shenzhen": {"feature": "shanghai", "operator": "eq", "threshold": False},
        "morning_launch": {"feature": "t_start", "operator": "lt", "threshold": 113000000},
        "afternoon_launch": {"feature": "t_start", "operator": "ge", "threshold": 130000000},
    })
    rules = [
        {"rule": name, "conditions": [condition]}
        for name, condition in atoms.items()
    ]
    # Bound the economic interactions to flow confirmation plus one risk filter.
    pairs = [
        (flow, risk)
        for flow in ("flow_high", "flow_positive")
        for risk in ("turnover_low", "volume_ratio_low", "range_low", "bottom_low", "cap_low", "sealed")
    ]
    pairs += [
        ("net_flow_positive", "turnover_low"),
        ("net_flow_positive", "volume_ratio_low"),
        ("absorption_high", "sell_pressure_low"),
        ("opening_fill_high", "sell_cancel_low"),
    ]
    rules += [
        {"rule": f"{left}__{right}", "conditions": [atoms[left], atoms[right]]}
        for left, right in pairs
    ]
    return rules


def apply_rule(panel: pd.DataFrame, rule: dict) -> pd.Series:
    mask = pd.Series(True, index=panel.index)
    methods = {"le": "le", "gt": "gt", "lt": "lt", "ge": "ge", "eq": "eq"}
    for condition in rule["conditions"]:
        operator = condition["operator"]
        if operator not in methods:
            raise ValueError(f"Unsupported rule operator: {operator}")
        values = panel[condition["feature"]]
        mask &= values.notna() & getattr(values, methods[operator])(condition["threshold"])
    return mask.fillna(False).astype(bool)


def label_summary(panel: pd.DataFrame, mask: pd.Series, cost_bps: float) -> dict:
    selected = panel.loc[mask]
    labeled = selected.dropna(subset=["next_open_1w_pct"])
    net = ((1 + labeled["next_open_1w_pct"] / 100)
           * (1 - cost_bps / 10_000) / (1 + cost_bps / 10_000) - 1) * 100
    date_means = net.groupby(labeled["signal_date"]).mean()
    weekly = date_means.groupby(
        pd.to_datetime(date_means.index).to_period("W-FRI")
    ).mean()
    if len(weekly):
        exact = len(weekly) <= 16
        signs = (
            np.asarray(list(itertools.product((-1, 1), repeat=len(weekly))))
            if exact else np.random.default_rng(61).choice((-1, 1), size=(10_000, len(weekly)))
        )
        null_means = signs @ weekly.to_numpy() / len(weekly)
        positive = int((null_means >= weekly.mean() - 1e-12).sum())
        p_value = positive / len(signs) if exact else (positive + 1) / (len(signs) + 1)
    else:
        p_value = float("nan")
    code_means = net.groupby(labeled["code"]).mean()
    return {
        "matched_count": len(selected),
        "coverage_pct": len(selected) / len(panel) * 100 if len(panel) else 0.0,
        "labeled_count": len(labeled),
        "signal_dates": labeled["signal_date"].nunique(),
        "unique_codes": labeled["code"].nunique(),
        "net_label_mean_pct": net.mean(),
        "net_label_median_pct": net.median(),
        "positive_rate_pct": (net > 0).mean() * 100 if len(net) else float("nan"),
        "date_equal_net_mean_pct": date_means.mean(),
        "positive_date_rate_pct": (date_means > 0).mean() * 100 if len(date_means) else float("nan"),
        "weekly_blocks": len(weekly),
        "weekly_signflip_p": p_value,
        "mean_excluding_best_code_pct": (
            net[labeled["code"] != code_means.idxmax()].mean()
            if len(code_means) > 1 else float("nan")
        ),
    }


def holm_adjust(p_values: pd.Series) -> pd.Series:
    result = pd.Series(np.nan, index=p_values.index)
    valid = p_values.dropna().sort_values()
    if len(valid):
        adjusted = np.maximum.accumulate(
            valid.to_numpy() * np.arange(len(valid), 0, -1)
        ).clip(max=1.0)
        result.loc[valid.index] = adjusted
    return result


def training_screen(train: pd.DataFrame, rules: list[dict], cost_bps: float) -> pd.DataFrame:
    rows = []
    for rule in rules:
        summary = label_summary(train, apply_rule(train, rule), cost_bps)
        supported = (
            summary["labeled_count"] >= MIN_TRAIN_SAMPLES
            and summary["signal_dates"] >= MIN_TRAIN_DATES
        )
        frozen = (
            supported and summary["net_label_mean_pct"] > 0
            and summary["date_equal_net_mean_pct"] > 0
        )
        rows.append({
            "rule": rule["rule"], "training_supported": supported,
            "frozen_from_training": frozen, **summary,
        })
    frame = pd.DataFrame(rows)
    frame["holm_p"] = holm_adjust(frame["weekly_signflip_p"])
    return frame


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-from", default="20260601")
    parser.add_argument("--train-through", default="20260731")
    parser.add_argument("--test-through", default="20260831")
    parser.add_argument("--diagnostic-through", default="20260930")
    parser.add_argument("--cost-bps-per-side", type=float, default=15.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not np.isfinite(args.cost_bps_per_side) or not 0 <= args.cost_bps_per_side < 10_000:
        raise ValueError("Expected finite costs between 0 and 10,000 bp per side")
    panel = load_panel(args.train_from, args.diagnostic_through)
    eligible = panel[panel["launch_detected"] & panel["data_quality_valid"]].copy()
    eligible = add_subset_features(rank_panel(eligible))
    eligible["rule_only_unranked"] = 1.0
    current_model = json.loads((HERE / "lv2_score_model.json").read_text(encoding="utf-8"))
    eligible["current_model_score"] = apply_weighted_model(
        eligible, current_model["production_weights"]
    )
    train, test, diagnostic = split_datasets(
        eligible, args.train_from, args.train_through,
        args.test_through, args.diagnostic_through,
    )
    if train.empty or test.empty or diagnostic.empty:
        raise RuntimeError("Training, test and historical diagnostic periods are required")
    rules = build_rules(train)
    screen = training_screen(train, rules, args.cost_bps_per_side)
    frozen_names = screen.loc[screen["frozen_from_training"], "rule"].tolist()
    manifest = {
        "threshold_source": "mature_training_features_only",
        "train_through": args.train_through,
        "training_samples": len(train),
        "attempted_rules": len(rules),
        "minimum_train_samples": MIN_TRAIN_SAMPLES,
        "minimum_train_dates": MIN_TRAIN_DATES,
        "frozen_rules": frozen_names,
        "rules": rules,
        "deployment": "research_only; no rule is promoted automatically",
        "multiple_testing": "weekly sign-flip diagnostic with Holm adjustment",
        "current_model_version": current_model["version"],
        "current_model_weights": current_model["production_weights"],
        "current_model_available_after": current_model["available_after"],
        "diagnostic_only_rules": ["bottom_low"],
        "score_interpretation": (
            "Training NAV for fitted models is retrospective, not out-of-sample. "
            "Current model was selected using August data; test NAV is diagnostic. "
            "Rule-only selection preserves original per-stock budgets and keeps rejected cash."
        ),
    }
    (DATA_DIR / "ambush_subset_rules.json").write_text(
        json.dumps(json_compatible(manifest), ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )
    screen.to_csv(DATA_DIR / "ambush_subset_training_screen.csv", index=False, encoding="utf-8-sig")
    prices = load_prices(eligible["code"])
    calendar = sorted(set().union(*(set(frame.index) for frame in prices.values())))
    score_columns = (
        "lv2_score_pre_sol61", "current_model_score",
        "lv2_score_v7_fixed", "rule_only_unranked",
    )
    summaries = []
    portfolios = []
    matches = []
    nav_frames = []
    baseline = {"rule": "all_candidates", "conditions": []}
    post_train = pd.concat([test, diagnostic]).sort_values(["signal_date", "code"])
    post_start = (pd.Timestamp(args.train_through) + pd.Timedelta(days=1)).strftime("%Y%m%d")
    for split, frame, start, through in (
        ("train", train, args.train_from, args.train_through),
        ("test", test, (pd.Timestamp(args.train_through) + pd.Timedelta(days=1)).strftime("%Y%m%d"), args.test_through),
        ("diagnostic", diagnostic, (pd.Timestamp(args.test_through) + pd.Timedelta(days=1)).strftime("%Y%m%d"), args.diagnostic_through),
        ("post_train_continuous", post_train, post_start, args.diagnostic_through),
    ):
        for rule in [baseline, *rules]:
            mask = apply_rule(frame, rule)
            summaries.append({
                "dataset_split": split, "rule": rule["rule"],
                "frozen_from_training": rule["rule"] in frozen_names,
                **label_summary(frame, mask, args.cost_bps_per_side),
            })
            tested = frame.copy()
            tested["subset_entry_allowed"] = mask
            for score in score_columns:
                metrics, nav = backtest_score(
                    tested, score, prices, calendar, start, through,
                    cost_bps_per_side=args.cost_bps_per_side,
                    entry_mask_column="subset_entry_allowed",
                )
                portfolios.append({
                    "dataset_split": split, "rule": rule["rule"],
                    "frozen_from_training": rule["rule"] in frozen_names,
                    **metrics,
                })
                if split == "post_train_continuous" and rule["rule"] in [
                    "all_candidates", "bottom_low", *frozen_names
                ]:
                    nav["score"] = score
                    nav["rule"] = rule["rule"]
                    nav_frames.append(nav)
            if rule["rule"] in frozen_names and split != "post_train_continuous":
                selected = frame.loc[mask, [
                    "signal_date", "code", "name", *MEDIAN_FEATURES.values(),
                    "next_open_3d_pct", "next_open_1w_pct",
                ]].copy()
                selected["rule"] = rule["rule"]
                selected["dataset_split"] = split
                matches.append(selected)
    summary = pd.DataFrame(summaries)
    portfolio = pd.DataFrame(portfolios)
    summary.to_csv(DATA_DIR / "ambush_subset_label_evaluation.csv", index=False, encoding="utf-8-sig")
    portfolio.to_csv(DATA_DIR / "ambush_subset_portfolio_evaluation.csv", index=False, encoding="utf-8-sig")
    pd.concat(nav_frames, ignore_index=True).to_csv(
        DATA_DIR / "ambush_subset_frozen_nav.csv", index=False, encoding="utf-8-sig",
    )
    match_frame = pd.concat(matches, ignore_index=True) if matches else pd.DataFrame(
        columns=["signal_date", "code", "rule", "dataset_split"]
    )
    match_frame.to_csv(
        DATA_DIR / "ambush_subset_frozen_matches.csv", index=False, encoding="utf-8-sig",
    )
    stress_rows = []
    for rule in [baseline, *[item for item in rules if item["rule"] in [*frozen_names, "bottom_low"]]]:
        mask = apply_rule(post_train, rule)
        for score in score_columns:
            for cost in (15.0, 30.0, 50.0):
                tested = post_train.copy()
                tested["subset_entry_allowed"] = mask
                metrics, _ = backtest_score(
                    tested, score, prices, calendar, post_start, args.diagnostic_through,
                    cost_bps_per_side=cost, entry_mask_column="subset_entry_allowed",
                )
                stress_rows.append({
                    "rule": rule["rule"], "frozen_from_training": rule["rule"] in frozen_names,
                    "stress": "cost_sensitivity", **metrics,
                })
            if rule["rule"] == "all_candidates":
                continue
            leave_out = []
            for date in sorted(post_train.loc[mask, "signal_date"].unique()):
                tested = post_train.copy()
                tested["subset_entry_allowed"] = mask & tested["signal_date"].ne(date)
                metrics, _ = backtest_score(
                    tested, score, prices, calendar, post_start, args.diagnostic_through,
                    cost_bps_per_side=args.cost_bps_per_side,
                    entry_mask_column="subset_entry_allowed",
                )
                leave_out.append({"removed_signal_date": date, **metrics})
            if leave_out:
                worst = min(leave_out, key=lambda row: row["net_return_pct"])
                stress_rows.append({
                    "rule": rule["rule"], "frozen_from_training": rule["rule"] in frozen_names,
                    "stress": "worst_leave_one_signal_date_out",
                    **worst,
                })
    pd.DataFrame(stress_rows).to_csv(
        DATA_DIR / "ambush_subset_stress_evaluation.csv", index=False, encoding="utf-8-sig",
    )
    print(f"Attempted {len(rules)} bounded rules; frozen training candidates: {frozen_names}")
    print("Training screen (not ranked on test or diagnostic returns):")
    columns = [
        "rule", "training_supported", "frozen_from_training", "labeled_count",
        "signal_dates", "net_label_mean_pct", "net_label_median_pct",
        "date_equal_net_mean_pct", "weekly_blocks", "holm_p",
    ]
    print(screen[columns].sort_values("net_label_mean_pct", ascending=False).head(15).to_string(index=False))
    print("Frozen candidates and baseline, net daily NAV:")
    print(portfolio[portfolio["rule"].isin(["all_candidates", *frozen_names])].to_string(index=False))


if __name__ == "__main__":
    main()
