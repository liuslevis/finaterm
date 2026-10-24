"""V8: avoid limit-up boards whose pre-touch order book is crowded near the limit.

Every non-ST A-share limit-up touch is examined. Features use only orders and
trades strictly before the first trade at the limit price, so a board buyer can
observe them when deciding whether to buy. Labels assume buying at the limit
price on the signal day and selling at the next session open.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "hfq"))

from strategy import (  # noqa: E402
    CACHE_DIR,
    OUTPUT_DIR,
    PRICE_SCALE,
    Thresholds,
    horizontal_metrics,
    is_a_share,
    limit_up_rate,
    passes_dormant_filter,
    rounded_limit_price,
)

PREOPEN_START = 91500000
CONTINUOUS_START = 93000000
PARK_WINDOW_END = 100000000
NEAR_LIMIT_BAND = 0.02
SMALL_ORDER_NOTIONAL = 200_000
ADV_DAYS = 20
FLAT_DAYS = 120
FLAT_MAX_RANGE_PCT = 50.0
FLAT_MAX_TURNOVER_PCT = 3.0
FLAG_QUANTILE = 2 / 3
COST_BPS_PER_SIDE = 15.0
TRAIN_THROUGH = "20260731"
TEST_THROUGH = "20260831"
PRIMARY_FEATURE = "v8_parked_near_limit_buy_adv_pct"
FEATURES = (
    PRIMARY_FEATURE,
    "v8_parked_preopen_share_pct",
    "v8_parked_near_limit_orders",
    "v8_parked_small_order_share_pct",
    "v8_preopen_near_limit_buy_adv_pct",
    "v8_preopen_near_limit_buy_share_pct",
    "v8_early_near_limit_aggr_buy_adv_pct",
    "v8_touch_minutes",
    "v8_touch_queue_adv_pct",
)
UNSELECTABLE_FEATURES = ("v8_touch_queue_adv_pct",)
UNIVERSES = ("all", "dormant_pool", "half_year_flat")
PANEL_PATH = OUTPUT_DIR / "ambush_v8_board_panel.csv"
RULES_PATH = HERE / "board_v8_rules.json"


def _clock_minutes(clock_ms: int) -> float:
    hours, rest = divmod(int(clock_ms), 10_000_000)
    minutes, rest = divmod(rest, 100_000)
    return hours * 60 + minutes + rest / 60_000


def trading_minutes_since_open(clock_ms: int) -> float:
    minutes = _clock_minutes(clock_ms)
    if minutes <= 9 * 60 + 30:
        return 0.0
    if minutes <= 11 * 60 + 30:
        return minutes - (9 * 60 + 30)
    if minutes <= 13 * 60:
        return 120.0
    return 120.0 + minutes - 13 * 60


def pre_touch_features(
    orders: pd.DataFrame,
    trades: pd.DataFrame,
    quotes: pd.DataFrame,
    market: str,
    limit_raw: int,
    adv_shares: float,
) -> dict | None:
    """Order state before the first trade at ``limit_raw``.

    ``orders``: t, exch_order_no, order_type, order_code, price, qty.
    ``trades``: t, trade_code, side, price, qty, sell_seq, buy_seq.
    ``quotes``: t, bid_px1, bid_qty1.
    SH new-order quantity is already the post-immediate-fill resting balance;
    SZ quantity is gross, so its aggressive continuous fills are deducted.
    """
    is_cancel_trade = trades["trade_code"].astype(str).str.strip() == "C"
    deals = trades[~is_cancel_trade & (trades["price"] > 0) & (trades["qty"] > 0)]
    touched = deals[deals["price"] >= limit_raw]
    if touched.empty or adv_shares <= 0:
        return None
    t_touch = int(touched["t"].min())
    near_raw = limit_raw * (1 - NEAR_LIMIT_BAND)

    if market == "SH":
        new = orders[orders["order_type"] == "A"]
        cancels = orders[(orders["order_type"] == "D") & (orders["order_code"] == "B")]
        cancel_rows = cancels[["exch_order_no", "t", "qty"]]
    else:
        new = orders
        cancels = trades[is_cancel_trade & (trades["buy_seq"] > 0)]
        cancel_rows = cancels.rename(columns={"buy_seq": "exch_order_no"})[
            ["exch_order_no", "t", "qty"]
        ]
    buys = new[
        (new["order_code"] == "B")
        & (new["price"] > 0)
        & (new["t"] >= PREOPEN_START)
        & (new["t"] < t_touch)
    ]
    preopen_end = min(CONTINUOUS_START, t_touch)
    preopen = buys[buys["t"] < preopen_end]
    preopen_near = preopen[preopen["price"] >= near_raw]
    window = buys[(buys["t"] < PARK_WINDOW_END) & (buys["price"] >= near_raw)]

    cancel_before = (
        cancel_rows[cancel_rows["t"] < t_touch]
        .groupby("exch_order_no")["qty"]
        .sum()
    )
    fills = deals[deals["t"] < t_touch][["t", "side", "qty", "buy_seq"]]
    fills = fills[fills["buy_seq"] > 0].merge(
        window[["exch_order_no", "t"]].rename(
            columns={"exch_order_no": "buy_seq", "t": "order_t"}
        ),
        on="buy_seq",
    )
    aggressive = fills["side"].astype(str).str.strip() == "B"
    if market == "SH":
        immediate = aggressive & (fills["t"] <= fills["order_t"])
    else:
        immediate = aggressive & (fills["t"] >= CONTINUOUS_START)
    immediate_qty = fills[immediate].groupby("buy_seq")["qty"].sum()
    passive_qty = fills[~immediate].groupby("buy_seq")["qty"].sum()

    parked = window.set_index("exch_order_no")
    resting = parked["qty"].astype(float)
    if market == "SZ":
        resting = (resting - immediate_qty.reindex(parked.index, fill_value=0)).clip(lower=0)
    remaining = (
        resting
        - passive_qty.reindex(parked.index, fill_value=0)
        - cancel_before.reindex(parked.index, fill_value=0)
    ).clip(lower=0)
    parked_qty = float(remaining.sum())
    preopen_parked = float(remaining[parked["t"] < preopen_end].sum())
    notional = parked["price"] / PRICE_SCALE * parked["qty"]
    small_parked = float(remaining[notional < SMALL_ORDER_NOTIONAL].sum())

    preopen_near_net = float(
        (
            preopen_near.set_index("exch_order_no")["qty"]
            - cancel_before.reindex(preopen_near["exch_order_no"], fill_value=0).values
        )
        .clip(lower=0)
        .sum()
    )
    preopen_qty = float(preopen["qty"].sum())
    early = deals[
        (deals["t"] >= CONTINUOUS_START)
        & (deals["t"] < t_touch)
        & (deals["price"] >= near_raw)
        & (deals["side"].astype(str).str.strip() == "B")
    ]
    after = quotes[quotes["t"] >= t_touch].sort_values("t")
    queue = 0.0
    queue_time = t_touch
    if not after.empty:
        queue_time = int(after.iloc[0]["t"])
        if after.iloc[0]["bid_px1"] >= limit_raw:
            queue = float(after.iloc[0]["bid_qty1"])
    # Fill labels use post-touch data and must never be used as features: a
    # buyer joining the queue fills once the queue ahead trades or the board breaks.
    post = deals[deals["t"] > queue_time]
    limit_volume_after = float(post.loc[post["price"] >= limit_raw, "qty"].sum())
    broke_after = bool((post["price"] < limit_raw).any())

    return {
        "t_touch": t_touch,
        "v8_open_at_limit": t_touch < CONTINUOUS_START,
        PRIMARY_FEATURE: parked_qty / adv_shares * 100,
        "v8_parked_preopen_share_pct": (
            preopen_parked / parked_qty * 100 if parked_qty else math.nan
        ),
        "v8_parked_near_limit_orders": int((remaining > 0).sum()),
        "v8_parked_small_order_share_pct": (
            small_parked / parked_qty * 100 if parked_qty else math.nan
        ),
        "v8_preopen_near_limit_buy_adv_pct": preopen_near_net / adv_shares * 100,
        "v8_preopen_near_limit_buy_share_pct": (
            float(preopen_near["qty"].sum()) / preopen_qty * 100
            if preopen_qty
            else math.nan
        ),
        "v8_early_near_limit_aggr_buy_adv_pct": float(early["qty"].sum())
        / adv_shares
        * 100,
        "v8_touch_minutes": trading_minutes_since_open(t_touch),
        "v8_touch_queue_adv_pct": queue / adv_shares * 100,
        "fill_queue_ahead": queue,
        "fill_limit_volume_after": limit_volume_after,
        "fill_broke_after": broke_after,
        "filled_queue": bool(broke_after or limit_volume_after >= queue),
    }


def board_labels(
    limit_price: float,
    today: dict,
    tomorrow: dict | None,
) -> dict:
    """Returns of a buyer filled at the limit price on the signal day.

    Next-day returns are chained through the exchange previous close, so
    ex-rights adjustments between the two sessions do not create fake gaps.
    """
    hold = today["close"] / limit_price
    labels = {
        "d0_close_vs_entry_pct": (hold - 1) * 100,
        "sealed_close": bool(today["close"] >= limit_price - 1e-6),
        "one_word_board": bool(
            today["low"] >= limit_price - 1e-6 and today["open"] >= limit_price - 1e-6
        ),
    }
    valid = (
        tomorrow is not None
        and tomorrow["prev_close"] > 0
        and tomorrow["open"] > 0
        and tomorrow["vol"] > 0
    )
    for name in ("open", "close"):
        labels[f"d1_{name}_ret_pct"] = (
            (hold * tomorrow[name] / tomorrow["prev_close"] - 1) * 100
            if valid
            else math.nan
        )
    return labels


def half_year_flat_metrics(frame: pd.DataFrame, signal_date: pd.Timestamp) -> dict:
    window = frame[frame["date"] < signal_date].tail(FLAT_DAYS)
    if len(window) < FLAT_DAYS:
        return {"half_year_flat": False}
    range_pct = (window["high"].max() / window["low"].min() - 1) * 100
    turnover = window["turnover"].mean() * 100
    return {
        "range_120d_pct": range_pct,
        "mean_turnover_120d_pct": turnover,
        "half_year_flat": bool(
            range_pct <= FLAT_MAX_RANGE_PCT and turnover <= FLAT_MAX_TURNOVER_PCT
        ),
    }


_KLINES: dict[str, pd.DataFrame | None] = {}


def _kline(code: str) -> pd.DataFrame | None:
    if code not in _KLINES:
        path = CACHE_DIR / "kline" / f"{code.replace('.', '_')}.csv"
        _KLINES[code] = (
            pd.read_csv(path, parse_dates=["date"]) if path.exists() else None
        )
    return _KLINES[code]


def _stock_names() -> dict[str, str]:
    path = CACHE_DIR / "stock_names_tx.csv"
    frame = pd.read_csv(path, dtype=str)
    return {
        f"{row[2:]}.{row[:2].upper()}": name
        for row, name in zip(frame["market_code"].str.lower(), frame["name"])
    }


def build_day(date: str, next_date: str | None) -> list[dict]:
    import pyarrow.parquet as pq
    from app.parquet_store import Store

    store = Store().open()
    names = _stock_names()
    catalog = store.read_catalog(dates=[date]).to_pandas()
    tomorrow = (
        store.read_catalog(dates=[next_date]).to_pandas().set_index("code")
        if next_date
        else pd.DataFrame()
    )
    signal_date = pd.Timestamp(date)
    limits = Thresholds()
    candidates = []
    for row in catalog.to_dict("records"):
        code = row["code"]
        name = names.get(code, "")
        if not is_a_share(code) or "ST" in name.upper() or row["prev_close"] <= 0:
            continue
        limit_price = rounded_limit_price(
            row["prev_close"] / PRICE_SCALE, limit_up_rate(code, name)
        )
        limit_raw = round(limit_price * PRICE_SCALE)
        if row["high"] < limit_raw:
            continue
        kline = _kline(code)
        if kline is None:
            continue
        history = kline[kline["date"] < signal_date]
        if len(history) < ADV_DAYS:
            continue
        candidates.append((row, name, limit_price, limit_raw, kline, history))

    by_shard: dict[int, list[str]] = {}
    for row, *_ in candidates:
        by_shard.setdefault(store.shard_of(row["code"])[0], []).append(row["code"])
    tables: dict[str, dict[str, pd.DataFrame]] = {"orders": {}, "trades": {}, "quotes": {}}
    columns = {
        "orders": ["code", "t", "exch_order_no", "order_type", "order_code", "price", "qty"],
        "trades": ["code", "t", "trade_code", "side", "price", "qty", "sell_seq", "buy_seq"],
        "quotes": ["code", "t", "bid_px1", "bid_qty1"],
    }
    for shard, codes in by_shard.items():
        for table, cols in columns.items():
            path = store.table_path(date, table, shard)
            frame = pq.read_table(
                path, columns=cols, filters=[("code", "in", codes)]
            ).to_pandas()
            for column in ("code", "order_type", "order_code", "trade_code", "side"):
                if column in frame:
                    frame[column] = frame[column].astype(str)
            for code, group in frame.groupby("code", sort=False):
                tables[table][code] = group

    rows = []
    for row, name, limit_price, limit_raw, kline, history in candidates:
        code = row["code"]
        adv = float(history.tail(ADV_DAYS)["volume"].mean())
        features = pre_touch_features(
            tables["orders"].get(code, pd.DataFrame(columns=columns["orders"])),
            tables["trades"].get(code, pd.DataFrame(columns=columns["trades"])),
            tables["quotes"].get(code, pd.DataFrame(columns=columns["quotes"])),
            code.split(".")[1],
            limit_raw,
            adv,
        )
        if features is None:
            continue
        scale = PRICE_SCALE
        today = {key: row[key] / scale for key in ("open", "high", "low", "close")}
        next_row = None
        if next_date and code in tomorrow.index:
            item = tomorrow.loc[code]
            next_row = {
                "open": item["open"] / scale,
                "close": item["close"] / scale,
                "prev_close": item["prev_close"] / scale,
                "vol": item["vol"],
            }
        dormant = horizontal_metrics(kline, signal_date, row["vol"])
        rows.append(
            {
                "signal_date": date,
                "code": code,
                "name": name,
                "limit_up_price": limit_price,
                "limit_up_rate_pct": limit_up_rate(code, name) * 100,
                "adv20_shares": adv,
                **features,
                **board_labels(limit_price, today, next_row),
                "dormant_pool": bool(dormant and passes_dormant_filter(dormant, limits)),
                "bottom_percentile": dormant["bottom_percentile"] if dormant else math.nan,
                **half_year_flat_metrics(kline, signal_date),
            }
        )
    return rows


def build_panel(workers: int) -> pd.DataFrame:
    from app.parquet_store import Store

    dates = Store().open().dates
    tasks = [(date, dates[index + 1] if index + 1 < len(dates) else None) for index, date in enumerate(dates)]
    rows = []
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for date, day_rows in zip(dates, executor.map(build_day, *zip(*tasks))):
            print(f"{date}: {len(day_rows)} limit-up touches", flush=True)
            rows.extend(day_rows)
    panel = pd.DataFrame(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    panel.to_csv(PANEL_PATH, index=False, encoding="utf-8-sig")
    return panel


def period_of(date: str) -> str:
    if date <= TRAIN_THROUGH:
        return "train"
    if date <= TEST_THROUGH:
        return "test"
    return "diagnostic"


def tradable_rows(panel: pd.DataFrame, fill: str = "queue") -> pd.DataFrame:
    """Rows a board buyer could actually hold overnight.

    ``queue`` keeps only orders filled by the queue model; unfilled orders stay
    in cash. ``optimistic`` assumes every non-one-word touch fills at the limit.
    """
    rows = panel[~panel["one_word_board"] & panel["d1_open_ret_pct"].notna()]
    if fill == "queue":
        rows = rows[rows["filled_queue"].astype(bool)]
    elif fill != "optimistic":
        raise ValueError(f"unknown fill mode: {fill}")
    rows = rows.copy()
    rows["signal_date"] = rows["signal_date"].astype(str)
    rows["period"] = rows["signal_date"].map(period_of)
    return rows


def net_return_pct(gross_pct: pd.Series, cost_bps: float) -> pd.Series:
    cost = cost_bps / 10_000
    return ((1 + gross_pct / 100) * (1 - cost) / (1 + cost) - 1) * 100


def _spearman(left: pd.Series, right: pd.Series) -> float:
    valid = left.notna() & right.notna()
    if valid.sum() < 3 or left[valid].nunique() < 2 or right[valid].nunique() < 2:
        return math.nan
    return float(left[valid].rank().corr(right[valid].rank()))


def feature_ic(rows: pd.DataFrame) -> pd.DataFrame:
    records = []
    for period, group in rows.groupby("period", sort=False):
        for feature in FEATURES:
            daily = pd.Series(
                [
                    _spearman(day[feature], day["d1_open_ret_pct"])
                    for _, day in group.groupby("signal_date")
                    if len(day) >= 5
                ],
                dtype=float,
            ).dropna()
            std = daily.std(ddof=1) if len(daily) > 2 else math.nan
            records.append(
                {
                    "period": period,
                    "feature": feature,
                    "samples": int(group[feature].notna().sum()),
                    "pooled_rank_ic": _spearman(group[feature], group["d1_open_ret_pct"]),
                    "daily_rank_ic_mean": float(daily.mean()) if len(daily) else math.nan,
                    "daily_rank_ic_t": (
                        float(daily.mean() / std * math.sqrt(len(daily)))
                        if std and std > 0
                        else math.nan
                    ),
                    "days": int(len(daily)),
                }
            )
    return pd.DataFrame(records)


def freeze_rules(candidates: pd.DataFrame) -> dict:
    """Freeze flags from training touches only, independent of the fill model.

    ``v8_touch_queue_adv_pct`` is read just after the touch and is mechanically
    tied to whether a queued order fills, so it is reported but not selectable.
    """
    train = candidates[candidates["period"] == "train"]
    train_ic = feature_ic(train).set_index("feature")["daily_rank_ic_t"]
    selectable = train_ic.drop(list(UNSELECTABLE_FEATURES)).dropna()
    avoid = str(selectable.idxmin())
    support = str(selectable.idxmax())
    return {
        "version": "v8",
        "flag_quantile": FLAG_QUANTILE,
        "train_through": TRAIN_THROUGH,
        "test_through": TEST_THROUGH,
        "train_samples": int(len(train)),
        "train_daily_rank_ic_t": {key: float(value) for key, value in train_ic.items()},
        "flags": {
            "primary": {
                "feature": PRIMARY_FEATURE,
                "direction": "high",
                "threshold": float(train[PRIMARY_FEATURE].quantile(FLAG_QUANTILE)),
            },
            "avoid_selected": {
                "feature": avoid,
                "direction": "high",
                "threshold": float(train[avoid].quantile(FLAG_QUANTILE)),
            },
            "weak_support": {
                "feature": support,
                "direction": "low",
                "threshold": float(train[support].quantile(1 - FLAG_QUANTILE)),
            },
        },
        "tercile_cuts": {
            feature: [
                float(train[feature].quantile(1 / 3)),
                float(train[feature].quantile(2 / 3)),
            ]
            for feature in FEATURES
        },
    }


def flag_mask(rows: pd.DataFrame, flag: dict) -> pd.Series:
    values = rows[flag["feature"]]
    if flag["direction"] == "high":
        return ((values >= flag["threshold"]) & (values > 0)).fillna(False)
    return (values <= flag["threshold"]).fillna(False)


def combined_flag(rows: pd.DataFrame, flags: dict) -> pd.Series:
    return flag_mask(rows, flags["avoid_selected"]) | flag_mask(rows, flags["weak_support"])


def universe_mask(rows: pd.DataFrame, universe: str) -> pd.Series:
    if universe == "all":
        return pd.Series(True, index=rows.index)
    return rows[universe].astype(bool)


def flag_evaluation(rows: pd.DataFrame, flags: dict, cost_bps: float) -> pd.DataFrame:
    records = []
    for period in ("train", "test", "diagnostic"):
        for universe in UNIVERSES:
            group = rows[(rows["period"] == period) & universe_mask(rows, universe)]
            if group.empty:
                continue
            net = net_return_pct(group["d1_open_ret_pct"], cost_bps)
            noodle = net < 0
            masks = {name: (flag["feature"], flag_mask(group, flag)) for name, flag in flags.items()}
            masks["combined"] = ("avoid_selected|weak_support", combined_flag(group, flags))
            for name, (feature, flagged) in masks.items():
                daily = (
                    pd.DataFrame({"date": group["signal_date"], "net": net, "flag": flagged})
                    .groupby(["date", "flag"])["net"]
                    .mean()
                    .unstack()
                )
                gap = (
                    (daily[False] - daily[True]).dropna()
                    if {False, True} <= set(daily.columns)
                    else pd.Series(dtype=float)
                )
                std = gap.std(ddof=1) if len(gap) > 2 else math.nan
                records.append(
                    {
                        "period": period,
                        "universe": universe,
                        "flag": name,
                        "feature": feature,
                        "samples": int(len(group)),
                        "flagged": int(flagged.sum()),
                        "noodle_rate_all_pct": float(noodle.mean() * 100),
                        "noodle_rate_flagged_pct": (
                            float(noodle[flagged].mean() * 100) if flagged.any() else math.nan
                        ),
                        "noodle_rate_kept_pct": (
                            float(noodle[~flagged].mean() * 100) if (~flagged).any() else math.nan
                        ),
                        "noodle_recall_pct": (
                            float((noodle & flagged).sum() / noodle.sum() * 100)
                            if noodle.any()
                            else math.nan
                        ),
                        "mean_net_all_pct": float(net.mean()),
                        "mean_net_flagged_pct": (
                            float(net[flagged].mean()) if flagged.any() else math.nan
                        ),
                        "mean_net_kept_pct": (
                            float(net[~flagged].mean()) if (~flagged).any() else math.nan
                        ),
                        "daily_kept_minus_flagged_pct": float(gap.mean()) if len(gap) else math.nan,
                        "daily_gap_t": (
                            float(gap.mean() / std * math.sqrt(len(gap)))
                            if std and std > 0
                            else math.nan
                        ),
                        "gap_days": int(len(gap)),
                    }
                )
    return pd.DataFrame(records)


def daily_portfolio(
    rows: pd.DataFrame,
    mask: pd.Series,
    calendar: list[str],
    cost_bps: float,
) -> pd.DataFrame:
    """Equal-weight every selected board each day; exit at the next open.

    Positions do not overlap: capital buys on day D and is back in cash at the
    D+1 open before that day's boards trigger. Days without picks earn zero.
    """
    selected = rows[mask]
    net = net_return_pct(selected["d1_open_ret_pct"], cost_bps)
    by_day = net.groupby(selected["signal_date"]).agg(["mean", "size"])
    daily = pd.DataFrame(index=pd.Index(calendar, name="signal_date"))
    daily["return_pct"] = by_day["mean"].reindex(daily.index).fillna(0.0)
    daily["positions"] = by_day["size"].reindex(daily.index).fillna(0).astype(int)
    daily["nav"] = (1 + daily["return_pct"] / 100).cumprod()
    return daily.reset_index()


def portfolio_metrics(daily: pd.DataFrame) -> dict:
    returns = daily["return_pct"] / 100
    nav = daily["nav"]
    std = returns.std(ddof=1)
    return {
        "net_return_pct": float((nav.iloc[-1] - 1) * 100),
        "sharpe": float(returns.mean() / std * math.sqrt(252)) if std > 0 else math.nan,
        "max_drawdown_pct": float(-((nav / nav.cummax()) - 1).min() * 100),
        "trades": int(daily["positions"].sum()),
        "invested_days": int((daily["positions"] > 0).sum()),
        "days": int(len(daily)),
    }


def portfolio_evaluation(
    rows: pd.DataFrame, flags: dict, calendars: dict[str, list[str]], cost_bps: float
) -> tuple[pd.DataFrame, dict[str, pd.DataFrame]]:
    records = []
    navs = {}
    for period, calendar in calendars.items():
        period_rows = rows[rows["period"] == period]
        for universe in UNIVERSES:
            base = universe_mask(period_rows, universe)
            variants = [("all", base)]
            for name, flag in flags.items():
                flagged = flag_mask(period_rows, flag)
                variants += [(f"exclude_{name}", base & ~flagged), (f"only_{name}", base & flagged)]
            variants.append(("exclude_combined", base & ~combined_flag(period_rows, flags)))
            for variant, mask in variants:
                daily = daily_portfolio(period_rows, mask, calendar, cost_bps)
                net = net_return_pct(period_rows.loc[mask, "d1_open_ret_pct"], cost_bps)
                records.append(
                    {
                        "period": period,
                        "universe": universe,
                        "variant": variant,
                        **portfolio_metrics(daily),
                        "mean_trade_net_pct": float(net.mean()) if len(net) else math.nan,
                        "win_rate_pct": float((net > 0).mean() * 100) if len(net) else math.nan,
                    }
                )
                navs[f"{period}_{universe}_{variant}"] = daily
    return pd.DataFrame(records), navs


def tercile_evaluation(rows: pd.DataFrame, cuts: dict, cost_bps: float) -> pd.DataFrame:
    net = net_return_pct(rows["d1_open_ret_pct"], cost_bps)
    frames = []
    for feature, (low, high) in cuts.items():
        bucket = pd.Series(
            np.select(
                [rows[feature] <= low, rows[feature] <= high, rows[feature] > high],
                ["low", "mid", "high"],
                default="missing",
            ),
            index=rows.index,
        )
        summary = (
            pd.DataFrame({"period": rows["period"], "bucket": bucket, "net": net})
            .groupby(["period", "bucket"])["net"]
            .agg(samples="size", mean_net_pct="mean", win_rate_pct=lambda x: (x > 0).mean() * 100)
            .reset_index()
        )
        summary.insert(0, "feature", feature)
        frames.append(summary)
    return pd.concat(frames, ignore_index=True)


def evaluate(panel: pd.DataFrame, rules: dict, fill: str, cost_bps: float) -> dict:
    candidates = panel.copy()
    candidates["signal_date"] = candidates["signal_date"].astype(str)
    candidates = candidates[candidates["d1_open_ret_pct"].notna()]
    calendars = {
        period: sorted(dates)
        for period, dates in candidates.groupby(
            candidates["signal_date"].map(period_of)
        )["signal_date"].unique().items()
    }
    rows = tradable_rows(panel, fill)
    outputs = {
        "feature_ic": feature_ic(rows),
        "flag_evaluation": flag_evaluation(rows, rules["flags"], cost_bps),
    }
    outputs["portfolio_evaluation"], navs = portfolio_evaluation(
        rows, rules["flags"], calendars, cost_bps
    )
    outputs["tercile_evaluation"] = tercile_evaluation(rows, rules["tercile_cuts"], cost_bps)
    for name, frame in outputs.items():
        frame.to_csv(OUTPUT_DIR / f"ambush_v8_{fill}_{name}.csv", index=False, encoding="utf-8-sig")
    for name, frame in navs.items():
        if name.startswith(("test_", "diagnostic_")) and "_all_" in f"_{name}_":
            frame.to_csv(
                OUTPUT_DIR / f"ambush_v8_{fill}_nav_{name}.csv", index=False, encoding="utf-8-sig"
            )
    return outputs


def fill_summary(panel: pd.DataFrame) -> pd.DataFrame:
    rows = panel[~panel["one_word_board"] & panel["d1_open_ret_pct"].notna()].copy()
    rows["period"] = rows["signal_date"].astype(str).map(period_of)
    rows["d0_broke"] = ~rows["sealed_close"].astype(bool)
    return (
        rows.groupby(["period", "filled_queue"])
        .agg(
            samples=("code", "size"),
            broke_by_close_pct=("d0_broke", lambda x: x.mean() * 100),
            mean_d1_open_gross_pct=("d1_open_ret_pct", "mean"),
        )
        .reset_index()
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="Rebuild the panel from Parquet LV2")
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--cost-bps-per-side", type=float, default=COST_BPS_PER_SIDE)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.build or not PANEL_PATH.exists():
        panel = build_panel(args.workers)
    else:
        panel = pd.read_csv(PANEL_PATH, dtype={"signal_date": str})
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 30)
    summary = fill_summary(panel)
    summary.to_csv(OUTPUT_DIR / "ambush_v8_fill_summary.csv", index=False, encoding="utf-8-sig")
    print("== fill_summary ==")
    print(summary.round(3).to_string(index=False))
    rules = freeze_rules(tradable_rows(panel, "optimistic"))
    RULES_PATH.write_text(json.dumps(rules, indent=2), encoding="utf-8")
    print(f"\nflags={json.dumps(rules['flags'], indent=1)}")
    for fill in ("queue", "optimistic"):
        outputs = evaluate(panel, rules, fill, args.cost_bps_per_side)
        print(f"\n######## fill={fill}")
        for name in ("feature_ic", "flag_evaluation", "portfolio_evaluation"):
            print(f"\n== {name} ==")
            print(outputs[name].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
