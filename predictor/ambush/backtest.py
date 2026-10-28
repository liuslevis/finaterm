"""Cost-aware daily NAV for close signals executed at the next session's open."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from strategy import CACHE_DIR, limit_up_rate, rounded_limit_price


def load_prices(codes, directory: Path = CACHE_DIR / "kline") -> dict[str, pd.DataFrame]:
    """读回测用的日线缓存；**缺缓存的代码跳过**而不是报错。

    2026-01~06 的样本里有约 150 只已退市标的，AkShare 拿不到它们的历史行情
    （策略侧已记进 kline_failed.json）。没有价格就无法回测，只能把它们排除，
    调用方需要把 panel 也过滤到 ``prices`` 的代码集合。
    """
    prices = {}
    missing = []
    for code in sorted(set(codes)):
        path = directory / f"{code.replace('.', '_')}.csv"
        if not path.exists():
            missing.append(code)
            continue
        frame = pd.read_csv(path, parse_dates=["date"]).sort_values("date")
        if frame["date"].duplicated().any():
            raise ValueError(f"Duplicate price dates: {path}")
        if (
            frame[["open", "close", "volume"]].isna().any().any()
            or (frame[["open", "close"]] <= 0).any().any()
            or (frame["volume"] < 0).any()
        ):
            raise ValueError(f"Invalid backtest prices or volume: {path}")
        frame["previous_close"] = frame["close"].shift()
        prices[code] = frame.set_index(
            frame["date"].dt.strftime("%Y%m%d")
        ).rename_axis("trading_date")
    if missing:
        print(f"skip {len(missing)} codes without price cache: {missing[:5]}...")
    return prices


def backtest_score(
    panel: pd.DataFrame,
    score_column: str,
    prices: dict[str, pd.DataFrame],
    calendar: list[str],
    start_date: str,
    end_date: str,
    holding_sessions: int = 5,
    cost_bps_per_side: float = 15.0,
    entry_mask_column: str | None = None,
) -> tuple[dict, pd.DataFrame]:
    """Allocate at most 1/h of NAV to each daily cohort; unfilled cash stays cash.

    Entries use only yesterday's rankings, never future labels. A locked upper
    limit open is not filled; locked lower limit exits are postponed. This is
    still an idealized daily-bar execution model, not a queue/impact simulator.
    """
    if (
        holding_sessions < 2 or not math.isfinite(cost_bps_per_side)
        or not 0 <= cost_bps_per_side < 10_000
    ):
        raise ValueError("A-share T+1 requires holding_sessions >= 2 and costs in [0, 10000) bp")
    if calendar != sorted(set(calendar)):
        raise ValueError("Expected a sorted unique trading calendar")
    if entry_mask_column is not None:
        if entry_mask_column not in panel:
            raise ValueError(f"Missing entry mask: {entry_mask_column}")
        mask = panel[entry_mask_column]
        if not pd.api.types.is_bool_dtype(mask) or mask.isna().any():
            raise ValueError("Entry mask must contain non-missing booleans")
    fee = cost_bps_per_side / 10_000
    signals = {date: group for date, group in panel.groupby("signal_date")}
    cash = 1.0
    positions = []
    rows = []
    entered = skipped = delayed = filtered = 0
    previous_nav = peak = 1.0
    for session, date in enumerate(calendar):
        if date < start_date or date > end_date:
            continue
        prior_date = calendar[session - 1] if session else None
        # Existing overnight positions are marked before spending today's cash.
        open_nav = cash
        for position in positions:
            history = prices[position["code"]]
            if date in history.index:
                position["mark"] = history.loc[date, "open"]
            open_nav += position["units"] * position["mark"]
        group = signals.get(prior_date)
        if group is not None:
            ranked = group.dropna(subset=[score_column])
            if len(ranked) >= 3:
                count = (len(ranked) + 1) // 2
                threshold = ranked[score_column].nlargest(count).iloc[-1]
                selected = ranked[ranked[score_column] >= threshold]
                budget = min(cash, open_nav / holding_sessions)
                per_stock = budget / len(selected)
                if entry_mask_column is not None:
                    accepted = selected[entry_mask_column]
                    filtered += int((~accepted).sum())
                    selected = selected[accepted]
                if per_stock <= 0:
                    selected = selected.iloc[:0]
                for _, candidate in selected.iterrows():
                    code = candidate["code"]
                    history = prices[code]
                    if date not in history.index:
                        skipped += 1
                        continue
                    bar = history.loc[date]
                    rate = limit_up_rate(code, str(candidate.get("name", "")))
                    upper = rounded_limit_price(bar["previous_close"], rate)
                    if bar["volume"] <= 0 or bar["open"] >= upper - 1e-8:
                        skipped += 1
                        continue
                    units = per_stock / (bar["open"] * (1 + fee))
                    positions.append({
                        "code": code, "units": units, "mark": bar["open"],
                        "exit_session": session + holding_sessions - 1,
                        "rate": rate,
                    })
                    cash -= per_stock
                    entered += 1
        remaining = []
        for position in positions:
            history = prices[position["code"]]
            tradable = False
            if date in history.index:
                bar = history.loc[date]
                position["mark"] = bar["close"]
                lower = rounded_limit_price(bar["previous_close"], -position["rate"])
                tradable = bar["volume"] > 0 and bar["close"] > lower + 1e-8
            if session >= position["exit_session"] and tradable:
                cash += position["units"] * position["mark"] * (1 - fee)
            else:
                remaining.append(position)
                if session >= position["exit_session"]:
                    delayed += 1
        positions = remaining
        nav = cash + sum(p["units"] * p["mark"] for p in positions)
        peak = max(peak, nav)
        rows.append({
            "date": date, "nav": nav, "daily_return": nav / previous_nav - 1,
            "drawdown_pct": (nav / peak - 1) * 100,
            "exposure_pct": (nav - cash) / nav * 100,
            "open_positions": len(positions),
        })
        previous_nav = nav
    daily = pd.DataFrame(rows)
    if daily.empty:
        raise RuntimeError(f"No trading sessions between {start_date} and {end_date}")
    std = daily["daily_return"].std(ddof=1)
    metrics = {
        "score": score_column,
        "holding_sessions": holding_sessions,
        "cost_bps_per_side": cost_bps_per_side,
        "sessions": len(daily),
        "net_return_pct": (daily.iloc[-1]["nav"] - 1) * 100,
        "net_sharpe": (
            daily["daily_return"].mean() / std * math.sqrt(252)
            if pd.notna(std) and std > 0 else float("nan")
        ),
        "max_drawdown_pct": -daily["drawdown_pct"].min(),
        "mean_exposure_pct": daily["exposure_pct"].mean(),
        "entries": entered,
        "skipped_entries": skipped,
        "rule_filtered_candidates": filtered,
        "delayed_exit_sessions": delayed,
        "unclosed_positions": len(positions),
    }
    return metrics, daily
