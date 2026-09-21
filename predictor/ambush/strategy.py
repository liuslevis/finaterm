"""Screen bottom-range A shares for a Level-2 accumulation proxy."""

from __future__ import annotations

import argparse
import bisect
import csv
import json
import math
import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pandas as pd
import py7zr

ROOT = Path(__file__).resolve().parents[2]
HFQ_DIR = ROOT / "hfq"
DATA_DIR = HFQ_DIR / "data-lv2"
CACHE_DIR = HFQ_DIR / "cache" / "ambush"
DEFAULT_SIGNAL_DATE = "20260901"
PRICE_SCALE = 10_000
FORWARD_HORIZONS = {"3d": 3, "1w": 5, "2w": 10, "3w": 15}


@dataclass(frozen=True)
class Thresholds:
    bottom_percentile: float = 0.40
    max_range_60d_pct: float = 40.0
    max_mean_abs_return_20d_pct: float = 2.5
    max_mean_turnover_20d_pct: float = 2.5
    min_persistent_minutes: int = 30
    min_order_qty: int = 10_000
    min_control_ratio_pct: float = 10.0


def is_a_share(code: str) -> bool:
    symbol, market = code.split(".")
    if market == "SZ":
        return symbol.startswith(("000", "001", "002", "003", "300", "301"))
    return market == "SH" and symbol.startswith(
        ("600", "601", "603", "605", "688", "689")
    )


def build_archive_index(archive: Path) -> dict[str, list[str]]:
    index: dict[str, list[str]] = {}
    with py7zr.SevenZipFile(archive, "r") as handle:
        for item in handle.list():
            if item.is_directory:
                continue
            parts = item.filename.replace("\\", "/").split("/")
            if len(parts) >= 3:
                index.setdefault(parts[1], []).append(item.filename)
    return index


def extract_members(archive: Path, members: list[str], destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    with py7zr.SevenZipFile(archive, "r") as handle:
        handle.extract(path=destination, targets=members)


def _load_akshare():
    source_root = ROOT / "akshare"
    sys.path.insert(0, str(source_root))
    os.chdir(source_root)
    import akshare as ak

    return ak


def _ak_symbol(code: str) -> str:
    symbol, market = code.split(".")
    return f"{market.lower()}{symbol}"


def fetch_kline(
    ak,
    code: str,
    start_date: str,
    end_date: str,
    retries: int = 3,
) -> pd.DataFrame:
    from akshare.utils.demjson import JSONDecodeError

    error: Exception | None = None
    for attempt in range(retries):
        try:
            frame = ak.stock_zh_a_daily(
                symbol=_ak_symbol(code),
                start_date=start_date,
                end_date=end_date,
                adjust="qfq",
            )
            if not frame.empty:
                frame["date"] = pd.to_datetime(frame["date"])
                return frame.sort_values("date").reset_index(drop=True)
        except (JSONDecodeError, ValueError, KeyError, TypeError, OSError) as exc:
            error = exc
        time.sleep(attempt + 1)
    raise RuntimeError(f"AkShare failed for {code}: {error}")


_WORKER_AK = None


def _init_akshare_worker(source_root: str) -> None:
    global _WORKER_AK
    sys.path.insert(0, source_root)
    os.chdir(source_root)
    import akshare as ak

    _WORKER_AK = ak


def _fetch_kline_worker(
    task: tuple[str, str, str],
) -> tuple[str, pd.DataFrame | None, str | None]:
    code, start_date, end_date = task
    try:
        return code, fetch_kline(_WORKER_AK, code, start_date, end_date), None
    except RuntimeError as exc:
        return code, None, str(exc)


def fetch_candidate_klines(
    event: pd.DataFrame,
    start_date: str,
    end_date: str,
    workers: int,
) -> dict[str, pd.DataFrame]:
    cache = CACHE_DIR / "kline"
    cache.mkdir(parents=True, exist_ok=True)
    result: dict[str, pd.DataFrame] = {}
    missing: list[str] = []
    for code in event["code"]:
        path = cache / f"{code.replace('.', '_')}.csv"
        if path.exists():
            frame = pd.read_csv(path, parse_dates=["date"])
            if not frame.empty and frame["date"].max() >= pd.Timestamp(end_date):
                result[code] = frame
                continue
        missing.append(code)

    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=_init_akshare_worker,
        initargs=(str(ROOT / "akshare"),),
    ) as executor:
        futures = {
            executor.submit(
                _fetch_kline_worker,
                (code, start_date, end_date),
            ): code
            for code in missing
        }
        completed = 0
        for future in as_completed(futures):
            code = futures[future]
            loaded_code, frame, error = future.result()
            completed += 1
            if error:
                print(error, file=sys.stderr)
                continue
            assert frame is not None
            frame.to_csv(
                cache / f"{loaded_code.replace('.', '_')}.csv",
                index=False,
                encoding="utf-8-sig",
            )
            result[loaded_code] = frame
            if completed % 100 == 0 or completed == len(missing):
                print(f"K-lines fetched: {completed}/{len(missing)}")
    return result


