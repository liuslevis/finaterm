"""A股「国家队」ETF 占比面板：头部四只沪深300ETF 市值 / 沪深300流通市值。

用法（在 dashboard/ 目录下运行）：
    uv run python tab/a-etf-share/build_panel.py            # 复用 raw/ 缓存，只重算
    uv run python tab/a-etf-share/build_panel.py --refresh  # 重新下载全部原始数据（约 2 分钟）

输出：raw/*.csv（原始数据）、panel.csv（逐日全量中间列）、panel.json（供 /api/a-etf-share）。
设计说明见同目录 SKILL.md。
"""
import argparse
import json
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests

warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
YI = 1e8  # 亿元

# 规模最大的四只沪深300ETF；exchange 决定份额来源（上交所逐日披露，深交所按代码查历史规模）
ETFS = [
    {"code": "510300", "symbol": "sh510300", "exchange": "sse", "name": "华泰柏瑞沪深300ETF",
     "short": "华泰柏瑞 510300", "manager": "华泰柏瑞", "color": "#38d7c5"},
    {"code": "510330", "symbol": "sh510330", "exchange": "sse", "name": "华夏沪深300ETF",
     "short": "华夏 510330", "manager": "华夏", "color": "#54a4ff"},
    {"code": "159919", "symbol": "sz159919", "exchange": "szse", "name": "嘉实沪深300ETF",
     "short": "嘉实 159919", "manager": "嘉实", "color": "#f5bd59"},
    {"code": "510310", "symbol": "sh510310", "exchange": "sse", "name": "易方达沪深300ETF",
     "short": "易方达 510310", "manager": "易方达", "color": "#a78bfa"},
]
CODES = [etf["code"] for etf in ETFS]
SSE_CODES = [etf["code"] for etf in ETFS if etf["exchange"] == "sse"]
SZSE_CODES = [etf["code"] for etf in ETFS if etf["exchange"] == "szse"]

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
SSE_URL = "https://query.sse.com.cn/commonQuery.do"
SSE_HEADERS = {"Referer": "https://www.sse.com.cn/", "User-Agent": UA}
SZSE_URL = "https://fund.szse.cn/api/report/ShowReport/data"
SZSE_HEADERS = {"Referer": "https://fund.szse.cn/marketdata/fundslist/index.html", "User-Agent": UA,
                "Accept": "application/json, text/javascript, */*; q=0.01", "X-Requested-With": "XMLHttpRequest"}
EM_INDEX_URL = "http://push2.eastmoney.com/api/qt/stock/get"
CSI300_SINA = "sh000300"


# ---------------------------------------------------------------- 下载

def fetch_sse_day(day: str) -> dict[str, float] | None:
    """上交所 ETF 份额（TOT_VOL 单位：万份）。返回 {代码: 份额(份)}，无数据返回 None。"""
    params = {
        "isPagination": "true", "pageHelp.pageSize": "10000", "pageHelp.pageNo": "1",
        "pageHelp.beginPage": "1", "pageHelp.cacheSize": "1", "pageHelp.endPage": "1",
        "sqlId": "COMMON_SSE_ZQPZ_ETFZL_XXPL_ETFGM_SEARCH_L",
        "STAT_DATE": f"{day[:4]}-{day[4:6]}-{day[6:]}",
    }
    for attempt in range(3):
        try:
            response = requests.get(SSE_URL, params=params, headers=SSE_HEADERS, timeout=30)
            rows = response.json().get("result") or []
            if not rows:
                return None
            out = {}
            for row in rows:
                code = str(row.get("SEC_CODE", "")).strip()
                if code in SSE_CODES:
                    out[code] = float(row["TOT_VOL"]) * 1e4  # 万份 → 份
            return out or None
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    return None


def download_sse_shares(days: list[pd.Timestamp]) -> pd.DataFrame:
    """逐日抓上交所 ETF 份额（接口一次查一天），失败重试后跳过。输出长表 date/code/shares。"""
    dates = [d.strftime("%Y%m%d") for d in days]
    records, missing = [], []

    def worker(day: str):
        return day, fetch_sse_day(day)

    with ThreadPoolExecutor(4) as pool:
        for i, (day, row) in enumerate(pool.map(worker, dates), 1):
            if row is None:
                missing.append(day)
            else:
                records.extend({"date": day, "code": code, "shares": value} for code, value in row.items())
            if i % 40 == 0:
                print(f"  sse {i}/{len(dates)}（缺失 {len(missing)}）", flush=True)

    if missing:
        print(f"  ! 上交所无数据/抓取失败的交易日 {len(missing)} 个：{missing[:8]}", flush=True)
    frame = pd.DataFrame(records)
    frame["date"] = pd.to_datetime(frame.date)
    return frame.sort_values(["date", "code"]).reset_index(drop=True)


