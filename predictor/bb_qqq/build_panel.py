"""Join LLM scores to QQQ forward returns with an explicit, documented clock.

Timeline (all New York time):

    d 06:00-10:00  Bloomberg Surveillance is broadcast live.
    d 10:30        the transcript exists -> the signal is known.  (t0)
    d 16:00        entry: QQQ close of d.                          (entry)
    d+h 16:00      label: QQQ close h trading days later.

So `r_h = close(d+h)/close(d) - 1`.  Nothing observed after 10:30 ET on d is used
to build a feature.  Returns are close-to-close, which is deliberately the most
conservative choice: it throws away the intraday move of d (where the show has
already been digested) instead of pretending we could trade the open.

Diagnostic columns (`ret_0`, `gap`) are *not* features; they exist only to audit
whether the model is reading the tape it was told about.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from common import DATA, FILES
from make_brief import numeric_features

HORIZONS = (1, 3, 7)


def load_scores(path: Path | None = None) -> pd.DataFrame:
    path = path or (DATA / "llm_scores_deepseek.csv")
    if not path.is_file():
        raise SystemExit(f"missing {path}; run llm_score.py first")
    df = pd.read_csv(path)
    df = df.sort_values(["show_date", "bvid"]).reset_index(drop=True)
    agg = {
        "p_up_1d": "mean", "p_up_3d": "mean", "p_up_7d": "mean",
        "sentiment": "mean", "confidence": "mean",
    }
    grouped = df.groupby("show_date", as_index=False).agg(
        {**agg, "bvid": lambda s: "+".join(sorted(s))}
    )
    counts = df.groupby("show_date", as_index=False).size().rename(columns={"size": "n_episodes"})
    grouped = grouped.merge(counts, on="show_date")
    # ordinal encoding of the pre-open tape description (bullish positive)
    move_map = {"sharply_down": -2, "down": -1, "flat": 0, "up": 1, "sharply_up": 2}
    moves = (df.assign(m=df["preopen_move"].map(move_map).fillna(0))
               .groupby("show_date", as_index=False)["m"].mean()
               .rename(columns={"m": "preopen_move_score"}))
    grouped = grouped.merge(moves, on="show_date")
    return grouped.sort_values("show_date").reset_index(drop=True)


def load_prices() -> pd.DataFrame:
    path = FILES["prices"]
    if not path.is_file():
        raise SystemExit(f"missing {path}; run fetch_prices.py first")
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    return df.sort_values("date").reset_index(drop=True)


def load_brief_features() -> pd.DataFrame:
    """Transparent ordinal features extracted by stage 1 (no prices involved)."""
    rows = []
    for path in sorted((DATA / "briefs").glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        rec = {"show_date": payload["show_date"], "bvid": payload["bvid"]}
        rec.update(numeric_features(payload.get("brief", {})))
        rows.append(rec)
    if not rows:
        return pd.DataFrame(columns=["show_date"])
    df = pd.DataFrame(rows)
    numeric = [c for c in df.columns if c.startswith("brf_")]
    return df.groupby("show_date", as_index=False)[numeric].mean()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default=str(DATA / "llm_scores_deepseek_brief.csv"))
    ap.add_argument("--out", default=str(FILES["panel"]))
    args = ap.parse_args()

    scores = load_scores(Path(args.scores))
    prices = load_prices()
    lex_path = DATA / "lexicon.csv"
    if lex_path.is_file():
        lex = pd.read_csv(lex_path)
        scores = scores.merge(lex[["show_date", "lex_net", "lex_density", "lex_bull", "lex_bear"]],
                              on="show_date", how="left")
    else:
        scores["lex_net"] = np.nan
        scores["lex_density"] = np.nan
        scores["lex_bull"] = np.nan
        scores["lex_bear"] = np.nan

    briefs = load_brief_features()
    if not briefs.empty:
        scores = scores.merge(briefs, on="show_date", how="left")
    dates = list(prices["date"])
    index_of = {d: i for i, d in enumerate(dates)}
    last = len(dates) - 1

    rows = []
    for row in scores.itertuples(index=False):
        show_date = row.show_date
        # entry = first trading day at or after the show date
        entry_idx = index_of.get(show_date)
        if entry_idx is None:
            later = [i for d, i in index_of.items() if d >= show_date]
            if not later:
                print(f"warn: {show_date} has no price row at/after it; dropped")
                continue
            entry_idx = min(later)
        rec = {
            "show_date": show_date,
            "bvid": row.bvid,
            "n_episodes": row.n_episodes,
            "entry_date": dates[entry_idx],
            "p_up_1d": row.p_up_1d, "p_up_3d": row.p_up_3d, "p_up_7d": row.p_up_7d,
            "sentiment": row.sentiment, "confidence": row.confidence,
            "preopen_move_score": row.preopen_move_score,
            "lex_net": getattr(row, "lex_net", np.nan),
            "lex_density": getattr(row, "lex_density", np.nan),
            "brf_composite": getattr(row, "brf_composite", np.nan),
            "brf_sentiment": getattr(row, "brf_sentiment", np.nan),
            "entry_close": float(prices["close"].iloc[entry_idx]),
        }
        for h in HORIZONS:
            j = entry_idx + h
            rec[f"has_r{h}"] = j <= last
            rec[f"r{h}"] = (prices["close"].iloc[j] / prices["close"].iloc[entry_idx] - 1.0) if j <= last else np.nan

        # --- diagnostics only (never used as features) ---
        if entry_idx >= 1:
            prev_close = float(prices["close"].iloc[entry_idx - 1])
            rec["ret_0"] = rec["entry_close"] / prev_close - 1.0
            rec["gap"] = float(prices["open"].iloc[entry_idx]) / prev_close - 1.0
        else:
            rec["ret_0"] = np.nan
            rec["gap"] = np.nan

        # --- fair baselines: last close known at 10:30 ET on d is close(d-1) ---
        ref = entry_idx - 1
        if ref >= 6:
            rec["mom5"] = float(prices["close"].iloc[ref]) / float(prices["close"].iloc[ref - 5]) - 1.0
        else:
            rec["mom5"] = np.nan
        if ref >= 21:
            rec["mom20"] = float(prices["close"].iloc[ref]) / float(prices["close"].iloc[ref - 21]) - 1.0
        else:
            rec["mom20"] = np.nan
        rows.append(rec)

    panel = pd.DataFrame(rows)
    panel["score_1d"] = 2 * panel["p_up_1d"] - 1
    panel["score_3d"] = 2 * panel["p_up_3d"] - 1
    panel["score_7d"] = 2 * panel["p_up_7d"] - 1
    for h in HORIZONS:
        panel[f"logit_{h}d"] = np.log(panel[f"p_up_{h}d"] / (1 - panel[f"p_up_{h}d"]))

    panel.to_csv(args.out, index=False)
    print(f"wrote {args.out} rows={len(panel)}")
    print(f"price coverage: {dates[0]} .. {dates[-1]}")
    for h in HORIZONS:
        print(f"  usable n for r{h}: {int(panel[f'has_r{h}'].sum())}")
    print(panel[["show_date", "bvid", "p_up_1d", "sentiment", "r1", "r3", "r7"]].tail(8).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())