def fetch_stock_names() -> dict[str, str]:
    output = CACHE_DIR / "stock_names_tx.csv"
    if output.exists():
        frame = pd.read_csv(output, dtype=str)
    else:
        ak = _load_akshare()
        frame = ak.stock_zh_a_spot_tx()[["code", "name"]].copy()
        frame.columns = ["market_code", "name"]
        frame.to_csv(output, index=False, encoding="utf-8-sig")
    names = {}
    for row in frame.to_dict("records"):
        market_code = str(row["market_code"]).lower()
        if market_code.startswith(("sh", "sz")):
            names[f"{market_code[2:]}.{market_code[:2].upper()}"] = str(row["name"])
    return names


def horizontal_metrics(
    frame: pd.DataFrame,
    signal_date: pd.Timestamp,
    event_volume: float,
) -> dict[str, float] | None:
    history = frame[frame["date"] < signal_date].copy()
    if len(history) < 120:
        return None
    history["return_pct"] = history["close"].pct_change() * 100
    last_240 = history.tail(240)
    last_60 = history.tail(60)
    last_20 = history.tail(20)
    low_240, high_240 = last_240["low"].min(), last_240["high"].max()
    price_span = high_240 - low_240
    bottom_percentile = (
        (history.iloc[-1]["close"] - low_240) / price_span if price_span > 0 else 0
    )
    mean_turnover = last_20["turnover"].mean() * 100
    return {
        "bottom_percentile": bottom_percentile,
        "range_60d_pct": (last_60["high"].max() / last_60["low"].min() - 1) * 100,
        "mean_abs_return_20d_pct": last_20["return_pct"].abs().mean(),
        "mean_turnover_20d_pct": mean_turnover,
        "recent_volume_ratio": last_20["volume"].mean()
        / history.tail(120)["volume"].median(),
        "event_volume_ratio": event_volume / last_20["volume"].mean(),
        "outstanding_share": history.iloc[-1]["outstanding_share"],
    }


def passes_dormant_filter(metrics: dict[str, float], limits: Thresholds) -> bool:
    return (
        metrics["bottom_percentile"] <= limits.bottom_percentile
        and metrics["range_60d_pct"] <= limits.max_range_60d_pct
        and metrics["mean_abs_return_20d_pct"]
        <= limits.max_mean_abs_return_20d_pct
        and metrics["mean_turnover_20d_pct"] <= limits.max_mean_turnover_20d_pct
    )


def percentile_score(
    frame: pd.DataFrame,
    weighted_columns: dict[str, tuple[float, bool]],
) -> pd.Series:
    score = pd.Series(0.0, index=frame.index)
    total_weight = sum(weight for weight, _ in weighted_columns.values())
    for column, (weight, higher_is_better) in weighted_columns.items():
        rank = frame[column].rank(method="average", pct=True)
        if not higher_is_better:
            rank = 1 - rank
        score += rank.fillna(0) * weight
    return score / total_weight * 100


def limit_up_rate(code: str, name: str = "") -> float:
    if "ST" in name.upper():
        return 0.05
    symbol, market = code.split(".")
    if market == "SZ" and symbol.startswith(("300", "301")):
        return 0.20
    if market == "SH" and symbol.startswith(("688", "689")):
        return 0.20
    return 0.10


def rounded_limit_price(previous_close: float, rate: float) -> float:
    return float(
        (Decimal(str(previous_close)) * (Decimal(1) + Decimal(str(rate)))).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    )