def download_szse_shares(start: str, end: str) -> pd.DataFrame:
    """深交所「基金规模」按代码查历史（current_size 单位：万份）。

    该接口单次最多返回约 183 天的数据，超过就返回空；自动按 175 天切段并翻页。
    """
    lo, hi = pd.Timestamp(start), pd.Timestamp(end)
    chunks = []
    cursor = lo
    while cursor <= hi:
        chunk_end = min(cursor + pd.Timedelta(days=175), hi)
        chunks.append((cursor, chunk_end))
        cursor = chunk_end + pd.Timedelta(days=1)

    frames = []
    for code in SZSE_CODES:
        for chunk_start, chunk_end in chunks:
            page, total = 1, 1
            while page <= total:
                params = {"SHOWTYPE": "JSON", "CATALOGID": "fund_jjgm", "TABKEY": "tab1",
                          "loading": "first", "txtDm": code, "random": "0.5",
                          "txtStart": chunk_start.strftime("%Y-%m-%d"),
                          "txtEnd": chunk_end.strftime("%Y-%m-%d"), "PAGENO": str(page)}
                for attempt in range(3):
                    try:
                        payload = requests.get(SZSE_URL, params=params, headers=SZSE_HEADERS,
                                               timeout=30).json()[0]
                        break
                    except Exception:
                        time.sleep(1.5 * (attempt + 1))
                else:
                    raise RuntimeError(f"深交所 {code} 历史规模下载失败")
                meta = payload.get("metadata") or {}
                total = int(meta.get("pagecount") or 0)
                for row in payload.get("data") or []:
                    if str(row.get("fund_code", "")).strip() != code:
                        continue
                    frames.append({
                        "date": pd.to_datetime(row["size_date"]),
                        "code": code,
                        "shares": float(str(row["current_size"]).replace(",", "")) * 1e4,  # 万份 → 份
                    })
                page += 1
    frame = pd.DataFrame(frames)
    frame = frame.drop_duplicates(["date", "code"]).sort_values(["date", "code"])
    print(f"  深交所份额 {len(frame)} 行（{frame.date.min().date()} ~ {frame.date.max().date()}）", flush=True)
    return frame.reset_index(drop=True)


def download_prices(days: list[pd.Timestamp]) -> pd.DataFrame:
    """新浪 ETF 日线收盘价（元/份）。一次请求返回全历史，这里只裁到窗口。"""
    import akshare as ak
    lo, hi = days[0], days[-1]
    frames = []
    for etf in ETFS:
        try:
            history = ak.fund_etf_hist_sina(symbol=etf["symbol"])
        except Exception as error:
            raise RuntimeError(f"新浪 ETF 日线失败 {etf['symbol']}: {error}") from error
        history = history.assign(
            date=pd.to_datetime(history.date), code=etf["code"], close=history.close.astype(float))
        frames.append(history.loc[(history.date >= lo) & (history.date <= hi), ["date", "code", "close"]])
    return pd.concat(frames).sort_values(["date", "code"]).reset_index(drop=True)


def download_csi300(start: str, end: str) -> pd.DataFrame:
    import akshare as ak
    index = ak.stock_zh_index_daily(symbol=CSI300_SINA)
    index = index.assign(date=pd.to_datetime(index.date), close=index.close.astype(float))
    index = index[(index.date >= pd.Timestamp(start)) & (index.date <= pd.Timestamp(end))]
    return index[["date", "close"]].reset_index(drop=True)


def download_float_mcap() -> dict:
    """沪深300 总市值/流通市值现值与对应指数点位（东财行情快照，作为流通市值序列的锚）。"""
    for attempt in range(3):
        try:
            response = requests.get(EM_INDEX_URL, params={
                "secid": "1.000300", "fields": "f43,f57,f58,f116,f117,f169,f170"},
                headers={"User-Agent": UA}, timeout=30)
            data = response.json()["data"]
            return {
                "snapshot_at": datetime.now().isoformat(timespec="seconds"),
                "index": float(data["f43"]) / 100,
                "total_mcap": float(data["f116"]),
                "float_mcap": float(data["f117"]),
                "source": "东财 push2 指数行情 f117（沪深300 流通市值）",
            }
        except Exception:
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("沪深300 流通市值快照下载失败")


