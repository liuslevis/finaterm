import pandas as pd

from optimize_score import FEATURES, apply_weighted_model, train_ridge_model


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
