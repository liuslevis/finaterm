"""美股供需月度面板：净股权供给 vs 增量资金。

用法（在 dashboard/ 目录下）：
    uv run python tab/us-supply-demand/build_panel.py            # 复用 raw/ 缓存，只重算
    uv run python tab/us-supply-demand/build_panel.py --refresh  # 重新下载自动数据源（约 2 分钟）

自动源：Nasdaq IPO 日历、openinsider（Form 4）、FINRA 融资余额、Yahoo（^GSPC/^W5000/新股首日）。
手工源：manual.json（ETF/共同基金资金流、增发/可转债、回购/分红；AI 用 web_search 刷新）。
输出：raw/*.json、panel.csv、panel.json（供 /api/us-supply-demand）。设计说明见同目录 SKILL.md。
"""
import argparse
import json
import re
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
MANUAL = HERE / "manual.json"
HISTORY_START = "2025-10"  # z-score 回看起点；FINRA 网页只列最近 12 个月
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0 Safari/537.36", "Accept-Language": "en-US,en;q=0.9"}
SPAC_NAME = re.compile(r"\b(Acquisition|Merger|Blank Check|SPAC)\b", re.I)


def is_spac(row: dict, price: float | None) -> bool:
    # SPAC 以 $10 单位发行；只按名称匹配会误伤 Space/Aerospace（如 SpaceX、Firefly Aerospace）
    ticker = row.get("proposedTickerSymbol") or ""
    return price == 10.0 and (bool(SPAC_NAME.search(row.get("companyName") or "")) or ticker.endswith("U"))
FINRA_URL = "https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics"
DEMAND_KEYS = ("etf_us_equity", "mf_domestic_equity", "margin")


def http(url: str, timeout: int = 60) -> str:
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
                return r.read().decode("utf-8", "ignore")
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 + attempt * 3)
    return ""


def months_between(start: str, end: str) -> list[str]:
    return [str(m) for m in pd.period_range(start, end, freq="M")]


# ---------------- 下载 ----------------
def fetch_nasdaq(month: str) -> dict:
    data = json.loads(http(f"https://api.nasdaq.com/api/ipo/calendar?date={month}"))["data"] or {}
    deals = []
    for row in (data.get("priced") or {}).get("rows") or []:
        value = re.sub(r"[^\d.]", "", row.get("dollarValueOfSharesOffered") or "")
        prices = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", row.get("proposedSharePrice") or "")]
        price = sum(prices) / len(prices) if prices else None  # 区间价 "4.00-6.00" 取中值
        deals.append({
            "ticker": row.get("proposedTickerSymbol") or "", "name": row.get("companyName") or "",
            "date": datetime.strptime(row["pricedDate"], "%m/%d/%Y").date().isoformat(),
            "price": price, "value": float(value) / 1e9 if value else 0.0, "spac": is_spac(row, price),
        })
    count = lambda key: len((data.get(key) or {}).get("rows") or [])
    return {"month": month, "deals": deals, "filed": count("filed"), "withdrawn": count("withdrawn")}


