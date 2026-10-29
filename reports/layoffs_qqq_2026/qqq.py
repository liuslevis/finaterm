# -*- coding: utf-8 -*-
"""Derive QQQ scenario table from the Big-8 model output."""
import json
from pathlib import Path

BASE = Path(__file__).parent
data = json.loads((BASE / "out" / "model_results.json").read_text(encoding="utf-8"))

NDX0 = 29651.441
PE_FWD = 25.0          # 2027E forward P/E at the index level
DIV = 0.006
W_BIG = 0.65           # share of NDX earnings from the Big 8

# name, model key, rest-of-index EPS growth, exit P/E, probability
SCEN = [
    ("牛市", "cut10_bull", 0.08, 26.0, 0.25),
    ("基准", "cut10_base", 0.07, 23.0, 0.50),
    ("熊市", "cut10_bear", 0.03, 18.0, 0.20),
    ("深度衰退", "cut20_bear", 0.00, 14.0, 0.05),
]

rows = []
for name, key, rest_g, pe_end, prob in SCEN:
    a = data[key]["agg"]
    big_cagr = (a["eps"][-1] / a["eps"][0]) ** (1 / 5) - 1
    idx_cagr = W_BIG * big_cagr + (1 - W_BIG) * rest_g
    eps31 = NDX0 / PE_FWD * (1 + idx_cagr) ** 5
    lvl31 = eps31 * pe_end
    total = (lvl31 / NDX0) ** (1 / 5) - 1 + DIV
    rows.append(dict(name=name, key=key, big_cagr=big_cagr, idx_cagr=idx_cagr, pe_end=pe_end,
                     lvl31=lvl31, total=total, prob=prob, big_eps31=a["eps"][-1]))

exp = sum(r["total"] * r["prob"] for r in rows)
print(f"{'情景':<8}{'Big8 EPS CAGR':>14}{'指数EPS CAGR':>14}{'期末PE':>9}{'2031点位':>11}{'年化回报':>10}{'概率':>7}")
for r in rows:
    print(f"{r['name']:<8}{r['big_cagr']*100:>13.1f}%{r['idx_cagr']*100:>13.1f}%{r['pe_end']:>9.0f}"
          f"{r['lvl31']:>11,.0f}{r['total']*100:>9.1f}%{r['prob']*100:>6.0f}%")
print(f"\n概率加权年化回报: {exp*100:.1f}%")
print(f"期末点位概率加权: {sum(r['lvl31']*r['prob'] for r in rows):,.0f}")

(BASE / "out" / "qqq_scenarios.json").write_text(json.dumps(dict(rows=rows, expected=exp), indent=1), encoding="utf-8")

