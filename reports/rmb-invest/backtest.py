"""银行股 / 红利 / 沪深300 分市场阶段回测（后复权，含分红再投入）。

数据源：腾讯（akshare.stock_zh_a_hist_tx，adjust='hfq'）。
用法：在本目录运行 `python backtest.py`（勿在仓库根目录运行，根目录的 akshare/ 会遮蔽 pip 包）。
"""
import akshare as ak
import numpy as np
import pandas as pd

RF = 0.015  # 无风险利率（年化）

NAMES = {
    '工商银行': 'sh601398', '建设银行': 'sh601939', '农业银行': 'sh601288',
    '招商银行': 'sh600036', '兴业银行': 'sh601166',
    '银行ETF': 'sh512800', '红利低波ETF': 'sh512890', '沪深300ETF': 'sh510300',
}

WINDOWS = {
    '牛 2014-07~2015-06 大牛市': ('2014-07-01', '2015-06-12'),
    '牛 2019-01~2021-02 结构牛': ('2019-01-04', '2021-02-18'),
    '牛 2024-09-13~10-08 急涨': ('2024-09-13', '2024-10-08'),
    '牛 2025-04-08~2025-10-31': ('2025-04-08', '2025-10-31'),
    '熊 2015-06-12~2016-01-28 股灾': ('2015-06-12', '2016-01-28'),
    '熊 2018-01-24~2019-01-03 熊市': ('2018-01-24', '2019-01-03'),
    '熊 2021-02-18~2024-02-05 长熊': ('2021-02-18', '2024-02-05'),
    '近6月 2026-04-30~2026-10-30': ('2026-04-30', '2026-10-30'),
}


def load(start='20140101', end='20261030'):
    s = {}
    for n, c in NAMES.items():
        d = ak.stock_zh_a_hist_tx(symbol=c, start_date=start, end_date=end, adjust='hfq')
        s[n] = d.set_index(pd.to_datetime(d['date']))['close']
    return pd.DataFrame(s).sort_index()


def stats(p, a):
    rows = []
    for n in p.columns:
        s = p[n].dropna()
        if len(s) < 5 or s.index[0] > pd.Timestamp(a) + pd.Timedelta(days=10):
            continue  # 区间开始时尚未上市
        x = s.pct_change().dropna()
        tot = s.iloc[-1] / s.iloc[0] - 1
        vol = x.std() * np.sqrt(252)
        rows.append((n, tot * 100, vol * 100, (x.mean() * 252 - RF) / vol,
                     (s / s.cummax() - 1).min() * 100))
    return pd.DataFrame(rows, columns=['标的', '区间收益%', '年化波动%', '夏普', '最大回撤%']).round(2)


if __name__ == '__main__':
    P = load()
    for w, (a, b) in WINDOWS.items():
        p = P.loc[a:b]
        print(f'\n== {w} ({len(p)} 交易日)')
        print(stats(p, a).to_string(index=False))