def fetch_insider_month(month: str, kind: str) -> list[dict]:
    """kind: xs=卖出(S - Sale / Sale+OE)，xp=买入(P - Purchase)。按交易日期筛选，每页 1000 行翻页。"""
    p = pd.Period(month, "M")
    rng = urllib.parse.quote(f"{p.start_time:%m/%d/%Y} - {p.end_time:%m/%d/%Y}")
    rows = []
    for page in range(1, 60):
        html = http(f"http://openinsider.com/screener?fd=0&td=-1&tdr={rng}&{kind}=1&cnt=1000&page={page}", 90)
        table = html[html.find('class="tinytable"'):]
        batch = []
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", table, re.S)[1:]:
            c = [re.sub(r"<[^>]+>", "", x).strip() for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
            if len(c) >= 13:
                value = re.sub(r"[^\d.]", "", c[12])
                batch.append({"date": c[2], "title": c[6], "type": c[7], "value": float(value) / 1e9 if value else 0.0})
        rows += batch
        if len(batch) < 1000:
            return rows
    raise RuntimeError(f"openinsider {kind} {month} 超过 60 页")


def fetch_finra() -> dict:
    """FINRA 网页表格（百万美元）；本机常被 403，失败时用 manual.json 的 finra 字段兜底。"""
    html = http(FINRA_URL)
    out = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        c = [re.sub(r"<[^>]+>|&nbsp;", "", x).strip() for x in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(c) >= 4 and re.fullmatch(r"[A-Z][a-z]{2}-\d{2}", c[0]):
            out[datetime.strptime(c[0], "%b-%y").strftime("%Y-%m")] = [float(x.replace(",", "")) for x in c[1:4]]
    if not out:
        raise RuntimeError("FINRA 表格解析为空")
    return out


def fetch_yahoo(symbol: str, start: str, interval: str = "1mo", end: str | None = None) -> dict:
    t0 = int(pd.Timestamp(start).timestamp())
    t1 = int(pd.Timestamp(end).timestamp()) if end else int(time.time())
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol)}"
           f"?period1={t0}&period2={t1}&interval={interval}")
    result = json.loads(http(url))["chart"]["result"][0]
    closes = result["indicators"]["quote"][0]["close"]
    return {datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"): c
            for t, c in zip(result.get("timestamp") or [], closes) if c is not None}


def first_day_close(deal: dict) -> float | None:
    """首个交易日收盘价。Yahoo 价格按后续拆股（小盘新股常见反向拆股）复权，需用拆股事件还原。"""
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(deal['ticker'])}"
           f"?period1={int(pd.Timestamp(deal['date']).timestamp())}&period2={int(time.time())}"
           f"&interval=1d&events=split")
    try:
        result = json.loads(http(url))["chart"]["result"][0]
        first = next((t, c) for t, c in zip(result["timestamp"], result["indicators"]["quote"][0]["close"])
                     if c is not None)
    except Exception:
        return None  # 代码变更 / 退市 / 尚未上市
    factor = 1.0
    for split in (result.get("events") or {}).get("splits", {}).values():
        if split["date"] > first[0]:
            factor *= split["numerator"] / split["denominator"]
    return first[1] * factor


def download(start: str, end: str) -> None:
    RAW.mkdir(exist_ok=True)
    months = months_between((pd.Period(start, "M") - 6).strftime("%Y-%m"), end)  # 多取 6 个月算锁定到期参考
    with ThreadPoolExecutor(6) as pool:
        ipo = list(pool.map(fetch_nasdaq, months))
    deals = [d for m in ipo for d in m["deals"] if not d["spac"] and d["ticker"] and d["price"]]
    with ThreadPoolExecutor(6) as pool:
        for deal, close in zip(deals, pool.map(first_day_close, deals)):
            deal["first_close"] = close
    (RAW / "nasdaq_ipo.json").write_text(json.dumps(ipo, indent=0), encoding="utf-8")
    print("download nasdaq ipo", len(months), "months", flush=True)

    jobs = [(m, k) for m in months_between(start, end) for k in ("xs", "xp")]
    with ThreadPoolExecutor(4) as pool:
        insider = {f"{m}:{k}": rows for (m, k), rows in zip(jobs, pool.map(lambda a: fetch_insider_month(*a), jobs))}
    (RAW / "insider.json").write_text(json.dumps(insider), encoding="utf-8")
    print("download openinsider", sum(map(len, insider.values())), "rows", flush=True)

    yahoo_start = (pd.Period(start, "M") - 1).start_time.isoformat()
    yahoo = {s: fetch_yahoo(s, yahoo_start) for s in ("^GSPC", "^W5000")}
    (RAW / "yahoo.json").write_text(json.dumps(yahoo, indent=0), encoding="utf-8")
    try:
        (RAW / "finra.json").write_text(json.dumps(fetch_finra(), indent=0), encoding="utf-8")
        print("download finra ok", flush=True)
    except Exception as error:
        print(f"download finra 失败（{error}），使用 manual.json 的 finra 兜底", flush=True)


