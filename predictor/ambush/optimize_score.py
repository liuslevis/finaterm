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
DATA_DIR = HERE / "data"
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
V5_FEATURES = (
    "opening_buy_order_volume_pct",
    "opening_buy_fill_ratio_pct",
    "opening_buy_filled_volume_pct",
)
V6_FEATURES = (
    "small_buy_volume_share_pct",
    "split_order_size_concentration_pct",
    "split_order_interval_entropy",
    "odd_price_buy_volume_share_pct",
    "large_buy_cancel_gap_pct",
    "bid_support_dwell_ratio_pct",
    "passive_sell_absorb_ratio_pct",
    "wash_trade_volume_pct",
    "equal_size_streak_volume_pct",
    "flat_price_volume_share_pct",
    "probe_pulse_count",
    "probe_pullback_volume_ratio_pct",
    "down_day_volume_ratio_20d",
    "max_drawdown_60d_pct",
)
EXTRA_FEATURE_SETS = {
    "lv2_score_v5": V5_FEATURES,
    "lv2_score_v6": V6_FEATURES,
}
TARGET_WEIGHTS = {"3d": 0.4, "1w": 0.6}
EVALUATION_HORIZONS = ("3d", "1w", "3w")
MIN_ABS_CORRELATION = 0.10
MIN_DAILY_CROSS_SECTION = 3
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


def pearson(left: pd.Series, right: pd.Series) -> float:
    values = pd.DataFrame({"left": np.asarray(left), "right": np.asarray(right)})
    values = values.dropna()
    if (
        len(values) < 2
        or values["left"].nunique() < 2
        or values["right"].nunique() < 2
    ):
        return float("nan")
    return values["left"].corr(values["right"])


def centered_feature_ranks(
    panel: pd.DataFrame,
    features: tuple[str, ...],
) -> pd.DataFrame:
    """Demean each day's percentile ranks inside that day's cross-section.

    ``rank(pct=True)`` returns 1.0 for a single-candidate day, so subtracting a
    constant 0.5 turns those rows into an all-positive constant design row that
    biases every ridge weight toward the same sign. Subtracting the day's own
    mean rank makes thin cross-sections contribute nothing instead.
    """
    columns = [f"{feature}_rank" for feature in features]
    ranks = panel[columns]
    means = ranks.groupby(panel["signal_date"]).transform("mean")
    return (ranks.fillna(means) - means).fillna(0.0)


def centered_target_rank(panel: pd.DataFrame) -> pd.Series:
    target = panel["target_rank"]
    means = target.groupby(panel["signal_date"]).transform("mean")
    return (target - means).fillna(0.0)


def has_cross_sectional_variation(
    panel: pd.DataFrame,
    features: tuple[str, ...],
) -> bool:
    design = centered_feature_ranks(panel, features)
    return bool(
        np.any(np.abs(design.to_numpy()) > 1e-9)
        and np.any(np.abs(centered_target_rank(panel).to_numpy()) > 1e-9)
    )


def daily_rank_ic(
    panel: pd.DataFrame,
    score_column: str,
    return_column: str,
) -> dict[str, float]:
    """Average the per-day rank IC instead of pooling every day together.

    Scores are day-local percentiles while returns are absolute, so a pooled
    Spearman mixes cross-day return drift into the ranking metric.
    """
    values = []
    for _, group in panel.groupby("signal_date"):
        if len(group) < MIN_DAILY_CROSS_SECTION:
            continue
        correlation = spearman(group[score_column], group[return_column])
        if not pd.isna(correlation):
            values.append(correlation)
    if not values:
        return {
            "daily_ic_mean": float("nan"),
            "daily_ic_std": float("nan"),
            "daily_ic_t": float("nan"),
            "daily_ic_days": 0,
        }
    series = pd.Series(values)
    std = float(series.std(ddof=1)) if len(series) > 1 else float("nan")
    mean = float(series.mean())
    t_stat = (
        mean / (std / np.sqrt(len(series)))
        if std and not pd.isna(std) and std > 0
        else float("nan")
    )
    return {
        "daily_ic_mean": mean,
        "daily_ic_std": std,
        "daily_ic_t": float(t_stat),
        "daily_ic_days": len(series),
    }


