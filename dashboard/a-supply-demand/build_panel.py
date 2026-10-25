"""A股供需月度面板：净股权供给 vs 增量资金。

用法（在 dashboard/ 目录下）：
    uv run python a-supply-demand/build_panel.py            # 复用 raw/ 缓存，只重算
    uv run python a-supply-demand/build_panel.py --refresh  # 重新下载全部原始数据（约 5 分钟）

输出：raw/*.pkl（原始数据）、panel.csv（全部月份 × 全部指标）、panel.json（供 /api/a-supply-demand）。
设计说明见同目录 SKILL.md。
"""
import argparse
import json
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

import akshare as ak
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
YI = 1e8
HISTORY_START = "2025-01"  # z-score 需要的回看历史起点

# 沪市 ETF 只保留 A 股股票类，剔除债券/货币/商品/跨境
NON_EQUITY_ETF = (
    "债|国开|政金|短融|货币|黄金|金ETF|恒生|港|HK|H股|纳指|纳斯达克|标普|日经|德国|法国|沙特|"
    "东南亚|亚太|中概|美|豆粕|有色期货|能源化工|原油|快线|现金|添益|日利|保证金|REIT"
)
EQUITY_FUND_TYPES = ["股票型", "混合型-偏股", "混合型-灵活", "指数型-股票", "混合型-平衡"]


def month_ends(start: str, end: str) -> list[pd.Timestamp]:
    cal = pd.to_datetime(ak.tool_trade_date_hist_sina().trade_date)
    lo = pd.Period(start, "M").start_time - pd.Timedelta(days=40)  # 多取上月末作为差分基期
    cal = cal[(cal >= lo) & (cal <= pd.Period(end, "M").end_time)]
    return list(cal.groupby(cal.dt.to_period("M")).max())


