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
V5_FEATURES = (
    "opening_buy_order_volume_pct",
    "opening_buy_fill_ratio_pct",
    "opening_buy_filled_volume_pct",
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


def load_panel(start_date: str, end_date: str) -> pd.DataFrame:
    frames = []
    for path in sorted(HERE.glob("ambush_results_*.csv")):
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
    for feature in (*FEATURES, *V5_FEATURES):
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


def fit_ridge_weights(
    panel: pd.DataFrame,
    alpha: float,
    features: tuple[str, ...] = FEATURES,
) -> dict[str, float]:
    feature_columns = [f"{feature}_rank" for feature in features]
    design = panel[feature_columns].fillna(0.5).to_numpy() - 0.5
    target = panel["target_rank"].to_numpy() - 0.5
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
    alpha_metrics = []
    for alpha in RIDGE_ALPHAS:
        fold_correlations = []
        for signal_date in sorted(panel["signal_date"].unique()):
            fold_train = panel[panel["signal_date"] != signal_date]
            fold_test = panel[panel["signal_date"] == signal_date]
            weights = fit_ridge_weights(fold_train, alpha, features)
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
    include_v5: bool = False,
) -> list[dict]:
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
        if include_v5 and features_are_trainable(fold_train, V5_FEATURES):
            v5_model = train_ridge_model(fold_train, V5_FEATURES)
            fold_test["lv2_score_v5_cv"] = apply_weighted_model(
                fold_test, v5_model["weights"]
            )
            score_models["lv2_score_v5_cv"] = v5_model["weights"]
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
                "ic": pearson(labeled[score_column], labeled[return_column]),
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
    parser.add_argument("--train-from", default="20260601")
    parser.add_argument("--train-through", default="20260731")
    parser.add_argument("--test-through", default="20260831")
    parser.add_argument("--validation-through", default="20260930")
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
    v5_model: dict | None,
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
    scored["lv2_score_v5"] = np.nan
    if v5_model:
        scored["lv2_score_v5"] = apply_weighted_model(
            scored, v5_model["weights"]
        )
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
        or column in {"3d_rank", "1w_rank", "target_rank"}
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
    evaluation_model_v5 = (
        train_ridge_model(train, V5_FEATURES)
        if features_are_trainable(train, V5_FEATURES)
        else None
    )
    test = apply_models(
        test,
        evaluation_model_v3,
        evaluation_model_v4,
        evaluation_model_v5,
    )
    validation = apply_models(
        validation,
        evaluation_model_v3,
        evaluation_model_v4,
        evaluation_model_v5,
    )
    evaluation_rows = evaluate_score(test, "lv2_score")
    evaluation_rows += evaluate_score(test, "lv2_score_v2_baseline")
    evaluation_rows += evaluate_score(test, "lv2_score_v3")
    evaluation_rows += evaluate_score(test, "lv2_score_v4")
    if evaluation_model_v5:
        evaluation_rows += evaluate_score(test, "lv2_score_v5")

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
    if evaluation_model_v5:
        selectable_models["lv2_score_v5"] = {
            "version": 5,
            "method": "opening_buy_layout_date_cross_validated_ridge",
            "parameters": evaluation_model_v5["weights"],
            "ridge": evaluation_model_v5,
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
    for score_column in (
        "lv2_score_v2_baseline",
        "lv2_score_v3",
        "lv2_score_v4",
        "lv2_score_v5",
    ):
        panel[score_column] = np.nan
        panel.loc[test.index, score_column] = test[score_column]
        panel.loc[validation.index, score_column] = validation[score_column]
    cross_validation = cross_validate_by_date(
        train,
        include_v5=evaluation_model_v5 is not None,
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
                evaluation_model_v5["weights"]
                if evaluation_model_v5
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
        HERE
        / (
            f"ambush_lv2_training_panel_{min(panel['signal_date'])}_"
            f"{args.validation_through}.csv"
        ),
        index=False,
        encoding="utf-8-sig",
    )
    evaluation = pd.DataFrame(evaluation_rows)
    evaluation.to_csv(
        HERE / f"ambush_lv2_test_evaluation_{args.test_through}.csv",
        index=False,
        encoding="utf-8-sig",
    )
    print(evaluation.to_string(index=False, float_format=lambda value: f"{value:.3f}"))
    print("Production weights:")
    for feature, weight in production_weights.items():
        print(f"  {feature}: {weight:+g}")


if __name__ == "__main__":
    main()