# ---------------------------------------------------------------- 计算

def load(name: str) -> pd.DataFrame:
    frame = pd.read_csv(RAW / f"{name}.csv", parse_dates=["date"])
    if "code" in frame.columns:  # 代码不能按整数读，否则 159919 会对不上
        frame["code"] = frame["code"].astype(str).str.zfill(6)
    return frame


def compute() -> tuple[pd.DataFrame, dict]:
    anchor = json.loads((RAW / "float_mcap.json").read_text(encoding="utf-8"))
    index = load("csi300").set_index("date").close.sort_index()
    prices = load("prices").pivot(index="date", columns="code", values="close")
    prices = prices.reindex(index=index.index, columns=CODES).ffill()
    if prices.isna().any().any():
        raise RuntimeError(f"缺少 ETF 收盘价：{prices.columns[prices.isna().any()].tolist()}")

    sse = load("sse_shares").pivot(index="date", columns="code", values="shares")
    szse = load("szse_shares").pivot(index="date", columns="code", values="shares")
    shares = pd.concat([sse, szse], axis=1).reindex(index=index.index, columns=CODES)
    coverage = shares.notna().sum(axis=1)  # 当日有原始披露的 ETF 只数
    shares = shares.ffill()                # 份额只在申赎时变化，未披露日沿用前值
    if shares.iloc[0].isna().any():
        raise RuntimeError("窗口起始日缺少 ETF 份额数据，请把 --start 往后挪或先 --refresh")
    if shares.isna().any().any():
        raise RuntimeError("ETF 份额序列存在无法前向填充的空洞")

    # 流通市值：以快照（点位 + 流通市值）为锚，按沪深300收盘价等比回溯（成分股调整带来 1%~2% 偏差）
    scale = index / float(anchor["index"])
    panel = pd.DataFrame(index=index.index)
    panel.index.name = "date"
    panel["csi300"] = index
    for code in CODES:
        panel[f"shares_{code}"] = shares[code] / YI              # 亿份
        panel[f"aum_{code}"] = shares[code] * prices[code] / YI  # 亿元
    panel["shares"] = panel[[f"shares_{c}" for c in CODES]].sum(axis=1)
    panel["aum"] = panel[[f"aum_{c}" for c in CODES]].sum(axis=1)
    panel["float_mcap"] = anchor["float_mcap"] / YI * scale      # 亿元
    panel["total_mcap"] = anchor["total_mcap"] / YI * scale      # 亿元
    panel["ratio"] = panel.aum / panel.float_mcap * 100
    panel["coverage"] = coverage

    # 份额变动 × 当日收盘价 ≈ 净申购/赎回（亿元）
    for code in CODES:
        panel[f"flow_{code}"] = shares[code].diff() * prices[code] / YI
    panel["flow"] = panel[[f"flow_{c}" for c in CODES]].sum(axis=1)
    panel["shares_chg"] = panel.shares.diff()
    panel["flow_5d"] = panel.flow.rolling(5, min_periods=1).sum()
    panel["flow_20d"] = panel.flow.rolling(20, min_periods=1).sum()
    panel["flow_cum"] = panel.flow.fillna(0).cumsum()
    panel["ratio_chg_20d"] = panel.ratio.diff(20)
    return panel, anchor


def monthly(panel: pd.DataFrame) -> pd.DataFrame:
    grouped = panel.groupby(panel.index.to_period("M"))
    rows = pd.DataFrame({
        "ratio": grouped.ratio.last(),
        "aum": grouped.aum.last(),
        "shares": grouped.shares.last(),
        "shares_chg": grouped.shares_chg.sum(),
        "flow": grouped.flow.sum(),
        "csi300": grouped.csi300.last(),
        "float_mcap": grouped.float_mcap.last(),
    })
    for code in CODES:
        rows[f"shares_{code}"] = grouped[f"shares_{code}"].last()
    rows["csi300_ret"] = rows.csi300.pct_change() * 100
    rows["aum_ret"] = rows.aum.pct_change() * 100
    rows["flow_pct_aum"] = rows.flow / rows.aum.shift() * 100
    rows["ratio_chg"] = rows.ratio.diff()
    return rows


