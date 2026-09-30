import math

import pandas as pd

from optimize_score import (
    FEATURES,
    V5_FEATURES,
    apply_weighted_model,
    blind_validation_labels,
    evaluate_score,
    features_are_trainable,
    select_production_model,
    split_datasets,
    train_ridge_model,
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


def test_production_model_uses_weighted_test_spearman():
    rows = [
        {"score": "v3", "horizon": "3d", "spearman": 0.2},
        {"score": "v3", "horizon": "1w", "spearman": 0.1},
        {"score": "v4", "horizon": "3d", "spearman": 0.1},
        {"score": "v4", "horizon": "1w", "spearman": 0.3},
    ]
    models = {"v3": {"version": 3}, "v4": {"version": 4}}

    name, model = select_production_model(rows, models)

    assert name == "v4"
    assert model["version"] == 4