# ---------------- 计算 ----------------
def manual_series(manual: dict, key: str, months: pd.PeriodIndex) -> tuple[pd.Series, list]:
    """月度值直接用；季度值 ÷3 均摊；最近季度未公布时沿用上一季度（记为估算）。"""
    if key in manual.get("monthly", {}):
        s = pd.Series({pd.Period(k, "M"): v for k, v in manual["monthly"][key].items() if v is not None}, dtype=float)
        return s.reindex(months), []
    quarters = {pd.Period(k, "Q"): v for k, v in manual["quarterly"][key].items() if v is not None}
    out, estimated = pd.Series(np.nan, index=months), []
    for m in months:
        q = m.asfreq("Q")
        if q in quarters:
            out[m] = quarters[q] / 3
        elif quarters and q > max(quarters):
            out[m] = quarters[max(quarters)] / 3
            estimated.append(str(m))
    return out, estimated


def monthly_last(series: dict) -> pd.Series:
    s = pd.Series(series, dtype=float)
    s.index = pd.to_datetime(s.index).to_period("M")
    return s.groupby(level=0).last()


def compute(start: str, end: str) -> tuple[pd.DataFrame, dict]:
    months = pd.period_range(start, end, freq="M")
    manual = json.loads(MANUAL.read_text(encoding="utf-8"))
    p = pd.DataFrame(index=months)
    estimated = {}

    # ---- 供给 ----
    ipo = json.loads((RAW / "nasdaq_ipo.json").read_text(encoding="utf-8"))
    deals = pd.DataFrame([d for m in ipo for d in m["deals"]])
    deals["m"] = pd.to_datetime(deals.date).dt.to_period("M")
    real = deals[~deals.spac]
    proceeds = real.groupby("m").value.sum()
    p["ipo"] = proceeds.reindex(months).fillna(0)
    p["ipo_count"] = real.groupby("m").size().reindex(months).fillna(0)
    p["spac_count"] = deals[deals.spac].groupby("m").size().reindex(months).fillna(0)
    lockup = proceeds.copy()
    lockup.index = lockup.index + 6  # 常规 180 天锁定期
    p["lockup_ref"] = lockup.reindex(months).fillna(0)
    pipeline = pd.DataFrame(ipo).set_index("month")
    pipeline.index = pd.PeriodIndex(pipeline.index, freq="M")
    p["filed"] = pipeline.filed.reindex(months)
    p["withdrawn"] = pipeline.withdrawn.reindex(months)

    for key in ("follow_on", "convertible", "buyback", "dividend"):
        p[key], est = manual_series(manual, key, months)
        if est:
            estimated[key] = est

    insider = json.loads((RAW / "insider.json").read_text(encoding="utf-8"))
    for col, kind in (("insider_sell", "xs"), ("insider_buy", "xp")):
        values, tenpct = {}, {}
        for m in months:
            rows = insider.get(f"{m}:{kind}")
            if rows is None:
                continue
            # 纯 10% 大股东（多为 PE/创投）卖出通常走大宗/增发，已计入 follow_on，剔除以免重复
            pure = sum(r["value"] for r in rows if r["title"].strip() in ("10%", "10% Owner"))
            values[m] = sum(r["value"] for r in rows) - pure
            tenpct[m] = pure
        p[col] = pd.Series(values, dtype=float).reindex(months)
        if kind == "xs":
            p["insider_sell_10pct"] = pd.Series(tenpct, dtype=float).reindex(months)

    p["net_supply"] = (p[["ipo", "follow_on", "convertible", "insider_sell"]].sum(axis=1, min_count=4)
                       - p[["buyback", "dividend", "insider_buy"]].sum(axis=1, min_count=3))
    p["net_supply_ex_div"] = p.net_supply + p.dividend

    # ---- 需求 ----
    for key in ("etf_us_equity", "mf_domestic_equity"):
        p[key], _ = manual_series(manual, key, months)
    finra_path = RAW / "finra.json"
    finra = {**manual.get("finra", {}).get("values", {}),
             **(json.loads(finra_path.read_text(encoding="utf-8")) if finra_path.exists() else {})}  # 自动抓取优先
    debit = pd.Series({pd.Period(k, "M"): v[0] for k, v in finra.items()}, dtype=float).sort_index()
    credit = pd.Series({pd.Period(k, "M"): v[1] + v[2] for k, v in finra.items()}, dtype=float).sort_index()
    p["margin"] = (debit.diff() / 1e3).reindex(months)  # 百万 → 十亿
    p["free_credit"] = (credit.diff() / 1e3).reindex(months)

    # 首月差分天然缺失，只看第 2 个月起是否齐全；不齐全的需求分项只展示、不进公式
    demand_parts = [k for k in DEMAND_KEYS if p[k].iloc[1:].notna().all()]
    p["demand"] = p[demand_parts].sum(axis=1, min_count=len(demand_parts))
    p["gap"] = p.demand - p.net_supply
    p["gap_ex_div"] = p.demand - p.net_supply_ex_div

    yahoo = json.loads((RAW / "yahoo.json").read_text(encoding="utf-8"))
    p["mcap"] = monthly_last(yahoo["^W5000"]).reindex(months)  # 指数点 ≈ 十亿美元总市值
    for col in ("gap", "gap_ex_div"):
        x = p[col] / p.mcap * 1e4
        p[f"{col}_bp"] = x
        for w in (3, 6):
            p[f"{col}_z{w}"] = (x - x.rolling(w).mean()) / x.rolling(w).std()
    p["spx_ret"] = (monthly_last(yahoo["^GSPC"]).pct_change() * 100).reindex(months)

    # ---- 情绪 ----
    if "first_close" in real:
        listed = real[real.price.notna() & real.first_close.notna()].copy()
        listed["ret"] = listed.first_close / listed.price - 1
        p = p.join(listed.groupby("m").agg(first_day_median=("ret", "median"),
                                           break_rate=("ret", lambda v: (v < 0).mean())))
    return p, {"estimated": estimated, "demand_parts": demand_parts, "manual": manual}


