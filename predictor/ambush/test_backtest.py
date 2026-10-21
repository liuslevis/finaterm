import math

import pandas as pd
import pytest

from backtest import backtest_score, load_prices
from strategy import add_forward_returns


CALENDAR = ["20260701", "20260702", "20260703", "20260706"]
CODES = ["600001.SH", "600002.SH", "600003.SH"]


def _prices():
    return {
        code: pd.DataFrame({
            "open": [100.0] * 4, "close": [100.0, 102.0, 104.0, 106.0],
            "volume": [1000.0] * 4, "previous_close": [100.0, 100.0, 102.0, 104.0],
        }, index=CALENDAR)
        for code in CODES
    }


def _signals():
    return pd.DataFrame({
        "signal_date": ["20260701"] * 3, "code": CODES, "score": [3, 2, 1],
        "forward_1w_pct": [-999, -999, 999],
    })


def test_next_open_entry_cash_and_exact_two_sided_cost():
    metrics, daily = backtest_score(
        _signals(), "score", _prices(), CALENDAR, CALENDAR[0], CALENDAR[-1],
        holding_sessions=2, cost_bps_per_side=15,
    )
    first_nav = 0.5 + 0.5 * 102 / 100 / (1 + 0.0015)
    expected_nav = 0.5 + 0.5 * 104 / 100 * (1 - 0.0015) / (1 + 0.0015)
    assert daily.iloc[0].nav == 1.0
    assert daily.iloc[1].nav == pytest.approx(first_nav)
    assert daily.iloc[2].nav == pytest.approx(expected_nav)
    assert metrics["entries"] == 2
    assert metrics["unclosed_positions"] == 0
    assert metrics["net_return_pct"] == pytest.approx((expected_nav - 1) * 100)
    returns = pd.Series([0.0, first_nav - 1, expected_nav / first_nav - 1, 0.0])
    assert metrics["net_sharpe"] == pytest.approx(
        returns.mean() / returns.std(ddof=1) * math.sqrt(252)
    )


def test_future_returns_do_not_affect_portfolio_selection():
    expected, _ = backtest_score(
        _signals(), "score", _prices(), CALENDAR, CALENDAR[0], CALENDAR[-1],
    )
    panel = _signals()
    panel["forward_1w_pct"] *= -1
    changed, _ = backtest_score(
        panel, "score", _prices(), CALENDAR, CALENDAR[0], CALENDAR[-1],
    )
    assert changed == expected


def test_locked_upper_limit_open_is_not_filled():
    prices = _prices()
    prices[CODES[0]].loc["20260702", "open"] = 110.0
    metrics, _ = backtest_score(
        _signals(), "score", prices, CALENDAR, CALENDAR[0], CALENDAR[-1],
        holding_sessions=2,
    )
    assert metrics["entries"] == 1
    assert metrics["skipped_entries"] == 1


def test_locked_lower_limit_exit_is_delayed():
    prices = _prices()
    prices[CODES[0]].loc["20260703", "close"] = 91.8
    metrics, daily = backtest_score(
        _signals(), "score", prices, CALENDAR, CALENDAR[0], CALENDAR[-1],
        holding_sessions=2,
    )
    assert metrics["delayed_exit_sessions"] == 1
    assert daily.iloc[2].open_positions == 1
    assert daily.iloc[3].open_positions == 0


def test_thin_cross_section_remains_in_cash():
    metrics, daily = backtest_score(
        _signals().iloc[:2], "score", _prices(), CALENDAR, CALENDAR[0], CALENDAR[-1],
    )
    assert metrics["entries"] == 0
    assert daily.nav.eq(1.0).all()
    assert math.isnan(metrics["net_sharpe"])


def test_score_ties_receive_equal_weight_not_file_order():
    signals = _signals()
    signals["score"] = 1.0
    metrics, _ = backtest_score(
        signals, "score", _prices(), CALENDAR, CALENDAR[0], CALENDAR[-1],
    )
    assert metrics["entries"] == 3


def test_cohorts_have_one_over_holding_period_budget():
    _, daily = backtest_score(
        _signals(), "score", _prices(), CALENDAR, CALENDAR[0], CALENDAR[-1],
        holding_sessions=3, cost_bps_per_side=0,
    )
    assert daily.iloc[1].nav == pytest.approx(2 / 3 + 102 / 100 / 3)
    assert daily.iloc[-1].open_positions == 0


