"""Train and evaluate a date-walk-forward LV2 ranking score."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd
from strategy import signed_percentile_score, weighted_signed_percentile_score

HERE = Path(__file__).resolve().parent
FEATURES = (
    "gross_sell_float_ratio_pct",
    "active_sell_float_ratio_pct",
    "persistent_sell_float_ratio_pct",
    "persistent_sell_share_pct",
    "sell_cancel_ratio_pct",
    "sell_lifetime_mean_seconds",
    "sell_lifetime_median_seconds",
    "above_market_sell_share_pct",
    "above_market_sell_distance_bps",
    "sell_wall_refill_ratio_pct",
    "large_sell_cancel_ratio_pct",
    "aggressive_buy_3m_event_volume_pct",
    "max_aggressive_buy_3m_float_pct",
    "max_aggressive_buy_3m_volume_pct",
    "max_aggressive_buy_3m_prelaunch_sell_pct",
    "launch_absorption_ratio_pct",
    "churn_proxy_pct",
    "delta_ratio_pct",
    "large_order_net_flow_pct",
    "stacked_buy_imbalance_levels",
    "bullish_absorption_ratio_pct",
    "buy_refill_float_ratio_pct",
    "median_order_book_imbalance_pct",
)
TARGET_WEIGHTS = {"3d": 0.4, "1w": 0.6}
MIN_ABS_CORRELATION = 0.10
RIDGE_ALPHAS = (0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0)
BASELINE_DIRECTIONS = {
    "gross_sell_float_ratio_pct": -1,
    "active_sell_float_ratio_pct": -1,
    "sell_cancel_ratio_pct": -1,
    "delta_ratio_pct": -1,
    "large_order_net_flow_pct": -1,
    "buy_refill_float_ratio_pct": 1,
    "median_order_book_imbalance_pct": 1,
}


def spearman(left: pd.Series, right: pd.Series) -> float:
    values = pd.DataFrame({"left": np.asarray(left), "right": np.asarray(right)})
    values = values.dropna()
    if (
        len(values) < 2
        or values["left"].nunique() < 2
        or values["right"].nunique() < 2
    ):
        return float("nan")
    return values["left"].rank().corr(values["right"].rank())


def load_panel(end_date: str) -> pd.DataFrame:
    frames = []
    for path in sorted(HERE.glob("ambush_results_202609*.csv")):
        match = re.search(r"(202609\d{2})", path.name)
        if not match or match.group(1) > end_date:
            continue
        frame = pd.read_csv(path)
        frame["signal_date"] = match.group(1)
        frames.append(frame)
    if not frames:
        raise RuntimeError("No multi-date result files found")
    panel = pd.concat(frames, ignore_index=True)
    ranks = {}
    for feature in FEATURES:
        ranks[f"{feature}_rank"] = panel.groupby("signal_date")[feature].rank(
            method="average", pct=True
        )
    for horizon in TARGET_WEIGHTS:
        column = f"forward_{horizon}_pct"
        ranks[f"{horizon}_rank"] = panel.groupby("signal_date")[column].rank(
            method="average", pct=True
        )
    panel = pd.concat([panel, pd.DataFrame(ranks, index=panel.index)], axis=1)
    panel["target_rank"] = sum(
        weight * panel[f"{horizon}_rank"]
        for horizon, weight in TARGET_WEIGHTS.items()
    )
    return panel


def train_direction_model(panel: pd.DataFrame) -> dict:
    correlations = {
        feature: spearman(panel[f"{feature}_rank"], panel["target_rank"])
        for feature in FEATURES
    }
    selected = {
        feature: 1 if correlation > 0 else -1
        for feature, correlation in correlations.items()
        if abs(correlation) >= MIN_ABS_CORRELATION
    }
    if not selected:
        raise RuntimeError("No LV2 factor met the minimum training correlation")
    return {"correlations": correlations, "directions": selected}


def fit_ridge_weights(panel: pd.DataFrame, alpha: float) -> dict[str, float]:
    feature_columns = [f"{feature}_rank" for feature in FEATURES]
    design = panel[feature_columns].fillna(0.5).to_numpy() - 0.5
    target = panel["target_rank"].to_numpy() - 0.5
    penalty = alpha * np.eye(len(FEATURES))
    coefficients = np.linalg.solve(
        design.T @ design + penalty,
        design.T @ target,
    )
    return {
        feature: float(coefficient)
        for feature, coefficient in zip(FEATURES, coefficients)
    }


def train_ridge_model(panel: pd.DataFrame) -> dict:
    if panel["signal_date"].nunique() < 2:
        raise RuntimeError("Ridge training requires at least two signal dates")
    alpha_metrics = []
    for alpha in RIDGE_ALPHAS:
        fold_correlations = []
        for signal_date in sorted(panel["signal_date"].unique()):
            fold_train = panel[panel["signal_date"] != signal_date]
            fold_test = panel[panel["signal_date"] == signal_date]
            weights = fit_ridge_weights(fold_train, alpha)
            score = apply_weighted_model(fold_test, weights)
            fold_correlations.append(
                spearman(score, fold_test["target_rank"])
            )
        alpha_metrics.append(
            {
                "alpha": alpha,
                "mean_date_spearman": float(np.nanmean(fold_correlations)),
                "date_spearman": fold_correlations,
            }
        )
    selected = max(
        alpha_metrics,
        key=lambda row: (row["mean_date_spearman"], row["alpha"]),
    )
    return {
        "alpha": selected["alpha"],
        "weights": fit_ridge_weights(panel, selected["alpha"]),
        "alpha_cross_validation": alpha_metrics,
    }


def apply_direction_model(panel: pd.DataFrame, directions: dict[str, int]) -> pd.Series:
    return signed_percentile_score(panel, directions, group_column="signal_date")


def apply_weighted_model(panel: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    return weighted_signed_percentile_score(
        panel, weights, group_column="signal_date"
    )


def cross_validate_by_date(panel: pd.DataFrame) -> list[dict]:
    rows = []
    for signal_date in sorted(panel["signal_date"].unique()):
        fold_train = panel[panel["signal_date"] != signal_date]
        fold_test = panel[panel["signal_date"] == signal_date].copy()
        v3_model = train_direction_model(fold_train)
        v4_model = train_ridge_model(fold_train)
        fold_test["lv2_score_v3_cv"] = apply_direction_model(
            fold_test, v3_model["directions"]
        )
        fold_test["lv2_score_v4_cv"] = apply_weighted_model(
            fold_test, v4_model["weights"]
        )
        for score_column in ("lv2_score_v3_cv", "lv2_score_v4_cv"):
            rows.append(
                {
                    "signal_date": signal_date,
                    "score": score_column,
                    "sample_count": len(fold_test),
                    "factor_count": len(
                        v3_model["directions"]
                        if score_column == "lv2_score_v3_cv"
                        else v4_model["weights"]
                    ),
                    "target_spearman": spearman(
                        fold_test[score_column], fold_test["target_rank"]
                    ),
                }
            )
    return rows


def evaluate_score(panel: pd.DataFrame, score_column: str) -> list[dict]:
    rows = []
    for horizon in TARGET_WEIGHTS:
        return_column = f"forward_{horizon}_pct"
        labeled = panel.dropna(subset=[score_column, return_column])
        if labeled.empty:
            continue
        top_groups = []
        bottom_groups = []
        for _, group in labeled.groupby("signal_date"):
            top_count = (len(group) + 1) // 2
            top_groups.append(group.nlargest(top_count, score_column))
            bottom_count = len(group) - top_count
            if bottom_count:
                bottom_groups.append(group.nsmallest(bottom_count, score_column))
        top = pd.concat(top_groups)
        bottom = pd.concat(bottom_groups)
        rows.append(
            {
                "score": score_column,
                "horizon": horizon,
                "spearman": spearman(
                    labeled[score_column], labeled[return_column]
                ),
                "top_count": len(top),
                "top_mean_pct": top[return_column].mean(),
                "top_positive_rate_pct": (top[return_column] > 0).mean() * 100,
                "bottom_count": len(bottom),
                "bottom_mean_pct": bottom[return_column].mean(),
                "bottom_positive_rate_pct": (bottom[return_column] > 0).mean()
                * 100,
            }
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-through", default="20260908")
    parser.add_argument("--end-date", default="20260911")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    panel = load_panel(args.end_date)
    eligible = panel[
        panel["launch_detected"].astype(bool)
        & panel["data_quality_valid"].astype(bool)
    ].copy()
    train = eligible[
        (eligible["signal_date"] <= args.train_through)
        & eligible["target_rank"].notna()
    ].copy()
    holdout = eligible[eligible["signal_date"] > args.train_through].copy()
    if train.empty or holdout.empty:
        raise RuntimeError("Training and holdout date groups are both required")

    evaluation_model_v3 = train_direction_model(train)
    evaluation_model_v4 = train_ridge_model(train)
    holdout["lv2_score_v3"] = apply_direction_model(
        holdout, evaluation_model_v3["directions"]
    )
    holdout["lv2_score_v4"] = apply_weighted_model(
        holdout, evaluation_model_v4["weights"]
    )
    holdout["lv2_score_v2_baseline"] = apply_direction_model(
        holdout, BASELINE_DIRECTIONS
    )
    evaluation_rows = evaluate_score(holdout, "lv2_score")
    evaluation_rows += evaluate_score(holdout, "lv2_score_v2_baseline")
    evaluation_rows += evaluate_score(holdout, "lv2_score_v3")
    evaluation_rows += evaluate_score(holdout, "lv2_score_v4")

    production_weights = evaluation_model_v4["weights"]
    production_directions = {
        feature: 1 if weight > 0 else -1
        for feature, weight in production_weights.items()
    }
    panel["lv2_score_v3_fitted"] = np.nan
    panel.loc[eligible.index, "lv2_score_v3_fitted"] = apply_direction_model(
        eligible, evaluation_model_v3["directions"]
    )
    panel["lv2_score_v3_holdout"] = np.nan
    panel.loc[holdout.index, "lv2_score_v3_holdout"] = holdout["lv2_score_v3"]
    panel["lv2_score_v4_fitted"] = np.nan
    panel.loc[eligible.index, "lv2_score_v4_fitted"] = apply_weighted_model(
        eligible, production_weights
    )
    panel["lv2_score_v4_holdout"] = np.nan
    panel.loc[holdout.index, "lv2_score_v4_holdout"] = holdout["lv2_score_v4"]
    cross_validation = cross_validate_by_date(train)

    model = {
        "version": 4,
        "method": "date_cross_validated_ridge_within_date_percentile",
        "trained_from": min(panel["signal_date"]),
        "trained_through": args.train_through,
        "validated_through": args.end_date,
        "sample_count": len(train),
        "candidate_count": len(panel),
        "eligible_count": len(eligible),
        "date_count": train["signal_date"].nunique(),
        "eligibility": "launch_detected and data_quality_valid",
        "target_rank_weights": TARGET_WEIGHTS,
        "minimum_absolute_training_spearman": MIN_ABS_CORRELATION,
        "ridge_alpha_candidates": RIDGE_ALPHAS,
        "selected_ridge_alpha": evaluation_model_v4["alpha"],
        "production_directions": production_directions,
        "production_weights": production_weights,
        "ridge_alpha_cross_validation": evaluation_model_v4[
            "alpha_cross_validation"
        ],
        "training_date_leave_one_out": cross_validation,
        "holdout": {
            "train_through": args.train_through,
            "dates": sorted(holdout["signal_date"].unique()),
            "sample_count": len(holdout),
            "v3_directions": evaluation_model_v3["directions"],
            "v4_weights": production_weights,
            "metrics": evaluation_rows,
        },
    }
    (HERE / "lv2_score_model.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    panel.to_csv(
        HERE / f"ambush_lv2_training_panel_{min(panel['signal_date'])}_{args.end_date}.csv",
        index=False,
        encoding="utf-8-sig",
    )
    evaluation = pd.DataFrame(evaluation_rows)
    evaluation.to_csv(
        HERE / f"ambush_lv2_optimization_{args.end_date}.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print(evaluation.to_string(index=False, float_format=lambda value: f"{value:.3f}"))
    print("Production weights:")
    for feature, weight in production_weights.items():
        print(f"  {feature}: {weight:+g}")


if __name__ == "__main__":
    main()