COLUMNS = [  # key, 中文名, 分组, 单位
    ("ipo", "IPO", "供给", "$B"),
    ("follow_on", "增发/大宗", "供给", "$B"),
    ("convertible", "可转债", "供给", "$B"),
    ("insider_sell", "内部人卖出", "供给", "$B"),
    ("buyback", "回购", "供给减项", "$B"),
    ("dividend", "现金分红", "供给减项", "$B"),
    ("insider_buy", "内部人买入", "供给减项", "$B"),
    ("net_supply", "净股权供给", "供给", "$B"),
    ("lockup_ref", "锁定到期(6月前IPO)", "参考", "$B"),
    ("insider_sell_10pct", "10%股东卖出", "参考", "$B"),
    ("etf_us_equity", "美股ETF净流入", "需求", "$B"),
    ("mf_domestic_equity", "美股共同基金净流入", "需求", "$B"),
    ("margin", "融资余额变化", "需求", "$B"),
    ("demand", "增量资金", "需求", "$B"),
    ("free_credit", "券商现金余额变化", "参考", "$B"),
    ("gap", "供需差", "结果", "$B"),
    ("gap_bp", "供需差/市值", "结果", "bp"),
    ("gap_z3", "z3", "结果", ""),
    ("gap_z6", "z6", "结果", ""),
    ("gap_ex_div", "供需差(扣分红)", "结果", "$B"),
    ("gap_ex_div_bp", "扣分红/市值", "结果", "bp"),
    ("gap_ex_div_z6", "扣分红 z6", "结果", ""),
    ("spx_ret", "S&P500 月涨幅", "市场", "%"),
    ("ipo_count", "IPO 家数(非SPAC)", "情绪", "家"),
    ("spac_count", "SPAC 家数", "情绪", "家"),
    ("filed", "新递表", "情绪", "家"),
    ("withdrawn", "撤回", "情绪", "家"),
    ("first_day_median", "首日涨幅中位数", "情绪", "%"),
    ("break_rate", "首日破发率", "情绪", "%"),
]
PERCENT_KEYS = {"first_day_median", "break_rate"}
LABELS = {k: l for k, l, *_ in COLUMNS}


