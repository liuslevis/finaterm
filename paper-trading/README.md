# 模拟盘

多策略模拟账户，结果显示在 dashboard「模拟盘」tab。dashboard 服务启动时运行一次 `run_daily.py`，之后每 2 小时一次；
任务幂等，只处理新收盘的交易日（美股按纽约 16:30、A 股按上海 15:30 之后视为收盘）。

```bash
uv run --project paper-trading python paper-trading/run_daily.py         # 只记账
uv run --project paper-trading python paper-trading/run_daily.py --git   # dashboard 默认：拉取 → 记账 → 提交 state/ → push
cd paper-trading && uv run python -m unittest test_engine                 # 引擎测试
```

## 多台电脑同步

- `state/` 进 git，`.cache/`（行情缓存、`run.log`、`last_run.json`）不进。
- `--git`：先 `git fetch` + `git merge --ff-only`（失败则沿用本地，不做 rebase / 强推），记账后只提交 `paper-trading/state`
  （`git commit -- state`，不会带上你暂存的其他改动），再 `git push`；push 失败下次重试。
- 已入账的日期不再重算，CSV 只追加，所以两台电脑各自算出的同一天是同一行；先 push 的那台为准，
  另一台下次 fast-forward 后接着记。
- 关闭自动 git：启动 dashboard 前设 `PAPER_TRADING_GIT=0`。

## 记账规则（`engine.py`）

每个交易日：现金按前一日 13 周国债计息 → 入金 → 按开盘价成交挂单与 `on_open` 订单（费率按策略）→ 收盘估值 →
`on_close` 产生下一开盘的挂单与支持数据快照。收益率为时间加权（入金不算收益），dashboard 另显示 盈亏 = 市值 − 投入。

| 文件 | 内容 |
|---|---|
| `state/strategies.json` | tab 中的策略顺序 |
| `state/benchmarks.csv` / `.json` | 基准收盘价长表（SHY 代表 2Y 国债、沪深300 来自腾讯行情、QQQ、SPY）与显示名 |
| `state/<id>/nav.csv` | 每日现金、持仓、净值、入金、累计投入、时间加权净值 |
| `state/<id>/trades.csv` | 成交记录（成交日、信号日、股数、开盘价、金额、费用、原因） |
| `state/<id>/signals.csv` | 每日收盘的支持数据快照（列由策略 `SUPPORT` 定义） |
| `state/<id>/account.json` | 续跑状态：现金、持仓、待成交挂单 |
| `state/<id>/meta.json` | 名称、说明、起始日、本金、支持数据字段 |

## 新增策略

在 `strategies/` 加一个模块并追加到 `strategies/__init__.py` 的 `STRATEGIES`。模块需定义：

| 名称 | 含义 |
|---|---|
| `ID` `NAME` `DESC` | 目录名 / tab 按钮 / 说明 |
| `START` `CAPITAL` | 第一个入账交易日、首日入金（定投类为 0） |
| `CALENDAR` `DATA` `NEED_GPR` | 交易日历标的、需要下载的 yfinance 代码（A 股指数写 `sh000300`）、是否需要 GPR |
| `FEE` `FRACTIONAL` `CASH_YIELD` | 单边费率、是否允许碎股、现金是否计息 |
| `SUPPORT` | `[{key, label, fmt}]`，fmt ∈ `text usd pct1 pct2 num2 num4 int bool` |
| `prepare(market)` | 预计算全历史特征（只能用回看窗口） |
| `contribution(day)` | 当日入金 |
| `on_open(day, ctx, acct)` | 当日开盘成交的订单（不能依赖当日收盘） |
| `on_close(day, ctx, acct)` | 返回 `(下一开盘挂单, 支持数据 dict)` |

订单：`{"symbol", "side": "buy"|"sell", "weight"|"amount"|"shares": "all", "reason"}`。

改策略参数会让后续信号与已入账历史不一致；要重来就换一个新 `ID`（旧目录保留作记录）。

## 当前策略

- `brent-v2`：Brent 区间 v2，2026-11-10 起 $10,000。研究与回测见 `predictor/brent-regr/README.md`；OPEC+ 会议日期在
  `strategies/opec.py`，需要每月按 opec.org 公告补充（`2026-06-07`、`2026-11-29` 为推断）。
- `qqq-dca`：QQQ 定投，2026-09-10 起每个美股交易日开盘买 $10。
