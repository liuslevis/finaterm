"""A dumb text baseline: count finance sentiment words in the transcript.

The point is not to be good.  The point is to give the LLM factor something to
beat.  If a word list gets the same IC, the LLM is not adding information.
"""

from __future__ import annotations

import re
import sys
from collections import Counter

import pandas as pd

from common import DATA, FILES

BULLISH = {
    "rally", "rallies", "surge", "surges", "soar", "soars", "record high", "record highs",
    "gain", "gains", "higher", "upside", "bullish", "risk-on", "risk on", "strong",
    "strength", "resilient", "resilience", "upgrade", "upgrades", "beat", "beats",
    "optimism", "optimistic", "soft landing", "rebound", "rebounds", "buy the dip",
    "outperform", "breakout", "momentum", "supportive", "tailwind", "tailwinds",
    "cooling inflation", "dovish", "rate cut", "rate cuts", "cut rates", "easing",
}

BEARISH = {
    "sell-off", "selloff", "selloffs", "slump", "slumps", "plunge", "plunges", "tumble",
    "tumbles", "drop", "drops", "lower", "downside", "bearish", "risk-off", "risk off",
    "weak", "weakness", "recession", "downgrade", "downgrades", "miss", "misses",
    "pessimism", "pessimistic", "hard landing", "crash", "crashes", "correction",
    "hawkish", "rate hike", "rate hikes", "hike rates", "tightening", "stagflation",
    "headwind", "headwinds", "stress", "strain", "strains", "default", "contagion",
    "overvalued", "bubble", "layoffs", "downturn", "slowdown", "shock", "escalation",
    "war", "strikes", "blockade", "sanctions", "tariff", "tariffs",
}


def phrase_counts(text: str, phrases: set[str]) -> int:
    low = text.lower()
    total = 0
    for phrase in phrases:
        total += len(re.findall(r"\b" + re.escape(phrase) + r"\b", low))
    return total


def score_transcript(path: str) -> dict:
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    text = re.sub(r"^\[\d{2}:\d{2}:\d{2} - \d{2}:\d{2}:\d{2}\]$", "", text, flags=re.MULTILINE)
    bull = phrase_counts(text, BULLISH)
    bear = phrase_counts(text, BEARISH)
    words = len(text.split())
    net = (bull - bear) / (bull + bear + 1.0)
    return {
        "lex_bull": bull,
        "lex_bear": bear,
        "lex_net": net,
        "lex_density": (bull + bear) / max(words, 1) * 1000,
        "lex_words": words,
    }


def main() -> int:
    episodes = pd.read_csv(FILES["episodes"])
    rows = []
    for row in episodes.itertuples(index=False):
        rec = {"show_date": row.show_date, "bvid": row.bvid}
        rec.update(score_transcript(row.transcript))
        rows.append(rec)
    df = pd.DataFrame(rows)
    agg = df.groupby("show_date", as_index=False)[["lex_bull", "lex_bear", "lex_net", "lex_density"]].mean()
    agg.to_csv(DATA / "lexicon.csv", index=False)
    print(agg.describe().round(3).to_string())
    print(f"wrote {DATA / 'lexicon.csv'} rows={len(agg)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
