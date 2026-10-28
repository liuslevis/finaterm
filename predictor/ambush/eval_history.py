# -*- coding: utf-8 -*-
r"""在扩展历史（2026-01~06）上评估生产 LV2 打分的样本外表现。

背景
----
数据集从 59 天扩到 175 天，新增了 2026-01~06。要回答的问题是：
**这套 LV2 因子在训练窗口（2026-06~07）之外还成立吗？**

两条路径：

1. **走查前推（walk-forward）**：每个信号日只用它之前的数据拟合方向。
   实测在 2026-01~06 上到窗口后段（训练样本 300+ 行）时，没有任何因子的
   |Spearman| 能达到 0.10 的门槛 —— 也就是说这段历史上因子与前瞻收益无关，
   模型根本拟合不出来。这是「没有信号」，不是「没数据」。

2. **本次脚本**：把生产权重（在 2026-06-01~07-31 上拟合）直接套到 2026-01~06
   的样本上，看排序能力。注意这是**回顾性**诊断：权重是用更晚的数据拟合的，
   存在前视偏差，不能当作可交易的回测结论，只能回答「同一套因子的排序在
   更早的样本上是否同向」。

用法
----
    python predictor/ambush/eval_history.py
    python predictor/ambush/eval_history.py --split 20260630
"""

from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import optimize_score as o  # noqa: E402
from backtest import load_prices  # noqa: E402
from strategy import LV2_MODEL_PATH  # noqa: E402


def score_window(panel: pd.DataFrame, weights: dict[str, float]) -> pd.DataFrame:
    frame = panel.dropna(subset=list(weights)).copy()
    if frame.empty:
        return frame
    frame["score"] = o.apply_weighted_model(frame, weights)
    return frame


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from", dest="date_from", default="20260105")
    ap.add_argument("--through", default="20260921")
    ap.add_argument("--split", default="20260630", help="把样本切成前后两段比较")
    ap.add_argument("--out", default=os.path.join(HERE, "data"))
    args = ap.parse_args(argv)

    model = json.loads(LV2_MODEL_PATH.read_text(encoding="utf-8"))
    weights = {k: float(v) for k, v in model["production_weights"].items()}
    print(f"生产模型 {model['production_score']}（训练 {model['trained_from']}~"
          f"{model['trained_through']}，{len(weights)} 个因子）")

    panel = o.load_panel(args.date_from, args.through)
    eligible = o.rank_panel(
        panel[
            panel["launch_detected"].astype(bool)
            & panel["data_quality_valid"].astype(bool)
        ].copy()
    )
    panel.loc[eligible.index, eligible.columns] = eligible
    scored = score_window(eligible, weights)
    print(f"样本 {len(scored)} 行 / {scored['signal_date'].nunique()} 个交易日")

    prices = load_prices(scored["code"])
    priced = set(prices)
    scored = scored[scored["code"].isin(priced)].copy()
    calendar = sorted(set().union(*(set(f.index) for f in prices.values())))
    print(f"有价格缓存 {len(priced)} 只，回测样本 {len(scored)} 行")

    windows = [
        ("oos_early", args.date_from, args.split),
        ("is_late", (pd.Timestamp(args.split) + pd.Timedelta(days=1)).strftime("%Y%m%d"),
         args.through),
    ]
    rows = []
    for name, start, end in windows:
        sub = scored[(scored["signal_date"] >= start) & (scored["signal_date"] <= end)].copy()
        if sub.empty:
            print(f"{name}: 无样本")
            continue
        for horizon in o.EVALUATION_HORIZONS:
            col = f"next_open_{horizon}_pct"
            sub[f"forward_{horizon}_pct"] = sub[col]
        ev = pd.DataFrame(o.evaluate_score(sub, "score"))
        metrics, nav = o.backtest_score(
            sub, "score", prices, calendar, start, end, 5, 15.0
        )
        nav.to_csv(os.path.join(args.out, f"ambush_history_{name}_nav.csv"), index=False)
        ev.to_csv(os.path.join(args.out, f"ambush_history_{name}_ic.csv"), index=False)
        print(f"\n=== {name}  {start}~{end}  {len(sub)} 行 / "
              f"{sub['signal_date'].nunique()} 天 ===")
        for _, r in ev.iterrows():
            print(f"  {r['horizon']:>3}: 日均 rank IC {r['daily_ic_mean']:+.4f}  "
                  f"整体 IC {r['spearman']:+.4f}  "
                  f"头半均值 {r['top_mean_pct']:+.2f}%  "
                  f"尾半均值 {r['bottom_mean_pct']:+.2f}%")
        print(f"  组合: 净收益 {metrics['net_return_pct']:+.2f}%  "
              f"Sharpe {metrics['net_sharpe']:+.2f}  "
              f"最大回撤 {metrics['max_drawdown_pct']:.2f}%  "
              f"成交 {metrics['entries']} 笔  敞口 {metrics['mean_exposure_pct']:.1f}%")
        rows.append({"window": name, "start": start, "end": end,
                     "samples": len(sub), **metrics})

    if rows:
        out = pd.DataFrame(rows)
        out.to_csv(os.path.join(args.out, "ambush_history_portfolio.csv"), index=False)
        print("\n汇总 ->", os.path.join(args.out, "ambush_history_portfolio.csv"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
