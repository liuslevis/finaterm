import numpy as np
import pandas as pd
import pytest

from enhance_v9 import empirical_cdf, rerank_without, shuffled_within_day


def test_empirical_cdf_uses_frozen_reference_and_neutral_missing():
    reference = pd.Series([1.0, 2.0, 3.0, 4.0])
    values = pd.Series([0.0, 2.0, 9.0, np.nan])

    assert empirical_cdf(reference, values).tolist() == pytest.approx([0.0, 0.5, 1.0, 0.5])


def test_rerank_without_removes_vetoed_names_from_ranking():
    rows = pd.DataFrame({"score": [90.0, 50.0, 10.0]})
    scores = rerank_without(rows, "score", pd.Series([True, False, False]))

    assert np.isnan(scores.iloc[0]) and scores.iloc[1:].tolist() == [50.0, 10.0]


def test_placebo_keeps_veto_count_per_day():
    allow = pd.Series([True, False, True, True, False])
    dates = pd.Series(["d1", "d1", "d1", "d2", "d2"])
    shuffled = shuffled_within_day(allow, dates, np.random.default_rng(0))

    assert shuffled.groupby(dates).sum().tolist() == [2, 1]
