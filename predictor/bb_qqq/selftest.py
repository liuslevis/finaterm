"""Harness self-test: with random scores the IC inference must be null.

Runs ``ic_block`` on a panel whose score column has been replaced by pure noise,
many times, and reports how often it claims significance.  If the p-values are
not roughly uniform, the Newey-West / block-bootstrap machinery is mis-calibrated
and every number in CORR.md is suspect.

Usage: python selftest.py --panel data/panel_brief.csv --reps 200
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from evaluate import ic_block

HORIZONS = (1, 3, 7)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="data/panel_brief.csv")
    ap.add_argument("--reps", type=int, default=200)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    panel = pd.read_csv(args.panel)
    rng = np.random.default_rng(args.seed)
    print(f"panel n={len(panel)}; running {args.reps} random-score draws")

    for h in HORIZONS:
        p_values, ics = [], []
        for _ in range(args.reps):
            probe = panel.copy()
            probe["noise"] = rng.normal(size=len(probe))
            block = ic_block(probe, "noise", h)
            if "p_pearson" not in block:
                continue
            p_values.append(block["p_pearson"])
            ics.append(block["pearson"])
        if not p_values:
            print(f"h={h}d: not enough rows")
            continue
        p = np.array(p_values)
        print(f"h={h}d  reps={len(p)}  mean IC={np.mean(ics):+.3f}  "
              f"sd IC={np.std(ics):.3f}  "
              f"P(p<0.05)={np.mean(p < 0.05):.3f}  P(p<0.10)={np.mean(p < 0.10):.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
