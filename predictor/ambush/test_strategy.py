import pandas as pd
import pytest
from strategy import (
    Thresholds,
    add_forward_returns,
    build_evaluation,
    is_a_share,
    limit_up_rate,
    passes_dormant_filter,
    percentile_score,
    rounded_limit_price,
)


def test_a_share_code_filter():
    assert is_a_share("000001.SZ")
    assert is_a_share("688001.SH")
    assert not is_a_share("200001.SZ")
    assert not is_a_share("510300.SH")


def test_horizontal_thresholds_are_inclusive():
    limits = Thresholds()
    metrics = {
        "bottom_percentile": 0.35,
        "range_60d_pct": 20.0,
        "mean_abs_return_20d_pct": 2.5,
        "mean_turnover_20d_pct": 2.0,
        "event_volume_ratio": 2.0,
    }
    assert passes_dormant_filter(metrics, limits)


def test_forward_returns_require_exact_sessions():
    dates = pd.bdate_range("2026-09-01", periods=14)
    frame = pd.DataFrame({"date": dates, "close": range(100, 114)})
    row = {}
    add_forward_returns(row, frame, pd.Timestamp("2026-09-01"))
    assert row["forward_3d_pct"] == pytest.approx(3.0)
    assert row["forward_1w_pct"] == pytest.approx(5.0)
    assert row["forward_2w_pct"] == pytest.approx(10.0)
    assert pd.isna(row["forward_3w_pct"])


def test_percentile_score_respects_factor_direction():
    frame = pd.DataFrame({"bottom": [0.1, 0.5], "volume": [3.0, 1.0]})
    score = percentile_score(
        frame,
        {"bottom": (1, False), "volume": (1, True)},
    )
    assert score.iloc[0] > score.iloc[1]


def test_evaluation_does_not_treat_missing_returns_as_losses():
    frame = pd.DataFrame(
        {
            "rank": [1, 2],
            "forward_3d_pct": [1.0, -1.0],
            "forward_1w_pct": [2.0, float("nan")],
            "forward_2w_pct": [float("nan"), float("nan")],
            "forward_3w_pct": [float("nan"), float("nan")],
        }
    )
    evaluation = build_evaluation(frame)
    assert evaluation.iloc[0]["3d_positive_rate_pct"] == 50
    assert evaluation.iloc[0]["1w_available"] == 1


def test_board_and_st_limit_prices():
    assert limit_up_rate("600000.SH", "普通股票") == 0.10
    assert limit_up_rate("300001.SZ", "创业板") == 0.20
    assert limit_up_rate("688001.SH", "科创板") == 0.20
    assert limit_up_rate("600001.SH", "*ST 测试") == 0.05
    assert rounded_limit_price(7.15, 0.10) == 7.87
