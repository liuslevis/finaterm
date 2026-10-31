"""Download/cache QQQ daily bars (adjusted close basis) as CSV."""

from __future__ import annotations

import sys

import pandas as pd

from common import FILES


def fetch_qqq() -> pd.DataFrame:
    import akshare as ak  # local checkout, stock_us_daily -> qfq-adjusted

    df = ak.stock_us_daily(symbol="QQQ", adjust="qfq")
    df = df.rename(columns={c: c.lower() for c in df.columns})
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df = df[["date", "open", "high", "low", "close", "volume"]].copy()
    for col in ("open", "high", "low", "close"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"]).drop_duplicates("date").sort_values("date")
    return df.reset_index(drop=True)


def main() -> int:
    df = fetch_qqq()
    df.to_csv(FILES["prices"], index=False)
    print(f"wrote {FILES['prices']}  rows={len(df)}  {df['date'].iloc[0]} .. {df['date'].iloc[-1]}")
    print(df.tail(5).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