def fetch_etf(start: str, end: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    frames = []
    ends = month_ends(start, end)
    for d in ends:
        x = ak.fund_etf_scale_sse(date=d.strftime("%Y%m%d"))
        x["me"] = d
        frames.append(x)
    shares = pd.concat(frames)

    def hist(code):
        try:
            x = ak.fund_etf_hist_sina(symbol="sh" + code)
            x = x[pd.to_datetime(x.date) >= ends[0] - pd.Timedelta(days=40)]
            x["code"] = code
            return x
        except Exception:
            return None

    with ThreadPoolExecutor(8) as pool:
        prices = pd.concat([x for x in pool.map(hist, sorted(shares.基金代码.unique())) if x is not None])
    return shares, prices


def fetch_dividends(years) -> pd.DataFrame:
    frames = []
    for y in years:
        for md in ("0630", "1231"):
            try:
                frames.append(ak.stock_fhps_em(date=f"{y}{md}"))
            except Exception:
                pass  # 尚未披露的报告期
    return pd.concat(frames)


def download(start: str, end: str) -> None:
    RAW.mkdir(exist_ok=True)
    s, e = pd.Period(start, "M"), pd.Period(end, "M")
    jobs = {
        "ipo": lambda: ak.stock_xgsglb_em(symbol="全部股票"),
        "seo": lambda: ak.stock_qbzf_em(),
        "rights": lambda: ak.stock_pg_em(),
        "cb": lambda: ak.bond_zh_cov(),
        "unlock": lambda: ak.stock_restricted_release_summary_em(
            symbol="全部股票", start_date=s.start_time.strftime("%Y%m%d"), end_date=e.end_time.strftime("%Y%m%d")),
        "holder_change": lambda: ak.stock_ggcg_em(symbol="全部"),
        "buyback": lambda: ak.stock_repurchase_em(),
        "dividend": lambda: fetch_dividends(range(s.year - 1, e.year + 1)),
        "new_fund": lambda: ak.fund_new_found_em(),
        "margin_sh": lambda: ak.macro_china_market_margin_sh(),
        "margin_sz": lambda: ak.macro_china_market_margin_sz(),
        "mcap": lambda: ak.macro_china_stock_market_cap(),
        "csi300": lambda: ak.stock_zh_index_daily(symbol="sh000300"),
    }
    for name, job in jobs.items():
        print("download", name, flush=True)
        job().to_pickle(RAW / f"{name}.pkl")
    print("download etf", flush=True)
    shares, prices = fetch_etf(start, end)
    shares.to_pickle(RAW / "etf_shares.pkl")
    prices.to_pickle(RAW / "etf_prices.pkl")


def load(name: str) -> pd.DataFrame:
    return pd.read_pickle(RAW / f"{name}.pkl")


def compute(start: str, end: str) -> pd.DataFrame:
    months = pd.period_range(start, end, freq="M")

    def by_month(dates, values):
        idx = pd.DatetimeIndex(pd.to_datetime(np.asarray(dates), errors="coerce")).to_period("M")
        s = pd.Series(np.asarray(values, float), index=idx)
        return s.groupby(level=0).sum().reindex(months).fillna(0)

    p = pd.DataFrame(index=months)
    # ---- 供给 ----
    ipo = load("ipo")
    ipo = ipo[ipo.发行价格.notna()]
    p["ipo"] = by_month(ipo.申购日期, ipo.发行总数 * 1e4 * ipo.发行价格) / YI
    p["ipo_count"] = by_month(ipo.申购日期, np.ones(len(ipo)))
    seo = load("seo")
    p["seo"] = by_month(seo.发行日期, seo.发行总数 * seo.发行价格) / YI
    rights = load("rights")
    p["rights"] = by_month(rights.缴款起始日期, rights.配股数量 * rights.配股价) / YI
    cb = load("cb")
    p["cb"] = by_month(cb.申购日期, cb.发行规模)
    unlock = load("unlock")
    p["unlock"] = by_month(unlock.解禁时间, unlock.实际解禁市值) / YI

    hc = load("holder_change").drop_duplicates(["代码", "股东名称", "变动开始日", "变动截止日", "持股变动信息-变动数量"])
    amount = hc["持股变动信息-变动数量"] * 1e4 * hc.最新价
    down, up = hc["持股变动信息-增减"] == "减持", hc["持股变动信息-增减"] == "增持"
    p["holder_sell"] = by_month(hc.变动截止日[down], amount[down]) / YI
    p["holder_buy"] = by_month(hc.变动截止日[up], amount[up]) / YI

    bb = load("buyback").dropna(subset=["已回购金额", "回购起始时间", "最新公告日期"])
    buyback = pd.Series(0.0, index=months)
    for _, row in bb.iterrows():
        span = pd.period_range(pd.Timestamp(row.回购起始时间).to_period("M"),
                               pd.Timestamp(row.最新公告日期).to_period("M"), freq="M")
        for m in span:
            if m in buyback.index:
                buyback[m] += row.已回购金额 / len(span)
    p["buyback"] = buyback / YI

    dv = load("dividend").drop_duplicates(["代码", "除权除息日"])
    dv = dv[dv.除权除息日.notna()]
    p["dividend"] = by_month(dv.除权除息日, dv["现金分红-现金分红比例"].fillna(0) / 10 * dv.总股本) / YI

    p["gross_supply"] = p[["ipo", "seo", "rights", "cb", "holder_sell"]].sum(axis=1)
    p["net_supply"] = p.gross_supply - p[["buyback", "dividend", "holder_buy"]].sum(axis=1)
    p["net_supply_ex_div"] = p.net_supply + p.dividend

    # ---- 需求 ----
    fund = load("new_fund")
    keep = fund.基金类型.isin(EQUITY_FUND_TYPES) & ~(fund.基金简称.str.contains("ETF") & ~fund.基金简称.str.contains("联接"))
    fund = fund[keep]
    p["new_fund"] = by_month(fund.成立日期, fund.募集份额.fillna(0))

    balances = []
    for name in ("margin_sh", "margin_sz"):
        d = load(name)
        balances.append(d.set_index(pd.to_datetime(d.日期)).融资余额.astype(float))
    margin = pd.concat(balances, axis=1, sort=True).ffill().sum(axis=1)
    p["margin"] = (margin.groupby(margin.index.to_period("M")).last().diff() / YI).reindex(months)

    shares = load("etf_shares")
    shares = shares[~shares.基金简称.str.contains(NON_EQUITY_ETF)]
    sh = shares.pivot_table(index=shares.me.dt.to_period("M"), columns="基金代码", values="基金份额")
    px = load("etf_prices")
    px = px.pivot_table(index=pd.to_datetime(px.date), columns="code", values="close").ffill()
    pxm = px.groupby(px.index.to_period("M")).last().reindex(sh.index)
    avg_px = ((pxm + pxm.shift()) / 2).fillna(pxm)
    p["etf"] = ((sh.fillna(0).diff() * avg_px).sum(axis=1) / YI).reindex(months)

    p["demand"] = p[["new_fund", "margin", "etf"]].sum(axis=1)
    p["gap"] = p.demand - p.net_supply
    p["gap_ex_div"] = p.demand - p.net_supply_ex_div

    mc = load("mcap")
    mc.index = pd.PeriodIndex(pd.to_datetime(mc.数据日期.str.replace("年", "-").str.replace("月份", "")), freq="M")
    p["mcap"] = (mc["市价总值-上海"] + mc["市价总值-深圳"]).reindex(months)
    for col in ("gap", "gap_ex_div"):
        x = p[col] / p.mcap * 1e4
        p[f"{col}_bp"] = x
        for w in (3, 6):
            p[f"{col}_z{w}"] = (x - x.rolling(w).mean()) / x.rolling(w).std()

    # ---- 情绪 ----
    listed = load("ipo")
    listed = listed[listed.首日收盘价.notna() & listed.发行价格.notna()].copy()
    listed["ret"] = listed.首日收盘价 / listed.发行价格 - 1
    listed["m"] = pd.to_datetime(listed.上市日期).dt.to_period("M")
    s = listed.groupby("m").agg(
        listed_count=("ret", "size"), first_day_mean=("ret", "mean"),
        break_rate=("ret", lambda v: (v < 0).mean()), quote_multiple=("询价累计报价倍数", "median"))
    p = p.join(s)

    idx = load("csi300")
    close = idx.set_index(pd.to_datetime(idx.date)).close.astype(float)
    monthly = close.groupby(close.index.to_period("M")).last()
    p["csi300_ret"] = (monthly.pct_change() * 100).reindex(months)
    return p


COLUMNS = [  # key, 中文名, 分组, 单位
    ("csi300_ret", "CSI300 月涨幅", "市场", "%"),
    ("ipo", "IPO", "供给", "亿"),
    ("seo", "定增/增发", "供给", "亿"),
    ("rights", "配股", "供给", "亿"),
    ("cb", "可转债", "供给", "亿"),
    ("holder_sell", "减持(估)", "供给", "亿"),
    ("buyback", "回购(估)", "供给减项", "亿"),
    ("holder_buy", "增持(估)", "供给减项", "亿"),
    ("dividend", "现金分红", "供给减项", "亿"),
    ("net_supply", "净股权供给", "净供给", "亿"),
    ("unlock", "解禁市值", "参考", "亿"),
    ("new_fund", "新发偏股基金", "需求", "亿"),
    ("margin", "融资余额变化", "需求", "亿"),
    ("etf", "沪市股票ETF净申购", "需求", "亿"),
    ("demand", "增量资金", "需求", "亿"),
    ("gap", "供需差", "结果", "亿"),
    ("gap_bp", "供需差/市值", "结果", "bp"),
    ("gap_z6", "z6", "结果", ""),
    ("gap_ex_div", "供需差(扣分红)", "结果", "亿"),
    ("gap_ex_div_bp", "扣分红/市值", "结果", "bp"),
    ("gap_ex_div_z6", "扣分红 z6", "结果", ""),
    ("ipo_count", "IPO 申购家数", "情绪", "家"),
    ("first_day_mean", "新股首日均涨幅", "情绪", "%"),
    ("break_rate", "首日破发率", "情绪", "%"),
    ("quote_multiple", "网下报价倍数(中位)", "情绪", "倍"),
]
PERCENT_KEYS = {"first_day_mean", "break_rate"}  # 内部为比例，输出 ×100


def to_json(p: pd.DataFrame, display_start: str, display_end: str) -> dict:
    view = p.loc[pd.Period(display_start, "M"):pd.Period(display_end, "M")]
    rows = []
    for m, r in view.iterrows():
        row = {"month": str(m)}
        for key, *_ in COLUMNS:
            v = r.get(key)
            if v is None or pd.isna(v):
                row[key] = None
            else:
                row[key] = round(float(v) * (100 if key in PERCENT_KEYS else 1), 2)
        rows.append(row)
    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "display": [display_start, display_end],
        "history_start": str(p.index[0]),
        "unit": "亿元",
        "columns": [{"key": k, "label": l, "group": g, "unit": u} for k, l, g, u in COLUMNS],
        "rows": rows,
        "formula": "净股权供给 = IPO + 定增/增发 + 配股 + 可转债 + 减持 − 回购 − 分红 − 增持；"
                   "供需差 = 增量资金(新发偏股基金 + 融资余额变化 + 沪市股票ETF净申购) − 净股权供给；"
                   "z6 = 供需差/沪深总市值 的 6 个月滚动 z-score",
        "caveats": [
            "减持/增持 = 变动数量 × 最新价（估算），按变动截止日归月",
            "回购 = 已回购金额在 回购起始→最新公告 期间均摊（估算）",
            "ETF 仅沪市 A 股股票类，Δ份额 × 月均价；深市接口不可用",
            "分母为沪深总市值（非自由流通市值）；分红季节性强，看趋势优先用扣分红口径",
            "银证转账（证券保证金）与新开户数无公开接口（开户数 2023-08 起停更），未纳入",
        ],
        "source": "akshare：东方财富（IPO/增发/配股/可转债/解禁/增减持/回购/分红/新发基金）、"
                  "上交所/深交所（两融）、上交所（ETF 份额）、新浪（ETF 价格/CSI300）",
    }


def main() -> None:
    last_full = (pd.Period(date.today(), "M") - 1).strftime("%Y-%m")
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="重新下载 raw/ 原始数据")
    parser.add_argument("--start", default=f"{last_full[:4]}-01", help="展示起始月 YYYY-MM（默认当年 1 月）")
    parser.add_argument("--end", default=last_full, help="展示结束月 YYYY-MM（默认上一个完整月）")
    args = parser.parse_args()
    history_start = min(HISTORY_START, (pd.Period(args.start, "M") - 12).strftime("%Y-%m"))
    if args.refresh or not (RAW / "csi300.pkl").exists():
        download(history_start, args.end)
    panel = compute(history_start, args.end)
    panel.round(4).to_csv(HERE / "panel.csv", encoding="utf-8-sig")
    payload = to_json(panel, args.start, args.end)
    (HERE / "panel.json").write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    cols = ["net_supply", "demand", "gap", "gap_bp", "gap_z6", "gap_ex_div", "csi300_ret"]
    print(panel.loc[pd.Period(args.start, "M"):, cols].round(1).to_string())


if __name__ == "__main__":
    main()
