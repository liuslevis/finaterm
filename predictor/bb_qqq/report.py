"""Render reports/RESULTS.md from the metrics.json files produced by evaluate.py.

Keeps the write-up reproducible: every number in CORR.md comes from here.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import REPORTS

DEFAULT_RUNS = {
    "brief (dated)": "reports/metrics_brief.json",
    "brief (blind)": "reports/metrics_brief_blind.json",
    "full (dated)": "reports/metrics_full.json",
    "full (blind)": "reports/metrics_full_blind.json",
}


def fmt_p(p: float) -> str:
    if p is None:
        return "—"
    if p < 0.001:
        return "<0.001"
    return f"{p:.3f}"


def table_for(metrics: dict, name: str) -> list[str]:
    lines = [
        f"### {name}  (n={metrics['n_dates']} dates, {metrics['n_episodes']} episodes, "
        f"{metrics['date_range'][0]} .. {metrics['date_range'][1]})",
        "",
        "| predictor | h | n | Pearson IC | p | Rank IC | NW t | boot 95% CI | hit | top-bottom (pp) |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for predictor, by_h in metrics["table"].items():
        for h, block in by_h.items():
            if "pearson" not in block:
                continue
            ci = block.get("ci95", [None, None])
            lines.append(
                f"| {predictor} | {h} | {block['n']} | {block['pearson']:+.3f} | {fmt_p(block['p_pearson'])} | "
                f"{block['spearman']:+.3f} | {block['t_nw']:+.2f} | [{ci[0]}, {ci[1]}] | "
                f"{block['hit_rate']:.2f} | {block['ls_spread_pct']:+.2f} |"
            )
    lines.append("")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(REPORTS / "RESULTS.md"))
    args = ap.parse_args()

    runs = {}
    for name, rel in DEFAULT_RUNS.items():
        path = REPORTS.parent / rel if not Path(rel).is_absolute() else Path(rel)
        if path.is_file():
            runs[name] = json.loads(path.read_text(encoding="utf-8"))

    if not runs:
        raise SystemExit("no metrics files found; run evaluate.py first")

    lines = ["# bb_qqq — 评估结果（自动生成）", ""]
    for name, metrics in runs.items():
        lines += table_for(metrics, name)

    # leakage / placebo cross-check
    lines += ["## 泄漏对照", ""]
    lines += ["| run | placebo: 次日分数 vs 今日 r1 | corr(score, ret_0) | corr(score, gap) | corr(score, mom5) |",
              "|---|---|---|---|---|"]
    for name, metrics in runs.items():
        plc = metrics.get("placebo", {}).get("next_score_vs_today_r1", {})
        plc_r = f"{plc['pearson']:+.3f}" if "pearson" in plc else "—"
        diag = metrics.get("diagnostics", {})
        lines.append(f"| {name} | {plc_r} | {diag.get('corr_score_vs_ret_0','—')} | "
                     f"{diag.get('corr_score_vs_gap','—')} | {diag.get('corr_score_vs_mom5','—')} |")
    lines.append("")

    # ---- verdict -------------------------------------------------------
    main = runs.get("brief (dated)")
    if main:
        lines += ["## 自动判读", ""]
        power = main.get("power", {})
        best_baseline = {}
        for predictor, by_h in main["table"].items():
            if predictor.startswith("llm"):
                continue
            for h, block in by_h.items():
                if "pearson" in block:
                    key = h
                    if key not in best_baseline or abs(block["pearson"]) > abs(best_baseline[key][1]):
                        best_baseline[key] = (predictor, block["pearson"])
        for h in ("1d", "3d", "7d"):
            block = main["table"].get("llm_p(2p-1)", {}).get(h, {})
            if "pearson" not in block:
                lines.append(f"- **{h}**: 样本不足（n<8），无法给结论。")
                continue
            base = best_baseline.get(h)
            base_txt = f"最强 baseline 是 `{base[0]}`（IC {base[1]:+.3f}）" if base else "无可用 baseline"
            verdict = "方向性证据" if (block["ci95"][0] > 0 or block["ci95"][1] < 0) else "CI 含 0，不显著"
            lines.append(
                f"- **{h}**: n={block['n']}，IC {block['pearson']:+.3f}"
                f"（95% CI [{block['ci95'][0]}, {block['ci95'][1]}]，NW t={block['t_nw']:+.2f}，"
                f"胜率 {block['hit_rate']:.2f} vs 基准 {block['base_up_rate']:.2f}）；"
                f"{base_txt}；**{verdict}**。"
            )
        if power:
            lines += ["", f"> 统计功效：n={power.get('current_n')} 时 IC 的标准误约 "
                          f"{power.get('se_of_ic_at_current_n')}；要在 80% 功效下检出 IC=0.2 需要 "
                          f"n≈{power.get('n_for_ic_0.2')}，IC=0.1 需要 n≈{power.get('n_for_ic_0.1')}。"]
        lines.append("")

    Path(args.out).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")
    print("\n".join(lines[:20]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
