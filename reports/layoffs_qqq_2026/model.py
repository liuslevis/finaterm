# -*- coding: utf-8 -*-
"""
Big Tech layoff -> financial statement model, and QQQ scenario engine.
All figures in USD billions unless stated. Baseline = calendarised FY2026E.
"""
import json
from pathlib import Path

OUT = Path(__file__).parent / "out"
OUT.mkdir(parents=True, exist_ok=True)

TAX = 0.18
SBC_PCT = 0.025          # stock-based comp as % of revenue
WC_PCT = 0.02            # change in working capital as % of revenue change
DEP_LIFE = 8             # blended useful life of capex, years
COMP_GROWTH = 0.05       # fully-loaded comp per head growth
AI_COST_RATIO = 0.20     # AI inference/tooling cost as % of displaced comp
TOKEN_PCT = 0.08         # AI tool/token budget for retained staff, % of comp

# ---------------------------------------------------------------------------
# Baseline: calendarised FY2026E. Revenue/EBIT/headcount from company filings
# and 2026 quarterly reports; capex, D&A, comp are modelled estimates.
# ---------------------------------------------------------------------------
COMPANIES = {
    "MSFT":  dict(rev=331.8, ebit=153.0, hc=223, comp=0.290, capex=145, da=32, sh=7.43, px=600, seg="platform"),
    "GOOGL": dict(rev=502.0, ebit=164.0, hc=187, comp=0.300, capex=200, da=35, sh=12.10, px=347, seg="platform"),
    "AMZN":  dict(rev=815.0, ebit=95.0,  hc=350, comp=0.250, capex=200, da=65, sh=10.70, px=271, seg="platform"),
    "META":  dict(rev=248.0, ebit=75.0,  hc=70,  comp=0.400, capex=137, da=30, sh=2.48,  px=605, seg="platform"),
    "AAPL":  dict(rev=450.0, ebit=140.0, hc=160, comp=0.250, capex=12,  da=12, sh=14.60, px=274, seg="hardware"),
    "NVDA":  dict(rev=400.0, ebit=250.0, hc=42,  comp=0.400, capex=8,   da=4,  sh=24.30, px=230, seg="semi"),
    "AVGO":  dict(rev=75.0,  ebit=45.0,  hc=37,  comp=0.300, capex=3,   da=6,  sh=4.70,  px=383, seg="semi"),
    "TSLA":  dict(rev=115.0, ebit=9.0,   hc=120, comp=0.200, capex=10,  da=6,  sh=3.50,  px=400, seg="hardware"),
}

# historical combined series (6 mega caps, calendarised, estimates for 2026)
HIST = {
    "year":   [2019, 2020, 2021, 2022, 2023, 2024, 2025, 2026],
    "hc":     [1258, 1404, 1805, 2227, 2163, 2236, 2256, 2178],   # thousands
    "rev":    [911,  1075, 1366, 1533, 1672, 1909, 2285, 2747],   # bn
    "payroll":[150,  175,  210,  245,  265,  290,  310,  328],    # bn
    "capex":  [80,   95,   130,  160,  150,  230,  380,  715],    # bn
}

# capex history by vintage (used for depreciation roll-forward)
CAPEX_HIST = {2019: 80, 2020: 95, 2021: 130, 2022: 160, 2023: 150, 2024: 230, 2025: 380, 2026: 715}

SCEN = {
    "base": dict(rev=[0.12, 0.10, 0.08, 0.07, 0.06], capex_mult=[1.00, 1.00, 1.00, 1.00, 1.00]),
    "bull": dict(rev=[0.16, 0.15, 0.13, 0.11, 0.09], capex_mult=[1.00, 1.05, 1.08, 1.05, 1.02]),
    "bear": dict(rev=[0.07, 0.04, 0.01, 0.00, 0.02], capex_mult=[1.00, 1.00, 0.95, 0.85, 0.80]),
}

BASE_CAPEX = [900, 1020, 1100, 1120, 1100]  # aggregate 2027-2031 before scenario multiplier


