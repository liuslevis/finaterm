import json
import tempfile
import types
import unittest
from pathlib import Path

import pandas as pd

import engine


class FakeMarket:
    def __init__(self, frames):
        self.frames = frames

    def __getitem__(self, sym):
        return self.frames[sym]


def frame(opens, closes, start="2026-01-05"):
    idx = pd.bdate_range(start, periods=len(opens))
    return pd.DataFrame({"Open": opens, "Close": closes}, index=idx)


def strategy(**kw):
    base = dict(ID="t", NAME="t", DESC="", START="2026-01-05", CAPITAL=1000, CALENDAR="X", FEE=0.0,
                FRACTIONAL=False, CASH_YIELD=False, SUPPORT=[], prepare=lambda m: None,
                contribution=lambda d: 0.0, on_open=lambda d, c, a: [], on_close=lambda d, c, a: ([], {}))
    base.update(kw)
    return types.SimpleNamespace(**base)


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        engine.STATE = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def acct(self, sid="t"):
        return json.loads((engine.STATE / sid / "account.json").read_text())

    def test_weight_buy_next_open_then_sell_all(self):
        m = FakeMarket({"X": frame([10, 10, 20, 20], [10, 10, 20, 20]), "^IRX": frame([0] * 4, [0] * 4)})

        def on_close(d, c, a):
            i = m["X"].index.get_loc(d)
            if i == 0:
                return [{"symbol": "X", "side": "buy", "weight": 0.5}], {}
            if i == 2:
                return [{"symbol": "X", "side": "sell", "shares": "all"}], {}
            return [], {}

        st = strategy(on_close=on_close)
        self.assertEqual(engine.run_strategy(st, m), 4)
        a = self.acct()
        self.assertEqual(a["holdings"], {})
        self.assertAlmostEqual(a["nav"], 500 + 50 * 20)
        self.assertAlmostEqual(a["twr"], 1.5)
        self.assertEqual(engine.run_strategy(st, m), 0)

    def test_contributions_do_not_count_as_return(self):
        m = FakeMarket({"X": frame([10, 10, 10], [10, 10, 10]), "^IRX": frame([0] * 3, [0] * 3)})
        st = strategy(CAPITAL=0, FRACTIONAL=True, contribution=lambda d: 10.0,
                      on_open=lambda d, c, a: [{"symbol": "X", "side": "buy", "amount": 10.0}])
        engine.run_strategy(st, m)
        a = self.acct()
        self.assertAlmostEqual(a["invested"], 30)
        self.assertAlmostEqual(a["nav"], 30)
        self.assertAlmostEqual(a["twr"], 1.0)

    def test_cash_earns_previous_day_tbill(self):
        m = FakeMarket({"X": frame([10, 10], [10, 10]), "^IRX": frame([2.52, 2.52], [2.52, 2.52])})
        engine.run_strategy(strategy(CASH_YIELD=True), m)
        self.assertAlmostEqual(self.acct()["nav"], 1000 * (1 + 0.0252 / 252), places=4)


if __name__ == "__main__":
    unittest.main()