def to_json(p: pd.DataFrame, meta: dict, display_start: str, display_end: str) -> dict:
    view = p.loc[pd.Period(display_start, "M"):pd.Period(display_end, "M")]
    rows = []
    for m, r in view.iterrows():
        row = {"month": str(m)}
        for key, *_ in COLUMNS:
            v = r.get(key)
            row[key] = None if v is None or pd.isna(v) else round(float(v) * (100 if key in PERCENT_KEYS else 1), 2)
        rows.append(row)
    manual, parts = meta["manual"], meta["demand_parts"]
    caveats = [
        "增发/大宗、可转债、回购、分红为季度值 ÷3 均摊到月；回购/分红为 S&P 500 口径",
        "内部人买卖来自 SEC Form 4（openinsider，按交易日归月），剔除纯 10% 大股东卖出以免与大宗增发重复",
        "IPO 不含 SPAC（募资进信托账户，不吸收二级市场资金）；锁定到期仅作参考，不进公式",
        "分母为 Wilshire 5000 指数点（≈ 十亿美元总市值），非自由流通市值",
    ]
    caveats += [f"{LABELS[k]} {', '.join(v)} 尚未公布，沿用上一季度（估算）" for k, v in meta["estimated"].items()]
    missing = [LABELS[k] for k in DEMAND_KEYS if k not in parts]
    if missing:
        caveats.append(f"{'、'.join(missing)} 数据不完整，暂不计入增量资金（只展示）")
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "display": [display_start, display_end],
        "history_start": str(p.index[0]),
        "unit": "十亿美元 ($B)",
        "columns": [{"key": k, "label": l, "group": g, "unit": u} for k, l, g, u in COLUMNS],
        "rows": rows,
        "commentary": manual.get("commentary"),
        "formula": "净股权供给 = IPO + 增发/大宗 + 可转债 + 内部人卖出 − 回购 − 分红 − 内部人买入；"
                   f"供需差 = 增量资金({' + '.join(LABELS[k] for k in parts)}) − 净股权供给；"
                   "z3/z6 = 供需差/总市值 的 3/6 个月滚动 z-score",
        "caveats": caveats + manual.get("caveats", []),
        "source": "自动：Nasdaq IPO 日历、openinsider（SEC Form 4）、FINRA 融资统计、Yahoo（^GSPC/^W5000/新股首日价）；"
                  "manual.json：FactSet via First Trust（ETF 流量）、ICI（共同基金）、ICR/Dealogic（增发/可转债）、"
                  "S&P DJI（回购/分红）",
    }


def main() -> None:
    last_full = (pd.Period(date.today(), "M") - 1).strftime("%Y-%m")
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="重新下载 raw/ 自动数据源")
    parser.add_argument("--start", default=f"{last_full[:4]}-01", help="展示起始月 YYYY-MM（默认当年 1 月）")
    parser.add_argument("--end", default=last_full, help="展示结束月 YYYY-MM（默认上一个完整月）")
    args = parser.parse_args()
    history_start = min(HISTORY_START, (pd.Period(args.start, "M") - 3).strftime("%Y-%m"))
    if args.refresh or not (RAW / "yahoo.json").exists():
        download(history_start, args.end)
    panel, meta = compute(history_start, args.end)
    panel.round(4).to_csv(HERE / "panel.csv", encoding="utf-8-sig")
    payload = to_json(panel, meta, args.start, args.end)
    (HERE / "panel.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    cols = ["ipo", "follow_on", "convertible", "insider_sell", "buyback", "dividend", "net_supply",
            "etf_us_equity", "mf_domestic_equity", "margin", "demand", "gap", "gap_bp", "gap_z3", "gap_z6",
            "gap_ex_div_z6", "spx_ret"]
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(panel[cols].round(1).to_string())
    print("demand parts:", meta["demand_parts"], "estimated:", meta["estimated"])


if __name__ == "__main__":
    main()