def kpis(panel: pd.DataFrame) -> dict:
    ratio = panel.ratio
    peak_date, trough_date = ratio.idxmax(), ratio.idxmin()
    first, last = panel.iloc[0], panel.iloc[-1]
    return {
        "as_of": panel.index[-1].strftime("%Y-%m-%d"),
        "ratio": round(float(last.ratio), 2),
        "ratio_first": round(float(first.ratio), 2),
        "ratio_chg": round(float(last.ratio - first.ratio), 2),
        "ratio_chg_pct": round(float(last.ratio / first.ratio - 1) * 100, 1),
        "peak": round(float(ratio.max()), 2),
        "peak_date": peak_date.strftime("%Y-%m-%d"),
        "trough": round(float(ratio.min()), 2),
        "trough_date": trough_date.strftime("%Y-%m-%d"),
        "drawdown": round(float(last.ratio - ratio.max()), 2),
        "days_since_peak": int((panel.index[-1] - peak_date).days),
        "aum": round(float(last.aum), 1),
        "aum_chg": round(float(last.aum - first.aum), 1),
        "aum_chg_pct": round(float(last.aum / first.aum - 1) * 100, 1),
        "float_mcap": round(float(last.float_mcap), 1),
        "total_mcap": round(float(last.total_mcap), 1),
        "shares": round(float(last.shares), 1),
        "shares_chg": round(float(last.shares - first.shares), 1),
        "shares_chg_pct": round(float(last.shares / first.shares - 1) * 100, 1),
        "flow": round(float(panel.flow.sum()), 1),
        "flow_20d": round(float(panel.flow_20d.iloc[-1]), 1),
        "csi300": round(float(last.csi300), 2),
        "csi300_chg_pct": round(float(last.csi300 / first.csi300 - 1) * 100, 1),
    }


COLUMNS = [  # key, 中文名, 分组, 单位
    ("ratio", "占比", "核心", "%"),
    ("ratio_chg", "占比变动", "核心", "pp"),
    ("aum", "四只ETF市值", "规模", "亿"),
    ("aum_ret", "市值变动", "规模", "%"),
    ("shares", "合计份额", "份额", "亿份"),
    ("shares_chg", "份额变化", "份额", "亿份"),
    ("flow", "估算净申赎", "资金", "亿"),
    ("flow_pct_aum", "净申赎/期初市值", "资金", "%"),
    ("shares_510300", "510300", "单只份额", "亿份"),
    ("shares_510330", "510330", "单只份额", "亿份"),
    ("shares_159919", "159919", "单只份额", "亿份"),
    ("shares_510310", "510310", "单只份额", "亿份"),
    ("float_mcap", "沪深300流通市值", "参考", "亿"),
    ("csi300", "CSI300 收盘", "参考", ""),
    ("csi300_ret", "CSI300 月涨幅", "参考", "%"),
]


def to_json(panel: pd.DataFrame, months: pd.DataFrame, anchor: dict, start: str, end: str) -> dict:
    view = panel.loc[pd.Timestamp(start):pd.Timestamp(end)]
    cum_flow = view.flow.fillna(0).cumsum()  # 累计净申赎从窗口首日重新起算
    daily = []
    for day, row in view.iterrows():
        item = {"d": day.strftime("%Y-%m-%d")}
        for key in ("ratio", "aum", "shares", "flow", "flow_5d", "flow_20d", "csi300",
                    "float_mcap", "ratio_chg_20d", "coverage"):
            value = row.get(key)
            item[key] = None if value is None or pd.isna(value) else round(float(value), 4)
        item["flow_cum"] = round(float(cum_flow.loc[day]), 4)
        for code in CODES:
            item[f"s_{code}"] = round(float(row[f"shares_{code}"]), 4)
        daily.append(item)

    month_view = months.loc[pd.Period(start, "M"):pd.Period(end, "M")]
    monthly_rows = []
    for period, row in month_view.iterrows():
        item = {"month": str(period)}
        for key, *_ in COLUMNS:
            value = row.get(key)
            item[key] = None if value is None or pd.isna(value) else round(float(value), 2)
        monthly_rows.append(item)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "display": [start, end],
        "unit": "亿元",
        "etfs": [{k: etf[k] for k in ("code", "name", "short", "manager", "color")} for etf in ETFS],
        "kpi": kpis(view),
        "anchor": {
            "snapshot_at": anchor["snapshot_at"],
            "float_mcap": round(anchor["float_mcap"] / 1e12, 2),
            "total_mcap": round(anchor["total_mcap"] / 1e12, 2),
            "index": round(anchor["index"], 2),
            "source": anchor["source"],
        },
        "daily": daily,
        "monthly": monthly_rows,
        "columns": [{"key": k, "label": l, "group": g, "unit": u} for k, l, g, u in COLUMNS],
        "formula": "占比 = 四只沪深300ETF市值合计 ÷ 沪深300流通市值 × 100%；市值 = ETF 份额 × 收盘价；"
                   "估算净申赎 = 份额变化 × 当日收盘价（亿元）；"
                   "流通市值 = 东财快照 ×（沪深300收盘 ÷ 快照点位）",
        "caveats": [
            "样本只有 4 只头部沪深300ETF（510300/510330/159919/510310），占比低于全口径，看趋势不看绝对值",
            "沪深300流通市值用东财行情快照锚定后按指数点位等比回溯；指数成分股调整（6 月/12 月）会带来 1%~2% 偏差",
            "份额来自上交所逐日披露与深交所基金规模历史（原始单位万份），收盘价来自新浪，价格与份额同日匹配",
            "估算净申赎用当日收盘价近似成交净值，实际按 T 日净值或篮子折溢价成交，存在误差",
            "ETF 份额只在申赎时变化；拆分、分红再投、转托管等非申赎原因也会让份额变动，需结合公告判断",
        ],
        "source": "上交所 ETF 份额（query.sse.com.cn 逐日）、深交所基金规模（fund.szse.cn fund_jjgm）、"
                  "新浪 ETF 日线与沪深300日线、东财 push2（沪深300 流通市值快照）",
    }


