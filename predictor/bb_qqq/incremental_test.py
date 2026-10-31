"""Does the LLM score add anything on top of plain momentum reversal?

In this sample a trivial 20-day momentum rule is a far stronger predictor of the
next 1-7 days than anything the LLM produces.  So the only question that matters
for "is this a factor" is the *incremental* content: residualise the score on the
momentum baselines and see whether what is left still correlates with returns,
and whether the score's coefficient survives in a joint regression.
"""

import numpy as np
import pandas as pd
from scipy import stats

from evaluate import ic_block, newey_west_slope


def residual_ic(panel: pd.DataFrame, h: int) -> dict:
    sub = panel.dropna(subset=["score_1d", f"r{h}", "mom5", "mom20"]).copy()
    n = len(sub)
    if n < 10:
        return {"n": n}
    # residualise score on momentum (and the overnight gap, known at 10:30)
    C = np.column_stack([np.ones(n), sub["mom5"], sub["mom20"], sub["gap"].fillna(0)])
    X = sub["score_1d"].to_numpy(float)
    y = sub[f"r{h}"].to_numpy(float)
    beta = np.linalg.lstsq(C, X, rcond=None)[0]
    resid = X - C @ beta
    r_resid = float(np.corrcoef(resid, y)[0, 1])

    # joint regression: r_h ~ score + mom5 + mom20 (NW errors on the score term)
    Z = np.column_stack([np.ones(n), X, sub["mom5"], sub["mom20"]])
    b = np.linalg.lstsq(Z, y, rcond=None)[0]
    e = y - Z @ b
    ZtZ_inv = np.linalg.inv(Z.T @ Z)
    S = np.zeros((4, 4))
    for t in range(n):
        u = Z[t] * e[t]
        S += np.outer(u, u)
    for lag in range(1, h):
        G = np.zeros((4, 4))
        for t in range(lag, n):
            G += np.outer(Z[t] * e[t], Z[t - lag] * e[t - lag])
        S += (1 - lag / h) * (G + G.T)
    cov = ZtZ_inv @ S @ ZtZ_inv
    t_score = float(b[1] / np.sqrt(max(cov[1, 1], 1e-18)))
    t_mom20 = float(b[3] / np.sqrt(max(cov[3, 3], 1e-18)))

    return {
        "n": n,
        "ic_raw": round(float(np.corrcoef(X, y)[0, 1]), 3),
        "ic_momentum_residual": round(r_resid, 3),
        "beta_score": round(float(b[1]), 5),
        "t_score_joint": round(t_score, 2),
        "beta_mom20": round(float(b[3]), 4),
        "t_mom20_joint": round(t_mom20, 2),
    }


def main() -> None:
    panel = pd.read_csv("data/panel_brief.csv")
    for h in (1, 3, 7):
        print(f"h={h}d  {residual_ic(panel, h)}")


if __name__ == "__main__":
    main()
