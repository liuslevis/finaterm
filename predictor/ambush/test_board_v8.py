import math

import pandas as pd
import pytest

from board_v8 import board_labels, daily_portfolio, flag_mask, pre_touch_features

LIMIT = 110000
ADV = 10_000.0


def _orders(rows):
    return pd.DataFrame(
        rows, columns=["t", "exch_order_no", "order_type", "order_code", "price", "qty"]
    )


def _trades(rows):
    return pd.DataFrame(
        rows, columns=["t", "trade_code", "side", "price", "qty", "sell_seq", "buy_seq"]
    )


def _quotes(rows):
    return pd.DataFrame(rows, columns=["t", "bid_px1", "bid_qty1"])


def test_sz_parked_qty_nets_immediate_passive_and_cancel():
    orders = _orders(
        [
            (92000000, 1, "0", "B", LIMIT, 1000),  # pre-open, 300 cancelled
            (93100000, 2, "0", "B", 109000, 500),  # 200 filled on entry, 100 passive
            (93200000, 3, "0", "B", 100000, 900),  # far from limit
        ]
    )
    trades = _trades(
        [
            (92100000, "C", "", 0, 300, 0, 1),
            (93100000, "F", "B", 109000, 200, 9, 2),
            (93500000, "F", "S", 109000, 100, 8, 2),
            (94000000, "F", "B", LIMIT, 50, 7, 99),  # touch
            (94500000, "F", "B", LIMIT, 300, 6, 98),
        ]
    )
    quotes = _quotes([(94000500, LIMIT, 250)])
    out = pre_touch_features(orders, trades, quotes, "SZ", LIMIT, ADV)

    assert out["t_touch"] == 94000000
    assert out["v8_parked_near_limit_buy_adv_pct"] == pytest.approx((700 + 200) / ADV * 100)
    assert out["v8_preopen_near_limit_buy_adv_pct"] == pytest.approx(700 / ADV * 100)
    assert out["v8_parked_preopen_share_pct"] == pytest.approx(700 / 900 * 100)
    assert out["v8_touch_queue_adv_pct"] == pytest.approx(250 / ADV * 100)
    assert out["filled_queue"]


def test_sh_uses_resting_balance_and_d_cancels():
    orders = _orders(
        [
            (92000000, 1, "A", "B", LIMIT, 800),
            (92500000, 1, "D", "B", LIMIT, 800),
            (93100000, 2, "A", "B", LIMIT, 400),  # resting after immediate fill
        ]
    )
    trades = _trades(
        [
            (93100000, "", "B", 109500, 100, 9, 2),  # immediate, already netted by SH
            (93300000, "", "B", LIMIT, 10, 9, 77),
        ]
    )
    quotes = _quotes([(93300100, LIMIT, 5000)])
    out = pre_touch_features(orders, trades, quotes, "SH", LIMIT, ADV)

    assert out["v8_parked_near_limit_buy_adv_pct"] == pytest.approx(400 / ADV * 100)
    assert out["v8_preopen_near_limit_buy_adv_pct"] == 0
    assert not out["filled_queue"]


def test_queue_fills_when_board_breaks():
    trades = _trades(
        [
            (93300000, "", "B", LIMIT, 10, 9, 77),
            (100000000, "", "S", 109000, 10, 9, 76),
        ]
    )
    quotes = _quotes([(93300100, LIMIT, 5000)])
    out = pre_touch_features(_orders([]), trades, quotes, "SH", LIMIT, ADV)

    assert out["fill_broke_after"] and out["filled_queue"]


def test_board_labels_chain_through_exchange_prev_close():
    today = {"open": 10.5, "low": 10.2, "close": 11.0}
    tomorrow = {"open": 5.4, "close": 6.0, "prev_close": 5.5, "vol": 100}  # 1:1 bonus
    labels = board_labels(11.0, today, tomorrow)

    assert labels["d1_open_ret_pct"] == pytest.approx((5.4 / 5.5 - 1) * 100)
    assert labels["sealed_close"] and not labels["one_word_board"]
    assert math.isnan(board_labels(11.0, today, None)["d1_open_ret_pct"])


def test_flag_mask_ignores_zero_values_for_high_flags():
    rows = pd.DataFrame({"x": [0.0, 0.0, 1.0, math.nan]})
    flagged = flag_mask(rows, {"feature": "x", "direction": "high", "threshold": 0.0})

    assert flagged.tolist() == [False, False, True, False]


def test_daily_portfolio_holds_cash_on_empty_days_and_charges_both_sides():
    rows = pd.DataFrame(
        {"signal_date": ["d1", "d1"], "d1_open_ret_pct": [2.0, 0.0]}
    )
    daily = daily_portfolio(rows, pd.Series([True, True]), ["d1", "d2"], 10.0)
    expected = ((1.02 * 0.999 / 1.001 - 1) + (0.999 / 1.001 - 1)) / 2 * 100

    assert daily["return_pct"].tolist() == pytest.approx([expected, 0.0])
    assert daily["positions"].tolist() == [2, 0]
