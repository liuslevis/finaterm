"""Build and analyze a weekly proxy dataset for China's market-rescue activity."""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

import akshare as ak

ETF_CODES = ("510050", "510300", "510500", "512100", "588000")
LARGE_CAP_CODES = ("510050", "510300")
SMALL_GROWTH_CODES = ("510500", "512100", "588000")
DEFAULT_START = "2023-01-01"
DEFAULT_END = pd.Timestamp.today().strftime("%Y-%m-%d")
OUTPUT = Path(__file__).with_name("rescue_weekly.csv")
SHARE_CACHE = Path(__file__).with_name("rescue_weekly_shares.csv")
EVENTS = Path(__file__).with_name("rescue_events.csv")
EVENT_PERFORMANCE = Path(__file__).with_name("rescue_event_performance.csv")
EVENT_ASSET_PERFORMANCE = Path(__file__).with_name("rescue_event_asset_performance.csv")
INSTRUMENT_NAMES = {
    "510050": "上证50ETF",
    "510060": "央企ETF",
    "510300": "沪深300ETF",
    "510500": "中证500ETF",
    "512100": "中证1000ETF",
    "560170": "央企科技ETF",
    "561790": "央企现代能源ETF",
    "562380": "央企科技引领ETF",
    "563050": "央企科技引领ETF",
    "588000": "科创50ETF",
    "601288": "农业银行",
    "601398": "工商银行",
    "601939": "建设银行",
    "601988": "中国银行",
}
EVENT_CATEGORIES = (
    "confirmed_purchase",
    "committed_purchase",
    "liquidity_facility",
    "regulatory_stabilization",
)
EVENT_COLUMNS = (
    "official_announcement",
    "official_message_count",
    "core_purchase_cluster_count",
    "broad_rescue_cluster_count",
    *EVENT_CATEGORIES,
)
FORWARD_HORIZONS = {
    "1w": 1,
    "2w": 2,
    "1m": 4,
    "2m": 8,
    "3m": 13,
    "6m": 26,
}


def fetch_prices(
    start: str, end: str, symbols: tuple[str, ...] = ETF_CODES
) -> dict[str, pd.DataFrame]:
    prices = {}
    for code in symbols:
        frame = pd.DataFrame()
        eastmoney_error = None
        for attempt in range(1, 4):
            try:
                frame = ak.fund_etf_hist_em(
                    symbol=code,
                    period="daily",
                    start_date=start.replace("-", ""),
                    end_date=end.replace("-", ""),
                    adjust="qfq",
                )
                break
            except (requests.RequestException, ValueError, KeyError, TypeError) as exc:
                eastmoney_error = exc
                if attempt == 3:
                    break
                time.sleep(attempt)
        if frame.empty:
            print(f"Eastmoney unavailable for {code}; using Sina history")
            frame = ak.fund_etf_hist_sina(symbol=f"sh{code}")
            if frame.empty:
                raise RuntimeError(
                    f"No price data returned for ETF {code}"
                ) from eastmoney_error
            frame = frame.rename(
                columns={"date": "日期", "close": "收盘", "low": "最低", "amount": "成交额"}
            )
        if frame.empty:
            raise RuntimeError(f"No price data returned for ETF {code}")
        frame = frame.rename(
            columns={
                "日期": "date",
                "收盘": "close",
                "最低": "low",
                "成交额": "turnover",
            }
        )
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame[
            frame["date"].between(pd.Timestamp(start), pd.Timestamp(end), inclusive="both")
        ]
        prices[code] = frame.set_index("date")[["close", "low", "turnover"]].sort_index()
    return prices


def event_symbols(events: pd.DataFrame) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                symbol
                for value in events["asset_symbols"].dropna()
                for symbol in value.split("|")
            }
            | {"510300"}
        )
    )