def kline_selection_metrics(
    frame: pd.DataFrame,
    signal_date: pd.Timestamp,
    code: str,
    name: str = "",
) -> dict[str, float | bool] | None:
    signal = frame[frame["date"] == signal_date]
    if signal.empty:
        return None
    event_row = signal.iloc[-1]
    metrics = horizontal_metrics(frame, signal_date, event_row["volume"])
    if metrics is None:
        return None
    previous = frame[frame["date"] < signal_date].iloc[-1]
    rate = limit_up_rate(code, name)
    limit_price = rounded_limit_price(previous["close"], rate)
    return {
        **metrics,
        "event_open": event_row["open"],
        "event_high": event_row["high"],
        "event_low": event_row["low"],
        "event_close": event_row["close"],
        "event_volume": event_row["volume"],
        "event_amount": event_row["amount"],
        "event_gain_pct": (event_row["close"] / previous["close"] - 1) * 100,
        "limit_up_rate_pct": rate * 100,
        "limit_up_price": limit_price,
        "hit_limit_up": bool(event_row["high"] >= limit_price - 0.005),
    }


def _raw_int(value: str) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _clock_ms_to_seconds(value: int) -> float:
    milliseconds = value % 1000
    seconds = (value // 1000) % 100
    minutes = (value // 100_000) % 100
    hours = value // 10_000_000
    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000


def analyze_lv2(
    order_path: Path,
    trade_path: Path,
    quote_path: Path,
    market: str,
    outstanding_share: float,
    limits: Thresholds,
    cutoff: int = 132000000,
) -> dict[str, float]:
    orders: dict[int, dict] = {}
    with order_path.open(encoding="gbk", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for row in reader:
            if len(row) < 10:
                continue
            sequence = _raw_int(row[5])
            order_type, side = row[6], row[7]
            if market == "SH" and order_type == "D":
                if sequence in orders:
                    orders[sequence]["events"].append(
                        (_raw_int(row[3]), _raw_int(row[9]), "cancel")
                    )
                continue
            if side not in {"B", "S"} or (market == "SH" and order_type != "A"):
                continue
            orders[sequence] = {
                "time": _raw_int(row[3]),
                "side": side,
                "price": _raw_int(row[8]) / PRICE_SCALE,
                "qty": _raw_int(row[9]),
                "events": [],
            }

    trades: list[tuple[float, int, int, str]] = []
    with trade_path.open(encoding="gbk", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for row in reader:
            if len(row) < 12:
                continue
            event_time = _raw_int(row[3])
            trade_code, aggressor = row[5].strip(), row[7].strip()
            qty = _raw_int(row[9])
            sell_sequence, buy_sequence = _raw_int(row[10]), _raw_int(row[11])
            is_cancel = market == "SZ" and trade_code == "C"
            if is_cancel:
                sequence = buy_sequence or sell_sequence
                if sequence in orders:
                    orders[sequence]["events"].append((event_time, qty, "cancel"))
                continue
            for sequence in (sell_sequence, buy_sequence):
                if sequence in orders:
                    orders[sequence]["events"].append((event_time, qty, "fill"))
            if aggressor in {"B", "S"}:
                trades.append(
                    (
                        _clock_ms_to_seconds(event_time),
                        _raw_int(row[8]),
                        qty,
                        aggressor,
                    )
                )

    pre_cutoff_sell_qty = sum(
        order["qty"]
        for order in orders.values()
        if order["side"] == "S" and order["time"] <= cutoff
    )
    persistent_sell_qty = 0
    persistent_sell_orders = 0
    active_sell_qty_at_cutoff = 0
    canceled_sell_qty_before_cutoff = 0
    filled_sell_qty_before_cutoff = 0
    canceled_order_qty_before_cutoff = 0
    minimum_lifetime = limits.min_persistent_minutes * 60
    cutoff_seconds = _clock_ms_to_seconds(cutoff)
    for order in orders.values():
        if order["side"] != "S" or order["time"] > cutoff:
            continue
        start = _clock_ms_to_seconds(order["time"])
        filled = sum(
            qty
            for event_time, qty, kind in order["events"]
            if event_time <= cutoff and kind == "fill"
        )
        canceled = sum(
            qty
            for event_time, qty, kind in order["events"]
            if event_time <= cutoff and kind == "cancel"
        )
        remaining = max(order["qty"] - filled - canceled, 0)
        active_sell_qty_at_cutoff += remaining
        canceled_sell_qty_before_cutoff += canceled
        filled_sell_qty_before_cutoff += filled
        if (
            order["qty"] >= limits.min_order_qty
            and remaining > 0
            and cutoff_seconds - start >= minimum_lifetime
        ):
            persistent_sell_qty += remaining
            persistent_sell_orders += 1

    for order in orders.values():
        if order["time"] > cutoff:
            continue
        canceled_order_qty_before_cutoff += sum(
            qty
            for event_time, qty, kind in order["events"]
            if event_time <= cutoff and kind == "cancel"
        )

    trade_qty = sum(qty for _, _, qty, _ in trades)
    buy_qty = sum(qty for _, _, qty, side in trades if side == "B")
    sell_qty = sum(qty for _, _, qty, side in trades if side == "S")
    delta_qty = buy_qty - sell_qty

    trade_sizes = sorted(qty for _, _, qty, _ in trades)
    large_threshold = (
        trade_sizes[max(math.ceil(len(trade_sizes) * 0.95) - 1, 0)]
        if trade_sizes
        else 0
    )
    large_buy_qty = sum(
        qty for _, _, qty, side in trades if side == "B" and qty >= large_threshold
    )
    large_sell_qty = sum(
        qty for _, _, qty, side in trades if side == "S" and qty >= large_threshold
    )

    footprint: dict[int, list[int]] = {}
    for _, price, qty, side in trades:
        level = footprint.setdefault(price, [0, 0])
        level[0 if side == "B" else 1] += qty
    level_totals = sorted(sum(level) for level in footprint.values())
    median_level_volume = (
        level_totals[len(level_totals) // 2] if level_totals else 0
    )
    buy_imbalance_prices = sorted(
        price
        for price, (level_buy, level_sell) in footprint.items()
        if level_buy >= 3 * max(level_sell, 1)
        and level_buy + level_sell >= median_level_volume
    )
    stacked_buy_imbalance_levels = 0
    current_stack = 0
    previous_price = None
    for price in buy_imbalance_prices:
        current_stack = current_stack + 1 if price - (previous_price or price) == 100 else 1
        stacked_buy_imbalance_levels = max(
            stacked_buy_imbalance_levels, current_stack
        )
        previous_price = price

    price_values = [price for _, price, _, _ in trades if price > 0]
    low_band_sell_qty = 0
    if price_values:
        low_band = min(price_values) + (max(price_values) - min(price_values)) * 0.2
        low_band_sell_qty = sum(
            qty
            for _, price, qty, side in trades
            if side == "S" and price <= low_band
        )

    completion_by_side_price: dict[tuple[str, float], list[float]] = {}
    for order in orders.values():
        consumed = 0
        for event_time, qty, _ in sorted(order["events"]):
            consumed += qty
            if consumed >= order["qty"]:
                completion_by_side_price.setdefault(
                    (order["side"], order["price"]), []
                ).append(_clock_ms_to_seconds(event_time))
                break
    for completions in completion_by_side_price.values():
        completions.sort()
    refill_qty = {"B": 0, "S": 0}
    for order in orders.values():
        completions = completion_by_side_price.get(
            (order["side"], order["price"]), []
        )
        start = _clock_ms_to_seconds(order["time"])
        index_at = bisect.bisect_right(completions, start)
        if index_at and start - completions[index_at - 1] <= 3:
            refill_qty[order["side"]] += order["qty"]

    order_book_imbalances = []
    last_price = 0.0
    with quote_path.open(encoding="gbk", errors="replace", newline="") as handle:
        reader = csv.reader(handle)
        next(reader, None)
        for row in reader:
            if len(row) < 58:
                continue
            ask_qty = sum(_raw_int(row[27 + index]) for index in range(10))
            bid_qty = sum(_raw_int(row[47 + index]) for index in range(10))
            total = bid_qty + ask_qty
            if total:
                order_book_imbalances.append((bid_qty - ask_qty) / total * 100)
            if _raw_int(row[4]):
                last_price = _raw_int(row[4]) / PRICE_SCALE

    buy_trades = sorted((second, qty) for second, _, qty, side in trades if side == "B")
    buy_trades.sort()
    left = 0
    rolling_qty = 0
    max_buy_3m = 0
    for right, (second, qty) in enumerate(buy_trades):
        rolling_qty += qty
        while second - buy_trades[left][0] > 180:
            rolling_qty -= buy_trades[left][1]
            left += 1
        max_buy_3m = max(max_buy_3m, rolling_qty)

    first_trade_price = price_values[0] / PRICE_SCALE if price_values else 0
    price_change_pct = (
        (last_price / first_trade_price - 1) * 100 if first_trade_price else 0
    )
    return {
        "pre_cutoff_sell_qty": pre_cutoff_sell_qty,
        "active_sell_qty_at_cutoff": active_sell_qty_at_cutoff,
        "persistent_sell_orders": persistent_sell_orders,
        "persistent_sell_qty": persistent_sell_qty,
        "persistent_sell_share_pct": (
            persistent_sell_qty / pre_cutoff_sell_qty * 100
            if pre_cutoff_sell_qty
            else 0
        ),
        "sell_cancel_ratio_pct": (
            canceled_sell_qty_before_cutoff / pre_cutoff_sell_qty * 100
            if pre_cutoff_sell_qty
            else 0
        ),
        "sell_fill_ratio_pct": (
            filled_sell_qty_before_cutoff / pre_cutoff_sell_qty * 100
            if pre_cutoff_sell_qty
            else 0
        ),
        "cancel_to_trade_qty_ratio_pct": (
            canceled_order_qty_before_cutoff / trade_qty * 100 if trade_qty else 0
        ),
        "gross_sell_float_ratio_pct": pre_cutoff_sell_qty
        / outstanding_share
        * 100,
        "active_sell_float_ratio_pct": active_sell_qty_at_cutoff
        / outstanding_share
        * 100,
        "persistent_sell_float_ratio_pct": persistent_sell_qty
        / outstanding_share
        * 100,
        "max_aggressive_buy_3m": max_buy_3m,
        "delta_qty": delta_qty,
        "delta_ratio_pct": delta_qty / trade_qty * 100 if trade_qty else 0,
        "price_change_from_first_trade_pct": price_change_pct,
        "bullish_cvd_divergence": bool(price_change_pct <= 0 and delta_qty > 0),
        "large_order_threshold_qty": large_threshold,
        "large_order_net_flow_pct": (
            (large_buy_qty - large_sell_qty) / trade_qty * 100 if trade_qty else 0
        ),
        "buy_imbalance_price_levels": len(buy_imbalance_prices),
        "stacked_buy_imbalance_levels": stacked_buy_imbalance_levels,
        "bullish_absorption_ratio_pct": (
            low_band_sell_qty / sell_qty * 100 if sell_qty else 0
        ),
        "buy_refill_float_ratio_pct": refill_qty["B"] / outstanding_share * 100,
        "sell_refill_float_ratio_pct": refill_qty["S"] / outstanding_share * 100,
        "median_order_book_imbalance_pct": (
            float(pd.Series(order_book_imbalances).median())
            if order_book_imbalances
            else 0
        ),
    }


def add_forward_returns(
    row: dict,
    frame: pd.DataFrame,
    signal_date: pd.Timestamp,
) -> None:
    future = frame[frame["date"] >= signal_date].sort_values("date").reset_index(drop=True)
    if future.empty or future.iloc[0]["date"] != signal_date:
        for label in FORWARD_HORIZONS:
            row[f"forward_{label}_pct"] = math.nan
        return
    base = future.iloc[0]["close"]
    for label, sessions in FORWARD_HORIZONS.items():
        row[f"forward_{label}_pct"] = (
            (future.iloc[sessions]["close"] / base - 1) * 100
            if len(future) > sessions
            else math.nan
        )


def build_evaluation(results: pd.DataFrame, bucket_size: int = 20) -> pd.DataFrame:
    evaluated = results.copy()
    evaluated["rank_bucket"] = (
        ((evaluated["rank"] - 1) // bucket_size) * bucket_size + 1
    ).map(lambda start: f"{start}-{start + bucket_size - 1}")
    rows = []
    for bucket, group in evaluated.groupby("rank_bucket", sort=False):
        row: dict[str, float | int | str] = {
            "rank_bucket": bucket,
            "stock_count": len(group),
        }
        for label in FORWARD_HORIZONS:
            column = f"forward_{label}_pct"
            available = group[column].dropna()
            row[f"{label}_available"] = len(available)
            row[f"{label}_mean_pct"] = available.mean()
            row[f"{label}_median_pct"] = available.median()
            row[f"{label}_positive_rate_pct"] = (
                (available > 0).mean() * 100 if not available.empty else math.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", default=DEFAULT_SIGNAL_DATE)
    parser.add_argument("--workers", type=int, default=24)
    parser.add_argument(
        "--top",
        type=int,
        default=0,
        help="Limit final LV2 rows; 0 keeps every dormant non-ST limit-up hit",
    )
    parser.add_argument("--refresh", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    limits = Thresholds()
    date = args.date
    archive = DATA_DIR / f"{date}.7z"
    if not archive.exists():
        raise FileNotFoundError(archive)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if args.refresh:
        for path in (
            CACHE_DIR / f"{date}_archive_index.json",
        ):
            path.unlink(missing_ok=True)

    index_path = CACHE_DIR / f"{date}_archive_index.json"
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))
    else:
        index = build_archive_index(archive)
        index_path.write_text(json.dumps(index), encoding="utf-8")

    universe = pd.DataFrame(
        {"code": [code for code in index if is_a_share(code)]}
    )
    print(f"A-share universe in archive: {len(universe)}")
    signal_date = pd.Timestamp(date)
    end_date = max(
        (path.stem for path in DATA_DIR.glob("*.7z") if path.stem.isdigit()),
        default=date,
    )
    klines = fetch_candidate_klines(
        universe,
        start_date=(signal_date - pd.Timedelta(days=550)).strftime("%Y%m%d"),
        end_date=end_date,
        workers=args.workers,
    )
    stock_names = fetch_stock_names()

    candidate_rows = []
    for code in universe["code"]:
        frame = klines.get(code)
        if frame is None:
            continue
        name = stock_names.get(code, "")
        metrics = kline_selection_metrics(frame, signal_date, code, name)
        if metrics:
            candidate_rows.append(
                {
                    "code": code,
                    "name": name,
                    **metrics,
                    "is_st": "ST" in name.upper(),
                    "passes_dormant_filter": passes_dormant_filter(metrics, limits),
                }
            )
    candidates = pd.DataFrame(candidate_rows)
    if candidates.empty:
        raise RuntimeError("No event candidate had sufficient pre-signal K-line history")
    candidates["dormancy_score"] = percentile_score(
        candidates,
        {
            "bottom_percentile": (20, False),
            "range_60d_pct": (30, False),
            "mean_abs_return_20d_pct": (20, False),
            "mean_turnover_20d_pct": (20, False),
            "recent_volume_ratio": (10, False),
        },
    )
    pool = (
        candidates[
            candidates["passes_dormant_filter"] & ~candidates["is_st"]
        ]
        .sort_values(
            ["dormancy_score", "range_60d_pct"], ascending=[False, True]
        )
        .reset_index(drop=True)
    )
    pool.insert(0, "pool_rank", pool.index + 1)
    pool.to_csv(
        Path(__file__).with_name(f"ambush_kline_pool_{date}.csv"),
        index=False,
        encoding="utf-8-sig",
    )
    limit_hits = pool[pool["hit_limit_up"]].copy()
    limit_hits["trigger_score"] = percentile_score(
        limit_hits,
        {
            "event_volume_ratio": (60, True),
            "event_gain_pct": (25, True),
            "mean_turnover_20d_pct": (15, False),
        },
    )
    limit_hits.to_csv(
        Path(__file__).with_name(f"ambush_limit_hits_{date}.csv"),
        index=False,
        encoding="utf-8-sig",
    )
    print(
        f"All non-ST dormant stocks: {len(pool)}; "
        f"{signal_date.date()} limit-up touches: {len(limit_hits)}"
    )
    if limit_hits.empty:
        raise RuntimeError("No stock in the dormant pool touched its limit-up price")

    stage = CACHE_DIR / f"{date}_lv2_candidates"
    if stage.exists():
        shutil.rmtree(stage)
    all_members = [
        member
        for row in limit_hits.to_dict("records")
        for member in index[row["code"]]
        if member.endswith(("行情.csv", "逐笔委托.csv", "逐笔成交.csv"))
    ]
    extract_members(archive, all_members, stage)
    analyzed = []
    try:
        for row in limit_hits.to_dict("records"):
            code = row["code"]
            stock_dir = stage / date / code
            lv2 = analyze_lv2(
                stock_dir / "逐笔委托.csv",
                stock_dir / "逐笔成交.csv",
                stock_dir / "行情.csv",
                code.split(".")[1],
                row["outstanding_share"],
                limits,
            )
            result = {**row, **lv2}
            result["aggressive_buy_3m_event_volume_pct"] = (
                result["max_aggressive_buy_3m"] / result["event_volume"] * 100
            )
            result["meets_10pct_gross_sell_proxy"] = (
                result["gross_sell_float_ratio_pct"] + 1e-9
                >= limits.min_control_ratio_pct
            )
            add_forward_returns(result, klines[code], signal_date)
            analyzed.append(result)
    finally:
        shutil.rmtree(stage, ignore_errors=True)

    diagnostics = pd.DataFrame(analyzed)
    if diagnostics.empty:
        raise RuntimeError("No stock had usable Level-2 data")
    diagnostics["lv2_score"] = percentile_score(
        diagnostics,
        {
            "gross_sell_float_ratio_pct": (10, True),
            "active_sell_float_ratio_pct": (10, True),
            "persistent_sell_float_ratio_pct": (10, True),
            "persistent_sell_share_pct": (5, True),
            "sell_cancel_ratio_pct": (5, False),
            "aggressive_buy_3m_event_volume_pct": (10, True),
            "delta_ratio_pct": (10, True),
            "large_order_net_flow_pct": (15, True),
            "stacked_buy_imbalance_levels": (5, True),
            "bullish_absorption_ratio_pct": (10, True),
            "buy_refill_float_ratio_pct": (5, True),
            "median_order_book_imbalance_pct": (5, True),
        },
    )
    diagnostics["score"] = (
        diagnostics["dormancy_score"] * 0.45
        + diagnostics["trigger_score"] * 0.20
        + diagnostics["lv2_score"] * 0.35
    )
    high_confidence = (
        diagnostics["passes_dormant_filter"]
        & diagnostics["meets_10pct_gross_sell_proxy"]
        & (diagnostics["persistent_sell_share_pct"] >= 5)
    )
    medium_confidence = diagnostics["passes_dormant_filter"] & (
        (diagnostics["gross_sell_float_ratio_pct"] >= 5)
        | (diagnostics["persistent_sell_share_pct"] >= 5)
    )
    diagnostics["signal_quality"] = "watch"
    diagnostics.loc[medium_confidence, "signal_quality"] = "medium"
    diagnostics.loc[high_confidence, "signal_quality"] = "high"
    diagnostics = diagnostics.sort_values(
        ["score", "dormancy_score", "lv2_score"], ascending=False
    ).reset_index(drop=True)
    diagnostics.insert(0, "rank", diagnostics.index + 1)
    diagnostics.to_csv(
        Path(__file__).with_name(f"ambush_candidates_{date}.csv"),
        index=False,
        encoding="utf-8-sig",
    )
    results = diagnostics if args.top <= 0 else diagnostics.head(args.top)
    output = Path(__file__).with_name(f"ambush_results_{date}.csv")
    results.to_csv(output, index=False, encoding="utf-8-sig")
    evaluation = build_evaluation(results)
    evaluation.to_csv(
        Path(__file__).with_name(f"ambush_evaluation_{date}.csv"),
        index=False,
        encoding="utf-8-sig",
    )
    strict_count = int(results["meets_10pct_gross_sell_proxy"].sum())
    high_count = int((results["signal_quality"] == "high").sum())
    print(f"Top {len(results)}: high confidence {high_count}, gross 10% proxy {strict_count}")
    columns = [
        "code",
        "rank",
        "score",
        "pool_rank",
        "dormancy_score",
        "trigger_score",
        "lv2_score",
        "signal_quality",
        "event_gain_pct",
        "event_volume_ratio",
        "bottom_percentile",
        "mean_turnover_20d_pct",
        "pre_cutoff_sell_qty",
        "active_sell_qty_at_cutoff",
        "persistent_sell_qty",
        "persistent_sell_share_pct",
        "gross_sell_float_ratio_pct",
        "active_sell_float_ratio_pct",
        "persistent_sell_float_ratio_pct",
        "sell_cancel_ratio_pct",
        "cancel_to_trade_qty_ratio_pct",
        "meets_10pct_gross_sell_proxy",
        "max_aggressive_buy_3m",
        "delta_ratio_pct",
        "bullish_cvd_divergence",
        "large_order_net_flow_pct",
        "stacked_buy_imbalance_levels",
        "bullish_absorption_ratio_pct",
        "buy_refill_float_ratio_pct",
        "median_order_book_imbalance_pct",
        "forward_3d_pct",
        "forward_1w_pct",
        "forward_2w_pct",
        "forward_3w_pct",
    ]
    print(results[columns].to_string(index=False, float_format=lambda value: f"{value:.2f}"))
    print(f"Saved {output}")


if __name__ == "__main__":
    main()
