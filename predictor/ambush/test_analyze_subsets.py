import numpy as np
import pandas as pd
import pytest

from analyze_subsets import (
    MEDIAN_FEATURES,
    add_subset_features,
    apply_rule,
    build_rules,
    holm_adjust,
    label_summary,
    training_screen,
)


def _training():
    return pd.DataFrame({
        "signal_date": ["20260701"] * 3 + ["20260702"] * 3 + ["20260703"] * 3 + ["20260706"] * 3,
        "code": [f"600{index:03d}.SH" for index in range(12)],
        "next_open_1w_pct": [3.0] * 12,
        **{feature: np.arange(1, 13, dtype=float) for feature in MEDIAN_FEATURES.values()},
        "large_order_net_flow_pct": np.arange(-6, 6, dtype=float),
        "closed_at_limit": [True, False] * 6,
        "board_20pct": [False] * 12,
        "shanghai": [True] * 12,
        "t_start": [100000000] * 12,
    })


def test_thresholds_never_depend_on_returns_or_score_columns():
    train = _training()
    rules = build_rules(train)
    mutated = train.copy()
    mutated["next_open_1w_pct"] = -9999
    mutated["current_model_score"] = np.arange(12)
    assert build_rules(mutated) == rules
    assert len(rules) == 54
    assert all(len(rule["conditions"]) <= 2 for rule in rules)


def test_rule_application_keeps_training_threshold_in_future_cross_sections():
    train = _training()
    rule = next(rule for rule in build_rules(train) if rule["rule"] == "bottom_low")
    future = pd.DataFrame({"bottom_percentile": [6.5, 6.6, float("nan"), 1.0]})
    assert apply_rule(future, rule).tolist() == [True, False, False, True]


def test_unknown_operator_is_explicit_error():
    with pytest.raises(ValueError, match="Unsupported"):
        apply_rule(_training(), {
            "conditions": [{"feature": "bottom_percentile", "operator": "bad", "threshold": 1}],
        })


def test_subgroup_summary_applies_exact_two_sided_cost_and_excludes_missing_labels():
    train = _training().iloc[:3].copy()
    train["next_open_1w_pct"] = [3.0, -3.0, float("nan")]
    summary = label_summary(train, pd.Series(True, index=train.index), 15.0)
    assert summary["matched_count"] == 3
    assert summary["labeled_count"] == 2
    assert summary["net_label_mean_pct"] == pytest.approx(
        ((1 - 0.0015) / (1 + 0.0015) - 1) * 100
    )
    assert summary["positive_rate_pct"] == 50


def test_empty_subgroup_does_not_report_zero_return_as_profit():
    train = _training()
    summary = label_summary(train, pd.Series(False, index=train.index), 15.0)
    assert summary["labeled_count"] == 0
    assert np.isnan(summary["net_label_mean_pct"])
    assert np.isnan(summary["weekly_signflip_p"])


def test_holm_adjustment_preserves_missing_and_controls_family_size():
    values = pd.Series([0.01, 0.04, 0.03, float("nan")])
    adjusted = holm_adjust(values)
    assert adjusted.iloc[:3].tolist() == pytest.approx([0.03, 0.06, 0.06])
    assert np.isnan(adjusted.iloc[3])


def test_training_screen_requires_counts_and_dates_not_just_one_winner():
    train = _training()
    rules = [
        {"rule": "all", "conditions": []},
        {"rule": "rare", "conditions": [
            {"feature": "bottom_percentile", "operator": "le", "threshold": 1},
        ]},
    ]
    result = training_screen(train, rules, 15.0).set_index("rule")
    assert result.loc["all", "frozen_from_training"]
    assert not result.loc["rare", "frozen_from_training"]
    assert result.loc["rare", "net_label_mean_pct"] > 0


def test_derived_features_are_price_position_and_cap_not_future_labels():
    panel = pd.DataFrame({
        "code": ["300001.SZ", "600001.SH"],
        "outstanding_share": [100_000_000, 200_000_000],
        "event_close": [10.0, 20.0],
        "event_amount": [200_000_000, 100_000_000],
        "limit_up_price": [10.0, 22.0],
    })
    result = add_subset_features(panel)
    assert result.free_float_cap_billion.tolist() == [1.0, 4.0]
    assert result.board_20pct.tolist() == [True, False]
    assert result.closed_at_limit.tolist() == [True, False]


def test_long_history_sign_flip_is_bounded_and_deterministic():
    train = _training().iloc[:1]
    panel = pd.concat([train] * 20, ignore_index=True)
    panel["signal_date"] = pd.date_range("2026-01-01", periods=20, freq="7D").strftime("%Y%m%d")
    mask = pd.Series(True, index=panel.index)
    first = label_summary(panel, mask, 15.0)
    second = label_summary(panel, mask, 15.0)
    assert first["weekly_blocks"] == 20
    assert first["weekly_signflip_p"] == second["weekly_signflip_p"]
    assert first["weekly_signflip_p"] > 0
