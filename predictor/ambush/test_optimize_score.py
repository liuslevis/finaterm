import math

import pandas as pd
import pytest
from strategy import SOL61_GROUPS

from optimize_score import (
    FEATURES,
    V5_FEATURES,
    V6_FEATURES,
    apply_weighted_model,
    blind_validation_labels,
    centered_feature_ranks,
    daily_rank_ic,
    evaluate_score,
    features_are_trainable,
    fit_ridge_weights,
    json_compatible,
    rank_panel,
    select_production_model,
    split_datasets,
    train_ridge_model,
    walk_forward_folds,
)


def test_ridge_model_learns_positive_monotonic_factor():
    rows = []
    for date in ("20260901", "20260902", "20260903"):
        for rank in (0.25, 0.5, 0.75):
            row = {
                "signal_date": date,
                "target_rank": rank,
                **{feature: 0.5 for feature in FEATURES},
                **{f"{feature}_rank": 0.5 for feature in FEATURES},
            }
            row[FEATURES[0]] = rank
            row[f"{FEATURES[0]}_rank"] = rank
            rows.append(row)
    panel = pd.DataFrame(rows)

    model = train_ridge_model(panel)
    score = apply_weighted_model(panel, model["weights"])

    assert model["weights"][FEATURES[0]] > 0
    assert score.iloc[2] > score.iloc[0]


def test_v5_ridge_only_uses_opening_layout_factors():
    rows = []
    for date in ("20260630", "20260701", "20260702"):
        for rank in (0.25, 0.5, 0.75):
            row = {
                "signal_date": date,
                "target_rank": rank,
                **{feature: 0.5 for feature in V5_FEATURES},
                **{f"{feature}_rank": 0.5 for feature in V5_FEATURES},
            }
            row[V5_FEATURES[0]] = rank
            row[f"{V5_FEATURES[0]}_rank"] = rank
            rows.append(row)

    model = train_ridge_model(pd.DataFrame(rows), V5_FEATURES)

    assert set(model["weights"]) == set(V5_FEATURES)
    assert model["weights"][V5_FEATURES[0]] > 0


def test_missing_v5_history_is_not_trainable():
    panel = pd.DataFrame(
        {
            **{f"{feature}_rank": [float("nan"), 0.5] for feature in V5_FEATURES}
        }
    )

    assert not features_are_trainable(panel, V5_FEATURES)


def test_evaluation_reports_pearson_ic():
    panel = pd.DataFrame(
        {
            "signal_date": ["20260901"] * 3,
            "model_score": [1.0, 2.0, 3.0],
            "forward_3d_pct": [1.0, 4.0, 9.0],
            "forward_1w_pct": [float("nan")] * 3,
        }
    )

    rows = evaluate_score(panel, "model_score")

    assert len(rows) == 1
    assert rows[0]["horizon"] == "3d"
    assert math.isclose(rows[0]["spearman"], 1.0)
    assert math.isclose(rows[0]["ic"], 0.989743318610787)


def test_three_way_date_split_keeps_validation_labels_out_of_training():
    panel = pd.DataFrame(
        {
            "signal_date": [
                "20260601",
                "20260731",
                "20260801",
                "20260831",
                "20260901",
                "20260930",
            ],
            "target_rank": [0.1, 0.2, 0.3, 0.4, 0.5, float("nan")],
        }
    )

    train, test, validation = split_datasets(
        panel,
        "20260601",
        "20260731",
        "20260831",
        "20260930",
    )

    assert train["signal_date"].tolist() == ["20260601", "20260731"]
    assert test["signal_date"].tolist() == ["20260801", "20260831"]
    assert validation["signal_date"].tolist() == ["20260901", "20260930"]


def test_validation_export_hides_returns_and_target_but_keeps_score():
    panel = pd.DataFrame(
        {
            "dataset_split": ["test", "validation"],
            "forward_3d_pct": [1.0, 2.0],
            "3d_rank": [0.5, 1.0],
            "target_rank": [0.5, 1.0],
            "lv2_score_v5": [25.0, 75.0],
        }
    )

    blinded = blind_validation_labels(panel)

    assert blinded.loc[0, "forward_3d_pct"] == 1.0
    assert pd.isna(blinded.loc[1, "forward_3d_pct"])
    assert pd.isna(blinded.loc[1, "3d_rank"])
    assert pd.isna(blinded.loc[1, "target_rank"])
    assert blinded.loc[1, "lv2_score_v5"] == 75.0