def test_missing_next_session_bar_does_not_defer_entry():
    prices = _prices()
    prices[CODES[0]] = prices[CODES[0]].drop("20260702")
    metrics, _ = backtest_score(
        _signals(), "score", prices, CALENDAR, CALENDAR[0], CALENDAR[-1],
        holding_sessions=2,
    )
    assert metrics["entries"] == 1
    assert metrics["skipped_entries"] == 1


def test_marks_open_positions_at_period_end_without_future_exit():
    metrics, daily = backtest_score(
        _signals(), "score", _prices(), CALENDAR, CALENDAR[0], CALENDAR[1],
        holding_sessions=5, cost_bps_per_side=0,
    )
    assert metrics["unclosed_positions"] == 2
    assert daily.iloc[-1].nav == pytest.approx(0.8 + 1.02 / 5)


@pytest.mark.parametrize("holding,cost", [(0, 15), (1, 15), (5, -1), (5, float("nan")), (5, 10_000)])
def test_rejects_invalid_backtest_parameters(holding, cost):
    with pytest.raises(ValueError):
        backtest_score(
            _signals(), "score", _prices(), CALENDAR, CALENDAR[0], CALENDAR[-1],
            holding, cost,
        )


def test_missing_cache_is_explicit_error(tmp_path):
    with pytest.raises(RuntimeError, match="Missing"):
        load_prices(CODES, tmp_path)


def test_loaded_prices_work_with_market_calendar_labels(tmp_path):
    frame = _prices()[CODES[0]].copy()
    frame["date"] = pd.to_datetime(frame.index)
    frame.to_csv(tmp_path / "600001_SH.csv", index=False)
    loaded = load_prices([CODES[0]], tmp_path)[CODES[0]]
    row = {}
    add_forward_returns(
        row, loaded, pd.Timestamp(CALENDAR[0]), pd.DatetimeIndex(pd.to_datetime(CALENDAR))
    )
    assert row["next_open_3d_pct"] == pytest.approx(6.0)


def test_entry_rule_does_not_rerank_or_reallocate_rejected_budget():
    panel = _signals()
    panel["allowed"] = [False, True, True]
    metrics, daily = backtest_score(
        panel, "score", _prices(), CALENDAR, CALENDAR[0], CALENDAR[-1],
        holding_sessions=2, cost_bps_per_side=0, entry_mask_column="allowed",
    )
    assert metrics["entries"] == 1
    assert metrics["rule_filtered_candidates"] == 1
    assert daily.iloc[2].nav == pytest.approx(0.75 + 0.25 * 1.04)


def test_entry_rule_still_requires_original_cross_section_of_three():
    panel = _signals().iloc[:2].copy()
    panel["allowed"] = True
    metrics, _ = backtest_score(
        panel, "score", _prices(), CALENDAR, CALENDAR[0], CALENDAR[-1],
        entry_mask_column="allowed",
    )
    assert metrics["entries"] == 0


@pytest.mark.parametrize("mask", [["yes", "no", "yes"], [True, None, False]])
def test_entry_rule_rejects_non_boolean_or_missing_masks(mask):
    panel = _signals()
    panel["allowed"] = mask
    with pytest.raises(ValueError, match="booleans"):
        backtest_score(
            panel, "score", _prices(), CALENDAR, CALENDAR[0], CALENDAR[-1],
            entry_mask_column="allowed",
        )


def test_no_cash_does_not_skip_valuation_or_due_exits():
    panel = pd.concat([
        _signals().assign(signal_date=date) for date in CALENDAR[:3]
    ], ignore_index=True)
    prices = _prices()
    for frame in prices.values():
        frame.loc["20260703", "close"] = 91.8
    metrics, daily = backtest_score(
        panel, "score", prices, CALENDAR, CALENDAR[0], CALENDAR[-1],
        holding_sessions=2, cost_bps_per_side=0,
    )
    assert len(daily) == 4
    assert metrics["entries"] == 4
    assert metrics["unclosed_positions"] == 0
    assert daily.iloc[-1].nav == pytest.approx(1.06)