def run(cut=0.0, scen="base", years=5, comp_growth=COMP_GROWTH, ai_ratio=AI_COST_RATIO,
        rev_drag_per_cut=0.05, token_pct=TOKEN_PCT, dep_life=DEP_LIFE, capex_override=None,
        buyback_pct=0.6):
    """Project the Big 8 aggregate and per-company paths."""
    rev_g = SCEN[scen]["rev"]
    capex_m = SCEN[scen]["capex_mult"]

    agg = {k: [] for k in ["year", "rev", "comp", "ai_cost", "other", "da", "ebit", "ni",
                           "eps", "fcf", "capex", "shares", "hc", "ebit_margin", "fcf_margin",
                           "capex_rev", "da_rev", "rev_per_hc"]}
    per_co = {k: {kk: [] for kk in ["rev", "comp", "da", "ebit", "ni", "eps", "fcf", "hc"]} for k in COMPANIES}

    # aggregate baseline
    tot = dict(rev=sum(c["rev"] for c in COMPANIES.values()),
               ebit=sum(c["ebit"] for c in COMPANIES.values()),
               hc=sum(c["hc"] for c in COMPANIES.values()),
               comp=sum(c["hc"] * c["comp"] for c in COMPANIES.values()),
               da=sum(c["da"] for c in COMPANIES.values()),
               capex=sum(c["capex"] for c in COMPANIES.values()),
               sh=sum(c["sh"] for c in COMPANIES.values()),
               mcap=sum(c["sh"] * c["px"] for c in COMPANIES.values()))
    other0 = tot["rev"] - tot["comp"] - tot["da"] - tot["ebit"]
    rev0, hc0, comp0, da0 = tot["rev"], tot["hc"], tot["comp"], tot["da"]

    # state
    rev = rev0
    hc = {k: c["hc"] for k, c in COMPANIES.items()}
    comp_ph = {k: c["comp"] for k, c in COMPANIES.items()}
    da = {k: c["da"] for k, c in COMPANIES.items()}
    sh = {k: c["sh"] for k, c in COMPANIES.items()}
    capex_prev = {k: c["capex"] for k, c in COMPANIES.items()}
    capex_vintage = {y: v for y, v in CAPEX_HIST.items()}

    # record year 0
    def record(year, ai_cost=0.0):
        comp = sum(hc[k] * comp_ph[k] for k in COMPANIES)
        da_tot = sum(da.values())
        other = other0 * (rev / rev0) ** 0.75
        ebit = rev - comp - ai_cost - other - da_tot
        ni = ebit * (1 - TAX)
        sbc = rev * SBC_PCT
        capex_tot = sum(capex_prev.values())
        fcf = ni + da_tot + sbc - capex_tot - WC_PCT * (rev - (agg["rev"][-1] if agg["rev"] else rev0))
        shares = sum(sh.values())
        eps = ni / shares
        for key, val in [("year", year), ("rev", rev), ("comp", comp), ("ai_cost", ai_cost),
                         ("other", other), ("da", da_tot), ("ebit", ebit), ("ni", ni), ("eps", eps),
                         ("fcf", fcf), ("capex", capex_tot), ("shares", shares), ("hc", sum(hc.values())),
                         ("ebit_margin", ebit / rev), ("fcf_margin", fcf / rev), ("capex_rev", capex_tot / rev),
                         ("da_rev", da_tot / rev), ("rev_per_hc", rev / sum(hc.values()))]:
            agg[key].append(val)
        for k in COMPANIES:
            per_co[k]["rev"].append(rev * COMPANIES[k]["rev"] / rev0)
            per_co[k]["comp"].append(hc[k] * comp_ph[k])
            per_co[k]["da"].append(da[k])
            per_co[k]["hc"].append(hc[k])
        return comp, da_tot, ebit, ni, eps

    record(2026)

    for t in range(years):
        year = 2027 + t
        # revenue
        g = rev_g[t] - rev_drag_per_cut * cut
        rev = rev * (1 + g)
        # headcount
        for k in COMPANIES:
            hc[k] = max(hc[k] * (1 - cut), COMPANIES[k]["hc"] * 0.35)
            comp_ph[k] = comp_ph[k] * (1 + comp_growth)
        # displaced vs baseline (no-cut) path
        displaced = sum(max(0.0, COMPANIES[k]["hc"] * (1 - cut) ** (t + 1) * -1 + 0) for k in COMPANIES)
        # AI replacement cost on the cumulative headcount gap vs baseline
        gap = sum(max(0.0, COMPANIES[k]["hc"] - hc[k]) for k in COMPANIES)
        ai_cost = gap * sum(COMPANIES[k]["hc"] * COMPANIES[k]["comp"] for k in COMPANIES) / hc0 * ai_ratio
        # token budget for retained staff
        comp_now = sum(hc[k] * comp_ph[k] for k in COMPANIES)
        ai_cost += comp_now * token_pct
        # capex
        for k in COMPANIES:
            base = COMPANIES[k]["capex"] / tot["capex"]
            if capex_override is not None:
                target = capex_override[t] * base
            else:
                target = BASE_CAPEX[t] * base * capex_m[t]
            capex_prev[k] = target
        capex_vintage[year] = sum(capex_prev.values())
        # depreciation from vintages
        for k in COMPANIES:
            share = COMPANIES[k]["capex"] / tot["capex"]
            da[k] = sum(capex_vintage.get(y, 0) * share for y in range(year - dep_life, year)) / dep_life
        # shares (buybacks constrained by FCF)
        comp_est = sum(hc[k] * comp_ph[k] for k in COMPANIES)
        other = other0 * (rev / rev0) ** 0.75
        ebit_est = rev - comp_est - ai_cost - other - sum(da.values())
        ni_est = ebit_est * (1 - TAX)
        fcf_est = ni_est + sum(da.values()) + rev * SBC_PCT - sum(capex_prev.values()) - WC_PCT * (rev - agg["rev"][-1])
        price = 30.0 * (agg["ni"][-1] / agg["shares"][-1])
        for k in COMPANIES:
            buy = max(0.0, min(fcf_est * buyback_pct, ni_est * 0.9)) * COMPANIES[k]["rev"] / rev0
            sh[k] = max(COMPANIES[k]["sh"] * 0.6, sh[k] - buy / max(price, 1))
        record(year, ai_cost)

    return agg, per_co