def ensure_raw(warm_start: pd.Timestamp, end: pd.Timestamp, refresh: bool) -> None:
    """按缺失情况抓原始数据：单个文件缺失只补那一个，--refresh 则全部重下。"""
    RAW.mkdir(exist_ok=True)

    if not refresh and (RAW / "csi300.csv").exists():
        cached = load("csi300").date
        if cached.min() > warm_start + pd.Timedelta(days=5):
            print(f"缓存只覆盖 {cached.min().date()} 起，需重下以覆盖 {warm_start.date()} …", flush=True)
            refresh = True
        elif cached.max() < end:
            print(f"! 缓存数据到 {cached.max().date()} 为止；要包含 {end.date()} 请加 --refresh", flush=True)

    def stale(*names: str) -> bool:
        return refresh or any(not (RAW / f"{name}.csv").exists() for name in names)

    if stale("csi300", "prices"):
        print(f"下载指数与 ETF 日线 {warm_start.date()} ~ {end.date()} …", flush=True)
        csi = download_csi300(warm_start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        csi.to_csv(RAW / "csi300.csv", index=False)
        download_prices(list(csi.date)).to_csv(RAW / "prices.csv", index=False)
    if stale("sse_shares"):
        days = list(load("csi300").date)
        print(f"下载上交所 ETF 份额 {len(days)} 个交易日 …", flush=True)
        download_sse_shares(days).to_csv(RAW / "sse_shares.csv", index=False)
    if stale("szse_shares"):
        print("下载深交所 ETF 份额 …", flush=True)
        download_szse_shares(warm_start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")).to_csv(
            RAW / "szse_shares.csv", index=False)
    if refresh or not (RAW / "float_mcap.json").exists():
        (RAW / "float_mcap.json").write_text(
            json.dumps(download_float_mcap(), ensure_ascii=False, indent=1), encoding="utf-8")


def main() -> None:
    last_trading_hint = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    parser = argparse.ArgumentParser(description="头部沪深300ETF 市值占沪深300流通市值 面板")
    parser.add_argument("--refresh", action="store_true", help="重新下载 raw/ 原始数据")
    parser.add_argument("--start", default=None, help="展示起始日 YYYY-MM-DD（默认结束日往前一年）")
    parser.add_argument("--end", default=last_trading_hint, help="展示结束日 YYYY-MM-DD（默认昨天）")
    args = parser.parse_args()

    end = pd.Timestamp(args.end)
    start = pd.Timestamp(args.start) if args.start else end - pd.Timedelta(days=365)
    warm_start = start - pd.Timedelta(days=45)  # 首行要能算出份额变化

    ensure_raw(warm_start, end, args.refresh)

    panel, anchor = compute()
    panel.round(4).to_csv(HERE / "panel.csv", encoding="utf-8-sig")
    payload = to_json(panel, monthly(panel), anchor, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
    (HERE / "panel.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    cols = ["ratio", "aum", "shares", "flow", "csi300", "float_mcap"]
    print(panel.loc[pd.Timestamp(start.strftime("%Y-%m-%d")):, cols].round(2).to_string(max_rows=30))
    print("\nKPI:", json.dumps(payload["kpi"], ensure_ascii=False))


if __name__ == "__main__":
    main()
