from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent / "data"


def load(name: str) -> pd.DataFrame:
    df = pd.read_csv(DATA / f"{name}.csv", index_col=0, parse_dates=True)
    return df[df.Close > 0].dropna(subset=["Close"])