def test_production_model_uses_daily_ic_not_pooled_spearman():
    rows = [
        {"score": "v3", "horizon": "3d", "spearman": 0.9, "daily_ic_mean": 0.2},
        {"score": "v3", "horizon": "1w", "spearman": 0.9, "daily_ic_mean": 0.1},
        {"score": "v4", "horizon": "3d", "spearman": 0.1, "daily_ic_mean": 0.1},
        {"score": "v4", "horizon": "1w", "spearman": 0.1, "daily_ic_mean": 0.3},
    ]
    models = {"v3": {"version": 3}, "v4": {"version": 4}}

    name, model = select_production_model(rows, models)

    assert name == "v4"
    assert model["version"] == 4


def _single_candidate_day(date: str) -> dict:
    return {
        "signal_date": date,
        "target_rank": 1.0,
        **{f"{feature}_rank": 1.0 for feature in FEATURES},
    }


def test_single_candidate_day_is_centered_to_zero():
    panel = pd.DataFrame([_single_candidate_day("20260901")])

    design = centered_feature_ranks(panel, FEATURES)

    assert (design.abs().to_numpy() < 1e-12).all()


def test_single_candidate_days_do_not_shift_ridge_weights():
    rows = []
    for date in ("20260901", "20260902", "20260903"):
        for rank in (0.25, 0.5, 0.75):
            row = {
                "signal_date": date,
                "target_rank": rank,
                **{f"{feature}_rank": 0.5 for feature in FEATURES},
            }
            row[f"{FEATURES[0]}_rank"] = rank
            rows.append(row)
    panel = pd.DataFrame(rows)
    padded = pd.DataFrame(
        rows + [_single_candidate_day(f"2026090{index}") for index in (4, 5, 6)]
    )

    clean = fit_ridge_weights(panel, 1.0, FEATURES)
    padded_weights = fit_ridge_weights(padded, 1.0, FEATURES)

    for feature in FEATURES:
        assert math.isclose(
            clean[feature], padded_weights[feature], abs_tol=1e-12
        )


def test_daily_rank_ic_skips_thin_cross_sections():
    panel = pd.DataFrame(
        {
            "signal_date": ["20260901"] * 3 + ["20260902"] * 2,
            "model_score": [1.0, 2.0, 3.0, 1.0, 2.0],
            "forward_3d_pct": [1.0, 2.0, 3.0, 3.0, 1.0],
        }
    )

    metrics = daily_rank_ic(panel, "model_score", "forward_3d_pct")

    assert metrics["daily_ic_days"] == 1
    assert math.isclose(metrics["daily_ic_mean"], 1.0)


def test_evaluation_reports_daily_rank_ic_columns():
    panel = pd.DataFrame(
        {
            "signal_date": ["20260901"] * 3 + ["20260902"] * 3,
            "model_score": [1.0, 2.0, 3.0, 1.0, 2.0, 3.0],
            "forward_3d_pct": [1.0, 2.0, 3.0, 3.0, 2.0, 1.0],
            "forward_1w_pct": [float("nan")] * 6,
        }
    )

    rows = evaluate_score(panel, "model_score")

    assert rows[0]["daily_ic_days"] == 2
    assert math.isclose(rows[0]["daily_ic_mean"], 0.0)


def _monotonic_panel():
    rows = []
    for date in ("20260701", "20260702", "20260703", "20260706", "20260707"):
        for rank in (1 / 3, 2 / 3, 1.0):
            rows.append({
                "signal_date": date, "target_rank": rank,
                "target_available_date": date,
                **{feature: rank for feature in FEATURES},
                **{f"{feature}_rank": rank for feature in FEATURES},
            })
    return pd.DataFrame(rows)