def summarize(agg):
    return {k: v for k, v in agg.items()}


if __name__ == "__main__":
    out = {}
    for cut, name in [(0.0, "flat"), (0.10, "cut10"), (0.20, "cut20")]:
        for scen in ["base", "bull", "bear"]:
            agg, per_co = run(cut=cut, scen=scen)
            out[f"{name}_{scen}"] = {
                "agg": agg,
                "per_co": {k: {kk: vv for kk, vv in v.items()} for k, v in per_co.items()},
            }
    # sensitivity: EPS CAGR and FCF 2031 across cut rate x revenue growth shift
    sens = []
    for cut in [0.0, 0.05, 0.10, 0.15, 0.20, 0.25]:
        for shift in [-0.04, -0.02, 0.0, 0.02, 0.04]:
            base_rev = SCEN["base"]["rev"][:]
            SCEN["base"]["rev"] = [g + shift for g in base_rev]
            agg, _ = run(cut=cut, scen="base")
            SCEN["base"]["rev"] = base_rev
            eps_cagr = (agg["eps"][-1] / agg["eps"][0]) ** (1 / 5) - 1
            sens.append(dict(cut=cut, shift=shift, eps_cagr=eps_cagr, eps31=agg["eps"][-1],
                             fcf31=agg["fcf"][-1], ebit_margin31=agg["ebit_margin"][-1]))
    out["sensitivity"] = sens
    out["hist"] = HIST
    (OUT / "model_results.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8")

    # console summary
    for k in ["flat_base", "cut10_base", "cut20_base", "cut10_bull", "cut10_bear", "cut20_bear"]:
        a = out[k]["agg"]
        print(f"\n== {k} ==")
        for i, y in enumerate(a["year"]):
            print(f"  {y}: rev {a['rev'][i]:7.0f} ebit% {a['ebit_margin'][i]*100:5.1f} "
                  f"eps {a['eps'][i]:6.2f} fcf {a['fcf'][i]:6.0f} hc {a['hc'][i]:6.0f} "
                  f"capex% {a['capex_rev'][i]*100:5.1f} da% {a['da_rev'][i]*100:5.1f}")
    print("\n== sensitivity EPS CAGR ==")
    for cut in [0.0, 0.10, 0.20]:
        row = [s for s in sens if abs(s["cut"] - cut) < 1e-9]
        print(cut, ["%.3f" % s["eps_cagr"] for s in row])




