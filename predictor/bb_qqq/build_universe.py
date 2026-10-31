"""Build the episode universe: show date, BVID, transcript path.

Source of truth for *which* episodes exist is the manifest produced while
scraping (`opencli bilibili user-videos`, upload dates 2026-09-01..2026-10-31,
titles containing "Surveillance"). An episode only enters the study once its
GPU-ASR transcript exists.
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

from common import BILI_ROOT, FILES, MANIFEST


def load_manifest() -> pd.DataFrame:
    rows = list(csv.DictReader(MANIFEST.read_text(encoding="utf-8-sig").splitlines()))
    df = pd.DataFrame(rows)
    df = df.rename(columns={"showDate": "show_date", "uploadDate": "upload_date"})
    df["show_date"] = pd.to_datetime(df["show_date"]).dt.strftime("%Y-%m-%d")
    return df[["show_date", "bvid", "title", "upload_date"]]


def transcript_for(bvid: str) -> Path | None:
    path = BILI_ROOT / bvid / "text" / f"{bvid}.txt"
    return path if path.is_file() and path.stat().st_size > 0 else None


def main() -> int:
    df = load_manifest()
    paths, chars = [], []
    for bvid in df["bvid"]:
        p = transcript_for(bvid)
        paths.append(str(p) if p else "")
        chars.append(p.stat().st_size if p else 0)
    df["transcript"] = paths
    df["transcript_bytes"] = chars
    df = df.sort_values(["show_date", "bvid"]).reset_index(drop=True)

    have = df[df["transcript"] != ""].copy()
    have["n_on_date"] = have.groupby("show_date")["bvid"].transform("count")
    have.to_csv(FILES["episodes"], index=False)

    missing = df[df["transcript"] == ""]
    print(f"manifest episodes : {len(df)}")
    print(f"with transcript   : {len(have)}")
    print(f"still transcribing: {len(missing)}")
    if len(have):
        print(f"date range        : {have['show_date'].min()} .. {have['show_date'].max()}")
        dup = have[have["n_on_date"] > 1][["show_date", "bvid", "title"]]
        if len(dup):
            print("dates with >1 episode (scores will be averaged):")
            print(dup.to_string(index=False))
    print(f"wrote {FILES['episodes']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