def load_panel(start_date: str, end_date: str) -> pd.DataFrame:
    frames = []
    for path in sorted(DATA_DIR.glob("ambush_results_*.csv")):
        match = re.fullmatch(r"ambush_results_(\d{8})\.csv", path.name)
        if not match or not start_date <= match.group(1) <= end_date:
            continue
        frame = pd.read_csv(path)
        frame["signal_date"] = match.group(1)
        frames.append(frame)
    if not frames:
        raise RuntimeError("No multi-date result files found")
    panel = pd.concat(frames, ignore_index=True)
    ranks = {}
    for feature in (*FEATURES, *V5_FEATURES, *V6_FEATURES):
        ranks[f"{feature}_rank"] = panel.groupby("signal_date")[feature].rank(
            method="average", pct=True
        )
    for horizon in EVALUATION_HORIZONS:
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
    design = centered_feature_ranks(panel, FEATURES)
    target = centered_target_rank(panel)
    correlations = {
        feature: spearman(design[f"{feature}_rank"], target)
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


def fit_ridge_weights(
    panel: pd.DataFrame,
    alpha: float,
    features: tuple[str, ...] = FEATURES,
) -> dict[str, float]:
    design = centered_feature_ranks(panel, features).to_numpy()
    target = centered_target_rank(panel).to_numpy()
    penalty = alpha * np.eye(len(features))
    coefficients = np.linalg.solve(
        design.T @ design + penalty,
        design.T @ target,
    )
    return {
        feature: float(coefficient)
        for feature, coefficient in zip(features, coefficients)
    }


def features_are_trainable(
    panel: pd.DataFrame,
    features: tuple[str, ...],
) -> bool:
    return all(
        panel[f"{feature}_rank"].notna().sum() >= 2 for feature in features
    ) and any(
        panel[f"{feature}_rank"].nunique(dropna=True) >= 2
        for feature in features
    )


def train_ridge_model(
    panel: pd.DataFrame,
    features: tuple[str, ...] = FEATURES,
) -> dict:
    if panel["signal_date"].nunique() < 2:
        raise RuntimeError("Ridge training requires at least two signal dates")
    if not features_are_trainable(panel, features):
        raise RuntimeError("Ridge features lack sufficient non-constant training data")
    if not has_cross_sectional_variation(panel, features):
        raise RuntimeError(
            "Ridge features lack within-day cross-sectional variation"
        )
    alpha_metrics = []
    for alpha in RIDGE_ALPHAS:
        fold_correlations = []
        for signal_date in sorted(panel["signal_date"].unique()):
            fold_train = panel[panel["signal_date"] != signal_date]
            fold_test = panel[panel["signal_date"] == signal_date]
            if len(fold_test) < MIN_DAILY_CROSS_SECTION:
                continue
            weights = fit_ridge_weights(fold_train, alpha, features)
            score = apply_weighted_model(fold_test, weights)
            fold_correlations.append(
                spearman(score, fold_test["target_rank"])
            )
        alpha_metrics.append(
            {
                "alpha": alpha,
                "mean_date_spearman": (
                    float(np.nanmean(fold_correlations))
                    if fold_correlations
                    else float("nan")
                ),
                "date_spearman": fold_correlations,
            }
        )
    scored_alphas = [
        row for row in alpha_metrics if not pd.isna(row["mean_date_spearman"])
    ]
    selected = (
        max(
            scored_alphas,
            key=lambda row: (row["mean_date_spearman"], row["alpha"]),
        )
        if scored_alphas
        else alpha_metrics[-1]
    )
    return {
        "alpha": selected["alpha"],
        "weights": fit_ridge_weights(panel, selected["alpha"], features),
        "alpha_cross_validation": alpha_metrics,
    }


def apply_direction_model(panel: pd.DataFrame, directions: dict[str, int]) -> pd.Series:
    return signed_percentile_score(panel, directions, group_column="signal_date")


def apply_weighted_model(panel: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    return weighted_signed_percentile_score(
        panel, weights, group_column="signal_date"
    )


def cross_validate_by_date(
    panel: pd.DataFrame,
    extra_feature_sets: dict[str, tuple[str, ...]] | None = None,
) -> list[dict]:
    extra_feature_sets = extra_feature_sets or {}
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
        score_models = {
            "lv2_score_v3_cv": v3_model["directions"],
            "lv2_score_v4_cv": v4_model["weights"],
        }
        for score_name, features in extra_feature_sets.items():
            if not features_are_trainable(fold_train, features):
                continue
            extra_model = train_ridge_model(fold_train, features)
            fold_test[f"{score_name}_cv"] = apply_weighted_model(
                fold_test, extra_model["weights"]
            )
            score_models[f"{score_name}_cv"] = extra_model["weights"]
        for score_column, parameters in score_models.items():
            rows.append(
                {
                    "signal_date": signal_date,
                    "score": score_column,
                    "sample_count": len(fold_test),
                    "factor_count": len(parameters),
                    "target_spearman": spearman(
                        fold_test[score_column], fold_test["target_rank"]
                    ),
                }
            )
    return rows


def evaluate_score(panel: pd.DataFrame, score_column: str) -> list[dict]:
    rows = []
    for horizon in EVALUATION_HORIZONS:
        return_column = f"forward_{horizon}_pct"
        if return_column not in panel:
            continue
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
                "ic": pearson(labeled[score_column], labeled[return_column]),
                **daily_rank_ic(labeled, score_column, return_column),
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


def evaluate_all_scores(
    panel: pd.DataFrame,
    extra_models: dict[str, dict | None],
) -> list[dict]:
    rows = evaluate_score(panel, "lv2_score")
    rows += evaluate_score(panel, "lv2_score_v2_baseline")
    rows += evaluate_score(panel, "lv2_score_v3")
    rows += evaluate_score(panel, "lv2_score_v4")
    for score_name, model in extra_models.items():
        fixed_column = f"{score_name}_fixed"
        if fixed_column in panel:
            rows += evaluate_score(panel, fixed_column)
        if model:
            rows += evaluate_score(panel, score_name)
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-from", default="20260601")
    parser.add_argument("--train-through", default="20260731")
    parser.add_argument("--test-through", default="20260831")
    parser.add_argument("--validation-through", default="20260930")
    parser.add_argument(
        "--evaluate-validation",
        action="store_true",
        help=(
            "Unblind the validation period and write its evaluation CSV; "
            "model selection and lv2_score_model.json stay unchanged"
        ),
    )
    return parser.parse_args()


def split_datasets(
    panel: pd.DataFrame,
    train_from: str,
    train_through: str,
    test_through: str,
    validation_through: str,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not train_from <= train_through < test_through < validation_through:
        raise ValueError(
            "Expected train_from <= train_through < test_through "
            "< validation_through"
        )
    train = panel[
        (panel["signal_date"] >= train_from)
        & (panel["signal_date"] <= train_through)
        & panel["target_rank"].notna()
    ].copy()
    test = panel[
        (panel["signal_date"] > train_through)
        & (panel["signal_date"] <= test_through)
    ].copy()
    validation = panel[
        (panel["signal_date"] > test_through)
        & (panel["signal_date"] <= validation_through)
    ].copy()
    return train, test, validation


def apply_models(
    panel: pd.DataFrame,
    v3_model: dict,
    v4_model: dict,
    extra_models: dict[str, dict | None],
) -> pd.DataFrame:
    scored = panel.copy()
    scored["lv2_score_v2_baseline"] = apply_direction_model(
        scored, BASELINE_DIRECTIONS
    )
    scored["lv2_score_v3"] = apply_direction_model(
        scored, v3_model["directions"]
    )
    scored["lv2_score_v4"] = apply_weighted_model(
        scored, v4_model["weights"]
    )
    for score_name, model in extra_models.items():
        if score_name in scored:
            scored[f"{score_name}_fixed"] = scored[score_name]
        scored[score_name] = np.nan
        if model:
            scored[score_name] = apply_weighted_model(scored, model["weights"])
    return scored


def select_production_model(
    evaluation_rows: list[dict],
    models: dict[str, dict],
) -> tuple[str, dict]:
    evaluation = pd.DataFrame(evaluation_rows)
    weighted_spearman = {}
    for score_name in models:
        rows = evaluation[evaluation["score"] == score_name].set_index("horizon")
        if not all(horizon in rows.index for horizon in TARGET_WEIGHTS):
            continue
        values = [rows.loc[horizon, "spearman"] for horizon in TARGET_WEIGHTS]
        if any(pd.isna(value) for value in values):
            continue
        weighted_spearman[score_name] = sum(
            TARGET_WEIGHTS[horizon] * rows.loc[horizon, "spearman"]
            for horizon in TARGET_WEIGHTS
        )
    if not weighted_spearman:
        raise RuntimeError("No model has complete 3D and 1W test metrics")
    selected = max(weighted_spearman, key=weighted_spearman.get)
    return selected, models[selected]


def blind_validation_labels(panel: pd.DataFrame) -> pd.DataFrame:
    blinded = panel.copy()
    validation_mask = blinded["dataset_split"] == "validation"
    label_columns = [
        column
        for column in blinded
        if column.startswith("forward_")
        or column in {"3d_rank", "1w_rank", "3w_rank", "target_rank"}
    ]
    blinded.loc[validation_mask, label_columns] = np.nan
    return blinded


def main() -> None:
    args = parse_args()
    panel = load_panel(args.train_from, args.validation_through)
    eligible = panel[
        panel["launch_detected"].astype(bool)
        & panel["data_quality_valid"].astype(bool)
    ].copy()
    train, test, validation = split_datasets(
        eligible,
        args.train_from,
        args.train_through,
        args.test_through,
        args.validation_through,
    )
    if train.empty or test.empty or validation.empty:
        raise RuntimeError(
            "Training, test, and validation date groups are all required"
        )

    evaluation_model_v3 = train_direction_model(train)
    evaluation_model_v4 = train_ridge_model(train)
    extra_models = {
        score_name: (
            train_ridge_model(train, features)
            if features_are_trainable(train, features)
            else None
        )
        for score_name, features in EXTRA_FEATURE_SETS.items()
    }
    test = apply_models(
        test,
        evaluation_model_v3,
        evaluation_model_v4,
        extra_models,
    )
    validation = apply_models(
        validation,
        evaluation_model_v3,
        evaluation_model_v4,
        extra_models,
    )
    evaluation_rows = evaluate_all_scores(test, extra_models)

    selectable_models = {
        "lv2_score_v2_baseline": {
            "version": 2,
            "method": "fixed_direction_baseline",
            "parameters": BASELINE_DIRECTIONS,
        },
        "lv2_score_v3": {
            "version": 3,
            "method": "training_spearman_selected_directions",
            "parameters": evaluation_model_v3["directions"],
        },
        "lv2_score_v4": {
            "version": 4,
            "method": "date_cross_validated_ridge",
            "parameters": evaluation_model_v4["weights"],
            "ridge": evaluation_model_v4,
        },
    }
    extra_methods = {
        "lv2_score_v5": (
            5,
            "opening_buy_layout_date_cross_validated_ridge",
        ),
        "lv2_score_v6": (
            6,
            "covert_accumulation_wash_trade_date_cross_validated_ridge",
        ),
    }
    for score_name, model in extra_models.items():
        if not model:
            continue
        version, method = extra_methods[score_name]
        selectable_models[score_name] = {
            "version": version,
            "method": method,
            "parameters": model["weights"],
            "ridge": model,
        }
    production_score, production_model = select_production_model(
        evaluation_rows,
        selectable_models,
    )
    production_weights = production_model["parameters"]
    production_directions = {
        feature: 1 if weight > 0 else -1
        for feature, weight in production_weights.items()
    }
    panel["dataset_split"] = "excluded"
    panel.loc[train.index, "dataset_split"] = "train"
    panel.loc[test.index, "dataset_split"] = "test"
    panel.loc[validation.index, "dataset_split"] = "validation"
    for score_name in EXTRA_FEATURE_SETS:
        if score_name in panel:
            panel[f"{score_name}_fixed"] = panel[score_name]
    for score_column in (
        "lv2_score_v2_baseline",
        "lv2_score_v3",
        "lv2_score_v4",
        *EXTRA_FEATURE_SETS,
    ):
        panel[score_column] = np.nan
        panel.loc[test.index, score_column] = test[score_column]
        panel.loc[validation.index, score_column] = validation[score_column]
    cross_validation = cross_validate_by_date(
        train,
        {
            score_name: EXTRA_FEATURE_SETS[score_name]
            for score_name, model in extra_models.items()
            if model
        },
    )

    model = {
        "version": production_model["version"],
        "method": production_model["method"],
        "production_score": production_score,
        "trained_from": args.train_from,
        "trained_through": args.train_through,
        "available_after": args.train_through,
        "tested_through": args.test_through,
        "validation_through": args.validation_through,
        "sample_count": len(train),
        "candidate_count": len(panel),
        "eligible_count": len(eligible),
        "date_count": train["signal_date"].nunique(),
        "eligibility": "launch_detected and data_quality_valid",
        "target_rank_weights": TARGET_WEIGHTS,
        "evaluation_horizons": list(EVALUATION_HORIZONS),
        "minimum_absolute_training_spearman": MIN_ABS_CORRELATION,
        "ridge_alpha_candidates": RIDGE_ALPHAS,
        "features": list(production_weights),
        "production_directions": production_directions,
        "production_weights": production_weights,
        "training_date_leave_one_out": cross_validation,
        "test": {
            "train_through": args.train_through,
            "dates": sorted(test["signal_date"].unique()),
            "sample_count": len(test),
            "v3_directions": evaluation_model_v3["directions"],
            "v4_weights": evaluation_model_v4["weights"],
            "v5_weights": (
                extra_models["lv2_score_v5"]["weights"]
                if extra_models.get("lv2_score_v5")
                else None
            ),
            "v6_weights": (
                extra_models["lv2_score_v6"]["weights"]
                if extra_models.get("lv2_score_v6")
                else None
            ),
            "metrics": evaluation_rows,
        },
        "validation": {
            "from": (
                pd.Timestamp(args.test_through) + pd.Timedelta(days=1)
            ).strftime("%Y%m%d"),
            "through": args.validation_through,
            "status": "withheld_for_final_evaluation",
        },
    }
    if "ridge" in production_model:
        model["selected_ridge_alpha"] = production_model["ridge"]["alpha"]
        model["ridge_alpha_cross_validation"] = production_model["ridge"][
            "alpha_cross_validation"
        ]
    (HERE / "lv2_score_model.json").write_text(
        json.dumps(model, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    blinded_panel = blind_validation_labels(panel)
    blinded_panel.to_csv(
        DATA_DIR
        / (
            f"ambush_lv2_training_panel_{min(panel['signal_date'])}_"
            f"{args.validation_through}.csv"
        ),
        index=False,
        encoding="utf-8-sig",
    )
    evaluation = pd.DataFrame(evaluation_rows)
    evaluation.to_csv(
        DATA_DIR / f"ambush_lv2_test_evaluation_{args.test_through}.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print(evaluation.to_string(index=False, float_format=lambda value: f"{value:.3f}"))
    print("Production weights:")
    for feature, weight in production_weights.items():
        print(f"  {feature}: {weight:+g}")
    if args.evaluate_validation:
        validation_rows = evaluate_all_scores(validation, extra_models)
        validation_evaluation = pd.DataFrame(validation_rows)
        validation_evaluation.to_csv(
            DATA_DIR
            / f"ambush_lv2_validation_evaluation_{args.validation_through}.csv",
            index=False,
            encoding="utf-8-sig",
        )
        print(
            f"Validation evaluation ({min(validation['signal_date'])}-"
            f"{max(validation['signal_date'])}, "
            f"{len(validation)} samples):"
        )
        print(
            validation_evaluation.to_string(
                index=False, float_format=lambda value: f"{value:.3f}"
            )
        )


if __name__ == "__main__":
    main()