def build_event_performance(
    events: pd.DataFrame, prices: dict[str, pd.DataFrame]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    common_dates = pd.DatetimeIndex(
        sorted(set.intersection(*(set(frame.index) for frame in prices.values())))
    )
    week_ends = pd.Series(common_dates, index=common_dates).groupby(
        common_dates.to_period("W-FRI")
    ).max()
    weekly_close = pd.DataFrame(
        {
            symbol: frame["close"].reindex(week_ends.to_numpy()).to_numpy()
            for symbol, frame in prices.items()
        },
        index=week_ends.index,
    )
    weekly_return = weekly_close.pct_change() * 100
    forward_returns = {
        horizon: (weekly_close.shift(-horizon) / weekly_close - 1) * 100
        for horizon in FORWARD_HORIZONS.values()
    }

    detail_rows = []
    cluster_rows = []
    for cluster_id, group in events.groupby("cluster_id", sort=True):
        event_date = group["event_date"].min()
        period = event_date.to_period("W-FRI")
        symbols = sorted(
            {
                symbol
                for value in group["asset_symbols"].dropna()
                for symbol in value.split("|")
            }
        )
        assets = []
        for symbol in symbols:
            if period not in weekly_return.index or pd.isna(weekly_return.at[period, symbol]):
                continue
            event_week = weekly_return.at[period, symbol]
            benchmark_week = weekly_return.at[period, "510300"]
            forward = {
                horizon: forward_returns[horizon].at[period, symbol]
                for horizon in FORWARD_HORIZONS.values()
            }
            benchmark_forward = {
                horizon: forward_returns[horizon].at[period, "510300"]
                for horizon in FORWARD_HORIZONS.values()
            }
            detail_rows.append(
                {
                    "cluster_id": cluster_id,
                    "event_date": event_date.date(),
                    "week_end": week_ends.at[period].date(),
                    "symbol": symbol,
                    "asset_name": INSTRUMENT_NAMES[symbol],
                    "event_week_return_pct": event_week,
                    "event_week_excess_pct": event_week - benchmark_week,
                    **{
                        f"forward_{label}_return_pct": forward[horizon]
                        for label, horizon in FORWARD_HORIZONS.items()
                    },
                    **{
                        f"forward_{label}_excess_pct": forward[horizon]
                        - benchmark_forward[horizon]
                        for label, horizon in FORWARD_HORIZONS.items()
                    },
                }
            )
            assets.append((symbol, event_week, forward))
        if not assets:
            continue
        qualities = "|".join(sorted(group["mapping_quality"].unique()))
        cluster_rows.append(
            {
                "cluster_id": cluster_id,
                "event_date": event_date.date(),
                "week_end": week_ends.at[period].date(),
                "categories": "|".join(sorted(group["category"].unique())),
                "asset_scope": "|".join(sorted(group["asset_scope"].unique())),
                "asset_symbols": "|".join(symbol for symbol, _, _ in assets),
                "mapping_quality": qualities,
                "asset_count": len(assets),
                "event_week_return_pct": np.mean([value for _, value, _ in assets]),
                "event_week_excess_pct": np.mean([value for _, value, _ in assets])
                - weekly_return.at[period, "510300"],
                **{
                    f"forward_{label}_return_pct": np.mean(
                        [forward[horizon] for _, _, forward in assets]
                    )
                    for label, horizon in FORWARD_HORIZONS.items()
                },
                **{
                    f"forward_{label}_excess_pct": np.mean(
                        [forward[horizon] for _, _, forward in assets]
                    )
                    - benchmark_forward[horizon]
                    for label, horizon in FORWARD_HORIZONS.items()
                },
            }
        )
    return pd.DataFrame(cluster_rows), pd.DataFrame(detail_rows)


def weekly_market_data(prices: dict[str, pd.DataFrame]) -> pd.DataFrame:
    rows = []
    common_dates = sorted(
        set.intersection(*(set(prices[code].index) for code in ETF_CODES))
    )
    trading_days = pd.DatetimeIndex(common_dates)
    weeks = pd.Series(trading_days, index=trading_days).groupby(trading_days.to_period("W-FRI"))

    previous_closes = None
    for _, dates in weeks:
        week_dates = pd.DatetimeIndex(dates)
        end_date = week_dates.max()
        closes = {code: prices[code].loc[end_date, "close"] for code in ETF_CODES}
        if previous_closes is None:
            previous_closes = closes
            continue

        returns = {
            code: (closes[code] / previous_closes[code] - 1) * 100 for code in ETF_CODES
        }
        hs300 = prices["510300"].loc[week_dates]
        rows.append(
            {
                "week_end": end_date,
                "hs300_return_pct": returns["510300"],
                "panic_drawdown_pct": (hs300["low"].min() / previous_closes["510300"] - 1)
                * 100,
                "close_rebound_pct": (hs300["close"].iloc[-1] / hs300["low"].min() - 1)
                * 100,
                "largecap_relative_pct": np.mean([returns[c] for c in LARGE_CAP_CODES])
                - np.mean([returns[c] for c in SMALL_GROWTH_CODES]),
                "basket_turnover_bn": sum(
                    prices[code].loc[week_dates, "turnover"].sum() for code in ETF_CODES
                )
                / 1e9,
            }
        )
        previous_closes = closes

    weekly = pd.DataFrame(rows).set_index("week_end")
    prior_median = weekly["basket_turnover_bn"].shift(1).rolling(20, min_periods=8).median()
    weekly["turnover_ratio_20w"] = weekly["basket_turnover_bn"] / prior_median
    return weekly


def fetch_share_snapshot(date: pd.Timestamp, attempts: int = 3) -> dict[str, float]:
    for attempt in range(1, attempts + 1):
        try:
            frame = ak.fund_etf_scale_sse(date=date.strftime("%Y%m%d"))
            selected = frame[frame["基金代码"].isin(ETF_CODES)].set_index("基金代码")
            missing = set(ETF_CODES) - set(selected.index)
            if missing:
                raise RuntimeError(f"missing ETFs: {sorted(missing)}")
            return selected["基金份额"].astype(float).to_dict()
        except (requests.RequestException, ValueError, KeyError, TypeError, RuntimeError):
            if attempt == attempts:
                raise
            time.sleep(attempt)
    raise AssertionError("unreachable")


def add_share_flows(
    weekly: pd.DataFrame, prices: dict[str, pd.DataFrame], delay: float
) -> pd.DataFrame:
    snapshots = {}
    if SHARE_CACHE.exists():
        cached = pd.read_csv(SHARE_CACHE, index_col="week_end", parse_dates=["week_end"])
        snapshots = cached.to_dict(orient="index")

    total = len(weekly)
    for number, date in enumerate(weekly.index, start=1):
        if date not in snapshots:
            snapshots[date] = fetch_share_snapshot(date)
            cache = pd.DataFrame.from_dict(snapshots, orient="index").sort_index()
            cache.index.name = "week_end"
            cache.to_csv(SHARE_CACHE, encoding="utf-8-sig", float_format="%.0f")
        if number == 1 or number % 25 == 0 or number == total:
            print(f"share snapshots: {number}/{total}")
        if delay:
            time.sleep(delay)

    shares = pd.DataFrame.from_dict(snapshots, orient="index").sort_index().reindex(weekly.index)
    flow = pd.Series(0.0, index=shares.index)
    prior_value = pd.Series(0.0, index=shares.index)
    for code in ETF_CODES:
        close = prices[code]["close"].reindex(shares.index)
        flow += shares[code].diff() * close
        prior_value += shares[code].shift(1) * close
    weekly["share_flow_bn"] = flow / 1e9
    weekly["share_flow_pct"] = flow / prior_value * 100
    return weekly


def add_labels(weekly: pd.DataFrame) -> pd.DataFrame:
    iso = weekly.index.isocalendar()
    weekly["year"] = iso.year.astype(int)
    weekly["week"] = iso.week.astype(int)

    events = pd.read_csv(EVENTS, parse_dates=["event_date"])
    events["period"] = events["event_date"].dt.to_period("W-FRI")
    weekly_period = weekly.index.to_period("W-FRI")
    for column in EVENT_COLUMNS:
        weekly[column] = 0
    for period, group in events.groupby("period"):
        selector = weekly_period == period
        if not selector.any():
            continue
        weekly.loc[selector, "official_message_count"] = len(group)
        weekly.loc[selector, "core_purchase_cluster_count"] = group.loc[
            group["core_event"] == 1, "cluster_id"
        ].nunique()
        weekly.loc[selector, "broad_rescue_cluster_count"] = group["cluster_id"].nunique()
        weekly.loc[selector, "official_announcement"] = int(
            group["core_event"].eq(1).any()
        )
        for category in EVENT_CATEGORIES:
            weekly.loc[selector, category] = int(group["category"].eq(category).any())

    gross_return = 1 + weekly["hs300_return_pct"] / 100
    weekly["next_week_return_pct"] = weekly["hs300_return_pct"].shift(-1)
    for label, horizon in FORWARD_HORIZONS.items():
        if label == "1w":
            continue
        forward_gross = pd.Series(1.0, index=weekly.index)
        for offset in range(1, horizon + 1):
            forward_gross *= gross_return.shift(-offset)
        weekly[f"next_{label}_return_pct"] = (forward_gross - 1) * 100
    weekly["rescue_proxy"] = 0
    weekly.loc[
        (weekly["share_flow_bn"] >= 20)
        & (weekly["turnover_ratio_20w"] >= 1.5)
        & (weekly["panic_drawdown_pct"] <= -2),
        "rescue_proxy",
    ] = 1
    return weekly


def pearson(x: np.ndarray, y: np.ndarray) -> float:
    if np.std(x) == 0 or np.std(y) == 0:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def correlation_table(frame: pd.DataFrame) -> pd.DataFrame:
    factors = [
        "share_flow_bn",
        "share_flow_pct",
        "turnover_ratio_20w",
        "panic_drawdown_pct",
        "close_rebound_pct",
        "largecap_relative_pct",
        "official_announcement",
        "broad_rescue_cluster_count",
        "liquidity_facility",
        "regulatory_stabilization",
        "rescue_proxy",
    ]
    rows = []
    for factor_number, factor in enumerate(factors):
        for target_number, target in enumerate(
            (
                "hs300_return_pct",
                "next_week_return_pct",
                "next_2w_return_pct",
                "next_1m_return_pct",
                "next_2m_return_pct",
                "next_3m_return_pct",
                "next_6m_return_pct",
            )
        ):
            pair = frame[[factor, target]].dropna()
            x = pair[factor].to_numpy()
            y = pair[target].to_numpy()
            pearson_value = pearson(x, y)
            rng = np.random.default_rng(100 * factor_number + target_number)
            permuted = np.array(
                [pearson(x, rng.permutation(y)) for _ in range(4000)]
            )
            permutation_p = (
                np.count_nonzero(np.abs(permuted) >= abs(pearson_value)) + 1
            ) / (len(permuted) + 1)
            bootstrap = []
            for _ in range(4000):
                positions = rng.integers(0, len(pair), len(pair))
                value = pearson(x[positions], y[positions])
                if np.isfinite(value):
                    bootstrap.append(value)
            ci_low, ci_high = np.quantile(bootstrap, [0.025, 0.975])
            rows.append(
                {
                    "factor": factor,
                    "target": target,
                    "n": len(pair),
                    "pearson": pearson_value,
                    "permutation_p": permutation_p,
                    "spearman": pair[factor].rank().corr(pair[target].rank()),
                    "ci_low": ci_low,
                    "ci_high": ci_high,
                }
            )
    return pd.DataFrame(rows)


def print_event_study(frame: pd.DataFrame) -> None:
    official = frame.loc[
        frame["official_announcement"] == 1,
        [
            "week_end",
            "core_purchase_cluster_count",
            "official_message_count",
            "hs300_return_pct",
            "next_week_return_pct",
            "next_2w_return_pct",
            "next_1m_return_pct",
            "next_2m_return_pct",
            "next_3m_return_pct",
            "next_6m_return_pct",
            "share_flow_bn",
            "turnover_ratio_20w",
            "rescue_proxy",
        ],
    ]
    print("\n===== FORWARD EVENT STUDY =====")
    for target in (
        "next_week_return_pct",
        "next_2w_return_pct",
        "next_1m_return_pct",
        "next_2m_return_pct",
        "next_3m_return_pct",
        "next_6m_return_pct",
    ):
        baseline = frame.loc[frame["rescue_proxy"] == 0, target].dropna()
        proxy = frame.loc[frame["rescue_proxy"] == 1, target].dropna()
        print(
            f"{target}: proxy=1 n={len(proxy)} mean={proxy.mean():.2f}% "
            f"median={proxy.median():.2f}% up={(proxy > 0).mean():.1%}; "
            f"proxy=0 mean={baseline.mean():.2f}% up={(baseline > 0).mean():.1%}"
        )
    print("\n===== OFFICIAL ANNOUNCEMENT WEEKS =====")
    print(official.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default=DEFAULT_START)
    parser.add_argument("--end", default=DEFAULT_END)
    parser.add_argument("--refresh", action="store_true")
    parser.add_argument("--delay", type=float, default=0.05)
    args = parser.parse_args()

    if args.refresh or not OUTPUT.exists():
        events = pd.read_csv(EVENTS, parse_dates=["event_date"])
        prices = fetch_prices(args.start, args.end, event_symbols(events))
        weekly = weekly_market_data(prices)
        weekly = add_share_flows(weekly, prices, args.delay)
        weekly = add_labels(weekly).reset_index()
        weekly.insert(0, "id", np.arange(1, len(weekly) + 1))
        weekly.to_csv(OUTPUT, index=False, encoding="utf-8-sig", float_format="%.6f")
        event_performance, event_asset_performance = build_event_performance(events, prices)
        event_performance.to_csv(
            EVENT_PERFORMANCE, index=False, encoding="utf-8-sig", float_format="%.6f"
        )
        event_asset_performance.to_csv(
            EVENT_ASSET_PERFORMANCE,
            index=False,
            encoding="utf-8-sig",
            float_format="%.6f",
        )
        print(f"wrote {len(weekly)} rows to {OUTPUT}")
    else:
        weekly = pd.read_csv(OUTPUT, parse_dates=["week_end"]).set_index("week_end")
        weekly = weekly.drop(columns=list(EVENT_COLUMNS), errors="ignore")
        weekly = add_labels(weekly).reset_index()
        weekly.to_csv(OUTPUT, index=False, encoding="utf-8-sig", float_format="%.6f")

    print("\n===== CORRELATIONS =====")
    print(correlation_table(weekly).to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print_event_study(weekly)


if __name__ == "__main__":
    main()