def test_walk_forward_never_uses_future_or_unmatured_labels():
    panel = _monotonic_panel()
    panel.loc[panel["signal_date"] == "20260702", "target_available_date"] = "20260706"
    folds = list(walk_forward_folds(panel, FEATURES))
    assert folds
    for date, train, test in folds:
        assert (train["signal_date"] < date).all()
        assert (train["target_available_date"] < date).all()
        assert (test["signal_date"] == date).all()


def test_training_split_purges_labels_crossing_cutoff():
    panel = _monotonic_panel()
    panel.loc[0, "target_available_date"] = "20260803"
    train, _, _ = split_datasets(
        panel, "20260701", "20260731", "20260831", "20260930"
    )
    assert 0 not in train.index


def test_future_label_changes_do_not_change_earlier_fold_fit():
    panel = _monotonic_panel()
    _, train, _ = next(walk_forward_folds(panel, FEATURES))
    expected = fit_ridge_weights(train, 1.0)
    mutated = panel.copy()
    mutated.loc[mutated.signal_date > train.signal_date.max(), "target_rank"] = -999
    _, changed_train, _ = next(walk_forward_folds(mutated, FEATURES))
    assert fit_ridge_weights(changed_train, 1.0) == expected


def test_v7_shrinks_to_equal_economic_blocks_and_ignores_thin_days():
    features = tuple(SOL61_GROUPS)
    rows = []
    for date in ("20260701", "20260702"):
        for rank in (1 / 3, 2 / 3, 1.0):
            rows.append({
                "signal_date": date, "target_rank": rank,
                **{feature: rank for feature in features},
                **{f"{feature}_rank": rank for feature in features},
            })
    panel = pd.DataFrame(rows)
    weights = fit_ridge_weights(panel, 100.0, features)
    assert all(weight == pytest.approx(1 / 3) for weight in weights.values())
    padded = pd.concat([panel, pd.DataFrame([{
        "signal_date": "20260703", "target_rank": 0,
        **{f"{feature}_rank": 1 for feature in features},
    }])], ignore_index=True)
    assert fit_ridge_weights(padded, 100.0, features) == weights


def test_fewer_than_three_walk_forward_folds_uses_max_shrinkage():
    model = train_ridge_model(_monotonic_panel().iloc[:9])
    assert model["alpha"] == 100.0
    assert model["alpha_selection"] == "insufficient_folds_max_shrinkage"


def test_evaluation_handles_only_single_candidate_days():
    panel = pd.DataFrame({
        "signal_date": ["20260701", "20260702"],
        "score": [100, 100], "forward_3d_pct": [1, 2],
    })
    row = evaluate_score(panel, "score")[0]
    assert row["bottom_count"] == 0
    assert row["daily_ic_days"] == 0


def test_blind_validation_also_hides_executable_labels_and_maturity():
    panel = pd.DataFrame({
        "dataset_split": ["validation"],
        "next_open_3d_pct": [10.0],
        "forward_3d_end_date": ["20260907"],
        "target_available_date": ["20260909"],
    })
    blinded = blind_validation_labels(panel)
    assert blinded.drop(columns="dataset_split").isna().all().all()


def test_rank_label_waits_for_all_peers_and_uses_next_open_returns():
    panel = _monotonic_panel().iloc[:3].copy()
    for feature in (*V5_FEATURES, *V6_FEATURES):
        panel[feature] = 1.0
    for horizon in ("3d", "1w", "3w"):
        panel[f"forward_{horizon}_end_date"] = ["20260708", "20260709", "20260710"]
        panel[f"forward_{horizon}_pct"] = [30, 20, 10]
        panel[f"next_open_{horizon}_pct"] = [10, 20, 30]
    ranked = rank_panel(panel)
    assert ranked.target_available_date.eq("20260710").all()
    assert ranked.target_rank.tolist() == pytest.approx([1 / 3, 2 / 3, 1.0])
    panel.loc[2, "forward_1w_end_date"] = None
    assert rank_panel(panel).target_available_date.isna().all()


def test_unknown_metrics_export_as_valid_json_null():
    assert json_compatible({"cv": [float("nan"), float("inf"), 0.25]}) == {
        "cv": [None, None, 0.25],
    }
