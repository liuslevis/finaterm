import pandas as pd
import pytest
from strategy import (
    _record_trade_fill,
    Thresholds,
    add_forward_returns,
    build_evaluation,
    detect_launch_window,
    is_a_share,
    limit_up_rate,
    load_production_lv2_model,
    passes_dormant_filter,
    percentile_score,
    rounded_limit_price,
    SKIPPED_KLINE_CODES,
    signed_percentile_score,
    weighted_signed_percentile_score,
)


def test_a_share_code_filter():
    assert is_a_share("000001.SZ")
    assert is_a_share("688001.SH")
    assert not is_a_share("200001.SZ")
    assert not is_a_share("510300.SH")


def test_known_unavailable_kline_is_skipped():
    assert "689009.SH" in SKIPPED_KLINE_CODES


def test_v4_model_is_only_available_after_validation_window():
    assert load_production_lv2_model("20260916") is None
    assert load_production_lv2_model("20260917")["version"] == 4


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


def test_signed_percentile_score_can_reverse_direction():
    frame = pd.DataFrame({"supply": [10.0, 20.0], "refill": [2.0, 1.0]})
    score = signed_percentile_score(frame, {"supply": -1, "refill": 1})
    assert score.iloc[0] > score.iloc[1]


def test_weighted_signed_percentile_score_respects_factor_strength():
    frame = pd.DataFrame(
        {
            "strong": [1.0, 2.0, 3.0],
            "weak": [3.0, 2.0, 1.0],
        }
    )
    score = weighted_signed_percentile_score(
        frame, {"strong": 2, "weak": -1}
    )
    assert score.iloc[2] > score.iloc[0]


def test_detects_continuous_launch_without_reading_future_minutes():
    trades = []
    for minute in range(9 * 60 + 30, 9 * 60 + 36):
        for offset in (5, 20, 40):
            trades.append((minute * 60 + offset, 100_000, 100, "S"))
    for minute, price in zip(
        range(9 * 60 + 36, 9 * 60 + 39),
        (102_000, 105_000, 108_000),
    ):
        for offset in (5, 20, 40):
            trades.append((minute * 60 + offset, price, 1_000, "B"))
    trades.append((10 * 3600, 120_000, 1_000_000, "B"))

    launch = detect_launch_window(trades, previous_close=10, limit_rate=0.10)

    assert launch["launch_type"] == "CONTINUOUS_TRIGGER"
    assert launch["t_start"] == 93500000
    assert launch["t_detect"] == 93759999


def test_detects_auction_launch():
    trades = [
        (9 * 3600 + 25 * 60, 108_000, 700, "B"),
        (9 * 3600 + 25 * 60 + 1, 108_000, 300, "S"),
    ]

    launch = detect_launch_window(trades, previous_close=10, limit_rate=0.10)

    assert launch["launch_type"] == "AUCTION_TRIGGER"
    assert launch["t_start"] == 92500000
    assert launch["t_detect"] == 92501000


def test_launch_is_absent_when_volume_and_buy_pressure_are_insufficient():
    trades = [
        (minute * 60, 100_000, 100, "S")
        for minute in range(9 * 60 + 30, 9 * 60 + 40)
    ]

    launch = detect_launch_window(trades, previous_close=10, limit_rate=0.10)

    assert not launch["launch_detected"]
    assert launch["t_start"] == 0


def test_sh_immediate_aggressor_fill_does_not_consume_reported_balance():
    orders = {
        20: {"time": 1000, "qty": 500, "events": []},
        10: {"time": 900, "qty": 500, "events": []},
    }

    active_opportunity, active_unknown = _record_trade_fill(
        orders, 20, "B", "SH", "B", 1000, 300
    )
    passive_opportunity, passive_unknown = _record_trade_fill(
        orders, 10, "S", "SH", "B", 1000, 300
    )

    assert not active_opportunity
    assert not active_unknown
    assert orders[20]["events"] == []
    assert passive_opportunity
    assert not passive_unknown
    assert orders[10]["events"] == [(1000, 300, "fill")]


def test_sz_records_both_sides_and_flags_missing_links():
    orders = {10: {"time": 900, "qty": 500, "events": []}}

    opportunity, unknown = _record_trade_fill(
        orders, 10, "S", "SZ", "B", 1000, 300
    )
    missing_opportunity, missing_unknown = _record_trade_fill(
        orders, 20, "B", "SZ", "B", 1000, 300
    )

    assert opportunity and not unknown
    assert missing_opportunity and missing_unknown
    assert orders[10]["events"] == [(1000, 300, "fill")]
