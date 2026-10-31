"""Is the LLM's probability stable enough to be a factor input?

Calls the same prompt twice for a handful of episodes (temperature 0) and reports
the run-to-run spread.  Compare that noise to the cross-episode spread: if the
noise is a large share of the signal's variance, the factor is mostly sampling
noise from the model rather than information about the market.

Usage: python llm_noise_test.py --episodes 6
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from common import DATA, FILES, resolve_llm
from llm_score import build_prompt, call_llm, parse_json, validate


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", type=int, default=6)
    ap.add_argument("--model", default="deepseek")
    ap.add_argument("--mode", default="brief", choices=["brief", "full"])
    args = ap.parse_args()

    llm = resolve_llm(args.model)
    episodes = pd.read_csv(FILES["episodes"]).head(args.episodes)
    if not len(episodes):
        raise SystemExit("no episodes with transcripts yet")

    rows = []
    for row in episodes.itertuples(index=False):
        if args.mode == "brief":
            body = (DATA / "briefs" / f"{row.bvid}.md").read_text(encoding="utf-8")
        else:
            body = Path(row.transcript).read_text(encoding="utf-8", errors="replace")
        system, user = build_prompt(row.show_date, body, mode=args.mode, blind=False)
        first = second = None
        for attempt in range(3):
            try:
                first = validate(parse_json(call_llm(llm, system, user, use_json_mode=True,
                                                      max_tokens=8000)["raw"]))
                break
            except Exception as exc:  # noqa: BLE001
                print(f"{row.bvid} call1 failed: {exc}")
        for attempt in range(3):
            try:
                second = validate(parse_json(call_llm(llm, system, user, use_json_mode=True,
                                                      max_tokens=8000)["raw"]))
                break
            except Exception as exc:  # noqa: BLE001
                print(f"{row.bvid} call2 failed: {exc}")
        if not first or not second:
            continue
        rows.append({
            "bvid": row.bvid,
            "p1_a": first["p_up_1d"], "p1_b": second["p_up_1d"],
            "p3_a": first["p_up_3d"], "p3_b": second["p_up_3d"],
            "p7_a": first["p_up_7d"], "p7_b": second["p_up_7d"],
            "s_a": first["sentiment"], "s_b": second["sentiment"],
        })
        print(f"{row.bvid} p1 {first['p_up_1d']:.3f} vs {second['p_up_1d']:.3f} | "
              f"p7 {first['p_up_7d']:.3f} vs {second['p_up_7d']:.3f} | "
              f"sent {first['sentiment']:+d} vs {second['sentiment']:+d}")

    df = pd.DataFrame(rows)
    if not len(df):
        print("no usable pairs")
        return 1
    print(f"\npairs: {len(df)}")
    for h in (1, 3, 7):
        d = (df[f"p{h}_a"] - df[f"p{h}_b"]).to_numpy()
        spread = df[[f"p{h}_a", f"p{h}_b"]].mean(axis=1).std(ddof=1)
        print(f"  p_up_{h}d: run-to-run sd={d.std(ddof=1):.4f}  max|diff|={np.abs(d).max():.3f}  "
              f"cross-episode sd={spread:.4f}  noise share={(d.std(ddof=1)**2)/(spread**2 + 1e-12):.1%}")
    agree = int((df["s_a"] == df["s_b"]).sum())
    print(f"  sentiment exact agreement: {agree}/{len(df)}")
    df.to_csv(DATA / "llm_noise.csv", index=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
