# Finance API Catalog

> 生成时间：2026-09-06T15:00:09+08:00

本文件汇总本地 **Futu OpenD、AKShare、OpenBB Platform** 的接口目录，并附少量代表性真实请求结果。所有交易、下单、撤单、修改、订阅等写操作均已排除；样例响应只保留行数、字段和前几条记录。

| 平台 | 目录规模 | 调用方式 |
|---|---:|---|
| Futu OpenD | 123 | 本地 OpenD `127.0.0.1:11111` + `uv run python` |
| AKShare | 1090 | `import akshare as ak`，直接请求公开数据源 |
| OpenBB | 284 个唯一命令 / 432 个 provider 变体 | `from openbb import obb` |

## 使用说明

- 目录中的请求为单行模板，`<VALUE>`、`CODE` 等占位符需要替换。
- AKShare 依赖第三方网页接口，可能受限流、反爬、代理和页面改版影响。
- OpenBB 的部分 Provider 需要 API Key；具体凭据要求记录在“简述/限制”列。
- OpenD 请求需要 GUI 已登录，且行情/F10 数据受账户市场权限影响。
- 返回样例采用 JSONL；失败样例保留简短错误信息。

## Futu OpenD

共 **123** 条目录记录；分类：`aggregation` 1、`calendars` 3、`capital-flow` 2、`company-profile` 4、`corporate-actions` 3、`derivatives-reference` 2、`fund-holdings` 3、`fundamentals-financials` 4、`historical-market-data` 2、`industrial-chain` 5、`insiders` 2、`institutions` 5、`macro` 4、`market-breadth` 2、`market-calendar` 2、`market-classification` 3、`market-state` 1、`news` 1、`opend-state` 2、`options` 22、`prediction-market` 13、`quote-entitlements` 1、`quote-reference` 1、`quote-snapshot` 2、`rankings` 9、`reminders-read-only` 1、`research-ratings` 4、`screening` 2、`search` 1、`shareholders` 4、`short-selling` 3、`subscription-state` 1、`technical-indicators` 2、`valuation` 2、`warrants` 2、`watchlists-read-only` 2。

### aggregation (1)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `collect` | `uv run python skills/futuapi/scripts/quote/collect.py US.AAPL [--json] [--with-options] [--verbose]` | 并行抓取单个标的的多源数据，返回精简 JSON 摘要（约 3-4K tokens），; get_market_snapshot: 最多 400 标的; get_capital_flow: 30 req/30s，仅正股/窝轮/基… |

### calendars (3)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_dividend_calendar` | `uv run python skills/futuapi/scripts/quote/get_dividend_calendar.py --market US --date 2026-06-23 [--count 50] [--json]` | 获取指定市场和日期的派息日历数据; 每 30 秒内最多请求 60 次 |
| `get_earnings_calendar` | `uv run python skills/futuapi/scripts/quote/get_earnings_calendar.py --market US [--sort-type HOT] [--begin-date 2026-06-23] [--end-date 2026-06-25] [--config filters.json] [--json]` | 获取指定市场的财报日历数据; 每 30 秒内最多请求 60 次 |
| `get_economic_calendar` | `uv run python skills/futuapi/scripts/quote/get_economic_calendar.py --begin-date 2026-06-23 [--end-date 2026-06-25] [--markets US,HK] [--importance HIGH] [--count 50] [--json]` | 获取指定日期范围的经济事件日历数据，支持自动分页; 每 30 秒内最多请求 60 次 |

### capital-flow (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_capital_distribution` | `uv run python skills/futuapi/scripts/quote/get_capital_distribution.py HK.00700 [--json]` | 获取指定股票的资金分布（特大单/大单/中单/小单的流入流出）; 每 30 秒内最多请求 30 次; 仅支持正股、窝轮和基金 |
| `get_capital_flow` | `uv run python skills/futuapi/scripts/quote/get_capital_flow.py HK.00700 [--json]` | 获取指定股票的日内分时资金流向数据; 每 30 秒内最多请求 30 次; 仅支持正股、窝轮和基金; 历史周期仅提供最近 1 年数据 |

### company-profile (4)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_company_executive_background` | `uv run python skills/futuapi/scripts/quote/get_company_executive_background.py <CODE> <LEADER_NAME> [--json]` | 获取指定股票某位高管的背景介绍; 每 30 秒内最多请求 30 次; 支持正股及基金 |
| `get_company_executives` | `uv run python skills/futuapi/scripts/quote/get_company_executives.py <CODE> [--json]` | 获取指定股票的董事及高管列表，包含展示名称、姓名、职位、任职起始日、发布日期、性别、年龄、学历、年薪; 每 30 秒内最多请求 30 次; 支持正股及基金 |
| `get_company_operational_efficiency` | `uv run python skills/futuapi/scripts/quote/get_company_operational_efficiency.py <CODE> [options] [--json]` | 获取指定股票的公司经营效率数据，包括员工人数、人均营收、人均营业利润、人均净利润等指标; 每 30 秒内最多请求 30 次; 支持正股及基金 |
| `get_company_profile` | `uv run python skills/futuapi/scripts/quote/get_company_profile.py <CODE> [--json]` | 获取指定股票的公司详情标签列表，包含各类文本、链接和章节标题信息; 每 30 秒内最多请求 30 次; 支持正股及基金 |

### corporate-actions (3)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_corporate_actions_buybacks` | `uv run python skills/futuapi/scripts/quote/get_corporate_actions_buybacks.py <CODE> [options] [--json]` | 获取股票的回购记录（港股 / A 股，支持分页）; 每 30 秒内最多请求 30 次; 支持港股、A股正股及基金; 港股和A股各返回独立数据表，字段结构不同 |
| `get_corporate_actions_dividends` | `uv run python skills/futuapi/scripts/quote/get_corporate_actions_dividends.py <CODE> [--json]` | 获取股票的分红派息记录; 每 30 秒内最多请求 30 次; 支持正股及基金 |
| `get_corporate_actions_stock_splits` | `uv run python skills/futuapi/scripts/quote/get_corporate_actions_stock_splits.py <CODE> [options] [--json]` | 获取股票的拆合股历史记录（港股有额外字段），支持分页; 每 30 秒内最多请求 30 次; 支持港股、美股正股及基金 |

### derivatives-reference (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_future_info` | `uv run python skills/futuapi/scripts/quote/get_future_info.py HK.MCHmain HK.MCH2501 [--json]` | 获取期货合约的详细信息; 每 30 秒内最多请求 60 次; 每次最多传入 200 个代码 |
| `get_referencestock_list` | `uv run python skills/futuapi/scripts/quote/get_referencestock_list.py HK.00700 WARRANT [--json]` | 获取正股关联的窝轮、期货等数据; 每 30 秒内最多请求 60 次 |

### fund-holdings (3)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_ark_active_transaction` | `uv run python skills/futuapi/scripts/quote/get_ark_active_transaction.py [--holding-type INCREASE] [--cycle ONE_DAY] [--sort-field CHANGE_AMOUNT] [--sort-dir 0] [--count 50] [--json]` | 获取 ARK 主动交易聚合数据，支持自动分页; 每 30 秒内最多请求 60 次 |
| `get_ark_fund_holding` | `uv run python skills/futuapi/scripts/quote/get_ark_fund_holding.py [--holding-type POSITION] [--cycle FIVE_DAY] [--sort-field SHARES] [--sort-dir 0] [--count 20] [--json]` | 获取 ARK 基金持仓数据，支持自动分页; 每 30 秒内最多请求 60 次 |
| `get_ark_stock_dynamic` | `uv run python skills/futuapi/scripts/quote/get_ark_stock_dynamic.py --code US.TSLA [--json]` | 获取指定股票的 ARK 交易动态数据; 每 30 秒内最多请求 60 次 |

### fundamentals-financials (4)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_financials_earnings_price_history` | `uv run python skills/futuapi/scripts/quote/get_financials_earnings_price_history.py <CODE> [--json]` | 查询个股历次财报周期中财报当日的股价历史数据，含财报元信息、预期波动率及 IV Crush 分析; 每 30 秒内最多请求 30 次; 市场限制：支持港股、美股正股 |
| `get_financials_earnings_price_move` | `uv run python skills/futuapi/scripts/quote/get_financials_earnings_price_move.py <CODE> [options] [--json]` | 获取指定股票在多个财报周期内、财报公布日前后各交易日的价格表现数据; 每 30 秒内最多请求 30 次; 市场限制：支持港股、美股正股 |
| `get_financials_revenue_breakdown` | `uv run python skills/futuapi/scripts/quote/get_financials_revenue_breakdown.py <CODE> [options] [--json]` | 获取指定股票的主营构成数据，返回产品、行业、地区、业务各维度数据; 每 30 秒内最多请求 30 次; 支持正股及基金 |
| `get_financials_statements` | `uv run python skills/futuapi/scripts/quote/get_financials_statements.py <CODE> [options] [--json]` | 获取指定股票的财务报表（利润表/资产负债表/现金流量表/关键指标）; 每 30 秒内最多请求 30 次; 支持正股及基金 |

### historical-market-data (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_rehab` | `uv run python skills/futuapi/scripts/quote/get_rehab.py HK.00700 [--json]` | 获取股票的复权因子列表; 每 30 秒内最多请求 60 次 |
| `request_history_kline` | `uv run python skills/futuapi/scripts/quote/get_kline.py <CODE> --ktype <KTYPE> --start <YYYY-MM-DD> --end <YYYY-MM-DD> [--num <N>] [--json]` | 获取股票的 K 线（蜡烛图）数据，支持实时和历史数据; 实时 K 线：最多获取最近 1000 根，需先订阅; 历史 K 线：每 30 秒内最多请求 60 次；分 K 最近 8 年，日 K 最近 … |

### industrial-chain (5)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_industrial_chain_by_plate` | `uv run python skills/futuapi/scripts/quote/get_industrial_chain_by_plate.py --plate-id 123 [--json]` | 根据板块 ID 获取关联的产业链列表; 每 30 秒内最多请求 60 次 |
| `get_industrial_chain_detail` | `uv run python skills/futuapi/scripts/quote/get_industrial_chain_detail.py --chain-id 123 [--json]` | 根据产业链 ID 获取产业链详情（上中下游结构）; 每 30 秒内最多请求 60 次 |
| `get_industrial_chain_list` | `uv run python skills/futuapi/scripts/quote/get_industrial_chain_list.py --market HK [--keyword 芯片] [--count 20] [--json]` | 获取指定市场的产业链列表，支持关键字搜索和自动分页; 每 30 秒内最多请求 60 次 |
| `get_industrial_plate_info` | `uv run python skills/futuapi/scripts/quote/get_industrial_plate_info.py --plate-id 123 [--json]` | 根据板块 ID 获取产业板块详细信息; 每 30 秒内最多请求 60 次 |
| `get_industrial_plate_stock` | `uv run python skills/futuapi/scripts/quote/get_industrial_plate_stock.py --plate-id 123 [--chain-id 456] [--markets HK,US] [--sort-field MARKET_VAL] [--ascend] [--count 50] [--json]` | 获取产业板块内的成分股列表，支持按市场筛选、排序和自动分页; 每 30 秒内最多请求 60 次 |

### insiders (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_insider_holder_list` | `uv run python skills/futuapi/scripts/quote/get_insider_holder_list.py <CODE> [options] [--json]` | 获取美股股票内部人（高管/董事/大股东）的持股情况列表，同时返回内部人统计摘要; 每 30 秒内最多请求 30 次; 支持美股正股及基金; 首页额外返回内部人统计摘要（总人数/增持数/减持数），续页无此摘要 |
| `get_insider_trade_list` | `uv run python skills/futuapi/scripts/quote/get_insider_trade_list.py <CODE> [options] [--json]` | 获取美股股票内部人（高管/董事/大股东）的交易记录列表，支持按持有人过滤和分页续拉; 每 30 秒内最多请求 30 次; 支持美股正股及基金 |

### institutions (5)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_institution_distribution` | `uv run python skills/futuapi/scripts/quote/get_institution_distribution.py --market US --institution-id 123 [--json]` | 获取指定机构的持仓行业分布数据; 每 30 秒内最多请求 60 次 |
| `get_institution_holding_change` | `uv run python skills/futuapi/scripts/quote/get_institution_holding_change.py --market US --institution-id 123 [--change-type NEW] [--sort-field CHANGE_PCT] [--sort-dir 0] [--count 20] [--json]` | 获取指定机构的持仓变动明细，支持变动类型筛选、排序和自动分页; 每 30 秒内最多请求 60 次 |
| `get_institution_holding_list` | `uv run python skills/futuapi/scripts/quote/get_institution_holding_list.py --market US --institution-id 123 [--change-type INCREASE] [--sort-field HOLDING_VALUE] [--sort-dir 0] [--count 20] [--keyword TSLA] [--json]` | 获取指定机构的持股列表，支持变动类型筛选、排序、关键词搜索和自动分页; 每 30 秒内最多请求 60 次 |
| `get_institution_list` | `uv run python skills/futuapi/scripts/quote/get_institution_list.py --market US [--sort-field POSITION_VALUE] [--sort-dir 0] [--count 20] [--name 桥水] [--json]` | 获取指定市场的机构列表，支持排序、模糊搜索和自动分页; 每 30 秒内最多请求 60 次 |
| `get_institution_profile` | `uv run python skills/futuapi/scripts/quote/get_institution_profile.py --market US --institution-id 123 [--json]` | 根据机构 ID 获取机构详细概况; 每 30 秒内最多请求 60 次 |

### macro (4)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_fed_watch_dot_plot` | `uv run python skills/futuapi/scripts/quote/get_fed_watch_dot_plot.py [--json]` | 获取美联储点阵图数据（各委员利率预测投票）; 每 30 秒内最多请求 60 次 |
| `get_fed_watch_target_rate` | `uv run python skills/futuapi/scripts/quote/get_fed_watch_target_rate.py [--json]` | 获取 CME FedWatch 各次会议对应的目标利率区间概率; 每 30 秒内最多请求 60 次 |
| `get_macro_indicator_history` | `uv run python skills/futuapi/scripts/quote/get_macro_indicator_history.py --indicator-id 123 [--time 2026-06-01] [--max-count 100] [--json]` | 根据指标 ID 获取宏观指标历史数据; 每 30 秒内最多请求 60 次 |
| `get_macro_indicator_list` | `uv run python skills/futuapi/scripts/quote/get_macro_indicator_list.py --region US [--json]` | 获取指定国家/地区的宏观指标列表; 每 30 秒内最多请求 60 次 |

### market-breadth (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_heat_map_data` | `uv run python skills/futuapi/scripts/quote/get_heat_map_data.py --market US [--sort-field CHANGE_RATE] [--ascend] [--count 30] [--plate-type INDUSTRY] [--json]` | 获取指定市场的板块热力图数据，支持排序、板块类型筛选和自动分页; 每 30 秒内最多请求 60 次 |
| `get_rise_fall_distribution` | `uv run python skills/futuapi/scripts/quote/get_rise_fall_distribution.py [--security HK.BK1001] [--market HK] [--json]` | 获取指定板块或市场的涨跌分布数据; 每 30 秒内最多请求 60 次 |

### market-calendar (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_ipo_list` | `uv run python skills/futuapi/scripts/quote/get_ipo_list.py HK [--json]` | 获取指定市场的 IPO 信息列表; 每 30 秒内最多请求 60 次 |
| `request_trading_days` | `uv run python skills/futuapi/scripts/quote/get_trading_days.py US --start 2024-01-01 --end 2024-01-31 [--json]` | 获取指定市场的交易日列表; 每 30 秒内最多请求 60 次 |

### market-classification (3)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_owner_plate` | `uv run python skills/futuapi/scripts/quote/get_owner_plate.py HK.00700 US.AAPL [--json]` | 查询指定股票所属的所有板块; 每 30 秒内最多请求 10 次; 每次股票代码上限 200 个; 仅支持正股和指数 |
| `get_plate_list` | `uv run python skills/futuapi/scripts/quote/get_plate_list.py --market HK --type CONCEPT --keyword 科技 [--json]` | 获取指定市场的板块列表（行业/概念/地区），支持关键词过滤; 每 30 秒内最多请求 10 次 |
| `get_plate_stock` | `uv run python skills/futuapi/scripts/quote/get_plate_stock.py HK.BK1910 [--json]` | 获取指定板块的成分股列表，支持板块代码或内置别名; 每 30 秒内最多请求 10 次 |

### market-state (1)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_market_state` | `uv run python skills/futuapi/scripts/quote/get_market_state.py HK.00700 US.AAPL [--json]` | 查询指定股票所属市场的交易状态（开盘/收盘/盘前盘后等）; 每 30 秒内最多请求 10 次; 每次股票代码上限 400 个 |

### news (1)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_search_news` | `uv run python skills/futuapi/scripts/quote/get_search_news.py space [--max-count 10] [--news-sub-type ALL] [--json]` | 按关键词搜索新闻、公告、评级等资讯; 每 30 秒内最多请求 10 次 |

### opend-state (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_global_state` | `uv run python skills/futuapi/scripts/quote/get_global_state.py [--json]` | 获取 OpenD 全局状态信息，包括各市场状态、服务器版本、登录状态等 |
| `get_history_kl_quota` | `uv run python skills/futuapi/scripts/quote/get_history_kl_quota.py [--json]` | 查询历史 K 线额度使用情况; 每 30 秒内最多请求 60 次 |

### options (22)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_option_chain` | `uv run python skills/futuapi/scripts/quote/get_option_chain.py HK.00700 --start 2026-06-01 --end 2026-06-30 [--json]` | 获取指定正股的期权链数据; 每 30 秒内最多请求 60 次; **start ~ end 时间跨度不能超过 30 天**，否则返回错误码 -1 "获取期权链接口，请… |
| `get_option_chain` | `uv run python skills/futuapi/scripts/quote/resolve_option_code.py --underlying US.JPM --expiry 2026-03-20 --strike 267.50 --type CALL [--json]` | 将用户输入的期权描述解析并通过期权链接口查找对应的富途期权代码; 每 30 秒内最多请求 60 次 |
| `get_option_earnings_screener` | `uv run python skills/futuapi/scripts/quote/get_option_earnings_screener.py --market US_SECURITY --sort-type EARNINGS_DATE --count 50 [--json]` | 获取即将发布财报的期权标的列表，返回标的波动率数据、历史财报 IV Crush、股价变动及市场预期等信息; 市场仅支持 US_SECURITY 和 HK_SECURITY; count 范围 [1, 500]，默认 50; 支持 17 种排序字段… |
| `get_option_event` | `uv run python skills/futuapi/scripts/quote/get_option_event.py --market US_SECURITY --count 50 [--json]` | 查询指定期权市场的异动列表，支持多维度筛选（标的、期权类型、成交方向、希腊值等）和排序; count 范围 [1, 300]; 支持 25+ 种筛选因子 |
| `get_option_event_alert` | `uv run python skills/futuapi/scripts/quote/get_option_event_alert.py [--count 50] [--json]` | 查询当前账户已配置的期权异动提醒列表，支持分页获取; count 范围 [1, 500]，默认 200 |
| `get_option_exercise_probability` | `uv run python skills/futuapi/scripts/quote/get_option_exercise_probability.py <CODE> [--json]` | 获取指定期权合约的历史行权概率数据，按时间从大到小排序; 每 30 秒内最多请求 30 次; 仅支持期权合约代码 |
| `get_option_expiration_date` | `uv run python skills/futuapi/scripts/quote/get_option_expiration_date.py HK.00700 [--json]` | 获取指定正股的期权到期日列表; 每 30 秒内最多请求 60 次 |
| `get_option_market_statistic` | `uv run python skills/futuapi/scripts/quote/get_option_market_statistic.py --market US_SECURITY --data-type VOLUME --begin 2024-01-01 --end 2024-06-01 [--json]` | 获取期权市场统计数据（成交量/持仓量），按交易日粒度返回看涨、看跌及合计值，支持分页拉取; begin_time 与 end_time 跨度不超过一年；不传时默认取近一年数据; 分页通过 page_req_key 实现，自动翻页拉… |
| `get_option_quote` | `uv run python skills/futuapi/scripts/quote/get_option_quote.py '[{"code":"HK.TCH260522P330000","action":"BUY","quantity":1.0},{"code":"HK.TCH260522C330000","action":"BUY","quantity":1.0}]' [--json]` | 根据组合腿列表获取期权实时快照行情（最新价、Greeks 等；不含组合级 bid1/ask1）; 每 30 秒内最多请求 30 次 |
| `get_option_rank` | `uv run python skills/futuapi/scripts/quote/get_option_rank.py --market US_SECURITY --sort-type VOLUME --count 20 [--json]` | 获取期权合约排行，按指定维度对单个期权合约进行排名，支持分页拉取和多维度筛选; count 范围 [1, 200]; 支持 10 种排序类型 + 18 种筛选因子（标的级+期权级） |
| `get_option_screen` | `uv run python skills/futuapi/scripts/quote/get_option_screen.py --markets US_STOCK HK_STOCK --page-count 50 [--json]` | 筛选期权（get_option_screen）— 协议号 3253; OptIndicator.PREMIUM(2021)：仅支持 sort / retrieve；作为 filter 会报错 |
| `get_option_seller_screener` | `uv run python skills/futuapi/scripts/quote/get_option_seller_screener.py --market US_SECURITY --seller-type COVERED_CALL --sort-type ANNUALIZED_RETURN [--json]` | 获取期权卖方筛选列表，支持 Covered Call 和 Cash Secured Put 两种策略，可按多维度筛选与排序; 支持 4 种排序字段 + 26 种筛选因子（标的级13种+期权级13种）; 无分页 |
| `get_option_strategy` | `uv run python skills/futuapi/scripts/quote/get_option_strategy.py HK.00700 STRADDLE 2026-05-22 [--json]` | 按期权策略类型查询组合腿对应的期权链数据; 每 30 秒内最多请求 30 次 |
| `get_option_strategy_analysis` | `uv run python skills/futuapi/scripts/quote/get_option_strategy_analysis.py '[{"code":"HK.TCH260522P330000","action":"BUY","quantity":1.0},{"code":"HK.TCH260522C330000","action":"BUY","quantity":1.0}]' [--json]` | 对自定义或多腿期权组合进行损益分析；返回组合级 bid1/ask1（摆盘价）、最大盈亏、盈亏平衡点等; 每 30 秒内最多请求 30 次 |
| `get_option_strategy_spread` | `uv run python skills/futuapi/scripts/quote/get_option_strategy_spread.py HK.00700 STRANGLE 2026-05-22 [--json]` | 获取指定期权策略在当前标的、到期日条件下可用的有效价差列表; 每 30 秒内最多请求 30 次; option_strategy 仅支持 SPREAD / STRANGLE / COLLAR / BU… |
| `get_option_underlying_his_statistic` | `uv run python skills/futuapi/scripts/quote/get_option_underlying_his_statistic.py US.AAPL --begin 2025-01-01 --end 2025-06-01 [--json]` | 获取期权标的历史统计数据，按交易日返回该标的对应期权的成交量、持仓量及 Put/Call 比率时间序列; begin_time 与 end_time 跨度最多 364 天; 持仓量数据有 T-1 日延迟; 分页通过 page_req_key 实现 |
| `get_option_underlying_his_volatility` | `uv run python skills/futuapi/scripts/quote/get_option_underlying_his_volatility.py US.AAPL --begin 2025-01-01 --end 2025-06-01 [--json]` | 获取期权标的历史波动率数据，按交易日返回隐含波动率（IV）与历史波动率（HV）的时间序列; begin_time 与 end_time 跨度最多 364 天; 分页通过 page_req_key 实现 |
| `get_option_underlying_overview` | `uv run python skills/futuapi/scripts/quote/get_option_underlying_overview.py US.AAPL US.TSLA US.NVDA [--json]` | 批量获取期权标的总览数据，包含成交量、持仓量、IV 及多周期 HV 等核心指标的最新快照; code_list 最多 500 个标的; 快照接口，返回当前最新数据; 持仓量数据有 T-1 日延迟 |
| `get_option_underlying_rank` | `uv run python skills/futuapi/scripts/quote/get_option_underlying_rank.py --market US_SECURITY --sort-type VOLUME --count 20 [--json]` | 获取期权热门标的排行，按指定维度对期权标的（正股/ETF/指数）进行排名，支持多维度筛选与分页; count 范围 [1, 200]; 支持 13 种排序字段 + 13 种筛选因子 |
| `get_option_volatility` | `uv run python skills/futuapi/scripts/quote/get_option_volatility.py <CODE> [options] [--json]` | 获取期权波动率; 每 30 秒内最多请求 30 次; 仅支持期权合约代码 |
| `get_option_zero_dte_contract` | `uv run python skills/futuapi/scripts/quote/get_option_zero_dte_contract.py --owner US.TSLA --chain-info chain.json [--json]` | 获取末日期权合约列表，返回指定标的在指定行权日的 0DTE 期权合约详情，包含希腊值、盈亏平衡点及盈利概率等; chain_info 必须来自 get_option_zero_dte_screener 的返回结果; 支持 4 种排序字段 + 15 种… |
| `get_option_zero_dte_screener` | `uv run python skills/futuapi/scripts/quote/get_option_zero_dte_screener.py --market US_SECURITY --sort-type VOLUME --count 20 [--json]` | 获取末日期权标的筛选列表，返回当日到期（0DTE）期权对应的标的股票信息; count 范围 [1, 500]，默认 50; 支持 5 种排序字段 + 10 种筛选因子 |

### prediction-market (13)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `filter_competition` | `uv run python skills/futuapi/scripts/quote/filter_competition.py --category Sports [--tag Baseball] [--json]` | 按一级分类（category）与二级分类（tag）获取可用赛事名称列表与玩法全集，无需订阅; 功能：按一级分类（category）与二级分类（tag）获取可用赛事名称列表与玩法全集，无需订阅 |
| `get_event_contract` | `uv run python skills/futuapi/scripts/quote/get_event_contract.py EC.KXUFCVICROUND-26JUL11SAIPIM.EVENT [--count 20] [--next-page KEY] [--json]` | 按 Event 代码获取合约（Contract）列表，含合约类型、时间、状态、结果、交易属性等，无需订阅; 功能：按 Event 代码获取合约（Contract）列表，含合约类型、时间、状态、结果、交易属性等，无需订阅 |
| `get_event_contract_category` | `uv run python skills/futuapi/scripts/quote/get_event_contract_category.py [--category Sports] [--json]` | 获取预测市场一级分类及其下属二级分类（tags），无需订阅; 功能：获取预测市场一级分类及其下属二级分类（tags），无需订阅 |
| `get_event_contract_event_list` | `uv run python skills/futuapi/scripts/quote/get_event_contract_event_list.py EC.KXUFCVICROUND.SERIES [--count 20] [--status EVENT_ACTIVE] [--next-page KEY] [--json]` | 按 Series 代码获取 Event 列表，支持按状态过滤与分页，无需订阅; 功能：按 Series 代码获取 Event 列表，支持按状态过滤与分页，无需订阅 |
| `get_event_contract_kline` | `uv run python skills/futuapi/scripts/quote/get_event_contract_kline.py EC.KXODIMATCH-26JUL140600INDENG-IND --ktype K_DAY --pre-side YES [--kline-source ORDER_BOOK_YES] [--max-count 10] [--no-auto-subscribe] [--json]` | 获取预测市场实时 K 线（合约级成交价 K 线或 YES 子合约摆盘 K 线），需先订阅对应 K 线类型; ktype 仅支持 K_1M/K_5M/K_60M/K_DAY，其余报错; 查询前必须先订阅对应 K 线类型，否则报错"请求获取事件合约K… |
| `get_event_contract_milestone_list` | `uv run python skills/futuapi/scripts/quote/get_event_contract_milestone_list.py [--category Sports] [--competition "FIFA World Cup"] [--related-event EC.xxx] [--count 20] [--next-page KEY] [--json]` | 获取赛事类预测市场的重要时间节点（如某场比赛），支持分类/赛事/关联事件过滤与分页，无需订阅; 功能：获取赛事类预测市场的重要时间节点（如某场比赛），支持分类/赛事/关联事件过滤与分页，无需订阅 |
| `get_event_contract_order_book` | `uv run python skills/futuapi/scripts/quote/get_event_contract_order_book.py EC.KXODIMATCH-26JUL140600INDENG-IND [--num 5] [--no-auto-subscribe] [--json]` | 获取预测市场 YES/NO 双向多档买卖盘，需先订阅 ORDER_BOOK 类型; 查询前必须先订阅 SubType.ORDER_BOOK，否则报错"请求获取事件合约摆盘接口前，请先订阅OrderBook数据"; num … |
| `get_event_contract_series_list` | `uv run python skills/futuapi/scripts/quote/get_event_contract_series_list.py --category Sports [--tag Football] [--json]` | 按 category/tag 获取 Series 列表（Series 是一组相关 Event 的集合），无需订阅; 功能：按 category/tag 获取 Series 列表（Series 是一组相关 Event 的集合），无需订阅 |
| `get_event_contract_snapshot` | `uv run python skills/futuapi/scripts/quote/get_event_contract_snapshot.py EC.KXODIMATCH-26JUL140600INDENG-IND --json` | 批量获取预测市场实时快照（最新价、累计成交量、YES/NO 买卖盘、持仓量等），无需订阅; 功能：批量获取预测市场实时快照（最新价、累计成交量、YES/NO 买卖盘、持仓量等），无需订阅 |
| `get_event_contract_ticker` | `uv run python skills/futuapi/scripts/quote/get_event_contract_ticker.py EC.KXODIMATCH-26JUL140600INDENG-IND [--count 30] [--no-auto-subscribe] [--json]` | 获取预测市场实时逐笔成交数据（YES/NO 成交价、成交量、成交方向、逐笔序号），需先订阅 TICKER 类型; 查询前必须先订阅 SubType.TICKER，否则报错"请求获取事件合约逐笔接口前，请先订阅Ticker数据"; count 默认 30… |
| `get_valid_combo_list` | `uv run python skills/futuapi/scripts/quote/get_valid_combo_list.py [--category Sports] [--count 20] [--next-page KEY] [--json]` | 获取可组合的事件列表，返回每个可组合事件下的可组合合约列表及 MVC 标的（询价需透传），无需订阅; 功能：获取可组合的事件列表，返回每个可组合事件下的可组合合约列表及 MVC 标的（询价需透传），无需订阅 |
| `request_combo_quotes` | `uv run python skills/futuapi/scripts/quote/request_combo_quotes.py '[{"code":"EC.xxx-FRA","trd_side":"BUY","qty_ratio":1,"pred_side":"YES"},{"code":"EC.xxx-ENG","trd_side":"BUY","qty_ratio":1,"pred_side":"YES"}]' --mvc …` | 提交用户组合的合约腿（ComboLeg 列表）与 MVC 标的，获取组合报价（bid/ask）与报价 ID（下单用），无需订阅; 功能：提交用户组合的合约腿（ComboLeg 列表）与 MVC 标的，获取组合报价（bid/ask）与报价 ID（下单用），无需订阅 |
| `request_history_event_contract_kline` | `uv run python skills/futuapi/scripts/quote/request_history_event_contract_kline.py EC.KXNFLAFCCHAMP-27-CIN --start 2026-07-05 --end 2026-07-09 --pre-side YES --ktype K_DAY [--max-count 10] [--page-req-key KEY] [--json]` | 拉取预测市场历史 K 线，无需先下载历史数据，也无需订阅对应 K 线类型；自动处理分页; ktype 仅支持 K_1M/K_5M/K_60M/K_DAY; 历史 K 线无需订阅，走历史 K 线额度；单包最大 1000 根，max… |

### quote-entitlements (1)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_user_info` | `uv run python skills/futuapi/scripts/quote/get_user_info.py [--json]` | 查询当前用户的行情权限等级、订阅额度等信息; 无特殊限频 |

### quote-reference (1)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_top_ten_buy_sell_brokers` | `uv run python skills/futuapi/scripts/quote/get_top_ten_buy_sell_brokers.py <CODE> [options] [--json]` | 获取指定港股的十大净买入和净卖出经纪商列表（实时或历史）; 每 30 秒内最多请求 30 次; 支持港股正股及基金; days_before=0 返回实时数据（含均价/总量/总额），days_bef… |

### quote-snapshot (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_market_snapshot` | `uv run python skills/futuapi/scripts/quote/get_snapshot.py US.AAPL HK.00700 [--json]` | 获取指定股票的快照数据（最新价、开高低收、成交量等），无需订阅; 每 30 秒内最多请求 60 次; 每次请求股票代码上限 400 个; 港股 BMP 权限下，单次请求香港证券快照数量上限 20 个; 港… |
| `get_market_snapshot` | `uv run python skills/futuapi/scripts/quote/get_stock_info.py US.AAPL,HK.00700 [--json]` | 获取指定股票的基本信息（名称、每手数量、证券类型、上市日期等）; 每 30 秒内最多请求 10 次; 每次最多返回 200 个 |

### rankings (9)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_dividend_rank` | `uv run python skills/futuapi/scripts/quote/get_dividend_rank.py --market US --rank-type HIGH_YIELD [--count 10] [--sort-field DIVIDEND_YIELD_TTM] [--config filters.json] [--json]` | 获取指定市场的股息排行数据; 每 30 秒内最多请求 60 次 |
| `get_earnings_beat_rank` | `uv run python skills/futuapi/scripts/quote/get_earnings_beat_rank.py --market US --beat-type EPS [--count 30] [--term ALL] [--sort-field BEAT_RATIO] [--config filters.json] [--json]` | 获取指定市场的盈利超预期排名数据; 每 30 秒内最多请求 60 次 |
| `get_high_dividend_soe_rank` | `uv run python skills/futuapi/scripts/quote/get_high_dividend_soe_rank.py [--sort-field MARKET_CAP] [--sort-dir 0] [--count 10] [--offset 0] [--config filters.json] [--json]` | 获取破净高股息国央企排行数据（仅港股市场）; 每 30 秒内最多请求 60 次 |
| `get_hot_list` | `uv run python skills/futuapi/scripts/quote/get_hot_list.py --market US [--sort-field AVERAGE_HEAT] [--sort-dir 0] [--count 10] [--offset 0] [--config filters.json] [--json]` | 获取指定市场的热议榜数据，包含交易热度、搜索热度、新闻热度等; 每 30 秒内最多请求 60 次 |
| `get_period_change_rank` | `uv run python skills/futuapi/scripts/quote/get_period_change_rank.py --market US [--period FIVE_MIN] [--sort-dir 0] [--count 10] [--offset 0] [--config filters.json] [--json]` | 获取指定市场、指定时间区间的涨跌幅排行数据; 每 30 秒内最多请求 60 次 |
| `get_top_movers_rank` | `uv run python skills/futuapi/scripts/quote/get_top_movers_rank.py --market US [--sort-dir 0] [--count 10] [--offset 0] [--config filters.json] [--json]` | 获取指定市场的领涨或领跌排行榜数据; 每 30 秒内最多请求 60 次 |
| `get_us_after_hours_rank` | `uv run python skills/futuapi/scripts/quote/get_us_after_hours_rank.py [--sort-dir 0] [--count 10] [--offset 0] [--config filters.json] [--json]` | 获取美股盘后榜，按指定排序方向返回盘后交易排行数据，支持多维度筛选; 30秒内最多60次 |
| `get_us_overnight_rank` | `uv run python skills/futuapi/scripts/quote/get_us_overnight_rank.py [--sort-dir 0] [--count 10] [--offset 0] [--config filters.json] [--json]` | 获取美股夜盘榜，按指定排序方向返回夜盘交易排行数据，支持多维度筛选; 30秒内最多60次 |
| `get_us_pre_market_rank` | `uv run python skills/futuapi/scripts/quote/get_us_pre_market_rank.py [--sort-dir 0] [--count 10] [--offset 0] [--config filters.json] [--json]` | 获取美股盘前榜，按指定排序方向返回盘前交易排行数据，支持多维度筛选; 30秒内最多60次 |

### reminders-read-only (1)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_price_reminder` | `uv run python skills/futuapi/scripts/quote/get_price_reminder.py [--json]` | 获取已设置的到价提醒列表; 每 30 秒内最多请求 60 次 |

### research-ratings (4)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_rating_change` | `uv run python skills/futuapi/scripts/quote/get_rating_change.py --market US [--change-type UPGRADE] [--count 10] [--json]` | 获取美股评级变动数据，支持按变动类型筛选和自动分页; 每 30 秒内最多请求 60 次 |
| `get_research_analyst_consensus` | `uv run python skills/futuapi/scripts/quote/get_research_analyst_consensus.py <CODE> [--json]` | 获取指定股票近3个月的分析师综合评级、目标价区间及各档评级占比; 每 30 秒内最多请求 30 次; 支持正股及 REIT |
| `get_research_morningstar_report` | `uv run python skills/futuapi/scripts/quote/get_research_morningstar_report.py <CODE> [--json]` | 获取指定股票的晨星研究报告，含星级评分、公允价值、护城河、财务健康、分析师观点等; 每 30 秒内最多请求 30 次; 支持正股及 REIT |
| `get_research_rating_summary` | `uv run python skills/futuapi/scripts/quote/get_research_rating_summary.py <CODE> [options] [--json]` | 获取指定股票的机构或分析师评级汇总列表，或指定机构/分析师的评级详情; 每 30 秒内最多请求 30 次; 支持美股正股及 REIT |

### screening (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_stock_filter` | `uv run python skills/futuapi/scripts/quote/get_stock_filter.py --market HK --min-price 10 --max-price 100 [--json]` | 根据价格、市值、PE、涨跌幅等条件筛选股票; 港股 BMP 权限不支持; 每 30 秒内最多请求 10 次; 每页最多返回 200 个结果 |
| `get_stock_screen` | `uv run python skills/futuapi/scripts/quote/get_stock_screen.py --config config.json [--page-from 0] [--page-count 200] [--json]` | 筛选正股 V2（get_stock_screen）— 协议号 3252; 港股 BMP 权限不支持; 每页最多 200，分页用 page_from / page_count; 港股仅 Q1 + ANNUAL，Q2… |

### search (1)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_search_quote` | `uv run python skills/futuapi/scripts/quote/get_search_quote.py aapl [--max-count 10] [--json]` | 按关键词搜索股票、ETF、板块等行情标的; 每 30 秒内最多请求 10 次 |

### shareholders (4)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_shareholders_holder_detail` | `uv run python skills/futuapi/scripts/quote/get_shareholders_holder_detail.py <CODE> [options] [--json]` | 获取股票某一持股类型下的持有人明细列表，支持按类型、排序列、报告期过滤; 每 30 秒内最多请求 30 次; 支持港股、美股正股及基金; 支持分页，默认每页 10 条；分页标识为字符串类型 |
| `get_shareholders_holding_changes` | `uv run python skills/futuapi/scripts/quote/get_shareholders_holding_changes.py <CODE> [options] [--json]` | 获取股票持股人的变动记录（增持/减持/新进/清仓等）; 每 30 秒内最多请求 30 次; 支持港股、美股正股及基金; 支持分页，默认每页 10 条，最多 50 条 |
| `get_shareholders_institutional` | `uv run python skills/futuapi/scripts/quote/get_shareholders_institutional.py <CODE> [options] [--json]` | 获取股票的机构持股人数及持股量历史（支持分页）; 每 30 秒内最多请求 30 次; 支持港股、美股正股及基金 |
| `get_shareholders_overview` | `uv run python skills/futuapi/scripts/quote/get_shareholders_overview.py <CODE> [options] [--json]` | 一次请求同时返回指定股票的主要股东（main_holder）和持股类型（holder_type）两组数据; 每 30 秒内最多请求 30 次; 支持港股、美股正股及基金; period_id 为 0 或不传时，同一次响应中额外返回可用报告期列表（… |

### short-selling (3)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_daily_short_volume` | `uv run python skills/futuapi/scripts/quote/get_daily_short_volume.py <CODE> [options] [--json]` | 获取美股或港股每日卖空成交量、比例、价格等历史数据，支持分页续拉; 每 30 秒内最多请求 30 次; 支持港股、美股正股及基金 |
| `get_short_interest` | `uv run python skills/futuapi/scripts/quote/get_short_interest.py <CODE> [options] [--json]` | 获取美股或港股指定标的的空头持仓历史记录，包括卖空股数、卖空比例、回补天数、收盘价等数据（支持分页）; 每 30 秒内最多请求 30 次; 支持港股、美股正股及基金; 单次最多返回 50 条，默认 10 条 |
| `get_short_selling_rank` | `uv run python skills/futuapi/scripts/quote/get_short_selling_rank.py [--market US] [--sort-field SHORT_NUMBER_CHANGE] [--sort-dir 0] [--count 10] [--offset 0] [--plates US.BK2024] [--json]` | 获取指定市场的卖空异动排行数据; 每 30 秒内最多请求 60 次 |

### subscription-state (1)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `query_subscription` | `uv run python skills/futuapi/scripts/subscribe/query_subscription.py [--json]` | 查询当前已订阅的股票和数据类型; 无特殊限频 |

### technical-indicators (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_indicator_list` | `uv run python skills/futuapi/scripts/quote/get_indicator_list.py [--search SUB] [--lang 0\|1\|2] [--mode 0\|1] [--json]` | 列出所有已加载指标条目，每个 entry 可同时含 MyLang 与 Python 两版， |
| `request_indicator_calc_async` | `uv run python skills/futuapi/scripts/quote/get_indicator_calc_result.py --short-name MA --lang 1 --kl-file E:/OpenD/Output/test_cache_kl_HK_00700_day_100.json --param 0=5 [--json]` | 用本地缓存 K 线发起指标计算请求（Qot_RequestIndicatorCalc，3260）； |

### valuation (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_valuation_detail` | `uv run python skills/futuapi/scripts/quote/get_valuation_detail.py <CODE> [options] [--json]` | 获取指定个股或指数的估值详情，包含走势、市场分布、行业分布及盈利/营收增速四个聚合模块；个股返回全部模块，指数仅返回走势和市场分布; 每 30 秒内最多请求 30 次; 支持正股、基金及指数; PB 估值类型无盈利增速模块；指数无排名、均值、中位数字段 |
| `get_valuation_plate_stock_list` | `uv run python skills/futuapi/scripts/quote/get_valuation_plate_stock_list.py <CODE> [options] [--json]` | 获取板块或指数成分股的估值列表，包含估值、预测估值、历史分位、市值等；指数首次请求还返回所属板块列表; 每 30 秒内最多请求 30 次; 支持板块和指数；不支持个股; 指数作为入参时，首次请求额外返回所属板块列表（plate_list） |

### warrants (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_warrant` | `uv run python skills/futuapi/scripts/quote/get_warrant.py HK.00700 [--json]` | 获取指定正股的窝轮/牛熊证列表; 每 30 秒内最多请求 60 次 |
| `get_warrant_screen` | `uv run python skills/futuapi/scripts/quote/get_warrant_screen.py --market <MARKET> [options] [--json]` | 筛选窝轮 V2（get_warrant_screen）— 协议号 3254; 必传 warrant_market：HK=1、SG=4、MY=15; only_count=True 时返回的 DataFrame 为空，… |

### watchlists-read-only (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_user_security` | `uv run python skills/futuapi/scripts/quote/get_user_security.py "我的自选" [--json]` | 获取指定分组的自选股列表; 每 30 秒内最多请求 60 次 |
| `get_user_security_group` | `uv run python skills/futuapi/scripts/quote/get_user_security_group.py [--json]` | 获取用户的自选股分组列表; 每 30 秒内最多请求 60 次 |

## Futu OpenD 请求/返回样例

代表性只读请求 **5** 个：成功 **5**，失败 **0**。每行均为独立 JSON。

```jsonl
{"category":"quote-snapshot","request":"uv run python skills/futuapi/scripts/quote/get_snapshot.py US.AAPL --json","status":"success","response":{"data":{"row_count":1,"records":[{"code":"US.AAPL","name":"苹果","last_price":"319.97","open":"328.305","high":"328.93","low":"317.86","prev_close":"328.21","volume":"39606884","turnover":"12721009726.0","bid":"320.01"}]}},"error":null}
{"category":"historical-market-data","request":"uv run python skills/futuapi/scripts/quote/get_kline.py US.AAPL --ktype 1d --start 2026-08-24 --end 2026-08-28 --num 5 --max-page 1 --json","status":"success","response":{"data":{"row_count":5,"records":[{"time":"2026-08-24 00:00:00","open":"311.47","high":"313.36","low":"309.97","close":"310.34","volume":"34673582","turnover":"10793882889.0"},{"time":"2026-08-25 00:00:00","open":"310.79","high":"313.59","low":"308.21","close":"309.9","volume":"25869807","turnover":"8015823875.0"}]},"code":"US.AAPL","ktype":"1d","source":"history"},"error":null}
{"category":"fundamentals-financials","request":"uv run python skills/futuapi/scripts/quote/get_financials_statements.py US.AAPL --statement-type 4 --num 1 --json","status":"success","response":{"data":{"next_key":"1782489601,2026_3","structure_list":{"row_count":29,"records":[{"summary":"2 keys"},{"summary":"2 keys"}]},"report_list":{"row_count":1,"records":[{"summary":"10 keys"}]}},"code":"US.AAPL"},"error":null}
{"category":"valuation","request":"uv run python skills/futuapi/scripts/quote/get_valuation_detail.py US.AAPL --valuation-type 1 --interval-type 3 --json","status":"success","response":{"data":{"valuation_type":"PE","last_update_time":1788677553,"last_update_time_str":"2026-09-06 02:52:33","trend":{"current_value":36.693,"average_value":35.881,"avg_minus_1_stddev":33.648,"avg_plus_1_stddev":38.113,"valuation_percentile":66.9322709,"forward_value":34.551,"historical_items":{"row_count":"251","records":{"summary":"3 items"}}},"market_distribution":{"sections":{"row_count":"5","records":{"summary":"3 items"}},"total":2977,"ranking":2254,"average_value":22.345,"median_value":19.701},"plate_distribution":{"plate":"US.LIST2075","plate_name":"消费电子产品","plate_average_value":36.691,"plate_ranking":3,"plate_stock_item_count":3,"stock_items":{"row_count":"19","records":{"summary":"3 items"}}},"profit_growth_rate":{"financial_ttm_multiple":1.361,"market_cap_multiple":1.753,"year_count":5,"conclusion_detailed":"轻微高估 : 过去5年，市值增长略快于盈利增长，反映市值增长部分源于市场溢价。需关注业绩能否达到预期，若不及预期则存在回调风险。","profit_data":{"row_count":"21","records":{"summary":"3 items"}}}},"code":"US.AAPL"},"error":null}
{"category":"opend-state","request":"uv run python skills/futuapi/scripts/quote/get_global_state.py --json","status":"success","response":{"data":{"market_sz":"ASHARE_AFTER_HOURS_END","market_us":"AFTER_HOURS_END","market_sh":"ASHARE_AFTER_HOURS_END","market_hk":"CLOSED","market_hkfuture":"NIGHT_END","market_usfuture":"FUTURE_CLOSE","market_sgfuture":"NIGHT_END","market_jpfuture":"NIGHT_END","market_sg":"CLOSED","market_my":"CLOSED"}},"error":null}
```

## AKShare

共 **1090** 条目录记录；分类：`article` 7、`bank` 1、`bond` 44、`cal` 3、`currency` 5、`dc` 3、`energy` 8、`event` 2、`fund` 90、`futures` 83、`futures_derivative` 1、`fx` 11、`hf` 1、`index` 94、`interest_rate` 14、`macro` 215、`nlp` 2、`option` 46、`others` 34、`qdii` 3、`qhkc_web` 8、`reits` 1、`spot` 15、`stock` 388、`stock_feature` 6、`stock_fundamental` 4、`tool` 1。

### article (7)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `article_epu_index` | `import akshare as ak; ak.article_epu_index(symbol='China')` | 国家或地区的经济政策不确定性(EPU)数据; 单次返回某个具体国家或地区的所有月度经济政策不确定性数据 |
| `article_ff_crr` | `import akshare as ak; ak.article_ff_crr()` | 获取 Current Research Returns 多因子数据；更多信息请访问目标地址; 单次返回所有历史数据 |
| `article_oman_rv` | `import akshare as ak; ak.article_oman_rv(symbol='FTSE', index='rk_th2')` | 获取 Oxford-Man 已实现波动率数据; 单次返回某个指数具体指标的所有历史数据 |
| `article_oman_rv_short` | `import akshare as ak; ak.article_oman_rv_short()` |  |
| `article_rlab_rv` | `import akshare as ak; ak.article_rlab_rv(symbol='39693')` | 获取 Risk-Lab 已实现波动率数据; 单次返回某个指数所有历史数据 |
| `fred_md` | `import akshare as ak; ak.fred_md()` |  |
| `fred_qd` | `import akshare as ak; ak.fred_qd()` |  |

### bank (1)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `bank_fjcf_table_detail` | `import akshare as ak; ak.bank_fjcf_table_detail(page=5, item='分局本级')` | 首页-政务信息-行政处罚-银保监分局本级-XXXX行政处罚信息公开表，是信息公开表不是处罚决定书书; 单次返回银保监分局本级行政处罚中的指定页数的所有表格数据 |

### bond (44)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `bond_available_index_cbond` | `import akshare as ak; ak.bond_available_index_cbond()` | 中国债券信息网-中债指数-中债指数族系当中，非指定期限部分的可选指数 |
| `bond_buy_back_hist_em` | `import akshare as ak; ak.bond_buy_back_hist_em(symbol='204001')` | 东方财富网-行情中心-债券市场-质押式回购-历史数据; 单次返回所有历史行情数据 |
| `bond_cash_summary_sse` | `import akshare as ak; ak.bond_cash_summary_sse(date='20210111')` | 上登债券信息网-市场数据-市场统计-市场概览-债券现券市场概览; 单次返回指定交易日的债券现券市场概览数据 |
| `bond_cb_adj_logs_jsl` | `import akshare as ak; ak.bond_cb_adj_logs_jsl(symbol='128013')` | 集思录-单个可转债的转股价格-调整记录; 返回当前时刻该可转债的所有转股价格调整记录 |
| `bond_cb_index_jsl` | `import akshare as ak; ak.bond_cb_index_jsl()` | 可转债-集思录可转债等权指数; 单次返回所有历史数据数据 |
| `bond_cb_jsl` | `import akshare as ak; ak.bond_cb_jsl(cookie='您的集思录 cookie')` | 集思录可转债实时数据，包含行情数据（涨跌幅，成交量和换手率等）及可转债基本信息（转股价，溢价率和到期收益率等）; 单次返回当前交易时刻的所有数据 |
| `bond_cb_profile_sina` | `import akshare as ak; ak.bond_cb_profile_sina(symbol='sz128039')` | 新浪财经-债券-可转债-详情资料; 单次返回指定 symbol 的可转债-详情资料数据 |
| `bond_cb_redeem_jsl` | `import akshare as ak; ak.bond_cb_redeem_jsl()` | 集思录可转债-强赎; 单次返回所有数据 |
| `bond_cb_summary_sina` | `import akshare as ak; ak.bond_cb_summary_sina(symbol='sh155255')` | 新浪财经-债券-可转债-债券概况; 单次返回指定 symbol 的可转债-债券概况数据 |
| `bond_china_close_return` | `import akshare as ak; ak.bond_china_close_return(symbol='国债', period='1', start_date='20231101', end_date='20231101')` | 收盘收益率曲线历史数据，该接口只能获取近 3 个月的数据，且每次获取的数据不超过 1 个月 |
| `bond_china_close_return_map` | `import akshare as ak; ak.bond_china_close_return_map()` |  |
| `bond_china_yield` | `import akshare as ak; ak.bond_china_yield(start_date='20210201', end_date='20220201')` | 中国债券信息网-国债及其他债券收益率曲线; 单次返回所有指定日期间 start_date 到 end_date 需要小于一年的所有数据 |
| `bond_composite_index_cbond` | `import akshare as ak; ak.bond_composite_index_cbond(indicator='财富', period='总值')` | 中国债券信息网-中债指数-中债指数族系-分类指数-按待偿期限 |
| `bond_corporate_issue_cninfo` | `import akshare as ak; ak.bond_corporate_issue_cninfo(start_date='20210911', end_date='20211110')` | 巨潮资讯-数据中心-专题统计-债券报表-债券发行-企业债发行 |
| `bond_cov_comparison` | `import akshare as ak; ak.bond_cov_comparison()` | 东方财富网-行情中心-债券市场-可转债比价表; 单次返回当前交易时刻的所有可转债比价数据 |
| `bond_cov_issue_cninfo` | `import akshare as ak; ak.bond_cov_issue_cninfo(start_date='20210913', end_date='20211112')` | 巨潮资讯-数据中心-专题统计-债券报表-债券发行-可转债发行 |
| `bond_cov_stock_issue_cninfo` | `import akshare as ak; ak.bond_cov_stock_issue_cninfo()` | 巨潮资讯-数据中心-专题统计-债券报表-债券发行-可转债转股 |
| `bond_deal_summary_sse` | `import akshare as ak; ak.bond_deal_summary_sse(date='20210104')` | 上登债券信息网-市场数据-市场统计-市场概览-债券成交概览; 单次返回指定交易日的债券成交概览数据 |
| `bond_debt_nafmii` | `import akshare as ak; ak.bond_debt_nafmii(page='2')` | 中国银行间市场交易商协会-非金融企业债务融资工具注册信息系统; 单次获取指定 page 页面数据的 50 条数据 |
| `bond_gb_us_sina` | `import akshare as ak; ak.bond_gb_us_sina(symbol='美国10年期国债')` | 新浪财经-债券-美国国债收益率行情数据; 返回最近 1000 个交易日的数据 |
| `bond_gb_zh_sina` | `import akshare as ak; ak.bond_gb_zh_sina(symbol='中国10年期国债')` | 新浪财经-债券-中国国债收益率行情数据; 返回最近 1000 个交易日的数据 |
| `bond_index_general_cbond` | `import akshare as ak; ak.bond_index_general_cbond(index_category='新综合指数', indicator='全价', period='总值')` | 中国债券信息网-中债指数-中债指数族系 |
| `bond_info_cm` | `import akshare as ak; ak.bond_info_cm(bond_name='', bond_code='', bond_issue='', bond_type='短期融资券', coupon_type='零息式', issue_year='2019', grade='A-1', underwriter='重庆农村商业银行股份有限公司')` | 中国外汇交易中心暨全国银行间同业拆借中心-数据-债券信息-信息查询 |
| `bond_info_cm_query` | `import akshare as ak; ak.bond_info_cm_query()` |  |
| `bond_info_detail_cm` | `import akshare as ak; ak.bond_info_detail_cm(symbol='19万林投资CP001')` | 中国外汇交易中心暨全国银行间同业拆借中心-数据-债券信息-信息查询-债券详情 |
| `bond_local_government_issue_cninfo` | `import akshare as ak; ak.bond_local_government_issue_cninfo(start_date='20210911', end_date='20211110')` | 巨潮资讯-数据中心-专题统计-债券报表-债券发行-地方债发行 |
| `bond_new_composite_index_cbond` | `import akshare as ak; ak.bond_new_composite_index_cbond(indicator='财富', period='总值')` | 中国债券信息网-中债指数-中债指数族系-总指数-综合类指数-中债-新综合指数 |
| `bond_sh_buy_back_em` | `import akshare as ak; ak.bond_sh_buy_back_em()` | 东方财富网-行情中心-债券市场-上证质押式回购; 单次返回所有行情数据 |
| `bond_spot_deal` | `import akshare as ak; ak.bond_spot_deal()` | 中国外汇交易中心暨全国银行间同业拆借中心-市场数据-市场行情-债券市场行情-现券市场成交行情; 单次返回所有即期数据 |
| `bond_spot_quote` | `import akshare as ak; ak.bond_spot_quote()` | 中国外汇交易中心暨全国银行间同业拆借中心-市场数据-市场行情-债券市场行情-现券市场做市报价; 单次返回所有数据 |
| `bond_sz_buy_back_em` | `import akshare as ak; ak.bond_sz_buy_back_em()` | 东方财富网-行情中心-债券市场-深证质押式回购; 单次返回所有行情数据 |
| `bond_treasure_issue_cninfo` | `import akshare as ak; ak.bond_treasure_issue_cninfo(start_date='20210910', end_date='20211109')` | 巨潮资讯-数据中心-专题统计-债券报表-债券发行-国债发行 |
| `bond_treasury_index_cbond` | `import akshare as ak; ak.bond_treasury_index_cbond(indicator='财富', period='5Y')` | 中国债券信息网-中债指数-中债指数族系-总指数-综合类指数-中债-国债指数 |
| `bond_zh_cov` | `import akshare as ak; ak.bond_zh_cov()` | 东方财富网-数据中心-新股数据-可转债数据一览表; 单次返回当前交易时刻的所有可转债数据 |
| `bond_zh_cov_info` | `import akshare as ak; ak.bond_zh_cov_info(symbol='123121', indicator='基本信息')` | 东方财富网-数据中心-新股数据-可转债详情; 单次返回指定 symbol 的可转债详情数据 |
| `bond_zh_cov_info_ths` | `import akshare as ak; ak.bond_zh_cov_info_ths()` | 同花顺-数据中心-可转债; 单次返回所有数据 |
| `bond_zh_cov_value_analysis` | `import akshare as ak; ak.bond_zh_cov_value_analysis(symbol='113527')` | 东方财富网-行情中心-新股数据-可转债数据-可转债价值分析; 单次返回所有可转债价值分析数据 |
| `bond_zh_hs_cov_daily` | `import akshare as ak; ak.bond_zh_hs_cov_daily(symbol='sz128039')` | 新浪财经-历史行情数据，日频率更新，新上的标的需要次日更新数据; 单次返回具体某个沪深可转债的所有历史行情数据 |
| `bond_zh_hs_cov_min` | `import akshare as ak; ak.bond_zh_hs_cov_min(symbol='sz123124', period='1', adjust='', start_date='1979-09-01 09:32:00', end_date='2222-01-01 09:32:00')` | 东方财富网-可转债-分时行情; 单次返回指定可转债、指定频率、复权调整和时间区间的分时数据，其中 1 分钟数据只返回近 1 个交易日数据且不复权；其余 period 只能… |
| `bond_zh_hs_cov_pre_min` | `import akshare as ak; ak.bond_zh_hs_cov_pre_min(symbol='sh113570')` | 东方财富网-可转债-分时行情-盘前分时; 单次返回指定可转债在最近一个交易日的盘前分时数据 |
| `bond_zh_hs_cov_spot` | `import akshare as ak; ak.bond_zh_hs_cov_spot()` | 新浪财经-沪深可转债数据; 单次返回所有沪深可转债的实时行情数据 |
| `bond_zh_hs_daily` | `import akshare as ak; ak.bond_zh_hs_daily(symbol='sh010107')` | 新浪财经-债券-沪深债券-历史行情数据，历史数据按日频率更新; 单次返回具体某个沪深转债的所有历史行情数据 |
| `bond_zh_hs_spot` | `import akshare as ak; ak.bond_zh_hs_spot(start_page='1', end_page='5')` | 新浪财经-债券-沪深债券-实时行情数据; 单次返回所有沪深债券的实时行情数据 |
| `bond_zh_us_rate` | `import akshare as ak; ak.bond_zh_us_rate(start_date='19901219')` | 东方财富网-数据中心-经济数据-中美国债收益率历史数据; 返回 start_date 开始后的所有交易日的数据；数据从 19901219 开始 |

### cal (3)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `rv_from_futures_zh_minute_sina` | `import akshare as ak; ak.rv_from_futures_zh_minute_sina()` |  |
| `rv_from_stock_zh_a_hist_min_em` | `import akshare as ak; ak.rv_from_stock_zh_a_hist_min_em()` |  |
| `volatility_yz_rv` | `import akshare as ak; ak.volatility_yz_rv(data="<data>")` |  |

### currency (5)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `currency_convert` | `import akshare as ak; ak.currency_convert(base='USD', to='CNY', amount='10000', api_key='此处输入 API')` | 指定货币对指定货币数量的转换后价格; 单次返回指定货币对的转换后价格 |
| `currency_currencies` | `import akshare as ak; ak.currency_currencies(c_type='fiat', api_key='此处输入 API')` | 所有货币的基础信息; 单次返回指定所有货币基础信息 |
| `currency_history` | `import akshare as ak; ak.currency_history(base='USD', date='2023-02-03', symbols='', api_key='此处输入 API')` | 货币报价历史数据; 单次返回指定货币在指定交易日的报价历史数据-免费账号每月限量访问 5000 次 |
| `currency_latest` | `import akshare as ak; ak.currency_latest(base='USD', symbols='', api_key='此处输入 API')` | 货币报价最新数据; 单次返回指定货币的最新报价数据 |
| `currency_time_series` | `import akshare as ak; ak.currency_time_series(base='USD', start_date='2023-02-03', end_date='2023-03-04', symbols='', api_key='此处输入 API')` | 货币报价时间序列数据; 单次返回指定货币在指定交易日到另一指定交易日的报价数据 |

### dc (3)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `crypto_bitcoin_cme` | `import akshare as ak; ak.crypto_bitcoin_cme(date='20230830')` | 芝加哥商业交易所-比特币成交量报告; 单次返回指定交易日的比特币成交量报告数据 |
| `crypto_bitcoin_hold_report` | `import akshare as ak; ak.crypto_bitcoin_hold_report()` | 比特币持仓报告; 单次返回当前时点的比特币持仓报告数据 |
| `crypto_js_spot` | `import akshare as ak; ak.crypto_js_spot()` | 加密货币实时行情; 单次返回主流加密货币当前时点行情数据 |

### energy (8)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `energy_carbon_bj` | `import akshare as ak; ak.energy_carbon_bj()` | 北京市碳排放权电子交易平台-北京市碳排放权公开交易行情; 全部历史数据 |
| `energy_carbon_domestic` | `import akshare as ak; ak.energy_carbon_domestic(symbol='湖北')` | 碳交易网-行情信息; 返回指定 symbol 的所有历史数据 |
| `energy_carbon_eu` | `import akshare as ak; ak.energy_carbon_eu()` | 深圳碳排放交易所-国际碳情; 返回从 2018-03-13 至 2020-04-29 的所有历史数据 |
| `energy_carbon_gz` | `import akshare as ak; ak.energy_carbon_gz()` | 广州碳排放权交易中心-行情信息; 该接口返回从 2013-12-19 至今的所有历史数据 |
| `energy_carbon_hb` | `import akshare as ak; ak.energy_carbon_hb()` | 湖北碳排放权交易中心-碳排放权交易数据; 返回从 2014-04-02 至今的所有历史数据 |
| `energy_carbon_sz` | `import akshare as ak; ak.energy_carbon_sz()` | 深圳碳排放交易所-国内碳情; 全部历史数据 |
| `energy_oil_detail` | `import akshare as ak; ak.energy_oil_detail(date='20240118')` | 东方财富-数据中心-中国油价-地区油价; 返回指定调价日的全国各地区的油价的历史数据 |
| `energy_oil_hist` | `import akshare as ak; ak.energy_oil_hist()` | 东方财富-数据中心-中国油价-汽柴油历史调价信息; 单次返回中国油价的所有历史数据 |

### event (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `migration_area_baidu` | `import akshare as ak; ak.migration_area_baidu(area='重庆市', indicator='move_in', date='20230922')` | 百度-百度地图慧眼-百度迁徙-迁入/迁出地数据接口; 单次返回前 100 个城市的数据 |
| `migration_scale_baidu` | `import akshare as ak; ak.migration_scale_baidu(area='广州市', indicator='move_in')` | 百度-百度地图慧眼-百度迁徙-迁徙规模; 单次返回所有迁徙规模数据 |

### fund (90)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `amac_aoin_info` | `import akshare as ak; ak.amac_aoin_info()` | 中国证券投资基金业协会-信息公示-基金产品公示-证券公司直投基金; 单次返回当前时刻所有历史数据 |
| `amac_fund_abs` | `import akshare as ak; ak.amac_fund_abs()` | 中国证券投资基金业协会-信息公示-产品公示-资产支持专项计划; 单次返回当前时刻所有历史数据 |
| `amac_fund_account_info` | `import akshare as ak; ak.amac_fund_account_info()` | 中国证券投资基金业协会-信息公示-基金产品公示-基金公司及子公司集合资管产品公示; 单次返回当前时刻所有历史数据 |
| `amac_fund_info` | `import akshare as ak; ak.amac_fund_info(start_page='1', end_page='100')` | 中国证券投资基金业协会-信息公示-基金产品公示-私募基金管理人基金产品; 单次返回指定页码之间的所有历史数据，其中与每页 100 条的目标网站对应；默认返回所有数据 |
| `amac_fund_sub_info` | `import akshare as ak; ak.amac_fund_sub_info()` | 中国证券投资基金业协会-信息公示-基金产品公示-证券公司私募投资基金; 单次返回当前时刻所有历史数据 |
| `amac_futures_info` | `import akshare as ak; ak.amac_futures_info()` | 中国证券投资基金业协会-信息公示-基金产品公示-期货公司集合资管产品公示; 单次返回当前时刻所有历史数据 |
| `amac_manager_cancelled_info` | `import akshare as ak; ak.amac_manager_cancelled_info()` | 中国证券投资基金业协会-信息公示-诚信信息-已注销私募基金管理人名单; 单次返回当前时刻所有历史数据 |
| `amac_manager_classify_info` | `import akshare as ak; ak.amac_manager_classify_info()` | 中国证券投资基金业协会-信息公示-私募基金管理人公示-私募基金管理人分类公示; 单次返回当前时刻所有历史数据 |
| `amac_manager_info` | `import akshare as ak; ak.amac_manager_info()` | 中国证券投资基金业协会-信息公示-私募基金管理人公示-私募基金管理人综合查询; 单次返回当前时刻所有历史数据 |
| `amac_member_info` | `import akshare as ak; ak.amac_member_info()` | 中国证券投资基金业协会-信息公示-会员信息-会员机构综合查询; 单次返回当前时刻所有历史数据 |
| `amac_member_sub_info` | `import akshare as ak; ak.amac_member_sub_info()` | 中国证券投资基金业协会-信息公示-私募基金管理人公示-证券公司私募基金子公司管理人信息公示; 单次返回当前时刻所有历史数据 |
| `amac_person_bond_org_list` | `import akshare as ak; ak.amac_person_bond_org_list()` | 中国证券投资基金业协会-信息公示-从业人员信息-债券投资交易相关人员公示; 单次返回当前时刻所有历史数据 |
| `amac_person_fund_org_list` | `import akshare as ak; ak.amac_person_fund_org_list(symbol='公募基金管理公司')` | 中国证券投资基金业协会-信息公示-从业人员信息-基金从业人员资格注册信息; 单次返回当前时刻所有历史数据 |
| `amac_securities_info` | `import akshare as ak; ak.amac_securities_info()` | 中国证券投资基金业协会-信息公示-基金产品公示-证券公司集合资管产品公示; 单次返回当前时刻所有历史数据 |
| `fund_announcement_dividend_em` | `import akshare as ak; ak.fund_announcement_dividend_em(symbol='000001')` | 东方财富网站-天天基金网-基金档案-基金公告-分红配送; 返回所有历史数据 |
| `fund_announcement_personnel_em` | `import akshare as ak; ak.fund_announcement_personnel_em(symbol='000001')` | 东方财富网站-天天基金网-基金档案-基金公告-人事调整; 返回所有历史数据 |
| `fund_announcement_report_em` | `import akshare as ak; ak.fund_announcement_report_em(symbol='000001')` | 东方财富网站-天天基金网-基金档案-基金公告-定期报告; 返回所有历史数据 |
| `fund_aum_em` | `import akshare as ak; ak.fund_aum_em()` | 天天基金网-基金数据-基金规模; 单次返回所有基金规模数据 |
| `fund_aum_hist_em` | `import akshare as ak; ak.fund_aum_hist_em(year='2023')` | 天天基金网-基金数据-基金公司历年管理规模排行列表; 单次返回所有基金公司历年管理规模排行列表数据 |
| `fund_aum_trend_em` | `import akshare as ak; ak.fund_aum_trend_em()` | 天天基金网-基金数据-市场全部基金规模走势; 单次返回所有市场全部基金规模走势数据 |
| `fund_balance_position_lg` | `import akshare as ak; ak.fund_balance_position_lg()` | 乐咕乐股-基金仓位-平衡混合型基金仓位; 返回所有历史数据 |
| `fund_cf_em` | `import akshare as ak; ak.fund_cf_em(year='2025')` | 天天基金网-基金数据-分红送配-基金拆分; 单次返回所有历史数据 |
| `fund_etf_category_sina` | `import akshare as ak; ak.fund_etf_category_sina(symbol='封闭式基金')` | 新浪财经-基金列表及行情数据; 单次返回指定 symbol 基金的所有数据 |
| `fund_etf_category_ths` | `import akshare as ak; ak.fund_etf_category_ths(symbol='ETF', date='20240620')` | 同花顺理财-基金数据-每日净值-实时行情; 单次返回指定 date 和 symbol 的所有数据 |
| `fund_etf_dividend_sina` | `import akshare as ak; ak.fund_etf_dividend_sina(symbol='sh510050')` | 新浪财经-基金-ETF 基金-累计分红; 单次返回所有历史数据 |
| `fund_etf_fund_daily_em` | `import akshare as ak; ak.fund_etf_fund_daily_em()` | 东方财富网站-天天基金网-基金数据-场内交易基金-实时数据，此接口数据每个交易日 **16:00～23:00**; 单次返回当前时刻所有数据 |
| `fund_etf_fund_info_em` | `import akshare as ak; ak.fund_etf_fund_info_em(fund='511280', start_date='20000101', end_date='20500101')` | 东方财富网站-天天基金网-基金数据-场内交易基金-历史净值数据; 单次返回当前时刻所有历史数据 |
| `fund_etf_hist_em` | `import akshare as ak; ak.fund_etf_hist_em(symbol='513500', period='daily', start_date='20000101', end_date='20230201', adjust='')` | 东方财富-ETF 行情；历史数据按日频率更新，当日收盘价请在收盘后获取; 单次返回指定 ETF、指定周期和指定日期间的历史行情日频率数据 |
| `fund_etf_hist_min_em` | `import akshare as ak; ak.fund_etf_hist_min_em(symbol='511220', period='1', adjust='', start_date='2024-03-20 09:30:00', end_date='2024-03-20 17:40:00')` | 东方财富-ETF 分时行情；该接口只能获取近期的分时数据，注意时间周期的设置; 单次返回指定 ETF、频率、复权调整和时间区间的分时数据，其中 1 分钟数据只返回近 5 个交易日数据且不复权 |
| `fund_etf_hist_sina` | `import akshare as ak; ak.fund_etf_hist_sina(symbol='sh510050')` | 新浪财经-基金行情的日频率行情数据; 单次返回指定基金的所有数据 |
| `fund_etf_scale_sse` | `import akshare as ak; ak.fund_etf_scale_sse(date='20250115')` | 上海证券交易所-产品-基金产品-ETF产品-ETF产品列表-基金规模; 单次返回指定日期的 ETF 基金份额数据 |
| `fund_etf_scale_szse` | `import akshare as ak; ak.fund_etf_scale_szse()` | 深圳证券交易所-基金产品-基金列表-ETF基金份额; 单次返回最近交易日的 ETF 基金份额数据 |
| `fund_etf_spot_em` | `import akshare as ak; ak.fund_etf_spot_em()` | 东方财富-ETF 实时行情; 单次返回所有数据 |
| `fund_etf_spot_ths` | `import akshare as ak; ak.fund_etf_spot_ths(date='20240620')` | 同花顺理财-基金数据-每日净值-ETF-实时行情; 单次返回指定 date 的所有数据 |
| `fund_exchange_rank_em` | `import akshare as ak; ak.fund_exchange_rank_em()` | 东方财富网-数据中心-场内交易基金排行榜; 单次返回当前时刻所有数据，每个交易日 17 点后更新 |
| `fund_fee_em` | `import akshare as ak; ak.fund_fee_em(symbol='015641', indicator='认购费率')` | 天天基金-基金档案-购买信息; 单次返回指定 symbol 的 indicator 数据 |
| `fund_fh_em` | `import akshare as ak; ak.fund_fh_em(year='2025')` | 天天基金网-基金数据-分红送配-基金分红; 单次返回所有历史数据 |
| `fund_fh_rank_em` | `import akshare as ak; ak.fund_fh_rank_em()` | 天天基金网-基金数据-分红送配-基金分红排行; 单次返回所有历史数据 |
| `fund_financial_fund_daily_em` | `import akshare as ak; ak.fund_financial_fund_daily_em()` | 东方财富网-天天基金网-基金数据-理财型基金-实时数据，此接口数据每个交易日 **16:00～23:00** 更新; 该接口由于目标网站未更新数据，暂时不能返回数据 |
| `fund_financial_fund_info_em` | `import akshare as ak; ak.fund_financial_fund_info_em(symbol='000134')` | 东方财富网站-天天基金网-基金数据-理财型基金收益-历史净值明细; 单次返回当前时刻所有历史数据 |
| `fund_graded_fund_daily_em` | `import akshare as ak; ak.fund_graded_fund_daily_em()` | 东方财富网-天天基金网-基金数据-分级基金-实时数据，此接口数据每个交易日 **16:00～23:00**; 单次返回当前时刻所有历史数据 |
| `fund_graded_fund_info_em` | `import akshare as ak; ak.fund_graded_fund_info_em(symbol='150232')` | 东方财富网站-天天基金网-基金数据-分级基金-历史数据; 单次返回当前时刻所有历史数据 |
| `fund_hk_fund_hist_em` | `import akshare as ak; ak.fund_hk_fund_hist_em(code='1002200683', symbol='历史净值明细')` | 东方财富网站-天天基金网-基金数据-香港基金-历史净值明细; 单次返回指定 code 和 symbol 所有历史数据 |
| `fund_hk_rank_em` | `import akshare as ak; ak.fund_hk_rank_em()` | 东方财富网-数据中心-基金排行-香港基金排行; 单次返回当前时刻所有数据 |
| `fund_hold_structure_em` | `import akshare as ak; ak.fund_hold_structure_em()` | 天天基金网-基金数据-规模份额-持有人结构; 返回所有持有人结构数据 |
| `fund_individual_achievement_xq` | `import akshare as ak; ak.fund_individual_achievement_xq(symbol='000001')` | 雪球基金-基金详情-基金业绩-详情; 单次返回单只基金业绩详情 |
| `fund_individual_analysis_xq` | `import akshare as ak; ak.fund_individual_analysis_xq(symbol='000001')` | 雪球基金-基金详情-数据分析; 返回单只基金历史表现分析数据 |
| `fund_individual_basic_info_xq` | `import akshare as ak; ak.fund_individual_basic_info_xq(symbol='000001')` | 雪球基金-基金详情; 单次返回单只基金基本信息 |
| `fund_individual_detail_hold_xq` | `import akshare as ak; ak.fund_individual_detail_hold_xq(symbol='002804', date='20231231')` | 雪球基金-基金详情-基金持仓-详情; 单次返回单只基金指定日期的持仓大类资产比例 |
| `fund_individual_detail_info_xq` | `import akshare as ak; ak.fund_individual_detail_info_xq(symbol='000001')` | 雪球基金-基金详情-基金交易规则; 单次返回单只基金基金交易规则 |
| `fund_individual_profit_probability_xq` | `import akshare as ak; ak.fund_individual_profit_probability_xq(symbol='000001')` | 雪球基金-基金详情-盈利概率；历史任意时点买入，持有满X时间，盈利概率，以及平均收益; 单次返回单只基金历史任意时点买入，持有满 X 时间，盈利概率，以及平均收益 |
| `fund_info_index_em` | `import akshare as ak; ak.fund_info_index_em(symbol='沪深指数', indicator='增强指数型')` | 东方财富网-天天基金网-基金数据-基金基本信息-指数型; 单次返回当前时刻所有历史数据 |
| `fund_info_ths` | `import akshare as ak; ak.fund_info_ths(symbol='161130')` | 同花顺-基金数据-基金基本信息; 单次返回指定基金的基本信息 |
| `fund_lcx_rank_em` | `import akshare as ak; ak.fund_lcx_rank_em()` | 东方财富网-数据中心-理财基金排行，每个交易日17点后更新，货币基金的单位净值均为 1.0000 元，最新一年期定存利率：1.50%; 由于目标网站没有数据，该接口暂时未能返回数据 |
| `fund_linghuo_position_lg` | `import akshare as ak; ak.fund_linghuo_position_lg()` | 乐咕乐股-基金仓位-灵活配置型基金仓位; 返回所有历史数据 |
| `fund_lof_hist_em` | `import akshare as ak; ak.fund_lof_hist_em(symbol='166009', period='daily', start_date='20000101', end_date='20230703', adjust='')` | 东方财富-LOF 行情；历史数据按日频率更新，当日收盘价请在收盘后获取; 单次返回指定 LOF、指定周期和指定日期间的历史行情日频率数据 |
| `fund_lof_hist_min_em` | `import akshare as ak; ak.fund_lof_hist_min_em(symbol='166009', period='1', adjust='', start_date='2024-03-20 09:30:00', end_date='2024-03-20 14:40:00')` | 东方财富-LOF 分时行情；该接口只能获取近期的分时数据，注意时间周期的设置; 单次返回指定 LOF、频率、复权调整和时间区间的分时数据，其中 1 分钟数据只返回近 5 个交易日数据且不复权 |
| `fund_lof_spot_em` | `import akshare as ak; ak.fund_lof_spot_em()` | 东方财富-LOF 实时行情; 单次返回所有数据 |
| `fund_manager_em` | `import akshare as ak; ak.fund_manager_em()` | 天天基金网-基金数据-基金经理大全; 单次返回所有基金经理数据 |
| `fund_money_fund_daily_em` | `import akshare as ak; ak.fund_money_fund_daily_em()` | 东方财富网-天天基金网-基金数据-货币型基金收益，此接口数据每个交易日 **16:00～23:00**; 单次返回当前时刻所有历史数据 |
| `fund_money_fund_info_em` | `import akshare as ak; ak.fund_money_fund_info_em(symbol='000009')` | 东方财富网-天天基金网-基金数据-货币型基金-历史净值; 单次返回当前时刻所有历史数据 |
| `fund_money_rank_em` | `import akshare as ak; ak.fund_money_rank_em()` | 东方财富网-数据中心-货币型基金排行; 单次返回当前时刻所有数据，每个交易日 17 点后更新，货币基金的单位净值均为 1.0000 元，最新一年期定存利率：1.50% |
| `fund_name_em` | `import akshare as ak; ak.fund_name_em()` | 东方财富网-天天基金网-基金数据-所有基金的基本信息数据; 单次返回当前时刻所有历史数据 |
| `fund_new_found_em` | `import akshare as ak; ak.fund_new_found_em()` | 天天基金网-基金数据-新发基金-新成立基金; 单次返回所有新发基金数据 |
| `fund_new_found_ths` | `import akshare as ak; ak.fund_new_found_ths(symbol='全部')` | 同花顺-基金数据-新发基金; 单次返回所有新发基金数据 |
| `fund_open_fund_daily_em` | `import akshare as ak; ak.fund_open_fund_daily_em()` | 东方财富网-天天基金网-基金数据，此接口在每个交易日 **16:00-23:00** 更新当日的最新开放式基金净值数据; 单次返回当前时刻所有历史数据 |
| `fund_open_fund_info_em` | `import akshare as ak; ak.fund_open_fund_info_em(symbol='710001', indicator='单位净值走势')` | 东方财富网-天天基金网-基金数据-具体基金信息; 单次返回当前时刻所有历史数据，在查询基金数据的时候注意基金前后端问题 |
| `fund_open_fund_rank_em` | `import akshare as ak; ak.fund_open_fund_rank_em(symbol='全部')` | 东方财富网-数据中心-开放式基金排行; 单次返回当前时刻所有数据 |
| `fund_overview_em` | `import akshare as ak; ak.fund_overview_em(symbol='015641')` | 天天基金-基金档案-基本概况; 单次返回指定 symbol 的数据 |
| `fund_portfolio_bond_hold_em` | `import akshare as ak; ak.fund_portfolio_bond_hold_em(symbol='000001', date='2023')` | 天天基金网-基金档案-投资组合-债券持仓; 单次返回指定 symbol 和 date 的所有持仓数据 |
| `fund_portfolio_change_em` | `import akshare as ak; ak.fund_portfolio_change_em(symbol='003567', indicator='累计买入', date='2023')` | 天天基金网-基金档案-投资组合-重大变动; 单次返回指定 symbol、indicator 和 date 的所有重大变动数据 |
| `fund_portfolio_hold_em` | `import akshare as ak; ak.fund_portfolio_hold_em(symbol='000001', date='2024')` | 天天基金网-基金档案-投资组合-基金持仓; 单次返回指定 symbol 和 date 的所有持仓数据 |
| `fund_portfolio_industry_allocation_em` | `import akshare as ak; ak.fund_portfolio_industry_allocation_em(symbol='000001', date='2023')` | 天天基金网-基金档案-投资组合-行业配置; 单次返回指定 symbol 和 date 的所有持仓数据 |
| `fund_purchase_em` | `import akshare as ak; ak.fund_purchase_em()` | 东方财富网站-天天基金网-基金数据-基金申购状态; 单次返回当前时刻所有历史数据 |
| `fund_rating_all` | `import akshare as ak; ak.fund_rating_all()` | 天天基金网-基金评级-基金评级总汇; 单次返回所有基金评级数据 |
| `fund_rating_ja` | `import akshare as ak; ak.fund_rating_ja(date='20200930')` | 天天基金网-基金评级-济安金信评级; 单次返回指定交易日的所有基金评级数据 |
| `fund_rating_sh` | `import akshare as ak; ak.fund_rating_sh(date='20230630')` | 天天基金网-基金评级-上海证券评级; 单次返回指定交易日的所有基金评级数据 |
| `fund_rating_zs` | `import akshare as ak; ak.fund_rating_zs(date='20230331')` | 天天基金网-基金评级-招商证券评级; 单次返回指定交易日的所有基金评级数据 |
| `fund_report_asset_allocation_cninfo` | `import akshare as ak; ak.fund_report_asset_allocation_cninfo()` | 巨潮资讯-数据中心-专题统计-基金报表-基金资产配置; 返回所有基金资产配置数据 |
| `fund_report_industry_allocation_cninfo` | `import akshare as ak; ak.fund_report_industry_allocation_cninfo(date='20210630')` | 巨潮资讯-数据中心-专题统计-基金报表-基金行业配置; 返回指定 date 的所有数据；date 从 2017 年开始 |
| `fund_report_stock_cninfo` | `import akshare as ak; ak.fund_report_stock_cninfo(date='20210630')` | 巨潮资讯-数据中心-专题统计-基金报表-基金重仓股; 返回指定 date 的所有数据；date 从 2017 年开始 |
| `fund_scale_change_em` | `import akshare as ak; ak.fund_scale_change_em()` | 天天基金网-基金数据-规模份额-规模变动; 返回所有规模变动数据 |
| `fund_scale_close_sina` | `import akshare as ak; ak.fund_scale_close_sina()` | 基金数据中心-基金规模-封闭式基金; 单次返回所有封闭式基金的基金规模数据 |
| `fund_scale_daily_szse` | `import akshare as ak; ak.fund_scale_daily_szse(start_date='20260401', end_date='20260402', symbol='ETF')` | 深圳证券交易所-基金产品-基金规模-日频数据; 单次返回指定日期区间和基金类别的基金规模数据；日期范围不能超过 6 个月，否则返回带表头的空 DataFrame |
| `fund_scale_open_sina` | `import akshare as ak; ak.fund_scale_open_sina(symbol='股票型基金')` | 基金数据中心-基金规模-开放式基金; 单次返回指定 symbol 的基金规模数据 |
| `fund_scale_structured_sina` | `import akshare as ak; ak.fund_scale_structured_sina()` | 基金数据中心-基金规模-分级子基金; 单次返回所有分级子基金的基金规模数据 |
| `fund_stock_position_lg` | `import akshare as ak; ak.fund_stock_position_lg()` | 乐咕乐股-基金仓位-股票型基金仓位; 返回所有历史数据 |
| `fund_value_estimation_em` | `import akshare as ak; ak.fund_value_estimation_em(symbol='混合型')` | 东方财富网-数据中心-净值估算; 单次返回当前交易日指定 symbol 的所有数据 |
| `reits_hist_em` | `import akshare as ak; ak.reits_hist_em(symbol='508097')` | 东方财富网-行情中心-REITs-沪深 REITs-历史行情; 单次返回指定 symbol 的历史行情数据 |
| `reits_realtime_em` | `import akshare as ak; ak.reits_realtime_em()` | 东方财富网-行情中心-REITs-沪深 REITs-实时行情; 单次返回所有 REITs 的实时行情数据 |

### futures (83)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `futures_comex_inventory` | `import akshare as ak; ak.futures_comex_inventory(symbol='黄金')` | 东方财富网-数据中心-期货期权-COMEX 库存数据; 单次返回指定 symbol 的所有历史数据 |
| `futures_comm_info` | `import akshare as ak; ak.futures_comm_info(symbol='所有')` | 九期网-期货手续费数据; 单次返回指定 symbol 的所有数据 |
| `futures_comm_js` | `import akshare as ak; ak.futures_comm_js(date='20260213')` | 金十财经-期货手续费数据; 单次返回指定日期的期货手续费数据 |
| `futures_contract_detail` | `import akshare as ak; ak.futures_contract_detail(symbol='V2001')` | 新浪财经-期货-期货合约详情数据; 单次返回指定 symbol 的合约详情数据 |
| `futures_contract_detail_em` | `import akshare as ak; ak.futures_contract_detail_em(symbol='v2603F')` | 东方财富-期货-期货合约详情数据; 单次返回指定 symbol 的合约详情数据 |
| `futures_contract_info_cffex` | `import akshare as ak; ak.futures_contract_info_cffex(date='20240228')` | 中国金融期货交易所-数据-交易参数; 单次返回指定 date 的期货合约信息数据 |
| `futures_contract_info_czce` | `import akshare as ak; ak.futures_contract_info_czce(date='20240228')` | 郑州商品交易所-交易数据-参考数据; 单次返回指定 date 的期货合约信息数据 |
| `futures_contract_info_dce` | `import akshare as ak; ak.futures_contract_info_dce()` | 大连商品交易所-数据中心-业务数据-交易参数-合约信息; 单次返回最近交易日的期货合约信息数据 |
| `futures_contract_info_gfex` | `import akshare as ak; ak.futures_contract_info_gfex()` | 广州期货交易所-业务/服务-合约信息; 单次返回最近交易日的期货合约信息数据 |
| `futures_contract_info_ine` | `import akshare as ak; ak.futures_contract_info_ine(date='20241129')` | 上海国际能源交易中心-业务指南-交易参数汇总（期货）; 单次返回指定 date 的期货合约信息数据 |
| `futures_contract_info_shfe` | `import akshare as ak; ak.futures_contract_info_shfe(date='20240513')` | 上海期货交易所-交易所服务-业务数据-交易参数汇总查询; 单次返回指定 date 的期货合约信息数据 |
| `futures_dce_position_rank` | `import akshare as ak; ak.futures_dce_position_rank(date='20200513')` | 大连商品交易所指定交易日的具体合约的持仓排名; 单次返回所有合约的持仓排名数据，返回以合约名字为键，具体排名数据为值的字典 |
| `futures_dce_position_rank_other` | `import akshare as ak; ak.futures_dce_position_rank_other()` |  |
| `futures_delivery_czce` | `import akshare as ak; ak.futures_delivery_czce(date='20210112')` | 郑州商品交易所-交割统计; 单次返回指定交易月份的交割统计数据 |
| `futures_delivery_dce` | `import akshare as ak; ak.futures_delivery_dce(date='202312')` | 大连商品交易所-交割统计; 单次返回指定交易月份的交割统计数据 |
| `futures_delivery_match_czce` | `import akshare as ak; ak.futures_delivery_match_czce(date='20210106')` | 郑州商品交易所-交割配对; 单次返回指定品种的的交割配对数据 |
| `futures_delivery_match_dce` | `import akshare as ak; ak.futures_delivery_match_dce(symbol='a')` | 大连商品交易所-交割配对; 单次返回指定品种的的交割配对数据 |
| `futures_delivery_shfe` | `import akshare as ak; ak.futures_delivery_shfe(date='202312')` | 上海期货交易所-交割统计; 单次返回指定交易月份的交割统计数据 |
| `futures_fees_info` | `import akshare as ak; ak.futures_fees_info()` | openctp 期货交易费用参照表; 单次返回所有数据 |
| `futures_foreign_commodity_realtime` | `import akshare as ak; ak.futures_foreign_commodity_realtime(symbol='CT,NID')` | 新浪财经-外盘商品期货数据; 单次返回当前交易日的订阅的所有期货品种的数据 |
| `futures_foreign_commodity_subscribe_exchange_symbol` | `import akshare as ak; ak.futures_foreign_commodity_subscribe_exchange_symbol()` |  |
| `futures_foreign_detail` | `import akshare as ak; ak.futures_foreign_detail(symbol='ZSD')` | 新浪财经-期货外盘期货合约详情; 单次返回指定品种的合约详情数据 |
| `futures_foreign_hist` | `import akshare as ak; ak.futures_foreign_hist(symbol='ZSD')` | 新浪财经-期货外盘历史行情数据; 单次返回指定品种的历史数据 |
| `futures_gfex_position_rank` | `import akshare as ak; ak.futures_gfex_position_rank(date='20231113')` | 广州期货交易所-日成交持仓排名; 单次返回所有合约的日成交持仓排名数据，返回以合约名字为键，具体排名数据为值的字典 |
| `futures_gfex_warehouse_receipt` | `import akshare as ak; ak.futures_gfex_warehouse_receipt(date='20240122')` | 广州期货交易所-行情数据-仓单日报; 单次返回当前交易日的所有仓单日报数据 |
| `futures_global_hist_em` | `import akshare as ak; ak.futures_global_hist_em(symbol='HG00Y')` | 东方财富网-行情中心-期货市场-国际期货-历史行情数据; 单次返回指定品种的历史数据 |
| `futures_global_spot_em` | `import akshare as ak; ak.futures_global_spot_em()` | 东方财富网-行情中心-期货市场-国际期货-实时行情数据; 单次返回所有期货品种的实时行情数据 |
| `futures_hist_daily_cffex` | `import akshare as ak; ak.futures_hist_daily_cffex()` |  |
| `futures_hist_em` | `import akshare as ak; ak.futures_hist_em(symbol='热卷主连', period='daily')` | 东方财富网-期货行情-行情数据；其中 weekly, monthly 获取的成交额和持仓量未经验证; 单次返回指定 symbol 的所有数据；只能获取当期合约； |
| `futures_hist_table_em` | `import akshare as ak; ak.futures_hist_table_em()` |  |
| `futures_hog_core` | `import akshare as ak; ak.futures_hog_core(symbol='外三元')` | 玄田数据-核心数据; 单次返回指定 symbol 的所有历史数据 |
| `futures_hog_cost` | `import akshare as ak; ak.futures_hog_cost(symbol='玉米')` | 玄田数据-成本维度; 单次返回指定 symbol 的所有历史数据 |
| `futures_hog_supply` | `import akshare as ak; ak.futures_hog_supply(symbol='猪肉批发价')` | 玄田数据-供应维度; 单次返回指定 symbol 的所有历史数据 |
| `futures_hold_pos_sina` | `import akshare as ak; ak.futures_hold_pos_sina(symbol='成交量', contract='OI2501', date='20241016')` | 新浪财经-期货-成交持仓; 单次返回指定合约的成交持仓数据 |
| `futures_hq_subscribe_exchange_symbol` | `import akshare as ak; ak.futures_hq_subscribe_exchange_symbol()` | 新浪财经-外盘商品期货品种代码表数据; 单次返回当前交易日的订阅的所有期货品种的品种代码表数据 |
| `futures_index_ccidx` | `import akshare as ak; ak.futures_index_ccidx(symbol='中证商品期货指数')` | 中证商品指数; 单次返回指定 symbol 的指数日频率数据 |
| `futures_inventory_99` | `import akshare as ak; ak.futures_inventory_99(symbol='豆一')` | 99 期货网-大宗商品库存数据; 单次返回指定 symbol 的具体品种的期货库存数据，仓单日报数据 |
| `futures_inventory_em` | `import akshare as ak; ak.futures_inventory_em(symbol='A')` | 东方财富网-期货数据-库存数据；近 60 个交易日的期货库存日频率数据; 返回指定交易所指定品种的期货库存数据，仓单日报数据 |
| `futures_main_sina` | `import akshare as ak; ak.futures_main_sina(symbol='V0', start_date='20200101', end_date='20220101')` | 新浪财经-期货-主力连续合约历史数据; 单次返回单个期货品种的主力连续合约的日频历史数据 |
| `futures_news_shmet` | `import akshare as ak; ak.futures_news_shmet(symbol='铜')` | 上海金属网-快讯; 指定 symbol 的数据 |
| `futures_rule` | `import akshare as ak; ak.futures_rule(date='20231205')` | 国泰君安期货-交易日历数据表; 单次返回指定交易日所有合约的交易日历数据 |
| `futures_settle` | `import akshare as ak; ak.futures_settle(date='20260119', market='INE')` | 提供各交易所的结算参数数据，包括保证金、手续费、涨跌停板等参数; 单次返回指定日期指定交易所的结算参数数据；暂不支持 DCE |
| `futures_settle_cffex` | `import akshare as ak; ak.futures_settle_cffex()` |  |
| `futures_settle_czce` | `import akshare as ak; ak.futures_settle_czce()` |  |
| `futures_settle_gfex` | `import akshare as ak; ak.futures_settle_gfex()` |  |
| `futures_settle_ine` | `import akshare as ak; ak.futures_settle_ine()` |  |
| `futures_settle_shfe` | `import akshare as ak; ak.futures_settle_shfe()` |  |
| `futures_settlement_price_sgx` | `import akshare as ak; ak.futures_settlement_price_sgx(date='20231108')` | 新加坡交易所-衍生品-历史数据-历史结算价格；数据于下个工作日新加坡时间下午 2 点起提供; 单次获取指定交易日前一日的所有期货品种的结算价数据；只能获取过去 60 个交易日内的数据；由于国内网络限制，请使用代理访问 |
| `futures_shfe_warehouse_receipt` | `import akshare as ak; ak.futures_shfe_warehouse_receipt(date='20200702')` | 提供上海期货交易所指定交割仓库期货仓单日报; 单次返回当前交易日的所有仓单日报数据 |
| `futures_spot_price` | `import akshare as ak; ak.futures_spot_price()` |  |
| `futures_spot_price_daily` | `import akshare as ak; ak.futures_spot_price_daily()` |  |
| `futures_spot_price_previous` | `import akshare as ak; ak.futures_spot_price_previous()` |  |
| `futures_spot_stock` | `import akshare as ak; ak.futures_spot_stock(symbol='能源')` | 东方财富网-数据中心-现货与股票; 单次返回指定 indicator 的所有数据 |
| `futures_spot_sys` | `import akshare as ak; ak.futures_spot_sys(symbol='铜', indicator='市场价格')` | 生意社-商品与期货-现期图; 单次返回指定品种的现期图数据 |
| `futures_stock_shfe_js` | `import akshare as ak; ak.futures_stock_shfe_js(date='20240419')` | 金十财经-上海期货交易所指定交割仓库库存周报; 单次返回指定 date 的库存周报数据 |
| `futures_symbol_mark` | `import akshare as ak; ak.futures_symbol_mark()` |  |
| `futures_to_spot_czce` | `import akshare as ak; ak.futures_to_spot_czce(date='20231228')` | 郑州商品交易所-期转现统计数据; 单次返回指定交易日的期转现统计数据 |
| `futures_to_spot_dce` | `import akshare as ak; ak.futures_to_spot_dce(date='202312')` | 大连商品交易所-期转现统计数据; 单次返回指定交易日的期转现统计数据 |
| `futures_to_spot_shfe` | `import akshare as ak; ak.futures_to_spot_shfe(date='202312')` | 上海期货交易所-期转现数据; 单次返回指定交易月份的期转现数据 |
| `futures_warehouse_receipt_czce` | `import akshare as ak; ak.futures_warehouse_receipt_czce(date='20200702')` | 郑州商品交易所-交易数据-仓单日报; 单次返回当前交易日的所有仓单日报数据 |
| `futures_warehouse_receipt_dce` | `import akshare as ak; ak.futures_warehouse_receipt_dce(date='20251027')` | 大连商品交易所-行情数据-统计数据-日统计-仓单日报; 单次返回当前交易日的所有仓单日报数据 |
| `futures_zh_daily_sina` | `import akshare as ak; ak.futures_zh_daily_sina(symbol='RB0')` | 新浪财经-期货-日频数据; 单次返回指定 symbol 的所有日频数据；期货连续合约为 品种代码+0，比如螺纹钢连续合约为 RB0; |
| `futures_zh_minute_sina` | `import akshare as ak; ak.futures_zh_minute_sina(symbol='RB0', period='1')` | 新浪财经-期货-分时数据; 单次返回指定 symbol 和 period 的分时数据 |
| `futures_zh_realtime` | `import akshare as ak; ak.futures_zh_realtime(symbol='白糖')` | 新浪财经-期货实时行情数据; 单次返回指定 symbol 的数据 |
| `futures_zh_spot` | `import akshare as ak; ak.futures_zh_spot(symbol='V2205', market='CF', adjust='0')` | 新浪财经-期货页面的实时行情数据; 单次返回当日可以订阅的所有期货品种数据；只能获取近期合约的数据 |
| `get_cffex_daily` | `import akshare as ak; ak.get_cffex_daily()` |  |
| `get_cffex_rank_table` | `import akshare as ak; ak.get_cffex_rank_table()` |  |
| `get_czce_daily` | `import akshare as ak; ak.get_czce_daily()` |  |
| `get_dce_daily` | `import akshare as ak; ak.get_dce_daily()` |  |
| `get_dce_rank_table` | `import akshare as ak; ak.get_dce_rank_table()` |  |
| `get_futures_daily` | `import akshare as ak; ak.get_futures_daily(start_date='20200701', end_date='20200716', market='DCE')` | 提供各交易所各品种的网站的历史行情数据，其中 20040625, 20070604, 20081226, 20090119 原网页数据缺失; 单次返回指定时间段指定交易所的所有期货品种历史数据 |
| `get_gfex_daily` | `import akshare as ak; ak.get_gfex_daily()` |  |
| `get_ine_daily` | `import akshare as ak; ak.get_ine_daily()` |  |
| `get_rank_sum` | `import akshare as ak; ak.get_rank_sum()` |  |
| `get_rank_sum_daily` | `import akshare as ak; ak.get_rank_sum_daily()` |  |
| `get_rank_table_czce` | `import akshare as ak; ak.get_rank_table_czce()` |  |
| `get_receipt` | `import akshare as ak; ak.get_receipt()` |  |
| `get_roll_yield` | `import akshare as ak; ak.get_roll_yield()` |  |
| `get_roll_yield_bar` | `import akshare as ak; ak.get_roll_yield_bar()` |  |
| `get_shfe_daily` | `import akshare as ak; ak.get_shfe_daily()` |  |
| `get_shfe_rank_table` | `import akshare as ak; ak.get_shfe_rank_table()` |  |
| `index_hog_spot_price` | `import akshare as ak; ak.index_hog_spot_price()` | 行情宝-生猪市场价格指数; 单次返回所有数据 |
| `match_main_contract` | `import akshare as ak; ak.match_main_contract()` |  |

### futures_derivative (1)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `futures_display_main_sina` | `import akshare as ak; ak.futures_display_main_sina()` |  |

### fx (11)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `currency_boc_safe` | `import akshare as ak; ak.currency_boc_safe()` | 外汇管理局-人民币汇率中间价; 单次返回所有历史数据 |
| `currency_boc_sina` | `import akshare as ak; ak.currency_boc_sina(symbol='美元', start_date='20230304', end_date='20231110')` | 新浪财经-中行人民币牌价历史数据; 单次返回指定日期的所有历史数据 |
| `currency_pair_map` | `import akshare as ak; ak.currency_pair_map(symbol='人民币')` | 指定币种的所有能够获取到的货币对信息，历史数据可以调用 **ak.currency_history()** 获取; 单次返回指定币种的所有能获取数据的货币对 |
| `forex_hist_em` | `import akshare as ak; ak.forex_hist_em(symbol='USDCNH')` | 东方财富网-行情中心-外汇市场-所有汇率-历史行情数据; 单次返回指定 symbol 的历史行情数据 |
| `forex_spot_em` | `import akshare as ak; ak.forex_spot_em()` | 东方财富网-行情中心-外汇市场-所有汇率-实时行情数据; 单次返回所有实时行情数据 |
| `fx_c_swap_cm` | `import akshare as ak; ak.fx_c_swap_cm()` | 中国外汇交易中心暨全国银行间同业拆借中心-基准-外汇市场-外汇掉期曲线-外汇掉期 C-Swap 定盘曲线; 单次返回所有行情数据 |
| `fx_pair_quote` | `import akshare as ak; ak.fx_pair_quote()` | 外币对即期报价; 单次返回当前时点最近更新的即时数据 |
| `fx_quote_baidu` | `import akshare as ak; ak.fx_quote_baidu(symbol='人民币')` | 百度股市通-外汇-行情榜单; 单次返回指定 symbol 当前时点的行情报价 |
| `fx_spot_quote` | `import akshare as ak; ak.fx_spot_quote()` | 人民币外汇即期报价; 单次返回实时行情数据 |
| `fx_swap_quote` | `import akshare as ak; ak.fx_swap_quote()` | 人民币外汇远掉报价; 单次返回实时行情数据 |
| `macro_fx_sentiment` | `import akshare as ak; ak.macro_fx_sentiment(start_date=test_date, end_date=test_date)` | 货币对-投机情绪报告; 单次返回指定日期所有品种的数据（所指定的日期必须在当前交易日之前的30个交易日内） |

### hf (1)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `hf_sp_500` | `import akshare as ak; ak.hf_sp_500(year='2017')` | 获取标普 500 指数的分钟数据，由于数据量比较大，需要等待，由于服务器在国外，建议使用代理访问 |

### index (94)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `drewry_wci_index` | `import akshare as ak; ak.drewry_wci_index(symbol='composite')` | Drewry 集装箱指数的数据; 返回指定 symbol 的数据 |
| `index_ai_cx` | `import akshare as ak; ak.index_ai_cx()` | 财新指数-AI策略指数; 该接口返回所有历史数据 |
| `index_all_cni` | `import akshare as ak; ak.index_all_cni()` | 国证指数-最近交易日的所有指数的代码和基本信息 |
| `index_analysis_daily_sw` | `import akshare as ak; ak.index_analysis_daily_sw(symbol='市场表征', start_date='20241025', end_date='20241025')` | 申万宏源研究-指数分析-日报表; 该接口返回指定参数的数据 |
| `index_analysis_monthly_sw` | `import akshare as ak; ak.index_analysis_monthly_sw(symbol='市场表征', date='20240930')` | 申万宏源研究-指数分析-月报表; 该接口返回指定参数的数据 |
| `index_analysis_week_month_sw` | `import akshare as ak; ak.index_analysis_week_month_sw()` |  |
| `index_analysis_weekly_sw` | `import akshare as ak; ak.index_analysis_weekly_sw(symbol='市场表征', date='20241025')` | 申万宏源研究-指数分析-周报表; 该接口返回指定参数的数据 |
| `index_awpr_cx` | `import akshare as ak; ak.index_awpr_cx()` | 财新指数-新经济入职工资溢价水平; 该接口返回所有历史数据 |
| `index_bei_cx` | `import akshare as ak; ak.index_bei_cx()` | 财新指数-基石经济指数; 该接口返回所有历史数据 |
| `index_bi_cx` | `import akshare as ak; ak.index_bi_cx()` | 财新指数-基础指数; 该接口返回所有历史数据 |
| `index_cci_cx` | `import akshare as ak; ak.index_cci_cx()` | 财新指数-大宗商品指数; 该接口返回所有历史数据 |
| `index_ci_cx` | `import akshare as ak; ak.index_ci_cx()` | 财新指数-资本投入指数; 该接口返回所有历史数据 |
| `index_code_id_map_em` | `import akshare as ak; ak.index_code_id_map_em()` |  |
| `index_component_sw` | `import akshare as ak; ak.index_component_sw(symbol='801001')` | 申万宏源研究-指数发布-指数详情-成分股; 该接口返回指定 symbol 的数据 |
| `index_csindex_all` | `import akshare as ak; ak.index_csindex_all()` |  |
| `index_dei_cx` | `import akshare as ak; ak.index_dei_cx()` | 财新指数-数字经济指数; 该接口返回所有历史数据 |
| `index_detail_cni` | `import akshare as ak; ak.index_detail_cni(symbol='399001')` | 国证指数-指数样本详情数据；20251125 开始只能获取近期的数据 |
| `index_detail_hist_adjust_cni` | `import akshare as ak; ak.index_detail_hist_adjust_cni(symbol='399005')` | 国证指数-样本详情-历史调样 |
| `index_detail_hist_cni` | `import akshare as ak; ak.index_detail_hist_cni(symbol='399005')` | 国证指数-历史样本数据，返回所有历史数据 |
| `index_eri` | `import akshare as ak; ak.index_eri(symbol='月度')` | 浙江省排污权交易指数的数据 |
| `index_fi_cx` | `import akshare as ak; ak.index_fi_cx()` | 财新指数-融合指数; 该接口返回所有历史数据 |
| `index_global_hist_em` | `import akshare as ak; ak.index_global_hist_em(symbol='美元指数')` | 东方财富网-行情中心-全球指数-历史行情数据 |
| `index_global_hist_sina` | `import akshare as ak; ak.index_global_hist_sina(symbol='瑞士股票指数')` | 新浪财经-行情中心-环球市场-历史行情; 单次返回最近的 1000 条数据 |
| `index_global_name_table` | `import akshare as ak; ak.index_global_name_table()` |  |
| `index_global_spot_em` | `import akshare as ak; ak.index_global_spot_em()` | 东方财富网-行情中心-全球指数-实时行情数据 |
| `index_hist_cni` | `import akshare as ak; ak.index_hist_cni(symbol='399005', start_date='20230114', end_date='20240114')` | 国证指数-具体指数的日频率行情数据 |
| `index_hist_fund_sw` | `import akshare as ak; ak.index_hist_fund_sw(symbol='807200', period='day')` | 申万宏源研究-申万指数-指数发布-基金指数-历史行情; 该接口返回指定 symbol 的数据 |
| `index_hist_sw` | `import akshare as ak; ak.index_hist_sw(symbol='801193', period='day')` | 申万宏源研究-指数发布-指数详情-指数历史数据; 该接口返回指定 symbol 和 period 的数据 |
| `index_ii_cx` | `import akshare as ak; ak.index_ii_cx()` | 财新指数-产业指数; 该接口返回所有历史数据 |
| `index_inner_quote_sugar_msweet` | `import akshare as ak; ak.index_inner_quote_sugar_msweet()` | 沐甜科技数据中心-配额内进口糖估算指数 |
| `index_kq_fashion` | `import akshare as ak; ak.index_kq_fashion(symbol='柯桥时尚指数')` | 指定 symbol 的柯桥时尚指数的所有数据 |
| `index_kq_fz` | `import akshare as ak; ak.index_kq_fz(symbol='价格指数')` | 指定 symbol 的柯桥纺织品指数的所有历史数据 |
| `index_li_cx` | `import akshare as ak; ak.index_li_cx()` | 财新指数-劳动力投入指数; 该接口返回所有历史数据 |
| `index_min_sw` | `import akshare as ak; ak.index_min_sw(symbol='801001')` | 申万宏源研究-指数发布-指数详情-指数分时数据; 该接口返回指定 symbol 的数据 |
| `index_neaw_cx` | `import akshare as ak; ak.index_neaw_cx()` | 财新指数-新经济行业入职平均工资水平; 该接口返回所有历史数据 |
| `index_neei_cx` | `import akshare as ak; ak.index_neei_cx()` | 财新指数-新动能指数; 该接口返回所有历史数据 |
| `index_nei_cx` | `import akshare as ak; ak.index_nei_cx()` | 财新指数-中国新经济指数; 该接口返回所有历史数据 |
| `index_news_sentiment_scope` | `import akshare as ak; ak.index_news_sentiment_scope()` | 数库-A股新闻情绪指数; 该接口返回近一年的 A 股新闻情绪指数数据 |
| `index_option_1000index_min_qvix` | `import akshare as ak; ak.index_option_1000index_min_qvix()` | 中证1000股指 期权波动率指数-分时; 单次返回最近交易日的分时数据 |
| `index_option_1000index_qvix` | `import akshare as ak; ak.index_option_1000index_qvix()` | 中证1000股指 期权波动率指数 QVIX; 单次返回所有数据 |
| `index_option_100etf_min_qvix` | `import akshare as ak; ak.index_option_100etf_min_qvix()` | 深证100ETF 期权波动率指数-分时; 单次返回最近交易日的分时数据 |
| `index_option_100etf_qvix` | `import akshare as ak; ak.index_option_100etf_qvix()` | 深证100ETF 期权波动率指数 QVIX; 单次返回所有数据 |
| `index_option_300etf_min_qvix` | `import akshare as ak; ak.index_option_300etf_min_qvix()` | 300ETF 期权波动率指数-分时; 单次返回最近交易日的分时数据 |
| `index_option_300etf_qvix` | `import akshare as ak; ak.index_option_300etf_qvix()` | 300ETF 期权波动率指数 QVIX; 单次返回所有数据 |
| `index_option_300index_min_qvix` | `import akshare as ak; ak.index_option_300index_min_qvix()` | 中证300股指 期权波动率指数-分时; 单次返回最近交易日的分时数据 |
| `index_option_300index_qvix` | `import akshare as ak; ak.index_option_300index_qvix()` | 中证300股指 期权波动率指数 QVIX; 单次返回所有数据 |
| `index_option_500etf_min_qvix` | `import akshare as ak; ak.index_option_500etf_min_qvix()` | 500ETF 期权波动率指数-分时; 单次返回最近交易日的分时数据 |
| `index_option_500etf_qvix` | `import akshare as ak; ak.index_option_500etf_qvix()` | 500ETF 期权波动率指数 QVIX; 单次返回所有数据 |
| `index_option_50etf_min_qvix` | `import akshare as ak; ak.index_option_50etf_min_qvix()` | 50ETF 期权波动率指数-分时; 单次返回最近交易日的分时数据 |
| `index_option_50etf_qvix` | `import akshare as ak; ak.index_option_50etf_qvix()` | 50ETF 期权波动率指数 QVIX；又称中国版的恐慌指数; 单次返回所有数据 |
| `index_option_50index_min_qvix` | `import akshare as ak; ak.index_option_50index_min_qvix()` | 上证50股指 期权波动率指数-分时; 单次返回最近交易日的分时数据 |
| `index_option_50index_qvix` | `import akshare as ak; ak.index_option_50index_qvix()` | 上证50股指 期权波动率指数 QVIX; 单次返回所有数据 |
| `index_option_cyb_min_qvix` | `import akshare as ak; ak.index_option_cyb_min_qvix()` | 创业板 期权波动率指数-分时; 单次返回最近交易日的分时数据 |
| `index_option_cyb_qvix` | `import akshare as ak; ak.index_option_cyb_qvix()` | 创业板 期权波动率指数 QVIX; 单次返回所有数据 |
| `index_option_kcb_min_qvix` | `import akshare as ak; ak.index_option_kcb_min_qvix()` | 科创板 期权波动率指数-分时; 单次返回最近交易日的分时数据 |
| `index_option_kcb_qvix` | `import akshare as ak; ak.index_option_kcb_qvix()` | 科创板 期权波动率指数 QVIX; 单次返回所有数据 |
| `index_outer_quote_sugar_msweet` | `import akshare as ak; ak.index_outer_quote_sugar_msweet()` | 沐甜科技数据中心-配额外进口糖估算指数 |
| `index_pmi_com_cx` | `import akshare as ak; ak.index_pmi_com_cx()` | 财新数据-指数报告-财新中国 PMI-综合 PMI; 该接口返回所有历史数据，该数据更新至 202507 截止； |
| `index_pmi_man_cx` | `import akshare as ak; ak.index_pmi_man_cx()` | 财新数据-指数报告-财新中国 PMI-制造业 PMI; 该接口返回所有历史数据，该数据更新至 202507 截止； |
| `index_pmi_ser_cx` | `import akshare as ak; ak.index_pmi_ser_cx()` | 财新数据-指数报告-财新中国 PMI-服务业 PMI; 该接口返回所有历史数据，该数据更新至 202507 截止； |
| `index_price_cflp` | `import akshare as ak; ak.index_price_cflp(symbol='周指数')` | 获取指定 symbol 的中国公路物流运价指数的数据 |
| `index_qli_cx` | `import akshare as ak; ak.index_qli_cx()` | 财新指数-高质量因子; 该接口返回所有历史数据 |
| `index_realtime_fund_sw` | `import akshare as ak; ak.index_realtime_fund_sw(symbol='基础一级')` | 申万宏源研究-申万指数-指数发布-基金指数-实时行情; 该接口返回指定 symbol 的数据 |
| `index_realtime_sw` | `import akshare as ak; ak.index_realtime_sw(symbol='市场表征')` | 申万宏源研究-指数系列；注意其中大类风格指数和金创指数的字段与其他分类不同; 该接口返回指定 symbol 的数据；源站无数据时返回空的 pandas.DataFrame |
| `index_si_cx` | `import akshare as ak; ak.index_si_cx()` | 财新指数-溢出指数; 该接口返回所有历史数据 |
| `index_stock_cons` | `import akshare as ak; ak.index_stock_cons()` | 指定指数的最新成份股票信息，注意该接口返回的数据有部分是重复会导致数据缺失，可以调用 **ak.index_stock_cons_sina()** 获取主流指数数据，或调用**a… |
| `index_stock_cons_csindex` | `import akshare as ak; ak.index_stock_cons_csindex(symbol='000300')` | 中证指数网站-成份股目录，可以通过 ak.index_csindex_all() 获取所有指数 |
| `index_stock_cons_sina` | `import akshare as ak; ak.index_stock_cons_sina()` |  |
| `index_stock_cons_weight_csindex` | `import akshare as ak; ak.index_stock_cons_weight_csindex(symbol='000300')` | 中证指数网站-成份股权重 |
| `index_stock_info` | `import akshare as ak; ak.index_stock_info()` |  |
| `index_sugar_msweet` | `import akshare as ak; ak.index_sugar_msweet()` | 沐甜科技数据中心-中国食糖指数 |
| `index_ti_cx` | `import akshare as ak; ak.index_ti_cx()` | 财新指数-科技投入指数; 该接口返回所有历史数据 |
| `index_us_stock_sina` | `import akshare as ak; ak.index_us_stock_sina(symbol='.INX')` | 新浪财经-美股指数行情 |
| `index_volume_cflp` | `import akshare as ak; ak.index_volume_cflp(symbol='月指数')` | 指定 symbol 的中国公路物流运量指数的数据 |
| `index_yw` | `import akshare as ak; ak.index_yw(symbol='周价格指数')` | 指定 symbol 的义乌小商品指数的近期历史数据 |
| `index_zh_a_hist` | `import akshare as ak; ak.index_zh_a_hist(symbol='000016', period='daily', start_date='19700101', end_date='22220101')` | 东方财富网-中国股票指数-行情数据; 单次返回具体指数指定 period 从 start_date 到 end_date 的之间的近期数据 |
| `index_zh_a_hist_min_em` | `import akshare as ak; ak.index_zh_a_hist_min_em(symbol='000001', period='1', start_date='2023-12-11 09:30:00', end_date='2023-12-11 19:00:00')` | 东方财富网-指数数据-分时行情; 单次返回具体指数指定 period 从 start_date 到 end_date 的之间的近期数据，该接口不能返回所有历史数据 |
| `spot_goods` | `import akshare as ak; ak.spot_goods(symbol='波罗的海干散货指数')` | 新浪财经-商品现货价格指数 |
| `stock_a_code_to_symbol` | `import akshare as ak; ak.stock_a_code_to_symbol()` |  |
| `stock_hk_index_daily_em` | `import akshare as ak; ak.stock_hk_index_daily_em(symbol='HSTECF2L')` | 东方财富网-港股-股票指数数据; 单次返回指定 symbol 的所有数据 |
| `stock_hk_index_daily_sina` | `import akshare as ak; ak.stock_hk_index_daily_sina(symbol='CES100')` | 新浪财经-港股指数-历史行情数据; 单次返回指定 symbol 的所有数据 |
| `stock_hk_index_spot_em` | `import akshare as ak; ak.stock_hk_index_spot_em()` | 东方财富网-行情中心-港股-指数实时行情; 单次返回所有数据 |
| `stock_hk_index_spot_sina` | `import akshare as ak; ak.stock_hk_index_spot_sina()` | 新浪财经-行情中心-港股指数; 单次返回所有数据 |
| `stock_zh_index_daily` | `import akshare as ak; ak.stock_zh_index_daily(symbol='sz399552')` | 股票指数的历史数据按日频率更新; 单次返回指定 symbol 的所有历史行情数据 |
| `stock_zh_index_daily_em` | `import akshare as ak; ak.stock_zh_index_daily_em(symbol='sz399812')` | 东方财富股票指数数据，历史数据按日频率更新; 单次返回具体指数的所有历史行情数据 |
| `stock_zh_index_daily_tx` | `import akshare as ak; ak.stock_zh_index_daily_tx(symbol='sh000001', start_date='20260101', end_date='20260429')` | 股票指数（或者股票）历史行情数据，支持自定义时间范围; 单次返回具体某个股票指数（或者股票）指定时间范围内的历史行情数据 |
| `stock_zh_index_hist_csindex` | `import akshare as ak; ak.stock_zh_index_hist_csindex(symbol='000928', start_date='20100101', end_date='20240604')` | 中证指数日频率的数据; 该接口返回指定 symbol 的 start_date 和 end_date 的指数日频率数据 |
| `stock_zh_index_spot_em` | `import akshare as ak; ak.stock_zh_index_spot_em(symbol='上证系列指数')` | 东方财富网-行情中心-沪深京指数; 单次返回所有指数的实时行情数据 |
| `stock_zh_index_spot_sina` | `import akshare as ak; ak.stock_zh_index_spot_sina()` | 新浪财经-中国股票指数数据; 单次返回所有指数的实时行情数据 |
| `stock_zh_index_value_csindex` | `import akshare as ak; ak.stock_zh_index_value_csindex(symbol='H30374')` | 中证指数-指数估值数据; 该接口返回指定的指数的估值数据，该接口只能返回近期的数据 |
| `sw_index_first_info` | `import akshare as ak; ak.sw_index_first_info()` | 申万一级行业信息 |
| `sw_index_second_info` | `import akshare as ak; ak.sw_index_second_info()` | 申万二级行业信息 |
| `sw_index_third_cons` | `import akshare as ak; ak.sw_index_third_cons(symbol='850111.SI')` | 申万三级行业成份 |
| `sw_index_third_info` | `import akshare as ak; ak.sw_index_third_info()` | 申万三级行业信息 |

### interest_rate (14)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `macro_bank_australia_interest_rate` | `import akshare as ak; ak.macro_bank_australia_interest_rate()` | 澳洲联储决议报告，数据区间从 19800201-至今; 单次返回所有历史数据 |
| `macro_bank_brazil_interest_rate` | `import akshare as ak; ak.macro_bank_brazil_interest_rate()` | 巴西利率决议报告，数据区间从20080201-至今; 单次返回所有历史数据 |
| `macro_bank_china_interest_rate` | `import akshare as ak; ak.macro_bank_china_interest_rate()` | 中国央行决议报告，数据区间从 19910105-至今; 单次返回所有历史数据 |
| `macro_bank_english_interest_rate` | `import akshare as ak; ak.macro_bank_english_interest_rate()` | 英国央行决议报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `macro_bank_euro_interest_rate` | `import akshare as ak; ak.macro_bank_euro_interest_rate()` | 欧洲央行决议报告，数据区间从 19990101-至今; 单次返回所有历史数据 |
| `macro_bank_india_interest_rate` | `import akshare as ak; ak.macro_bank_india_interest_rate()` | 印度利率决议报告，数据区间从 20000801-至今; 单次返回所有历史数据 |
| `macro_bank_japan_interest_rate` | `import akshare as ak; ak.macro_bank_japan_interest_rate()` | 日本利率决议报告，数据区间从 20080214-至今; 单次返回所有历史数据 |
| `macro_bank_newzealand_interest_rate` | `import akshare as ak; ak.macro_bank_newzealand_interest_rate()` | 新西兰联储决议报告，数据区间从 19990401-至今; 单次返回所有历史数据 |
| `macro_bank_russia_interest_rate` | `import akshare as ak; ak.macro_bank_russia_interest_rate()` | 俄罗斯利率决议报告，数据区间从 20030601-至今; 单次返回所有历史数据 |
| `macro_bank_switzerland_interest_rate` | `import akshare as ak; ak.macro_bank_switzerland_interest_rate()` | 瑞士央行利率决议报告，数据区间从 20080313-至今; 单次返回所有历史数据 |
| `macro_bank_usa_interest_rate` | `import akshare as ak; ak.macro_bank_usa_interest_rate()` | 美联储利率决议报告，数据区间从 19820927-至今; 单次返回所有历史数据 |
| `rate_interbank` | `import akshare as ak; ak.rate_interbank(market='上海银行同业拆借市场', symbol='Shibor人民币', indicator='3月')` | 东方财富-拆借利率一览-具体市场的具体品种的具体指标的拆借利率数据; 返回所有历史数据 |
| `repo_rate_hist` | `import akshare as ak; ak.repo_rate_hist(start_date='20231001', end_date='20240101')` | 回购定盘利率数据; 单次返回指定日期间（一年）的所有历史数据 |
| `repo_rate_query` | `import akshare as ak; ak.repo_rate_query(symbol='回购定盘利率')` | 回购定盘利率数据; 单次返回指定 symbol 的近期数据 |

### macro (215)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `macro_australia_bank_rate` | `import akshare as ak; ak.macro_australia_bank_rate()` | 东方财富-经济数据-澳大利亚-央行公布利率决议; 单次返回所有历史数据 |
| `macro_australia_cpi_quarterly` | `import akshare as ak; ak.macro_australia_cpi_quarterly()` | 东方财富-经济数据-澳大利亚-消费者物价指数季率; 单次返回所有历史数据 |
| `macro_australia_cpi_yearly` | `import akshare as ak; ak.macro_australia_cpi_yearly()` | 东方财富-经济数据-澳大利亚-消费者物价指数年率; 单次返回所有历史数据 |
| `macro_australia_ppi_quarterly` | `import akshare as ak; ak.macro_australia_ppi_quarterly()` | 东方财富-经济数据-澳大利亚-生产者物价指数季率; 单次返回所有历史数据 |
| `macro_australia_retail_rate_monthly` | `import akshare as ak; ak.macro_australia_retail_rate_monthly()` | 东方财富-经济数据-澳大利亚-零售销售月率; 单次返回所有历史数据 |
| `macro_australia_trade` | `import akshare as ak; ak.macro_australia_trade()` | 东方财富-经济数据-澳大利亚-贸易帐; 单次返回所有历史数据 |
| `macro_australia_unemployment_rate` | `import akshare as ak; ak.macro_australia_unemployment_rate()` | 东方财富-经济数据-澳大利亚-失业率; 单次返回所有历史数据 |
| `macro_canada_bank_rate` | `import akshare as ak; ak.macro_canada_bank_rate()` | 东方财富-经济数据-加拿大-央行公布利率决议; 单次返回所有历史数据 |
| `macro_canada_core_cpi_monthly` | `import akshare as ak; ak.macro_canada_core_cpi_monthly()` | 东方财富-经济数据-加拿大-核心消费者物价指数月率; 单次返回所有历史数据 |
| `macro_canada_core_cpi_yearly` | `import akshare as ak; ak.macro_canada_core_cpi_yearly()` | 东方财富-经济数据-加拿大-核心消费者物价指数年率; 单次返回所有历史数据 |
| `macro_canada_cpi_monthly` | `import akshare as ak; ak.macro_canada_cpi_monthly()` | 东方财富-经济数据-加拿大-消费者物价指数月率; 单次返回所有历史数据 |
| `macro_canada_cpi_yearly` | `import akshare as ak; ak.macro_canada_cpi_yearly()` | 东方财富-经济数据-加拿大-消费者物价指数年率; 单次返回所有历史数据 |
| `macro_canada_gdp_monthly` | `import akshare as ak; ak.macro_canada_gdp_monthly()` | 东方财富-经济数据-加拿大-GDP 月率; 单次返回所有历史数据 |
| `macro_canada_new_house_rate` | `import akshare as ak; ak.macro_canada_new_house_rate()` | 东方财富-经济数据-加拿大-新屋开工; 单次返回所有历史数据 |
| `macro_canada_retail_rate_monthly` | `import akshare as ak; ak.macro_canada_retail_rate_monthly()` | 东方财富-经济数据-加拿大-零售销售月率; 单次返回所有历史数据 |
| `macro_canada_trade` | `import akshare as ak; ak.macro_canada_trade()` | 东方财富-经济数据-加拿大-贸易帐; 单次返回所有历史数据 |
| `macro_canada_unemployment_rate` | `import akshare as ak; ak.macro_canada_unemployment_rate()` | 东方财富-经济数据-加拿大-失业率; 单次返回所有历史数据 |
| `macro_china_agricultural_index` | `import akshare as ak; ak.macro_china_agricultural_index()` | 农副指数数据，数据区间从 20111205-至今; 单次返回所有历史数据 |
| `macro_china_agricultural_product` | `import akshare as ak; ak.macro_china_agricultural_product()` | 农产品批发价格总指数，数据区间从 20050927-至今; 单次返回所有历史数据 |
| `macro_china_au_report` | `import akshare as ak; ak.macro_china_au_report()` | 上海黄金交易所报告，数据区间从 20140905-至今; 单次返回所有历史数据 |
| `macro_china_bank_financing` | `import akshare as ak; ak.macro_china_bank_financing()` | 银行理财产品发行数量，数据区间从 2000 一月-至今; 单次返回所有历史数据 |
| `macro_china_bdti_index` | `import akshare as ak; ak.macro_china_bdti_index()` | 原油运输指数数据，数据区间从 20011227-至今; 单次返回所有历史数据 |
| `macro_china_bond_public` | `import akshare as ak; ak.macro_china_bond_public()` | 中国外汇交易中心暨全国银行间同业拆借中心-债券信息披露-新债发行；近期债券发行数据; 单次返回所有历史数据 |
| `macro_china_bsi_index` | `import akshare as ak; ak.macro_china_bsi_index()` | 超灵便型船运价指数数据，数据区间从 20060103-至今; 单次返回所有历史数据 |
| `macro_china_central_bank_balance` | `import akshare as ak; ak.macro_china_central_bank_balance()` | 新浪财经-中国宏观经济数据-央行货币当局资产负债; 单次返回所有历史数据 |
| `macro_china_commodity_price_index` | `import akshare as ak; ak.macro_china_commodity_price_index()` | 大宗商品价格数据，数据区间从 20111205-至今; 单次返回所有历史数据 |
| `macro_china_construction_index` | `import akshare as ak; ak.macro_china_construction_index()` | 建材指数数据，数据区间从 20111205-至今; 单次返回所有历史数据 |
| `macro_china_construction_price_index` | `import akshare as ak; ak.macro_china_construction_price_index()` | 建材价格指数数据，数据区间从 20100615-至今; 单次返回所有历史数据 |
| `macro_china_consumer_goods_retail` | `import akshare as ak; ak.macro_china_consumer_goods_retail()` | 东方财富-经济数据-社会消费品零售总额; 单次返回所有历史数据 |
| `macro_china_cpi` | `import akshare as ak; ak.macro_china_cpi()` | 中国居民消费价格指数，数据区间从 200801 至今，月度数据; 单次返回所有历史数据 |
| `macro_china_cpi_monthly` | `import akshare as ak; ak.macro_china_cpi_monthly()` | 中国月度 CPI 数据，数据区间从 19960201-至今; 单次返回所有历史数据 |
| `macro_china_cpi_yearly` | `import akshare as ak; ak.macro_china_cpi_yearly()` | 中国年度 CPI 数据，数据区间从 19860201-至今; 单次返回所有历史数据 |
| `macro_china_cx_pmi_yearly` | `import akshare as ak; ak.macro_china_cx_pmi_yearly()` | 中国年度财新 PMI 数据，数据区间从 20120120-至今; 单次返回所有历史数据 |
| `macro_china_cx_services_pmi_yearly` | `import akshare as ak; ak.macro_china_cx_services_pmi_yearly()` | 中国财新服务业 PMI 报告，数据区间从 20120405-至今; 单次返回所有历史数据 |
| `macro_china_czsr` | `import akshare as ak; ak.macro_china_czsr()` | 中国财政收入，数据区间从 200801 至今，月度数据; 单次返回所有历史数据 |
| `macro_china_daily_energy` | `import akshare as ak; ak.macro_china_daily_energy()` | 中国日度沿海六大电库存数据，数据区间从20160101-至今，不再更新，只能获得历史数据; 单次返回所有历史数据 |
| `macro_china_energy_index` | `import akshare as ak; ak.macro_china_energy_index()` | 能源指数数据，数据区间从 20111205-至今; 单次返回所有历史数据 |
| `macro_china_enterprise_boom_index` | `import akshare as ak; ak.macro_china_enterprise_boom_index()` | 中国企业景气及企业家信心指数数据，数据区间从 2005 一季度-至今; 单次返回所有历史数据 |
| `macro_china_exports_yoy` | `import akshare as ak; ak.macro_china_exports_yoy()` | 中国以美元计算出口年率报告，数据区间从 19820201-至今; 单次返回所有历史数据 |
| `macro_china_fdi` | `import akshare as ak; ak.macro_china_fdi()` | 东方财富-经济数据一览-中国-外商直接投资数据，数据区间从 200801-202307; 单次返回所有历史数据 |
| `macro_china_foreign_exchange_gold` | `import akshare as ak; ak.macro_china_foreign_exchange_gold()` | 国家统计局-央行黄金和外汇储备，比东财接口数据时间长; 单次返回所有历史数据 |
| `macro_china_freight_index` | `import akshare as ak; ak.macro_china_freight_index()` | 新浪财经-中国宏观经济数据-航贸运价指数; 单次返回所有历史数据 |
| `macro_china_fx_gold` | `import akshare as ak; ak.macro_china_fx_gold()` | 中国外汇和黄金储备，数据区间从 200801 至今，月度数据; 单次返回所有历史数据 |
| `macro_china_fx_reserves_yearly` | `import akshare as ak; ak.macro_china_fx_reserves_yearly()` | 中国年度外汇储备数据，数据区间从 20140115-至今; 单次返回所有历史数据 |
| `macro_china_gdp` | `import akshare as ak; ak.macro_china_gdp()` | 中国国内生产总值，数据区间从 200601 至今，月度数据; 单次返回所有历史数据 |
| `macro_china_gdp_yearly` | `import akshare as ak; ak.macro_china_gdp_yearly()` | 金十数据中心-中国 GDP 年率报告，数据区间从 20110120-至今; 单次返回所有历史数据 |
| `macro_china_gdzctz` | `import akshare as ak; ak.macro_china_gdzctz()` | 中国城镇固定资产投资，数据区间从 200802 至今，月度数据; 单次返回所有历史数据 |
| `macro_china_gyzjz` | `import akshare as ak; ak.macro_china_gyzjz()` | 东方财富-中国工业增加值增长，数据区间从 2008 - 至今; 单次返回所有历史数据 |
| `macro_china_hgjck` | `import akshare as ak; ak.macro_china_hgjck()` | 中国海关进出口增减情况一览表，数据区间从 200801 至今，月度数据; 单次返回所有历史数据 |
| `macro_china_hk_building_amount` | `import akshare as ak; ak.macro_china_hk_building_amount()` | 东方财富-经济数据一览-中国香港-香港楼宇买卖合约成交金额; 单次返回所有历史数据 |
| `macro_china_hk_building_volume` | `import akshare as ak; ak.macro_china_hk_building_volume()` | 东方财富-经济数据一览-中国香港-香港楼宇买卖合约数量; 单次返回所有历史数据 |
| `macro_china_hk_cpi` | `import akshare as ak; ak.macro_china_hk_cpi()` | 东方财富-经济数据一览-中国香港-消费者物价指数; 单次返回所有历史数据 |
| `macro_china_hk_cpi_ratio` | `import akshare as ak; ak.macro_china_hk_cpi_ratio()` | 东方财富-经济数据一览-中国香港-消费者物价指数年率; 单次返回所有历史数据 |
| `macro_china_hk_gbp` | `import akshare as ak; ak.macro_china_hk_gbp()` | 东方财富-经济数据一览-中国香港-香港 GDP; 单次返回所有历史数据 |
| `macro_china_hk_gbp_ratio` | `import akshare as ak; ak.macro_china_hk_gbp_ratio()` | 东方财富-经济数据一览-中国香港-香港 GDP 同比; 单次返回所有历史数据 |
| `macro_china_hk_market_info` | `import akshare as ak; ak.macro_china_hk_market_info()` | 香港同业拆借报告，数据区间从 20170320-至今; 单次返回所有历史数据 |
| `macro_china_hk_ppi` | `import akshare as ak; ak.macro_china_hk_ppi()` | 东方财富-经济数据一览-中国香港-香港制造业PPI年率; 单次返回所有历史数据 |
| `macro_china_hk_rate_of_unemployment` | `import akshare as ak; ak.macro_china_hk_rate_of_unemployment()` | 东方财富-经济数据一览-中国香港-失业率; 单次返回所有历史数据 |
| `macro_china_hk_trade_diff_ratio` | `import akshare as ak; ak.macro_china_hk_trade_diff_ratio()` | 东方财富-经济数据一览-中国香港-香港商品贸易差额年率; 单次返回所有历史数据 |
| `macro_china_imports_yoy` | `import akshare as ak; ak.macro_china_imports_yoy()` | 中国以美元计算进口年率报告，数据区间从 19960201-至今; 单次返回所有历史数据 |
| `macro_china_industrial_production_yoy` | `import akshare as ak; ak.macro_china_industrial_production_yoy()` | 中国规模以上工业增加值年率报告，数据区间从 19900301-至今; 单次返回所有历史数据 |
| `macro_china_insurance` | `import akshare as ak; ak.macro_china_insurance()` | 新浪财经-中国宏观经济数据-保险业经营情况; 单次返回所有历史数据 |
| `macro_china_insurance_income` | `import akshare as ak; ak.macro_china_insurance_income()` | 原保险保费收入，数据区间从 200407-至今; 单次返回所有历史数据 |
| `macro_china_international_tourism_fx` | `import akshare as ak; ak.macro_china_international_tourism_fx()` | 国家统计局-国际旅游外汇收入构成; 单次返回所有历史数据 |
| `macro_china_lpi_index` | `import akshare as ak; ak.macro_china_lpi_index()` | 物流景气指数数据，数据区间从 20130701-至今; 单次返回所有历史数据 |
| `macro_china_lpr` | `import akshare as ak; ak.macro_china_lpr()` | 中国 LPR 品种数据，数据区间从 19910421-至今; 单次返回所有历史数据 |
| `macro_china_m2_yearly` | `import akshare as ak; ak.macro_china_m2_yearly()` | 中国年度 M2 数据，数据区间从 19980201-至今; 单次返回所有历史数据 |
| `macro_china_market_margin_sh` | `import akshare as ak; ak.macro_china_market_margin_sh()` | 上海融资融券报告，数据区间从 20100331-至今; 单次返回所有历史数据 |
| `macro_china_market_margin_sz` | `import akshare as ak; ak.macro_china_market_margin_sz()` | 深圳融资融券报告，数据区间从 20100331-至今; 单次返回所有历史数据 |
| `macro_china_mobile_number` | `import akshare as ak; ak.macro_china_mobile_number()` | 手机出货量，数据区间从 201201-至今; 单次返回所有历史数据 |
| `macro_china_money_supply` | `import akshare as ak; ak.macro_china_money_supply()` | 东方财富-经济数据-中国宏观-中国货币供应量；数据区间从 200801 至今，月度数据; 单次返回所有历史数据 |
| `macro_china_national_tax_receipts` | `import akshare as ak; ak.macro_china_national_tax_receipts()` | 中国全国税收收入数据，数据区间从 2005 一季度-至今; 单次返回所有历史数据 |
| `macro_china_nbs_nation` | `import akshare as ak; ak.macro_china_nbs_nation(kind='年度数据', path='人口 > 总人口', period='LAST5')` | 国家统计局全国数据通用接口，包括月度数据、季度数据、年度数据，具体指标见国家统计局新站官网。; 根据参数返回指定数据 |
| `macro_china_nbs_region` | `import akshare as ak; ak.macro_china_nbs_region(kind='分省季度数据', path='国民经济核算 > 地区生产总值', period='last3', indicator=None, region='河北省')` | 国家统计局地区数据通用接口，包括分省月度数据、分省季度数据、分省年度数据、主要城市月度价格、主要城市年度数据、港澳台月度数据、港澳台年度数据，具体指标见国家统计局新站官网。; 根据参数返回指定数据 |
| `macro_china_new_financial_credit` | `import akshare as ak; ak.macro_china_new_financial_credit()` | 中国新增信贷数据数据，数据区间从 200801 至今，月度数据; 单次返回所有历史数据 |
| `macro_china_new_house_price` | `import akshare as ak; ak.macro_china_new_house_price(city_first='北京', city_second='上海')` | 中国新房价指数月度数据，数据区间从 201101-至今; 单次返回指定城市的所有历史数据 |
| `macro_china_non_man_pmi` | `import akshare as ak; ak.macro_china_non_man_pmi()` | 中国官方非制造业 PMI，数据区间从 20160101-至今; 单次返回所有历史数据 |
| `macro_china_passenger_load_factor` | `import akshare as ak; ak.macro_china_passenger_load_factor()` | 国家统计局-民航客座率及载运率; 单次返回所有历史数据 |
| `macro_china_pmi` | `import akshare as ak; ak.macro_china_pmi()` | 采购经理人指数，数据区间从 200801 至今，月度数据; 单次返回所有历史数据 |
| `macro_china_pmi_yearly` | `import akshare as ak; ak.macro_china_pmi_yearly()` | 中国年度PMI数据，数据区间从 20050201-至今; 单次返回所有历史数据 |
| `macro_china_postal_telecommunicational` | `import akshare as ak; ak.macro_china_postal_telecommunicational()` | 国家统计局-邮电业务基本情况-非累计; 单次返回所有历史数据 |
| `macro_china_ppi` | `import akshare as ak; ak.macro_china_ppi()` | 工业品出厂价格指数，数据区间从 200601 至今，月度数据; 单次返回所有历史数据 |
| `macro_china_ppi_yearly` | `import akshare as ak; ak.macro_china_ppi_yearly()` | 中国年度 PPI 数据，数据区间从 19950801-至今; 单次返回所有历史数据 |
| `macro_china_qyspjg` | `import akshare as ak; ak.macro_china_qyspjg()` | 东方财富-经济数据一览-中国-企业商品价格指数，数据区间从 20050101-至今; 单次返回所有历史数据 |
| `macro_china_real_estate` | `import akshare as ak; ak.macro_china_real_estate()` | 国家统计局-国房景气指数; 单次返回所有历史数据 |
| `macro_china_reserve_requirement_ratio` | `import akshare as ak; ak.macro_china_reserve_requirement_ratio()` | 国家统计局-存款准备金率; 单次返回所有历史数据 |
| `macro_china_retail_price_index` | `import akshare as ak; ak.macro_china_retail_price_index()` | 国家统计局-商品零售价格指数; 单次返回所有历史数据 |
| `macro_china_rmb` | `import akshare as ak; ak.macro_china_rmb()` | 中国人民币汇率中间价报告，数据区间从 20170103-20210513; 单次返回所有历史数据 |
| `macro_china_shibor_all` | `import akshare as ak; ak.macro_china_shibor_all()` | 上海银行业同业拆借报告，数据区间从 20170317-至今; 单次返回所有历史数据 |
| `macro_china_shrzgm` | `import akshare as ak; ak.macro_china_shrzgm()` | 商务数据中心-国内贸易-社会融资规模增量统计，数据区间从 201501-至今; 单次返回所有历史数据 |
| `macro_china_society_electricity` | `import akshare as ak; ak.macro_china_society_electricity()` | 国家统计局-全社会用电分类情况表; 单次返回所有历史数据 |
| `macro_china_society_traffic_volume` | `import akshare as ak; ak.macro_china_society_traffic_volume()` | 国家统计局-全社会客货运输量-非累计; 单次返回所有历史数据 |
| `macro_china_stock_market_cap` | `import akshare as ak; ak.macro_china_stock_market_cap()` | 全国股票交易统计表，数据区间从 200801 至今，月度数据; 单次返回所有历史数据 |
| `macro_china_supply_of_money` | `import akshare as ak; ak.macro_china_supply_of_money()` | 新浪财经-中国宏观经济数据-货币供应量; 单次返回所有历史数据 |
| `macro_china_swap_rate` | `import akshare as ak; ak.macro_china_swap_rate(start_date='20240501', end_date='20240531')` | 国家统计局-FR007利率互换曲线历史数据; 单次返回所有历史数据，该接口只能获取近一年的数据的数据，其中每次只能获取一个月的数据 |
| `macro_china_trade_balance` | `import akshare as ak; ak.macro_china_trade_balance()` | 中国以美元计算贸易帐报告，数据区间从19810201-至今; 单次返回所有历史数据 |
| `macro_china_urban_unemployment` | `import akshare as ak; ak.macro_china_urban_unemployment()` | 国家统计局-月度数据-城镇调查失业率; 单次返回所有历史数据 |
| `macro_china_vegetable_basket` | `import akshare as ak; ak.macro_china_vegetable_basket()` | 菜篮子产品批发价格指数，数据区间从 20050927-至今; 单次返回所有历史数据 |
| `macro_china_wbck` | `import akshare as ak; ak.macro_china_wbck()` | 本外币存款，数据区间从 200802 至今，月度数据; 单次返回所有历史数据 |
| `macro_china_whxd` | `import akshare as ak; ak.macro_china_whxd()` | 外汇贷款数据，数据区间从 200802 至今，月度数据; 单次返回所有历史数据 |
| `macro_china_xfzxx` | `import akshare as ak; ak.macro_china_xfzxx()` | 东方财富网-消费者信心指数; 单次返回所有历史数据 |
| `macro_china_yw_electronic_index` | `import akshare as ak; ak.macro_china_yw_electronic_index()` | 义乌小商品指数-电子元器件数据，数据区间从 20060911-至今; 单次返回所有历史数据 |
| `macro_cnbs` | `import akshare as ak; ak.macro_cnbs()` | 中国国家金融与发展实验室-中国宏观杠杆率数据; 单次返回所有历史数据 |
| `macro_cons_gold` | `import akshare as ak; ak.macro_cons_gold()` | 全球最大黄金 ETF—SPDR Gold Trust 持仓报告，数据区间从 20041119-至今; 单次返回所有历史数据 |
| `macro_cons_opec_month` | `import akshare as ak; ak.macro_cons_opec_month()` | 欧佩克报告，数据区间从 20170118-至今; 单次返回所有历史数据，以网页数据为准。 |
| `macro_cons_silver` | `import akshare as ak; ak.macro_cons_silver()` | 全球最大白银 ETF--iShares Silver Trust 持仓报告，数据区间从 20041202-至今; 单次返回所有历史数据 |
| `macro_euro_cpi_mom` | `import akshare as ak; ak.macro_euro_cpi_mom()` | 欧元区 CPI 月率报告，数据区间从 19900301-至今; 单次返回所有历史数据 |
| `macro_euro_cpi_yoy` | `import akshare as ak; ak.macro_euro_cpi_yoy()` | 欧元区 CPI 年率报告，数据区间从 19910201-至今; 单次返回所有历史数据 |
| `macro_euro_current_account_mom` | `import akshare as ak; ak.macro_euro_current_account_mom()` | 欧元区经常帐报告，数据区间从 20080221-至今; 单次返回所有历史数据 |
| `macro_euro_employment_change_qoq` | `import akshare as ak; ak.macro_euro_employment_change_qoq()` | 欧元区季调后就业人数季率报告，数据区间从 20083017-至今; 单次返回所有历史数据 |
| `macro_euro_gdp_yoy` | `import akshare as ak; ak.macro_euro_gdp_yoy()` | 欧元区季度 GDP 年率报告，数据区间从 20131114-至今; 单次返回所有历史数据 |
| `macro_euro_industrial_production_mom` | `import akshare as ak; ak.macro_euro_industrial_production_mom()` | 欧元区工业产出月率报告，数据区间从 19910301-至今; 单次返回所有历史数据 |
| `macro_euro_lme_holding` | `import akshare as ak; ak.macro_euro_lme_holding()` | 伦敦金属交易所(LME)-持仓报告，数据区间从 20151022-至今; 单次返回所有历史数据 |
| `macro_euro_lme_stock` | `import akshare as ak; ak.macro_euro_lme_stock()` | 伦敦金属交易所(LME)-库存报告，数据区间从 20140702-至今; 单次返回所有历史数据 |
| `macro_euro_manufacturing_pmi` | `import akshare as ak; ak.macro_euro_manufacturing_pmi()` | 欧元区制造业 PMI 初值报告，数据区间从 20080222-至今; 单次返回所有历史数据 |
| `macro_euro_ppi_mom` | `import akshare as ak; ak.macro_euro_ppi_mom()` | 欧元区 PPI 月率报告，数据区间从 19810301-至今; 单次返回所有历史数据 |
| `macro_euro_retail_sales_mom` | `import akshare as ak; ak.macro_euro_retail_sales_mom()` | 欧元区零售销售月率报告，数据区间从 20000301-至今; 单次返回所有历史数据 |
| `macro_euro_sentix_investor_confidence` | `import akshare as ak; ak.macro_euro_sentix_investor_confidence()` | 欧元区 Sentix 投资者信心指数报告，数据区间从 20020801-至今; 单次返回所有历史数据 |
| `macro_euro_services_pmi` | `import akshare as ak; ak.macro_euro_services_pmi()` | 欧元区服务业 PMI 终值报告，数据区间从 20080222-至今; 单次返回所有历史数据 |
| `macro_euro_trade_balance` | `import akshare as ak; ak.macro_euro_trade_balance()` | 欧元区未季调贸易帐报告，数据区间从 19990201-至今; 单次返回所有历史数据 |
| `macro_euro_unemployment_rate_mom` | `import akshare as ak; ak.macro_euro_unemployment_rate_mom()` | 欧元区失业率报告，数据区间从 19980501-至今; 单次返回所有历史数据 |
| `macro_euro_zew_economic_sentiment` | `import akshare as ak; ak.macro_euro_zew_economic_sentiment()` | 欧元区 ZEW 经济景气指数报告，数据区间从 20080212-至今; 单次返回所有历史数据 |
| `macro_germany_cpi_monthly` | `import akshare as ak; ak.macro_germany_cpi_monthly()` | 东方财富-数据中心-经济数据一览-德国-消费者物价指数月率终值; 单次返回所有历史数据 |
| `macro_germany_cpi_yearly` | `import akshare as ak; ak.macro_germany_cpi_yearly()` | 东方财富-数据中心-经济数据一览-德国-消费者物价指数年率终值; 单次返回所有历史数据 |
| `macro_germany_gdp` | `import akshare as ak; ak.macro_germany_gdp()` | 东方财富-数据中心-经济数据一览-德国-GDP; 单次返回所有历史数据 |
| `macro_germany_ifo` | `import akshare as ak; ak.macro_germany_ifo()` | 东方财富-数据中心-经济数据一览-IFO商业景气指数; 单次返回所有历史数据 |
| `macro_germany_retail_sale_monthly` | `import akshare as ak; ak.macro_germany_retail_sale_monthly()` | 东方财富-数据中心-经济数据一览-德国-实际零售销售月率; 单次返回所有历史数据 |
| `macro_germany_retail_sale_yearly` | `import akshare as ak; ak.macro_germany_retail_sale_yearly()` | 东方财富-数据中心-经济数据一览-德国-实际零售销售年率; 单次返回所有历史数据 |
| `macro_germany_trade_adjusted` | `import akshare as ak; ak.macro_germany_trade_adjusted()` | 东方财富-数据中心-经济数据一览-德国-贸易帐（季调后）; 单次返回所有历史数据 |
| `macro_germany_zew` | `import akshare as ak; ak.macro_germany_zew()` | 东方财富-数据中心-经济数据一览-德国-ZEW 经济景气指数; 单次返回所有历史数据 |
| `macro_global_sox_index` | `import akshare as ak; ak.macro_global_sox_index()` | 费城半导体指数数据，数据区间从 19940504-至今; 单次返回所有历史数据 |
| `macro_info_ws` | `import akshare as ak; ak.macro_info_ws(date='20240514')` | 华尔街见闻-日历-宏观; 单次返回指定 date 的数据 |
| `macro_japan_bank_rate` | `import akshare as ak; ak.macro_japan_bank_rate()` | 东方财富-经济数据-日本-央行公布利率决议; 单次返回所有历史数据 |
| `macro_japan_core_cpi_yearly` | `import akshare as ak; ak.macro_japan_core_cpi_yearly()` | 东方财富-经济数据-日本-全国核心消费者物价指数年率; 单次返回所有历史数据 |
| `macro_japan_cpi_yearly` | `import akshare as ak; ak.macro_japan_cpi_yearly()` | 东方财富-经济数据-日本-全国消费者物价指数年率; 单次返回所有历史数据 |
| `macro_japan_head_indicator` | `import akshare as ak; ak.macro_japan_head_indicator()` | 东方财富-经济数据-日本-领先指标终值; 单次返回所有历史数据 |
| `macro_japan_unemployment_rate` | `import akshare as ak; ak.macro_japan_unemployment_rate()` | 东方财富-经济数据-日本-失业率; 单次返回所有历史数据 |
| `macro_rmb_deposit` | `import akshare as ak; ak.macro_rmb_deposit()` | 同花顺-数据中心-宏观数据-人民币存款余额; 单次返回所有历史数据 |
| `macro_rmb_loan` | `import akshare as ak; ak.macro_rmb_loan()` | 同花顺-数据中心-宏观数据-新增人民币贷款; 单次返回所有历史数据 |
| `macro_shipping_bci` | `import akshare as ak; ak.macro_shipping_bci()` | 海岬型运费指数，数据区间从 19990430-至今; 单次返回所有历史数据 |
| `macro_shipping_bcti` | `import akshare as ak; ak.macro_shipping_bcti()` | 成品油运输指数，数据区间从 20011217-至今; 单次返回所有历史数据 |
| `macro_shipping_bdi` | `import akshare as ak; ak.macro_shipping_bdi()` | 波罗的海干散货指数，数据区间从 19881019-至今; 单次返回所有历史数据 |
| `macro_shipping_bpi` | `import akshare as ak; ak.macro_shipping_bpi()` | 巴拿马型运费指数，数据区间从 19981231-至今; 单次返回所有历史数据 |
| `macro_stock_finance` | `import akshare as ak; ak.macro_stock_finance()` | 同花顺-数据中心-宏观数据-股票筹资; 单次返回所有历史数据 |
| `macro_swiss_cpi_yearly` | `import akshare as ak; ak.macro_swiss_cpi_yearly()` | 东方财富-经济数据-瑞士-消费者物价指数年率; 单次返回所有历史数据 |
| `macro_swiss_gbd_bank_rate` | `import akshare as ak; ak.macro_swiss_gbd_bank_rate()` | 东方财富-经济数据-瑞士-央行公布利率决议; 单次返回所有历史数据 |
| `macro_swiss_gbd_yearly` | `import akshare as ak; ak.macro_swiss_gbd_yearly()` | 东方财富-经济数据-瑞士-GDP 年率; 单次返回所有历史数据 |
| `macro_swiss_gdp_quarterly` | `import akshare as ak; ak.macro_swiss_gdp_quarterly()` | 东方财富-经济数据-瑞士-GDP 季率; 单次返回所有历史数据 |
| `macro_swiss_svme` | `import akshare as ak; ak.macro_swiss_svme()` | 东方财富-经济数据-瑞士-SVME采购经理人指数; 单次返回所有历史数据 |
| `macro_swiss_trade` | `import akshare as ak; ak.macro_swiss_trade()` | 东方财富-经济数据-瑞士-贸易帐; 单次返回所有历史数据 |
| `macro_uk_bank_rate` | `import akshare as ak; ak.macro_uk_bank_rate()` | 东方财富-经济数据-英国-央行公布利率决议; 单次返回所有历史数据 |
| `macro_uk_core_cpi_monthly` | `import akshare as ak; ak.macro_uk_core_cpi_monthly()` | 东方财富-经济数据-英国-核心消费者物价指数月率; 单次返回所有历史数据 |
| `macro_uk_core_cpi_yearly` | `import akshare as ak; ak.macro_uk_core_cpi_yearly()` | 东方财富-经济数据-英国-核心消费者物价指数年率; 单次返回所有历史数据 |
| `macro_uk_cpi_monthly` | `import akshare as ak; ak.macro_uk_cpi_monthly()` | 东方财富-经济数据-英国-消费者物价指数月率; 单次返回所有历史数据 |
| `macro_uk_cpi_yearly` | `import akshare as ak; ak.macro_uk_cpi_yearly()` | 东方财富-经济数据-英国-消费者物价指数年率; 单次返回所有历史数据 |
| `macro_uk_gdp_quarterly` | `import akshare as ak; ak.macro_uk_gdp_quarterly()` | 东方财富-经济数据-英国-GDP 季率初值; 单次返回所有历史数据 |
| `macro_uk_gdp_yearly` | `import akshare as ak; ak.macro_uk_gdp_yearly()` | 东方财富-经济数据-英国-GDP 年率初值; 单次返回所有历史数据 |
| `macro_uk_halifax_monthly` | `import akshare as ak; ak.macro_uk_halifax_monthly()` | 东方财富-经济数据-英国-Halifax 房价指数月率; 单次返回所有历史数据 |
| `macro_uk_halifax_yearly` | `import akshare as ak; ak.macro_uk_halifax_yearly()` | 东方财富-经济数据-英国-Halifax 房价指数年率; 单次返回所有历史数据 |
| `macro_uk_retail_monthly` | `import akshare as ak; ak.macro_uk_retail_monthly()` | 东方财富-经济数据-英国-零售销售月率; 单次返回所有历史数据 |
| `macro_uk_retail_yearly` | `import akshare as ak; ak.macro_uk_retail_yearly()` | 东方财富-经济数据-英国-零售销售年率; 单次返回所有历史数据 |
| `macro_uk_rightmove_monthly` | `import akshare as ak; ak.macro_uk_rightmove_monthly()` | 东方财富-经济数据-英国-Rightmove 房价指数月率; 单次返回所有历史数据 |
| `macro_uk_rightmove_yearly` | `import akshare as ak; ak.macro_uk_rightmove_yearly()` | 东方财富-经济数据-英国-Rightmove 房价指数年率; 单次返回所有历史数据 |
| `macro_uk_trade` | `import akshare as ak; ak.macro_uk_trade()` | 东方财富-经济数据-英国-贸易帐; 单次返回所有历史数据 |
| `macro_uk_unemployment_rate` | `import akshare as ak; ak.macro_uk_unemployment_rate()` | 东方财富-经济数据-英国-失业率; 单次返回所有历史数据 |
| `macro_usa_adp_employment` | `import akshare as ak; ak.macro_usa_adp_employment()` | 美国 ADP 就业人数报告，数据区间从 20010601-至今; 单次返回所有历史数据 |
| `macro_usa_api_crude_stock` | `import akshare as ak; ak.macro_usa_api_crude_stock()` | 美国 API 原油库存报告，数据区间从 20120328-至今; 单次返回所有历史数据 |
| `macro_usa_building_permits` | `import akshare as ak; ak.macro_usa_building_permits()` | 美国营建许可总数报告，数据区间从 20080220-至今; 单次返回所有历史数据 |
| `macro_usa_business_inventories` | `import akshare as ak; ak.macro_usa_business_inventories()` | 美国商业库存月率报告，数据区间从 19920301-至今; 单次返回所有历史数据 |
| `macro_usa_cb_consumer_confidence` | `import akshare as ak; ak.macro_usa_cb_consumer_confidence()` | 美国谘商会消费者信心指数报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `macro_usa_cftc_c_holding` | `import akshare as ak; ak.macro_usa_cftc_c_holding()` | 美国商品期货交易委员会CFTC商品类非商业持仓报告，数据区间从 19830107-至今; 单次返回所有历史数据 |
| `macro_usa_cftc_merchant_currency_holding` | `import akshare as ak; ak.macro_usa_cftc_merchant_currency_holding()` | 美国商品期货交易委员会CFTC外汇类商业持仓报告，数据区间从 19860115-至今; 单次返回所有历史数据 |
| `macro_usa_cftc_merchant_goods_holding` | `import akshare as ak; ak.macro_usa_cftc_merchant_goods_holding()` | 美国商品期货交易委员会 CFTC 商品类商业持仓报告，数据区间从 19860115-至今; 单次返回所有历史数据 |
| `macro_usa_cftc_nc_holding` | `import akshare as ak; ak.macro_usa_cftc_nc_holding()` | 美国商品期货交易委员会CFTC外汇类非商业持仓报告，数据区间从 19830107-至今; 单次返回所有历史数据 |
| `macro_usa_cme_merchant_goods_holding` | `import akshare as ak; ak.macro_usa_cme_merchant_goods_holding()` | CME-贵金属，数据区间从 20180405-至今; 单次返回所有历史数据 |
| `macro_usa_core_cpi_monthly` | `import akshare as ak; ak.macro_usa_core_cpi_monthly()` | 美国核心 CPI 月率报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `macro_usa_core_pce_price` | `import akshare as ak; ak.macro_usa_core_pce_price()` | 美国核心 PCE 物价指数年率报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `macro_usa_core_ppi` | `import akshare as ak; ak.macro_usa_core_ppi()` | 美国核心生产者物价指数(PPI)报告，数据区间从 20080318-至今; 单次返回所有历史数据 |
| `macro_usa_cpi_monthly` | `import akshare as ak; ak.macro_usa_cpi_monthly()` | 美国 CPI 月率报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `macro_usa_cpi_yoy` | `import akshare as ak; ak.macro_usa_cpi_yoy()` | 东方财富-经济数据一览-美国-CPI年率，数据区间从2008-至今; 单次返回所有历史数据 |
| `macro_usa_crude_inner` | `import akshare as ak; ak.macro_usa_crude_inner()` | 美国原油产量报告，数据区间从 19830107-至今，每周三公布（美国节假日除外），美国能源信息署(EIA); 单次返回所有历史数据 |
| `macro_usa_current_account` | `import akshare as ak; ak.macro_usa_current_account()` | 美国经常帐报告，数据区间从 20080317-至今; 单次返回所有历史数据 |
| `macro_usa_durable_goods_orders` | `import akshare as ak; ak.macro_usa_durable_goods_orders()` | 美国耐用品订单月率报告，数据区间从 20080227-至今; 单次返回所有历史数据 |
| `macro_usa_eia_crude_rate` | `import akshare as ak; ak.macro_usa_eia_crude_rate()` | 美国EIA原油库存报告，数据区间从 19950801-至今; 单次返回所有历史数据 |
| `macro_usa_exist_home_sales` | `import akshare as ak; ak.macro_usa_exist_home_sales()` | 美国成屋销售总数年化报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `macro_usa_export_price` | `import akshare as ak; ak.macro_usa_export_price()` | 美国出口价格指数报告，数据区间从 19890201-至今; 单次返回所有历史数据 |
| `macro_usa_factory_orders` | `import akshare as ak; ak.macro_usa_factory_orders()` | 美国工厂订单月率报告，数据区间从 19920401-至今; 单次返回所有历史数据 |
| `macro_usa_gdp_monthly` | `import akshare as ak; ak.macro_usa_gdp_monthly()` | 美国国内生产总值(GDP)报告，数据区间从 20080228-至今; 单次返回所有历史数据 |
| `macro_usa_house_price_index` | `import akshare as ak; ak.macro_usa_house_price_index()` | 美国 FHFA 房价指数月率报告，数据区间从 19910301-至今; 单次返回所有历史数据 |
| `macro_usa_house_starts` | `import akshare as ak; ak.macro_usa_house_starts()` | 美国新屋开工总数年化报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `macro_usa_import_price` | `import akshare as ak; ak.macro_usa_import_price()` | 美国进口物价指数报告，数据区间从 19890201-至今; 单次返回所有历史数据 |
| `macro_usa_industrial_production` | `import akshare as ak; ak.macro_usa_industrial_production()` | 美国工业产出月率报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `macro_usa_initial_jobless` | `import akshare as ak; ak.macro_usa_initial_jobless()` | 美国初请失业金人数报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `macro_usa_ism_non_pmi` | `import akshare as ak; ak.macro_usa_ism_non_pmi()` | 美国 ISM 非制造业 PMI 报告，数据区间从 19970801-至今; 单次返回所有历史数据 |
| `macro_usa_ism_pmi` | `import akshare as ak; ak.macro_usa_ism_pmi()` | 美国 ISM 制造业 PMI 报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `macro_usa_job_cuts` | `import akshare as ak; ak.macro_usa_job_cuts()` | 美国挑战者企业裁员人数报告，数据区间从 19940201-至今; 单次返回所有历史数据 |
| `macro_usa_lmci` | `import akshare as ak; ak.macro_usa_lmci()` | 美联储劳动力市场状况指数报告，数据区间从 20141006-至今; 单次返回所有历史数据 |
| `macro_usa_michigan_consumer_sentiment` | `import akshare as ak; ak.macro_usa_michigan_consumer_sentiment()` | 美国密歇根大学消费者信心指数初值报告，数据区间从 19700301-至今; 单次返回所有历史数据 |
| `macro_usa_nahb_house_market_index` | `import akshare as ak; ak.macro_usa_nahb_house_market_index()` | 美国 NAHB 房产市场指数报告，数据区间从 19850201-至今; 单次返回所有历史数据 |
| `macro_usa_new_home_sales` | `import akshare as ak; ak.macro_usa_new_home_sales()` | 美国新屋销售总数年化报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `macro_usa_nfib_small_business` | `import akshare as ak; ak.macro_usa_nfib_small_business()` | 美国NFIB小型企业信心指数报告，数据区间从 19750201-至今; 单次返回所有历史数据 |
| `macro_usa_non_farm` | `import akshare as ak; ak.macro_usa_non_farm()` | 美国非农就业人数报告，数据区间从 19700102-至今; 单次返回所有历史数据 |
| `macro_usa_pending_home_sales` | `import akshare as ak; ak.macro_usa_pending_home_sales()` | 美国成屋签约销售指数月率报告，数据区间从 20010301-至今; 单次返回所有历史数据 |
| `macro_usa_personal_spending` | `import akshare as ak; ak.macro_usa_personal_spending()` | 美国个人支出月率报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `macro_usa_phs` | `import akshare as ak; ak.macro_usa_phs()` | 东方财富-经济数据一览-美国-未决房屋销售月率，数据区间从 20080201-至今; 单次返回所有历史数据 |
| `macro_usa_pmi` | `import akshare as ak; ak.macro_usa_pmi()` | 美国 Markit 制造业 PMI 初值报告，数据区间从 20120601-至今; 单次返回所有历史数据 |
| `macro_usa_ppi` | `import akshare as ak; ak.macro_usa_ppi()` | 美国生产者物价指数(PPI)报告，数据区间从 20080226-至今; 单次返回所有历史数据 |
| `macro_usa_real_consumer_spending` | `import akshare as ak; ak.macro_usa_real_consumer_spending()` | 美国实际个人消费支出季率初值报告，数据区间从 20131107-至今; 单次返回所有历史数据 |
| `macro_usa_retail_sales` | `import akshare as ak; ak.macro_usa_retail_sales()` | 美国零售销售月率报告，数据区间从 19920301-至今; 单次返回所有历史数据 |
| `macro_usa_rig_count` | `import akshare as ak; ak.macro_usa_rig_count()` | 贝克休斯钻井报告，数据区间从 19870717-至今; 单次返回所有历史数据 |
| `macro_usa_services_pmi` | `import akshare as ak; ak.macro_usa_services_pmi()` | 美国Markit服务业PMI初值报告，数据区间从 20120701-至今; 单次返回所有历史数据 |
| `macro_usa_spcs20` | `import akshare as ak; ak.macro_usa_spcs20()` | 美国S&P/CS20座大城市房价指数年率报告，数据区间从 20010201-至今; 单次返回所有历史数据 |
| `macro_usa_trade_balance` | `import akshare as ak; ak.macro_usa_trade_balance()` | 美国贸易帐报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `macro_usa_unemployment_rate` | `import akshare as ak; ak.macro_usa_unemployment_rate()` | 美国失业率报告，数据区间从 19700101-至今; 单次返回所有历史数据 |
| `news_economic_baidu` | `import akshare as ak; ak.news_economic_baidu(date='20241107')` | 全球宏观指标重大事件; 单次返回指定 date 的所有历史数据 |

### nlp (2)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `nlp_answer` | `import akshare as ak; ak.nlp_answer(question='姚明的身高')` | 思知-对话机器人的接口，以此来进行智能问答; 单次返回查询的数据结果 |
| `nlp_ownthink` | `import akshare as ak; ak.nlp_ownthink(word='人工智能', indicator='entity')` | 思知-知识图谱的接口，以此来查询知识图谱数据; 单次返回查询的数据结果 |

### option (46)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `option_cffex_hs300_daily_sina` | `import akshare as ak; ak.option_cffex_hs300_daily_sina(symbol='io2004C4450')` | 中金所-沪深300指数-指定合约-日频行情; 单次返回指定合约的日频行情 |
| `option_cffex_hs300_list_sina` | `import akshare as ak; ak.option_cffex_hs300_list_sina()` | 中金所-沪深300指数-所有合约，返回的第一个合约为主力合约; 单次返回所有合约 |
| `option_cffex_hs300_spot_sina` | `import akshare as ak; ak.option_cffex_hs300_spot_sina(symbol='io2104')` | 新浪财经-中金所-沪深300指数-指定合约-实时行情; 单次返回指定合约的实时行情 |
| `option_cffex_sz50_daily_sina` | `import akshare as ak; ak.option_cffex_sz50_daily_sina(symbol='ho2303P2350')` | 中金所-上证50指数-指定合约-日频行情; 单次返回指定合约的日频行情 |
| `option_cffex_sz50_list_sina` | `import akshare as ak; ak.option_cffex_sz50_list_sina()` | 中金所-上证50指数-所有合约，返回的第一个合约为主力合约; 单次返回所有合约 |
| `option_cffex_sz50_spot_sina` | `import akshare as ak; ak.option_cffex_sz50_spot_sina(symbol='ho2303')` | 新浪财经-中金所-上证50指数-指定合约-实时行情; 单次返回指定合约的实时行情 |
| `option_cffex_zz1000_daily_sina` | `import akshare as ak; ak.option_cffex_zz1000_daily_sina(symbol='mo2208P6200')` | 中金所-中证1000指数-指定合约-日频行情; 单次返回指定合约的日频行情 |
| `option_cffex_zz1000_list_sina` | `import akshare as ak; ak.option_cffex_zz1000_list_sina()` | 中金所-中证1000指数-所有合约，返回的第一个合约为主力合约; 单次返回所有合约 |
| `option_cffex_zz1000_spot_sina` | `import akshare as ak; ak.option_cffex_zz1000_spot_sina(symbol='mo2208')` | 新浪财经-中金所-中证1000指数-指定合约-实时行情; 单次返回指定合约的实时行情 |
| `option_comm_info` | `import akshare as ak; ak.option_comm_info(symbol='工业硅期权')` | 九期网-商品期权手续费数据; 单次返回指定 symbol 的所有数据 |
| `option_comm_symbol` | `import akshare as ak; ak.option_comm_symbol()` |  |
| `option_commodity_contract_sina` | `import akshare as ak; ak.option_commodity_contract_sina(symbol='黄金期权')` | 新浪财经-商品期权当前在交易的合约; 单次返回指定 symbol 的所有合约数据 |
| `option_commodity_contract_table_sina` | `import akshare as ak; ak.option_commodity_contract_table_sina(symbol='动力煤期权', contract='zc2103')` | 新浪财经-商品期权的 T 型报价表; 单次返回指定 symbol 和 contract 的所有数据 |
| `option_commodity_hist_sina` | `import akshare as ak; ak.option_commodity_hist_sina(symbol='au2012C328')` | 新浪财经-商品期权的历史行情数据-日频率; 单次返回指定合约的历史行情数据 |
| `option_contract_info_ctp` | `import akshare as ak; ak.option_contract_info_ctp()` | openctp 期权合约信息; 单次返回所有数据 |
| `option_current_day_sse` | `import akshare as ak; ak.option_current_day_sse()` | 上海证券交易所-产品-股票期权-信息披露-当日合约; 单次返回所有数据 |
| `option_current_day_szse` | `import akshare as ak; ak.option_current_day_szse()` | 深圳证券交易所-期权子网-行情数据-当日合约; 单次返回所有数据 |
| `option_current_em` | `import akshare as ak; ak.option_current_em()` | 东方财富网-行情中心-期权市场; 单次返回全部合约的实时行情 |
| `option_daily_stats_sse` | `import akshare as ak; ak.option_daily_stats_sse(date='20240626')` | 上海证券交易所-产品-股票期权-每日统计; 单次返回指定 date 的数据 |
| `option_daily_stats_szse` | `import akshare as ak; ak.option_daily_stats_szse(date='20240626')` | 深圳证券交易所-市场数据-期权数据-日度概况; 单次返回指定 date 的数据 |
| `option_finance_board` | `import akshare as ak; ak.option_finance_board(symbol='华夏上证50ETF期权', end_month='2212')` | 上海证券交易所、深圳证券交易所、中国金融期货交易所的金融期权行情数据; 单次返回当前交易日指定合约期权行情数据 |
| `option_finance_minute_sina` | `import akshare as ak; ak.option_finance_minute_sina(symbol='10002415')` | 新浪财经-金融期权-股票期权分时行情数据; 单次返回指定期权的分时行情数据 |
| `option_finance_sse_underlying` | `import akshare as ak; ak.option_finance_sse_underlying()` |  |
| `option_hist_czce` | `import akshare as ak; ak.option_hist_czce(symbol='白糖期权', trade_date='20240711')` | 郑州商品交易所-商品期权数据; 单次返回指定 symbol 和 trade_date 的期权行情数据 |
| `option_hist_dce` | `import akshare as ak; ak.option_hist_dce(symbol='聚丙烯期权', trade_date='20251016')` | 大连商品交易所-商品期权数据; 单次返回指定 symbol 和 trade_date 的期权日行情数据 |
| `option_hist_gfex` | `import akshare as ak; ak.option_hist_gfex(symbol='工业硅', trade_date='20230418')` | 广州期货交易所-商品期权数据; 单次返回指定 symbol 和 trade_date 的期权行情数据 |
| `option_hist_shfe` | `import akshare as ak; ak.option_hist_shfe(symbol='铝期权', trade_date='20200827')` | 上海期货交易所-商品期权数据; 单次返回指定 symbol 和 trade_date 的期权行情数据，只能获取 20200824 之后的数据 |
| `option_hist_yearly_czce` | `import akshare as ak; ak.option_hist_yearly_czce()` |  |
| `option_lhb_em` | `import akshare as ak; ak.option_lhb_em(symbol='510300', indicator='期权持仓情况-认沽持仓量', trade_date='20220121')` | 东方财富网-数据中心-期货期权-期权龙虎榜单-金融期权; 单次返回指定 symbol, indicator 和 trade_date 的所有数据 |
| `option_margin` | `import akshare as ak; ak.option_margin(symbol='原油期权')` | 唯爱期货-期权保证金; 单次返回指定 symbol 的所有数据 |
| `option_margin_symbol` | `import akshare as ak; ak.option_margin_symbol()` |  |
| `option_minute_em` | `import akshare as ak; ak.option_minute_em(symbol='MO2402-C-5400')` | 东方财富网-行情中心-期权市场-分时行情; 单次返回指定 symbol 的分时行情数据；只能获取近期合约的数据 |
| `option_premium_analysis_em` | `import akshare as ak; ak.option_premium_analysis_em()` | 东方财富网-数据中心-特色数据-期权折溢价; 单次返回所有数据 |
| `option_risk_analysis_em` | `import akshare as ak; ak.option_risk_analysis_em()` | 东方财富网-数据中心-特色数据-期权风险分析; 单次返回所有数据 |
| `option_risk_indicator_sse` | `import akshare as ak; ak.option_risk_indicator_sse(date='20240626')` | 上海证券交易所-产品-股票期权-期权风险指标数据; 单次返回指定 date 的数据 |
| `option_sse_codes_sina` | `import akshare as ak; ak.option_sse_codes_sina(trade_date='202002', underlying='510300')` | 新浪期权-看涨看跌合约合约的代码; 单次返回指定 symbol 合约的代码 |
| `option_sse_daily_sina` | `import akshare as ak; ak.option_sse_daily_sina(symbol='10002273')` | 期权行情日数据; 单次返回期权行情日数据 |
| `option_sse_expire_day_sina` | `import akshare as ak; ak.option_sse_expire_day_sina(trade_date='202002', symbol='50ETF', exchange='null')` | 获取指定到期月份指定品种的剩余到期时间; 单次返回指定品种的品种的剩余到期时间 |
| `option_sse_greeks_sina` | `import akshare as ak; ak.option_sse_greeks_sina(symbol='10002273')` | 新浪财经-期权希腊字母信息表; 单次返回当前交易日的期权希腊字母信息表 |
| `option_sse_list_sina` | `import akshare as ak; ak.option_sse_list_sina(symbol='50ETF', exchange='null')` | 获取期权-上交所-50ETF-合约到期月份列表; 单次返回指定品种的到期月份列表 |
| `option_sse_minute_sina` | `import akshare as ak; ak.option_sse_minute_sina(symbol='10003720')` | 期权行情分钟数据，只能返还当天的分钟数据; 单次返回期权行情分钟数据 |
| `option_sse_spot_price_sina` | `import akshare as ak; ak.option_sse_spot_price_sina(symbol='10002273')` | 期权实时数据; 单次返回期权实时数据 |
| `option_sse_underlying_spot_price_sina` | `import akshare as ak; ak.option_sse_underlying_spot_price_sina(symbol='sh510300')` | 获取期权标的物的实时数据; 单次返回期权标的物的实时数据 |
| `option_value_analysis_em` | `import akshare as ak; ak.option_value_analysis_em()` | 东方财富网-数据中心-特色数据-期权价值分析; 单次返回所有数据 |
| `option_vol_gfex` | `import akshare as ak; ak.option_vol_gfex(symbol='工业硅', trade_date='20230418')` | 广州期货交易所-商品期权数据-隐含波动参考值; 单次返回指定 symbol 和 trade_date 的期权行情数据 |
| `option_vol_shfe` | `import akshare as ak; ak.option_vol_shfe()` |  |

### others (34)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `air_city_table` | `import akshare as ak; ak.air_city_table()` | 所有能获取空气质量数据的城市表; 单次返回所有可以获取的城市表数据 |
| `air_quality_hebei` | `import akshare as ak; ak.air_quality_hebei()` | 河北省实时空气质量数据; 单次返回所有城市数据 |
| `air_quality_hist` | `import akshare as ak; ak.air_quality_hist(city='北京', period='hour', start_date='20200425', end_date='20200427')` | 指定城市和数据频率下并且在指定时间段内的空气质量数据; 单次返回所有的数据，在提取一小时频率数据时请注意时间跨度不宜过长，提取日频率数据的早年数据请分段提取 |
| `air_quality_rank` | `import akshare as ak; ak.air_quality_rank(date='')` | 获取指定 date 时间点上所有城市（168个）的空气质量数据; 单次返回所有的数据 |
| `air_quality_watch_point` | `import akshare as ak; ak.air_quality_watch_point(city='杭州', start_date='2018-01-01', end_date='2020-04-27')` | 获取每个城市的所有空气质量监测点的数据; 单次返回指定城市指定日期区间的所有监测点的空气质量数据 |
| `business_value_artist` | `import akshare as ak; ak.business_value_artist()` | 艺恩-艺人-艺人商业价值; 返回当前的艺人商业价值数据 |
| `car_market_cate_cpca` | `import akshare as ak; ak.car_market_cate_cpca(symbol='轿车', indicator='批发')` | 乘联会-统计数据-车型大类; 单次返回指定 symbol 和 indicator 的数据 |
| `car_market_country_cpca` | `import akshare as ak; ak.car_market_country_cpca()` | 乘联会-统计数据-国别细分市场; 单次返回指定 symbol 和 indicator 的数据 |
| `car_market_fuel_cpca` | `import akshare as ak; ak.car_market_fuel_cpca()` | 乘联会-统计数据-车型大类; 单次返回指定 symbol 的数据 |
| `car_market_man_rank_cpca` | `import akshare as ak; ak.car_market_man_rank_cpca(symbol='狭义乘用车-单月', indicator='批发')` | 乘联会-统计数据-厂商排名; 单次返回指定 symbol 和 indicator 的数据 |
| `car_market_segment_cpca` | `import akshare as ak; ak.car_market_segment_cpca(symbol='轿车')` | 乘联会-统计数据-级别细分市场; 单次返回指定 symbol 的数据 |
| `car_market_total_cpca` | `import akshare as ak; ak.car_market_total_cpca(symbol='狭义乘用车', indicator='产量')` | 乘联会-统计数据-总体市场; 单次返回指定 symbol 和 indicator 的数据 |
| `car_sale_rank_gasgoo` | `import akshare as ak; ak.car_sale_rank_gasgoo(symbol='品牌榜', date='202311')` | 盖世汽车资讯的汽车销量排行榜数据; 单次返回指定 symbol 和 date 的汽车销量排行榜数据 |
| `forbes_rank` | `import akshare as ak; ak.forbes_rank(symbol='2020福布斯中国400富豪榜')` | 福布斯中国-榜单数据，一共 87 个指标的数据可以获取; 单次返回指定 symbol 的数据 |
| `game_hot_rank_taptap` | `import akshare as ak; ak.game_hot_rank_taptap(symbol='热玩榜')` | 按照榜单类型查询 TapTap 平台游戏排行榜数据; 单次返回指定榜单的全部游戏排名数据 |
| `hurun_rank` | `import akshare as ak; ak.hurun_rank(indicator='胡润百富榜', year='2023')` | 胡润百富榜单；富豪榜系列，创业系列，500强系列，特色系列; 单次返回指定 indicator 和 year 的榜单数据 |
| `index_bloomberg_billionaires` | `import akshare as ak; ak.index_bloomberg_billionaires()` | 彭博亿万富豪指数，全球前 500 名；该接口需要使用代理访问; 单次返回所有数据彭博亿万富豪排名数据 |
| `index_bloomberg_billionaires_hist` | `import akshare as ak; ak.index_bloomberg_billionaires_hist(year='2019')` | 按照年份查询彭博亿万富豪指数；该接口需要使用代理访问; 单次返回当年所有数据彭博亿万富豪排名数据 |
| `movie_boxoffice_cinema_daily` | `import akshare as ak; ak.movie_boxoffice_cinema_daily(date='20240219')` | 指定日期的每日各影院的票房数据; 指定日期各影院的票房数据，注意当前日期的数据需要第二日才可以获取 |
| `movie_boxoffice_cinema_weekly` | `import akshare as ak; ak.movie_boxoffice_cinema_weekly(date='20240219')` | 指定日期的完整周各影院的票房数据; 指定日期的完整周各影院的票房数据，注意当前日期的数据只能返回上周的数据 |
| `movie_boxoffice_daily` | `import akshare as ak; ak.movie_boxoffice_daily(date='20240219')` | 指定日期的电影票房数据，每日 10:30, 12:30更新日票房，16:30 同时补充前 7 日票房; 只能指定最近的日期 |
| `movie_boxoffice_monthly` | `import akshare as ak; ak.movie_boxoffice_monthly(date='20240218')` | 获取指定日期所在月份的票房数据，每月5号更新上月票房，并补充之前两个月票房; 指定日期所在月份的票房数据，只能获取最近月份的数据 |
| `movie_boxoffice_realtime` | `import akshare as ak; ak.movie_boxoffice_realtime()` | 当前时刻的实时电影票房数据，每 5 分钟更新一次数据，实时票房包含今天未开映场次已售出的票房; 当前时刻的实时票房数据 |
| `movie_boxoffice_weekly` | `import akshare as ak; ak.movie_boxoffice_weekly(date='20240218')` | 指定日期所在完整周的票房数据，影片周票房数据初始更新周期为每周二，下周二补充数据; 指定日期所在完整周的票房数据 |
| `movie_boxoffice_yearly` | `import akshare as ak; ak.movie_boxoffice_yearly(date='20240218')` | 指定日期所在年度的票房数据; 指定日期所在年度的票房数据，只能获取最近年度的数据 |
| `movie_boxoffice_yearly_first_week` | `import akshare as ak; ak.movie_boxoffice_yearly_first_week(date='20201018')` | 指定日期所在年度的年度首周票房数据; 指定日期所在年度的年度首周票房数据，只能获取最近年度的数据 |
| `news_cctv` | `import akshare as ak; ak.news_cctv(date='20240424')` | 新闻联播文字稿，数据区间从 20160330-至今; 单次返回指定日期新闻联播文字稿数据 |
| `online_value_artist` | `import akshare as ak; ak.online_value_artist()` | 艺恩-艺人-艺人流量价值; 返回当前的艺人流量价值数据 |
| `stock_js_weibo_report` | `import akshare as ak; ak.stock_js_weibo_report(time_period='CNHOUR12')` | 微博舆情报告中近期受关注的股票; 单次返回指定时间内微博舆情报告中近期受关注的股票 |
| `sunrise_daily` | `import akshare as ak; ak.sunrise_daily(date='20240428', city='beijing')` | 中国各大城市-日出和日落时间，数据区间从 19990101-至今，推荐使用代理访问; 单次返回指定日期和指定城市的数据 |
| `sunrise_monthly` | `import akshare as ak; ak.sunrise_monthly(date='20240428', city='beijing')` | 中国各大城市-日出和日落时间，数据区间从 19990101-至今，推荐使用代理访问; 单次返回指定日期所在月份每天的数据，如果是未来日期则为预测值 |
| `video_tv` | `import akshare as ak; ak.video_tv()` | 艺恩-视频放映-电视剧集; 返回前一日的电视剧播映数据 |
| `video_variety_show` | `import akshare as ak; ak.video_variety_show()` | 艺恩-视频放映-综艺节目; 返回前一日的综艺播映数据 |
| `xincaifu_rank` | `import akshare as ak; ak.xincaifu_rank(year='2022')` | 新财富 500 富豪榜，从 2003 年至今; 单次返回指定年份的富豪榜数据 |

### qdii (3)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `qdii_a_index_jsl` | `import akshare as ak; ak.qdii_a_index_jsl()` | 集思录-T+0 QDII-亚洲市场-亚洲指数; 单次返回所有数据 |
| `qdii_e_comm_jsl` | `import akshare as ak; ak.qdii_e_comm_jsl()` | 集思录-T+0 QDII-欧美市场-欧美商品; 单次返回所有数据 |
| `qdii_e_index_jsl` | `import akshare as ak; ak.qdii_e_index_jsl()` | 集思录-T+0 QDII-欧美市场-欧美指数; 单次返回所有数据 |

### qhkc_web (8)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_qhkc_fund_bs` | `import akshare as ak; ak.get_qhkc_fund_bs()` |  |
| `get_qhkc_fund_money_change` | `import akshare as ak; ak.get_qhkc_fund_money_change()` |  |
| `get_qhkc_fund_position` | `import akshare as ak; ak.get_qhkc_fund_position()` |  |
| `get_qhkc_index` | `import akshare as ak; ak.get_qhkc_index()` |  |
| `get_qhkc_index_profit_loss` | `import akshare as ak; ak.get_qhkc_index_profit_loss()` |  |
| `get_qhkc_index_trend` | `import akshare as ak; ak.get_qhkc_index_trend()` |  |
| `qhkc_tool_foreign` | `import akshare as ak; ak.qhkc_tool_foreign()` |  |
| `qhkc_tool_gdp` | `import akshare as ak; ak.qhkc_tool_gdp()` |  |

### reits (1)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `reits_hist_min_em` | `import akshare as ak; ak.reits_hist_min_em()` |  |

### spot (15)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `spot_corn_price_soozhu` | `import akshare as ak; ak.spot_corn_price_soozhu()` | 搜猪-生猪大数据-全国玉米价格走势; 单次返回近半个月的历史数据 |
| `spot_golden_benchmark_sge` | `import akshare as ak; ak.spot_golden_benchmark_sge()` | 上海黄金交易所-数据资讯-上海金基准价-历史数据; 单次返回所有历史数据 |
| `spot_hist_sge` | `import akshare as ak; ak.spot_hist_sge(symbol='Au99.99')` | 上海黄金交易所-数据资讯-行情走势-历史数据; 单次返回指定 symbol 的所有历史数据 |
| `spot_hog_crossbred_soozhu` | `import akshare as ak; ak.spot_hog_crossbred_soozhu()` | 搜猪-生猪大数据-全国后备二元母猪; 单次返回近半个月的历史数据 |
| `spot_hog_lean_price_soozhu` | `import akshare as ak; ak.spot_hog_lean_price_soozhu()` | 搜猪-生猪大数据-全国瘦肉型肉猪; 单次返回近半个月的历史数据 |
| `spot_hog_soozhu` | `import akshare as ak; ak.spot_hog_soozhu()` | 搜猪-生猪大数据-各省均价实时排行榜; 单次返回所有实时数据 |
| `spot_hog_three_way_soozhu` | `import akshare as ak; ak.spot_hog_three_way_soozhu()` | 搜猪-生猪大数据-全国三元仔猪; 单次返回近半个月的历史数据 |
| `spot_hog_year_trend_soozhu` | `import akshare as ak; ak.spot_hog_year_trend_soozhu()` | 搜猪-生猪大数据-今年以来全国出栏均价走势; 单次返回近一年所有历史数据 |
| `spot_mixed_feed_soozhu` | `import akshare as ak; ak.spot_mixed_feed_soozhu()` | 搜猪-生猪大数据-全国育肥猪合料（含自配料）半月走势; 单次返回近半个月的历史数据 |
| `spot_price_qh` | `import akshare as ak; ak.spot_price_qh(symbol='螺纹钢')` | 99 期货-数据-期现-现货走势; 单次返回指定 symbol 的所有历史数据；由于数据源限制，只能获取个别品种 |
| `spot_price_table_qh` | `import akshare as ak; ak.spot_price_table_qh()` |  |
| `spot_quotations_sge` | `import akshare as ak; ak.spot_quotations_sge(symbol='Au99.99')` | 上海黄金交易所-数据资讯-行情走势-实时数据; 单次返回指定 symbol 的所有行情数据 |
| `spot_silver_benchmark_sge` | `import akshare as ak; ak.spot_silver_benchmark_sge()` | 上海黄金交易所-数据资讯-上海银基准价-历史数据; 单次返回所有历史数据 |
| `spot_soybean_price_soozhu` | `import akshare as ak; ak.spot_soybean_price_soozhu()` | 搜猪-生猪大数据-全国豆粕价格走势; 单次返回近半个月的历史数据 |
| `spot_symbol_table_sge` | `import akshare as ak; ak.spot_symbol_table_sge()` |  |

### stock (388)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `get_us_stock_name` | `import akshare as ak; ak.get_us_stock_name()` |  |
| `news_report_time_baidu` | `import akshare as ak; ak.news_report_time_baidu(date='20241107')` | 百度股市通-财报发行; 单次获取指定 date 的财报发行，提供港股的财报发行数据 |
| `news_trade_notify_dividend_baidu` | `import akshare as ak; ak.news_trade_notify_dividend_baidu(date='20251126')` | 百度股市通-交易提醒-分红派息; 单次获取指定 date 的分红派息数据，提供港股的分红派息数据 |
| `news_trade_notify_suspend_baidu` | `import akshare as ak; ak.news_trade_notify_suspend_baidu(date='20241107')` | 百度股市通-交易提醒-停复牌; 单次获取指定 date 的停复牌数据，提供港股的停复牌数据 |
| `stock_a_all_pb` | `import akshare as ak; ak.stock_a_all_pb()` | 乐咕乐股-A 股等权重与中位数市净率; 单次返回所有数据 |
| `stock_a_below_net_asset_statistics` | `import akshare as ak; ak.stock_a_below_net_asset_statistics(symbol='全部A股')` | 乐咕乐股-A 股破净股统计数据; 单次获取指定 symbol 的所有历史数据 |
| `stock_a_congestion_lg` | `import akshare as ak; ak.stock_a_congestion_lg()` | 乐咕乐股-大盘拥挤度; 单次获取近 4 年的历史数据 |
| `stock_a_gxl_lg` | `import akshare as ak; ak.stock_a_gxl_lg(symbol='上证A股')` | 乐咕乐股-股息率-A 股股息率; 单次获取指定 symbol 的所有历史数据 |
| `stock_a_high_low_statistics` | `import akshare as ak; ak.stock_a_high_low_statistics(symbol='all')` | 不同市场的创新高和新低的股票数量; 单次获取指定 market 的近两年的历史数据 |
| `stock_a_ttm_lyr` | `import akshare as ak; ak.stock_a_ttm_lyr()` | 乐咕乐股-A 股等权重市盈率与中位数市盈率; 单次返回所有数据 |
| `stock_account_statistics_em` | `import akshare as ak; ak.stock_account_statistics_em()` | 东方财富网-数据中心-特色数据-股票账户统计; 单次返回从 201504 开始 202308 的所有历史数据 |
| `stock_add_stock` | `import akshare as ak; ak.stock_add_stock(symbol='600004')` | 新浪财经-发行与分配-增发; 单次指定 symbol 的股票增发详情数据 |
| `stock_allotment_cninfo` | `import akshare as ak; ak.stock_allotment_cninfo(symbol='600030', start_date='19900101', end_date='20241022')` | 巨潮资讯-个股-配股实施方案; 单次获取指定 symbol 在 start_date 和 end_date 之间的公司股本变动数据 |
| `stock_analyst_detail_em` | `import akshare as ak; ak.stock_analyst_detail_em(analyst_id='11000200926', indicator='最新跟踪成分股')` | 东方财富网-数据中心-研究报告-东方财富分析师指数-分析师详情; 单次获取指定 indicator 指定的数据 |
| `stock_analyst_rank_em` | `import akshare as ak; ak.stock_analyst_rank_em(year='2024')` | 东方财富网-数据中心-研究报告-东方财富分析师指数; 单次获取指定年份的所有数据 |
| `stock_balance_sheet_by_report_delisted_em` | `import akshare as ak; ak.stock_balance_sheet_by_report_delisted_em(symbol='SZ000013')` | 东方财富-股票-财务分析-资产负债表-已退市股票-按报告期; 单次获取指定 symbol 的资产负债表-按报告期数据 |
| `stock_balance_sheet_by_report_em` | `import akshare as ak; ak.stock_balance_sheet_by_report_em(symbol='SH600519')` | 东方财富-股票-财务分析-资产负债表-按报告期; 单次获取指定 symbol 的资产负债表-按报告期数据 |
| `stock_balance_sheet_by_yearly_em` | `import akshare as ak; ak.stock_balance_sheet_by_yearly_em(symbol='SH600519')` | 东方财富-股票-财务分析-资产负债表-按年度; 单次获取指定 symbol 的资产负债表-按年度数据 |
| `stock_bid_ask_em` | `import akshare as ak; ak.stock_bid_ask_em(symbol='000001')` | 东方财富-行情报价; 单次返回指定股票的行情报价数据 |
| `stock_bj_a_spot_em` | `import akshare as ak; ak.stock_bj_a_spot_em()` | 东方财富网-京 A 股-实时行情数据; 单次返回所有京 A 股上市公司的实时行情数据 |
| `stock_board_change_em` | `import akshare as ak; ak.stock_board_change_em()` | 东方财富-行情中心-当日板块异动详情; 返回最近交易日的数据 |
| `stock_board_concept_cons_em` | `import akshare as ak; ak.stock_board_concept_cons_em(symbol='融资融券')` | 东方财富-沪深板块-概念板块-板块成份; 单次返回当前时刻所有成份股 |
| `stock_board_concept_hist_em` | `import akshare as ak; ak.stock_board_concept_hist_em(symbol='绿色电力', period='daily', start_date='20220101', end_date='20250227', adjust='')` | 东方财富-沪深板块-概念板块-历史行情数据; 单次返回指定 symbol 和 adjust 的历史数据 |
| `stock_board_concept_hist_min_em` | `import akshare as ak; ak.stock_board_concept_hist_min_em(symbol='长寿药', period='1')` | 东方财富-沪深板块-概念板块-分时历史行情数据; 单次返回指定 symbol 和 period 的历史数据 |
| `stock_board_concept_index_ths` | `import akshare as ak; ak.stock_board_concept_index_ths(symbol='阿里巴巴概念', start_date='20200101', end_date='20250321')` | 同花顺-板块-概念板块-指数日频率数据; 单次返回所有日频指数数据 |
| `stock_board_concept_info_ths` | `import akshare as ak; ak.stock_board_concept_info_ths(symbol='阿里巴巴概念')` | 同花顺-板块-概念板块-板块简介; 单次返回所有数据 |
| `stock_board_concept_name_em` | `import akshare as ak; ak.stock_board_concept_name_em()` | 东方财富网-行情中心-沪深京板块-概念板块; 单次返回当前时刻所有概念板块的实时行情数据 |
| `stock_board_concept_spot_em` | `import akshare as ak; ak.stock_board_concept_spot_em(symbol='可燃冰')` | 东方财富网-行情中心-沪深京板块-概念板块-实时行情; 单次返回指定概念板块的实时行情数据 |
| `stock_board_industry_cons_em` | `import akshare as ak; ak.stock_board_industry_cons_em(symbol='小金属')` | 东方财富-沪深板块-行业板块-板块成份; 单次返回指定 symbol 的所有成份股 |
| `stock_board_industry_hist_em` | `import akshare as ak; ak.stock_board_industry_hist_em(symbol='小金属', start_date='20211201', end_date='20240222', period='日k', adjust='')` | 东方财富-沪深板块-行业板块-历史行情数据; 单次返回指定 symbol 和 adjust 的所有历史数据 |
| `stock_board_industry_hist_min_em` | `import akshare as ak; ak.stock_board_industry_hist_min_em(symbol='小金属', period='1')` | 东方财富-沪深板块-行业板块-分时历史行情数据; 单次返回指定 symbol 和 period 的所有历史数据 |
| `stock_board_industry_index_ths` | `import akshare as ak; ak.stock_board_industry_index_ths(symbol='元件', start_date='20240101', end_date='20240718')` | 同花顺-板块-行业板块-指数日频率数据; 单次返回所有日频指数数据 |
| `stock_board_industry_name_em` | `import akshare as ak; ak.stock_board_industry_name_em()` | 东方财富-沪深京板块-行业板块; 单次返回当前时刻所有行业板的实时行情数据 |
| `stock_board_industry_spot_em` | `import akshare as ak; ak.stock_board_industry_spot_em(symbol='小金属')` | 东方财富网-沪深板块-行业板块-实时行情; 单次返回指定板块的实时行情数据 |
| `stock_board_industry_summary_ths` | `import akshare as ak; ak.stock_board_industry_summary_ths()` | 同花顺-同花顺行业一览表; 单次返回当前时刻同花顺行业一览表 |
| `stock_buffett_index_lg` | `import akshare as ak; ak.stock_buffett_index_lg()` | 乐估乐股-底部研究-巴菲特指标; 单次获取所有历史数据 |
| `stock_cash_flow_sheet_by_quarterly_em` | `import akshare as ak; ak.stock_cash_flow_sheet_by_quarterly_em(symbol='SH600519')` | 东方财富-股票-财务分析-现金流量表-按单季度; 单次获取指定 symbol 的现金流量表-按单季度数据 |
| `stock_cash_flow_sheet_by_report_delisted_em` | `import akshare as ak; ak.stock_cash_flow_sheet_by_report_delisted_em(symbol='SZ000013')` | 东方财富-股票-财务分析-现金流量表-已退市股票-按报告期; 单次获取指定 symbol 的现金流量表-按报告期数据 |
| `stock_cash_flow_sheet_by_report_em` | `import akshare as ak; ak.stock_cash_flow_sheet_by_report_em(symbol='SH600519')` | 东方财富-股票-财务分析-现金流量表-按报告期; 单次获取指定 symbol 的现金流量表-按报告期数据 |
| `stock_cash_flow_sheet_by_yearly_em` | `import akshare as ak; ak.stock_cash_flow_sheet_by_yearly_em(symbol='SH600519')` | 东方财富-股票-财务分析-现金流量表-按年度; 单次获取指定 symbol 的现金流量表-按年度数据 |
| `stock_cg_equity_mortgage_cninfo` | `import akshare as ak; ak.stock_cg_equity_mortgage_cninfo(date='20210930')` | 巨潮资讯-数据中心-专题统计-公司治理-股权质押; 单次指定 date 的股权质押数据 |
| `stock_cg_guarantee_cninfo` | `import akshare as ak; ak.stock_cg_guarantee_cninfo(symbol='全部', start_date='20180630', end_date='20210927')` | 巨潮资讯-数据中心-专题统计-公司治理-对外担保; 单次指定 symbol 和起始日期的对外担保数据 |
| `stock_cg_lawsuit_cninfo` | `import akshare as ak; ak.stock_cg_lawsuit_cninfo(symbol='全部', start_date='20180630', end_date='20210927')` | 巨潮资讯-数据中心-专题统计-公司治理-公司诉讼; 单次指定 symbol 和起始日期的公司诉讼数据 |
| `stock_changes_em` | `import akshare as ak; ak.stock_changes_em(symbol='大笔买入')` | 东方财富-行情中心-盘口异动数据; 单次指定 symbol 的最近交易日的盘口异动数据 |
| `stock_circulate_stock_holder` | `import akshare as ak; ak.stock_circulate_stock_holder(symbol='600000')` | 新浪财经-股东股本-流通股东; 单次获取指定 symbol 的流通股东数据 |
| `stock_comment_detail_scrd_desire_em` | `import akshare as ak; ak.stock_comment_detail_scrd_desire_em(symbol='600000')` | 东方财富网-数据中心-特色数据-千股千评-市场热度-市场参与意愿; 单次获取所有数据 |
| `stock_comment_detail_scrd_focus_em` | `import akshare as ak; ak.stock_comment_detail_scrd_focus_em(symbol='600000')` | 东方财富网-数据中心-特色数据-千股千评-市场热度-用户关注指数; 单次获取所有数据 |
| `stock_comment_detail_zhpj_lspf_em` | `import akshare as ak; ak.stock_comment_detail_zhpj_lspf_em(symbol='600000')` | 东方财富网-数据中心-特色数据-千股千评-综合评价-历史评分; 单次获取指定 symbol 的数据 |
| `stock_comment_detail_zlkp_jgcyd_em` | `import akshare as ak; ak.stock_comment_detail_zlkp_jgcyd_em(symbol='600000')` | 东方财富网-数据中心-特色数据-千股千评-主力控盘-机构参与度; 单次获取所有 symbol 的数据 |
| `stock_comment_em` | `import akshare as ak; ak.stock_comment_em()` | 东方财富网-数据中心-特色数据-千股千评; 单次获取所有数据 |
| `stock_concept_cons_futu` | `import akshare as ak; ak.stock_concept_cons_futu(symbol='特朗普概念股')` | 富途牛牛-主题投资-概念板块-成分股; 单次返回指定概念板块成分股数据 |
| `stock_concept_fund_flow_hist` | `import akshare as ak; ak.stock_concept_fund_flow_hist(symbol='数据要素')` | 东方财富网-数据中心-资金流向-概念资金流-概念历史资金流; 单次获取指定 symbol 的近期概念历史资金流数据 |
| `stock_cy_a_spot_em` | `import akshare as ak; ak.stock_cy_a_spot_em()` | 东方财富网-创业板-实时行情; 单次返回所有创业板的实时行情数据 |
| `stock_cyq_em` | `import akshare as ak; ak.stock_cyq_em(symbol='000001', adjust='')` | 东方财富网-概念板-行情中心-日K-筹码分布; 单次返回指定 symbol 和 adjust 的近 90 个交易日数据 |
| `stock_dividend_cninfo` | `import akshare as ak; ak.stock_dividend_cninfo(symbol='600009')` | 巨潮资讯-个股-历史分红; 单次获取指定股票的历史分红数据 |
| `stock_dxsyl_em` | `import akshare as ak; ak.stock_dxsyl_em()` | 东方财富网-数据中心-新股申购-打新收益率; 单次获取所有打新收益率数据 |
| `stock_dzjy_hygtj` | `import akshare as ak; ak.stock_dzjy_hygtj(symbol='近三月')` | 东方财富网-数据中心-大宗交易-活跃 A 股统计; 单次返回所有历史数据 |
| `stock_dzjy_hyyybtj` | `import akshare as ak; ak.stock_dzjy_hyyybtj(symbol='近3日')` | 东方财富网-数据中心-大宗交易-活跃营业部统计; 单次返回所有历史数据 |
| `stock_dzjy_mrmx` | `import akshare as ak; ak.stock_dzjy_mrmx(symbol='A股', start_date='20220104', end_date='20220104')` | 东方财富网-数据中心-大宗交易-每日明细; 单次返回所有历史数据 |
| `stock_dzjy_mrtj` | `import akshare as ak; ak.stock_dzjy_mrtj(start_date='20220105', end_date='20220105')` | 东方财富网-数据中心-大宗交易-每日统计; 单次返回所有历史数据 |
| `stock_dzjy_sctj` | `import akshare as ak; ak.stock_dzjy_sctj()` | 东方财富网-数据中心-大宗交易-市场统计; 单次返回所有历史数据 |
| `stock_dzjy_yybph` | `import akshare as ak; ak.stock_dzjy_yybph(symbol='近三月')` | 东方财富网-数据中心-大宗交易-营业部排行; 单次返回所有历史数据 |
| `stock_ebs_lg` | `import akshare as ak; ak.stock_ebs_lg()` | 乐咕乐股-股债利差; 单次所有历史数据 |
| `stock_esg_hz_sina` | `import akshare as ak; ak.stock_esg_hz_sina()` | 新浪财经-ESG评级中心-ESG评级-华证指数; 单次返回所有数据 |
| `stock_esg_msci_sina` | `import akshare as ak; ak.stock_esg_msci_sina()` | 新浪财经-ESG评级中心-ESG评级-MSCI; 单次返回所有数据 |
| `stock_esg_rate_sina` | `import akshare as ak; ak.stock_esg_rate_sina()` | 新浪财经-ESG评级中心-ESG评级-ESG评级数据; 单次返回所有数据 |
| `stock_esg_rft_sina` | `import akshare as ak; ak.stock_esg_rft_sina()` | 新浪财经-ESG评级中心-ESG评级-路孚特; 单次返回所有数据 |
| `stock_esg_zd_sina` | `import akshare as ak; ak.stock_esg_zd_sina()` | 新浪财经-ESG评级中心-ESG评级-秩鼎; 单次返回所有数据 |
| `stock_fhps_detail_em` | `import akshare as ak; ak.stock_fhps_detail_em(symbol='300073')` | 东方财富网-数据中心-分红送配-分红送配详情; 单次获取指定 symbol 的分红配送详情数据 |
| `stock_fhps_detail_ths` | `import akshare as ak; ak.stock_fhps_detail_ths(symbol='603444')` | 同花顺-分红情况; 单次获取指定 symbol 的分红情况数据 |
| `stock_fhps_em` | `import akshare as ak; ak.stock_fhps_em(date='20231231')` | 东方财富-数据中心-年报季报-分红配送; 单次获取指定日期的分红配送数据 |
| `stock_financial_abstract` | `import akshare as ak; ak.stock_financial_abstract(symbol='600004')` | 新浪财经-财务报表-关键指标; 单次获取关键指标所有历史数据 |
| `stock_financial_abstract_new_ths` | `import akshare as ak; ak.stock_financial_abstract_new_ths(symbol='000063', indicator='按报告期')` | 同花顺-财务指标-重要指标；替换 stock_financial_abstract_ths 接口; 单次获取指定 symbol 的所有数据 |
| `stock_financial_analysis_indicator` | `import akshare as ak; ak.stock_financial_analysis_indicator(symbol='600004', start_year='2020')` | 新浪财经-财务分析-财务指标; 单次获取指定 symbol 和 start_year 的所有财务指标历史数据 |
| `stock_financial_analysis_indicator_em` | `import akshare as ak; ak.stock_financial_analysis_indicator_em(symbol='301389.SZ', indicator='按报告期')` | 东方财富-A股-财务分析-主要指标; 单次获取指定 symbol 的所有数据 |
| `stock_financial_benefit_new_ths` | `import akshare as ak; ak.stock_financial_benefit_new_ths(symbol='000063', indicator='按报告期')` | 同花顺-财务指标-利润表；替换 stock_financial_benefit_ths 接口; 单次获取利润表所有历史数据 |
| `stock_financial_cash_new_ths` | `import akshare as ak; ak.stock_financial_cash_new_ths(symbol='000063', indicator='按年度')` | 同花顺-财务指标-现金流量表；替换 stock_financial_cash_ths 接口; 单次获取现金流量表所有历史数据 |
| `stock_financial_debt_new_ths` | `import akshare as ak; ak.stock_financial_debt_new_ths(symbol='000063', indicator='按年度')` | 同花顺-财务指标-资产负债表；替换 stock_financial_debt_ths 接口; 单次获取资产负债表所有历史数据 |
| `stock_financial_hk_analysis_indicator_em` | `import akshare as ak; ak.stock_financial_hk_analysis_indicator_em(symbol='00700', indicator='年度')` | 东方财富-港股-财务分析-主要指标; 单次获取财务指标所有历史数据 |
| `stock_financial_hk_report_em` | `import akshare as ak; ak.stock_financial_hk_report_em(stock='00700', symbol='资产负债表', indicator='年度')` | 东方财富-港股-财务报表-三大报表; 单次获取指定股票、指定报告且指定报告期的数据 |
| `stock_financial_report_sina` | `import akshare as ak; ak.stock_financial_report_sina(stock='sh600600', symbol='资产负债表')` | 新浪财经-财务报表-三大报表; 单次获取指定报表的所有年份数据的历史数据 |
| `stock_financial_us_analysis_indicator_em` | `import akshare as ak; ak.stock_financial_us_analysis_indicator_em(symbol='TSLA', indicator='年报')` | 东方财富-美股-财务分析-主要指标; 单次获取指定股票的所有历史数据 |
| `stock_financial_us_report_em` | `import akshare as ak; ak.stock_financial_us_report_em(stock='TSLA', symbol='资产负债表', indicator='年报')` | 东方财富-美股-财务分析-三大报表; 单次获取指定股票、指定报告且指定报告期的数据 |
| `stock_fund_flow_big_deal` | `import akshare as ak; ak.stock_fund_flow_big_deal()` | 同花顺-数据中心-资金流向-大单追踪; 单次获取当前时点的所有大单追踪数据 |
| `stock_fund_flow_concept` | `import akshare as ak; ak.stock_fund_flow_concept(symbol='即时')` | 同花顺-数据中心-资金流向-概念资金流; 单次获取指定 symbol 的概念资金流数据 |
| `stock_fund_flow_individual` | `import akshare as ak; ak.stock_fund_flow_individual(symbol='即时')` | 同花顺-数据中心-资金流向-个股资金流; 单次获取指定 symbol 的概念资金流数据 |
| `stock_fund_flow_industry` | `import akshare as ak; ak.stock_fund_flow_industry(symbol='即时')` | 同花顺-数据中心-资金流向-行业资金流; 单次获取指定 symbol 的行业资金流数据 |
| `stock_fund_stock_holder` | `import akshare as ak; ak.stock_fund_stock_holder(symbol='601318')` | 新浪财经-股本股东-基金持股; 新浪财经-股本股东-基金持股所有历史数据 |
| `stock_gddh_em` | `import akshare as ak; ak.stock_gddh_em()` | 东方财富网-数据中心-股东大会; 单次返回所有数据 |
| `stock_gdfx_free_holding_analyse_em` | `import akshare as ak; ak.stock_gdfx_free_holding_analyse_em(date='20230930')` | 东方财富网-数据中心-股东分析-股东持股分析-十大流通股东; 单次获取返回所有数据 |
| `stock_gdfx_free_holding_change_em` | `import akshare as ak; ak.stock_gdfx_free_holding_change_em(date='20210930')` | 东方财富网-数据中心-股东分析-股东持股变动统计-十大流通股东; 单次返回指定 date 的所有数据 |
| `stock_gdfx_free_holding_detail_em` | `import akshare as ak; ak.stock_gdfx_free_holding_detail_em(date='20210930')` | 东方财富网-数据中心-股东分析-股东持股明细-十大流通股东; 单次返回指定 date 的所有数据 |
| `stock_gdfx_free_holding_statistics_em` | `import akshare as ak; ak.stock_gdfx_free_holding_statistics_em(date='20210930')` | 东方财富网-数据中心-股东分析-股东持股统计-十大股东; 单次返回指定 date 的所有数据 |
| `stock_gdfx_free_holding_teamwork_em` | `import akshare as ak; ak.stock_gdfx_free_holding_teamwork_em(symbol='社保')` | 东方财富网-数据中心-股东分析-股东协同-十大流通股东; 单次返回所有数据 |
| `stock_gdfx_free_top_10_em` | `import akshare as ak; ak.stock_gdfx_free_top_10_em(symbol='sh688686', date='20240930')` | 东方财富网-个股-十大流通股东; 单次返回指定 symbol 和 date 的所有数据 |
| `stock_gdfx_holding_analyse_em` | `import akshare as ak; ak.stock_gdfx_holding_analyse_em(date='20210930')` | 东方财富网-数据中心-股东分析-股东持股分析-十大股东; 单次获取返回所有数据 |
| `stock_gdfx_holding_change_em` | `import akshare as ak; ak.stock_gdfx_holding_change_em(date='20210930')` | 东方财富网-数据中心-股东分析-股东持股变动统计-十大股东; 单次返回指定 date 的所有数据 |
| `stock_gdfx_holding_detail_em` | `import akshare as ak; ak.stock_gdfx_holding_detail_em(date='20230331', indicator='个人', symbol='新进')` | 东方财富网-数据中心-股东分析-股东持股明细-十大股东; 单次返回指定参数的所有数据 |
| `stock_gdfx_holding_statistics_em` | `import akshare as ak; ak.stock_gdfx_holding_statistics_em(date='20210930')` | 东方财富网-数据中心-股东分析-股东持股统计-十大股东; 单次返回指定 date 的所有数据 |
| `stock_gdfx_holding_teamwork_em` | `import akshare as ak; ak.stock_gdfx_holding_teamwork_em(symbol='社保')` | 东方财富网-数据中心-股东分析-股东协同-十大股东; 单次返回所有数据 |
| `stock_gdfx_top_10_em` | `import akshare as ak; ak.stock_gdfx_top_10_em(symbol='sh688686', date='20210630')` | 东方财富网-个股-十大股东; 单次返回指定 symbol 和 date 的所有数据 |
| `stock_ggcg_em` | `import akshare as ak; ak.stock_ggcg_em(symbol='全部')` | 东方财富网-数据中心-特色数据-高管持股; 单次获取所有高管持股数据数据 |
| `stock_gpzy_distribute_statistics_bank_em` | `import akshare as ak; ak.stock_gpzy_distribute_statistics_bank_em()` | 东方财富网-数据中心-特色数据-股权质押-质押机构分布统计-银行; 单次返回当前时点所有历史数据 |
| `stock_gpzy_distribute_statistics_company_em` | `import akshare as ak; ak.stock_gpzy_distribute_statistics_company_em()` | 东方财富网-数据中心-特色数据-股权质押-质押机构分布统计-证券公司; 单次返回当前时点所有历史数据 |
| `stock_gpzy_individual_pledge_ratio_detail_em` | `import akshare as ak; ak.stock_gpzy_individual_pledge_ratio_detail_em(symbol='603132')` | 东方财富网-数据中心-股权质押-个股; 单次所有历史数据 |
| `stock_gpzy_industry_data_em` | `import akshare as ak; ak.stock_gpzy_industry_data_em()` | 东方财富网-数据中心-特色数据-股权质押-上市公司质押比例-行业数据; 单次返回所有历史数据 |
| `stock_gpzy_pledge_ratio_detail_em` | `import akshare as ak; ak.stock_gpzy_pledge_ratio_detail_em()` | 东方财富网-数据中心-特色数据-股权质押-重要股东股权质押明细; 单次所有历史数据，由于数据量比较大需要等待一定时间 |
| `stock_gpzy_pledge_ratio_em` | `import akshare as ak; ak.stock_gpzy_pledge_ratio_em(date='20241220')` | 东方财富网-数据中心-特色数据-股权质押-上市公司质押比例; 单次返回指定交易日的所有历史数据；其中的交易日需要根据网站提供的为准；请访问 http://data.eastmoney.com/gpzy… |
| `stock_gpzy_profile_em` | `import akshare as ak; ak.stock_gpzy_profile_em()` | 东方财富网-数据中心-特色数据-股权质押-股权质押市场概况; 单次所有历史数据，由于数据量比较大需要等待一定时间 |
| `stock_gsrl_gsdt_em` | `import akshare as ak; ak.stock_gsrl_gsdt_em(date='20230808')` | 东方财富网-数据中心-股市日历-公司动态; 单次返回指定交易日的数据 |
| `stock_history_dividend` | `import akshare as ak; ak.stock_history_dividend()` | 新浪财经-发行与分配-历史分红; 单次获取所有股票的历史分红数据 |
| `stock_history_dividend_detail` | `import akshare as ak; ak.stock_history_dividend_detail(symbol='600012', indicator='分红')` | 新浪财经-发行与分配-分红配股; 单次获取指定股票的新浪财经-发行与分配-分红配股详情 |
| `stock_hk_company_profile_em` | `import akshare as ak; ak.stock_hk_company_profile_em(symbol='03900')` | 东方财富-港股-公司资料; 单次返回全部数据 |
| `stock_hk_daily` | `import akshare as ak; ak.stock_hk_daily(symbol='00700', adjust='hfq')` | 港股-历史行情数据，可以选择返回复权后数据，更新频率为日频; 单次返回指定上市公司的历史行情数据（包括前后复权因子），提供新浪财经拥有的该股票的所有数据( |
| `stock_hk_dividend_payout_em` | `import akshare as ak; ak.stock_hk_dividend_payout_em(symbol='03900')` | 东方财富-港股-核心必读-分红派息; 单次返回全部数据 |
| `stock_hk_famous_spot_em` | `import akshare as ak; ak.stock_hk_famous_spot_em()` | 东方财富网-行情中心-港股市场-知名港股实时行情数据; 单次返回全部行情数据 |
| `stock_hk_fhpx_detail_ths` | `import akshare as ak; ak.stock_hk_fhpx_detail_ths(symbol='0700')` | 同花顺-港股-分红派息; 单次获取指定股票的分红派息数据 |
| `stock_hk_financial_indicator_em` | `import akshare as ak; ak.stock_hk_financial_indicator_em(symbol='03900')` | 东方财富-港股-核心必读-最新指标; 单次返回全部数据 |
| `stock_hk_ggt_components_em` | `import akshare as ak; ak.stock_hk_ggt_components_em()` | 东方财富网-行情中心-港股市场-港股通成份股; 单次获取所有港股通成份股数据 |
| `stock_hk_growth_comparison_em` | `import akshare as ak; ak.stock_hk_growth_comparison_em(symbol='03900')` | 东方财富-港股-行业对比-成长性对比; 单次返回全部数据 |
| `stock_hk_gxl_lg` | `import akshare as ak; ak.stock_hk_gxl_lg()` | 乐咕乐股-股息率-恒生指数股息率; 单次获取所有月度历史数据 |
| `stock_hk_hist` | `import akshare as ak; ak.stock_hk_hist(symbol='00593', period='daily', start_date='19700101', end_date='22220101', adjust='')` | 港股-历史行情数据，可以选择返回复权后数据，更新频率为日频; 单次返回指定上市公司的历史行情数据 |
| `stock_hk_hist_min_em` | `import akshare as ak; ak.stock_hk_hist_min_em(symbol='01611', period='1', adjust='', start_date='2021-09-01 09:32:00', end_date='2021-09-07 18:32:00')` | 东方财富网-行情首页-港股-每日分时行情; 单次返回指定上市公司最近 5 个交易日分钟数据，注意港股有延时 |
| `stock_hk_hot_rank_detail_em` | `import akshare as ak; ak.stock_hk_hot_rank_detail_em(symbol='00700')` | 东方财富网-股票热度-历史趋势; 单次返回指定 symbol 的股票近期历史数据 |
| `stock_hk_hot_rank_detail_realtime_em` | `import akshare as ak; ak.stock_hk_hot_rank_detail_realtime_em(symbol='00700')` | 东方财富网-个股人气榜-实时变动; 单次返回指定 symbol 的股票近期历史数据 |
| `stock_hk_hot_rank_em` | `import akshare as ak; ak.stock_hk_hot_rank_em()` | 东方财富-个股人气榜-人气榜-港股市场; 单次返回当前交易日前 100 个股票的人气排名数据 |
| `stock_hk_hot_rank_latest_em` | `import akshare as ak; ak.stock_hk_hot_rank_latest_em(symbol='00700')` | 东方财富-个股人气榜-最新排名; 单次返回指定 symbol 的股票近期历史数据 |
| `stock_hk_indicator_eniu` | `import akshare as ak; ak.stock_hk_indicator_eniu(symbol='hk01093', indicator='市净率')` | 亿牛网-港股个股指标：市盈率，市净率，股息率，ROE，市值; 单次获取指定 symbol 和 indicator 的所有历史数据 |
| `stock_hk_main_board_spot_em` | `import akshare as ak; ak.stock_hk_main_board_spot_em()` | 港股主板的实时行情数据；该数据有 15 分钟延时; 单次返回港股主板的数据 |
| `stock_hk_profit_forecast_et` | `import akshare as ak; ak.stock_hk_profit_forecast_et(symbol='09999', indicator='盈利预测概览')` | 经济通-公司资料-盈利预测; 单次返回指定 symbol 和 indicator 的数据 |
| `stock_hk_scale_comparison_em` | `import akshare as ak; ak.stock_hk_scale_comparison_em(symbol='03900')` | 东方财富-港股-行业对比-规模对比; 单次返回全部数据 |
| `stock_hk_security_profile_em` | `import akshare as ak; ak.stock_hk_security_profile_em(symbol='03900')` | 东方财富-港股-证券资料; 单次返回全部数据 |
| `stock_hk_spot` | `import akshare as ak; ak.stock_hk_spot()` | 获取所有港股的实时行情数据 15 分钟延时; 单次返回当前时间戳的所有港股的数据 |
| `stock_hk_spot_em` | `import akshare as ak; ak.stock_hk_spot_em()` | 所有港股的实时行情数据；该数据有 15 分钟延时; 单次返回最近交易日的所有港股的数据 |
| `stock_hk_valuation_baidu` | `import akshare as ak; ak.stock_hk_valuation_baidu(symbol='06969', indicator='总市值', period='近一年')` | 百度股市通-港股-财务报表-估值数据; 单次获取指定 symbol 的指定 indicator 的特定 period 的历史数据 |
| `stock_hk_valuation_comparison_em` | `import akshare as ak; ak.stock_hk_valuation_comparison_em(symbol='03900')` | 东方财富-港股-行业对比-估值对比; 单次返回全部数据 |
| `stock_hold_change_cninfo` | `import akshare as ak; ak.stock_hold_change_cninfo(symbol='全部')` | 巨潮资讯-数据中心-专题统计-股东股本-股本变动; 单次指定 symbol 的股本变动数据 |
| `stock_hold_control_cninfo` | `import akshare as ak; ak.stock_hold_control_cninfo(symbol='全部')` | 巨潮资讯-数据中心-专题统计-股东股本-实际控制人持股变动; 单次指定 symbol 的实际控制人持股变动数据，从 2010 开始 |
| `stock_hold_management_detail_cninfo` | `import akshare as ak; ak.stock_hold_management_detail_cninfo(symbol='增持')` | 巨潮资讯-数据中心-专题统计-股东股本-高管持股变动明细; 单次指定 symbol 的高管持股变动明细数据，返回近一年的数据 |
| `stock_hold_management_detail_em` | `import akshare as ak; ak.stock_hold_management_detail_em()` | 东方财富网-数据中心-特色数据-高管持股-董监高及相关人员持股变动明细; 单次返回所有数据 |
| `stock_hold_management_person_em` | `import akshare as ak; ak.stock_hold_management_person_em(symbol='001308', name='孙建华')` | 东方财富网-数据中心-特色数据-高管持股-人员增减持股变动明细; 单次返回指定 symbol 和 name 的数据 |
| `stock_hold_num_cninfo` | `import akshare as ak; ak.stock_hold_num_cninfo(date='20210630')` | 巨潮资讯-数据中心-专题统计-股东股本-股东人数及持股集中度; 单次指定 date 的股东人数及持股集中度数据，从 20170331 开始 |
| `stock_hot_deal_xq` | `import akshare as ak; ak.stock_hot_deal_xq(symbol='最热门')` | 雪球-沪深股市-热度排行榜-交易排行榜; 单次返回指定 symbol 的排行数据 |
| `stock_hot_follow_xq` | `import akshare as ak; ak.stock_hot_follow_xq(symbol='最热门')` | 雪球-沪深股市-热度排行榜-关注排行榜; 单次返回指定 symbol 的排行数据 |
| `stock_hot_keyword_em` | `import akshare as ak; ak.stock_hot_keyword_em(symbol='SZ000665')` | 东方财富-个股人气榜-热门关键词; 单次返回指定 symbol 的最近交易日时点数据 |
| `stock_hot_rank_detail_em` | `import akshare as ak; ak.stock_hot_rank_detail_em(symbol='SZ000665')` | 东方财富网-股票热度-历史趋势及粉丝特征; 单次返回指定 symbol 的股票近期历史数据 |
| `stock_hot_rank_detail_realtime_em` | `import akshare as ak; ak.stock_hot_rank_detail_realtime_em(symbol='SZ000665')` | 东方财富网-个股人气榜-实时变动; 单次返回指定 symbol 的股票近期历史数据 |
| `stock_hot_rank_em` | `import akshare as ak; ak.stock_hot_rank_em()` | 东方财富网站-股票热度; 单次返回当前交易日前 100 个股票的人气排名数据 |
| `stock_hot_rank_latest_em` | `import akshare as ak; ak.stock_hot_rank_latest_em(symbol='SZ000665')` | 东方财富-个股人气榜-最新排名; 单次返回指定 symbol 的股票近期历史数据 |
| `stock_hot_rank_relate_em` | `import akshare as ak; ak.stock_hot_rank_relate_em(symbol='SZ000665')` | 东方财富-个股人气榜-相关股票; 单次返回指定 symbol 的股票近期历史数据 |
| `stock_hot_search_baidu` | `import akshare as ak; ak.stock_hot_search_baidu(symbol='A股', date='20250616', time='今日')` | 百度股市通-热搜股票; 单次返回指定 symbol, date 和 time 的热搜股票数据 |
| `stock_hot_tweet_xq` | `import akshare as ak; ak.stock_hot_tweet_xq(symbol='最热门')` | 雪球-沪深股市-热度排行榜-讨论排行榜; 单次返回指定 symbol 的排行数据 |
| `stock_hot_up_em` | `import akshare as ak; ak.stock_hot_up_em()` | 东方财富-个股人气榜-飙升榜; 单次返回当前交易日前 100 个股票的飙升榜排名数据 |
| `stock_hsgt_board_rank_em` | `import akshare as ak; ak.stock_hsgt_board_rank_em(symbol='北向资金增持行业板块排行', indicator='今日')` | 东方财富网-数据中心-沪深港通持股-板块排行; 单次获取指定 symbol 和 indicator 的所有数据 |
| `stock_hsgt_fund_flow_summary_em` | `import akshare as ak; ak.stock_hsgt_fund_flow_summary_em()` | 东方财富网-数据中心-资金流向-沪深港通资金流向; 单次获取沪深港通资金流向数据 |
| `stock_hsgt_fund_min_em` | `import akshare as ak; ak.stock_hsgt_fund_min_em(symbol='北向资金')` | 东方财富-数据中心-沪深港通-市场概括-分时数据; 单次返回指定 symbol 的所有数据；20240513起数据源不再提供数据 |
| `stock_hsgt_hist_em` | `import akshare as ak; ak.stock_hsgt_hist_em(symbol='北向资金')` | 东方财富网-数据中心-资金流向-沪深港通资金流向-沪深港通历史数据; 单次获取指定 symbol 的所有数据 |
| `stock_hsgt_hold_stock_em` | `import akshare as ak; ak.stock_hsgt_hold_stock_em(market='北向', indicator='今日排行')` | 东方财富网-数据中心-沪深港通持股-个股排行; 单次获取指定 market 和 indicator 的所有数据 |
| `stock_hsgt_individual_detail_em` | `import akshare as ak; ak.stock_hsgt_individual_detail_em(symbol='002008', start_date='20210830', end_date='20211026')` | 东方财富网-数据中心-沪深港通-沪深港通持股-具体股票-个股详情; 单次获取指定 symbol 的在 start_date 和 end_date 之间的所有数据；注意只能返回 90 个交易日内的数据 |
| `stock_hsgt_individual_em` | `import akshare as ak; ak.stock_hsgt_individual_em(symbol='002008')` | 东方财富网-数据中心-沪深港通-沪深港通持股-具体股票; 单次获取指定 symbol 的截至 20240816 的数据 |
| `stock_hsgt_institution_statistics_em` | `import akshare as ak; ak.stock_hsgt_institution_statistics_em(market='北向持股', start_date='20201218', end_date='20201218')` | 东方财富网-数据中心-沪深港通-沪深港通持股-机构排行; 单次获取指定 market 的所有数据，该接口只能获取近期的数据 |
| `stock_hsgt_sh_hk_spot_em` | `import akshare as ak; ak.stock_hsgt_sh_hk_spot_em()` | 东方财富网-行情中心-沪深港通-港股通（沪>港）-股票；按股票代码排序; 单次获取所有数据 |
| `stock_hsgt_stock_statistics_em` | `import akshare as ak; ak.stock_hsgt_stock_statistics_em(symbol='北向持股', start_date='20211027', end_date='20211027')` | 东方财富网-数据中心-沪深港通-沪深港通持股-每日个股统计; 单次获取指定 market 的 start_date 和 end_date 之间的所有数据，该接口只能获取近期的数据 |
| `stock_index_pb_lg` | `import akshare as ak; ak.stock_index_pb_lg(symbol='上证50')` | 乐咕乐股-指数市净率; 单次获取指定 symbol 的所有数据 |
| `stock_index_pe_lg` | `import akshare as ak; ak.stock_index_pe_lg(symbol='上证50')` | 乐咕乐股-指数市盈率; 单次获取指定 symbol 的所有数据 |
| `stock_individual_basic_info_hk_xq` | `import akshare as ak; ak.stock_individual_basic_info_hk_xq(symbol='02097')` | 雪球-个股-公司概况-公司简介; 单次返回指定 symbol 的个股信息 |
| `stock_individual_basic_info_us_xq` | `import akshare as ak; ak.stock_individual_basic_info_us_xq(symbol='NVDA')` | 雪球-个股-公司概况-公司简介; 单次返回指定 symbol 的个股信息 |
| `stock_individual_basic_info_xq` | `import akshare as ak; ak.stock_individual_basic_info_xq(symbol='SH601127')` | 雪球财经-个股-公司概况-公司简介; 单次返回指定 symbol 的个股信息 |
| `stock_individual_fund_flow` | `import akshare as ak; ak.stock_individual_fund_flow(stock='600094', market='sh')` | 东方财富网-数据中心-个股资金流向; 单次获取指定市场和股票的近 100 个交易日的资金流数据 |
| `stock_individual_fund_flow_rank` | `import akshare as ak; ak.stock_individual_fund_flow_rank(indicator='今日')` | 东方财富网-数据中心-资金流向-排名; 单次获取指定类型的个股资金流排名数据 |
| `stock_individual_info_em` | `import akshare as ak; ak.stock_individual_info_em(symbol='000001')` | 东方财富-个股-股票信息; 单次返回指定 symbol 的个股信息 |
| `stock_individual_notice_report` | `import akshare as ak; ak.stock_individual_notice_report(security='300237', symbol='财务报告', begin_date='20250401', end_date='20260101')` | 东方财富网-数据中心-公告大全-个股; 单次获取指定 security, symbol, begin_date 和 end_date 的数据 |
| `stock_individual_spot_xq` | `import akshare as ak; ak.stock_individual_spot_xq(symbol='SH600000')` | 雪球-行情中心-个股; 单次获取指定 symbol 的最新行情数据 |
| `stock_industry_category_cninfo` | `import akshare as ak; ak.stock_industry_category_cninfo(symbol='巨潮行业分类标准')` | 巨潮资讯-数据-行业分类数据; 单次获取指定 symbol 的行业分类数据 |
| `stock_industry_change_cninfo` | `import akshare as ak; ak.stock_industry_change_cninfo(symbol='002594', start_date='20091227', end_date='20220708')` | 巨潮资讯-数据-上市公司行业归属的变动情况; 单次获取指定 symbol 在 start_date 和 end_date 之间的上市公司行业归属的变动情况数据 |
| `stock_industry_clf_hist_sw` | `import akshare as ak; ak.stock_industry_clf_hist_sw()` | 申万宏源研究-行业分类-全部行业分类; 单次获取所有个股的行业分类变动历史数据 |
| `stock_industry_pe_ratio_cninfo` | `import akshare as ak; ak.stock_industry_pe_ratio_cninfo(symbol='国证行业分类', date='20240617')` | 巨潮资讯-数据中心-行业分析-行业市盈率; 单次获取指定 symbol 在指定交易日的所有数据；只能获取近期的数据 |
| `stock_info_a_code_name` | `import akshare as ak; ak.stock_info_a_code_name()` | 沪深京 A 股股票代码和股票简称数据; 单次获取所有 A 股股票代码和简称数据 |
| `stock_info_bj_name_code` | `import akshare as ak; ak.stock_info_bj_name_code()` | 北京证券交易所股票代码和简称数据; 单次获取北京证券交易所所有的股票代码和简称数据 |
| `stock_info_change_name` | `import akshare as ak; ak.stock_info_change_name(symbol='000503')` | 新浪财经-股票曾用名; 单次指定 symbol 的所有历史曾用名称 |
| `stock_info_cjzc_em` | `import akshare as ak; ak.stock_info_cjzc_em()` | 东方财富-财经早餐; 单次返回全部历史数据 |
| `stock_info_global_cls` | `import akshare as ak; ak.stock_info_global_cls(symbol='全部')` | 财联社-电报; 单次返回指定 symbol 的最近 20 条财联社-电报的数据 |
| `stock_info_global_em` | `import akshare as ak; ak.stock_info_global_em()` | 东方财富-全球财经快讯; 单次返回最近 200 条新闻数据 |
| `stock_info_global_futu` | `import akshare as ak; ak.stock_info_global_futu()` | 富途牛牛-快讯; 单次返回最近 50 条新闻数据 |
| `stock_info_global_sina` | `import akshare as ak; ak.stock_info_global_sina()` | 新浪财经-全球财经快讯; 单次返回最近 20 条新闻数据 |
| `stock_info_global_ths` | `import akshare as ak; ak.stock_info_global_ths()` | 同花顺财经-全球财经直播; 单次返回最近 20 条新闻数据 |
| `stock_info_sh_delist` | `import akshare as ak; ak.stock_info_sh_delist(symbol='全部')` | 上海证券交易所暂停/终止上市股票; 单次获取上海证券交易所暂停/终止上市股票 |
| `stock_info_sh_name_code` | `import akshare as ak; ak.stock_info_sh_name_code(symbol='主板A股')` | 上海证券交易所股票代码和简称数据; 单次获取所有上海证券交易所股票代码和简称数据 |
| `stock_info_sz_change_name` | `import akshare as ak; ak.stock_info_sz_change_name(symbol='全称变更')` | 深证证券交易所-市场数据-股票数据-名称变更; 单次获取所有历史数据 |
| `stock_info_sz_delist` | `import akshare as ak; ak.stock_info_sz_delist(symbol='终止上市公司')` | 深证证券交易所终止/暂停上市股票; 单次获取深证证券交易所终止/暂停上市数据 |
| `stock_info_sz_name_code` | `import akshare as ak; ak.stock_info_sz_name_code(symbol='A股列表')` | 深证证券交易所股票代码和股票简称数据; 单次获取深证证券交易所股票代码和简称数据 |
| `stock_inner_trade_xq` | `import akshare as ak; ak.stock_inner_trade_xq()` | 雪球-行情中心-沪深股市-内部交易; 单次返回所有历史数据 |
| `stock_institute_hold` | `import akshare as ak; ak.stock_institute_hold(symbol='20201')` | 新浪财经-机构持股-机构持股一览表; 单次获取所有历史数据 |
| `stock_institute_hold_detail` | `import akshare as ak; ak.stock_institute_hold_detail(stock='300003', quarter='20201')` | 新浪财经-机构持股-机构持股详情; 单次所有历史数据 |
| `stock_institute_recommend` | `import akshare as ak; ak.stock_institute_recommend(symbol='投资评级选股')` | 新浪财经-机构推荐池-具体指标的数据; 单次获取新浪财经-机构推荐池-具体指标的所有数据 |
| `stock_institute_recommend_detail` | `import akshare as ak; ak.stock_institute_recommend_detail(symbol='002709')` | 新浪财经-机构推荐池-股票评级记录; 单次获取新浪财经-机构推荐池-股票评级记录的所有数据 |
| `stock_intraday_em` | `import akshare as ak; ak.stock_intraday_em(symbol='000001')` | 东方财富-分时数据; 单次返回指定股票最近一个交易日的分时数据，包含盘前数据 |
| `stock_intraday_sina` | `import akshare as ak; ak.stock_intraday_sina(symbol='sz000001', date='20240321')` | 新浪财经-日内分时数据; 单次返回指定交易日的分时数据；只能获取近期的数据，此处仅返回大单数据（成交量大于等于：400手） |
| `stock_ipo_benefit_ths` | `import akshare as ak; ak.stock_ipo_benefit_ths()` | 同花顺-数据中心-新股数据-IPO受益股; 单次返回当前交易日的所有数据；该数据每周更新一次，返回最近一周的数据 |
| `stock_ipo_declare_em` | `import akshare as ak; ak.stock_ipo_declare_em()` | 东方财富网-数据中心-新股申购-首发申报信息-首发申报企业信息; 单次返回所有历史数据 |
| `stock_ipo_hk_ths` | `import akshare as ak; ak.stock_ipo_hk_ths()` | 同花顺-数据中心-新股申购与中签-港股; 单次返回所有港股新股申购与中签数据 |
| `stock_ipo_info` | `import akshare as ak; ak.stock_ipo_info(stock='600004')` | 新浪财经-发行与分配-新股发行; 单次获取新股发行的基本信息数据 |
| `stock_ipo_review_em` | `import akshare as ak; ak.stock_ipo_review_em()` | 东方财富网-数据中心-新股申购-新股上会信息; 单次获取所有数据 |
| `stock_ipo_summary_cninfo` | `import akshare as ak; ak.stock_ipo_summary_cninfo(symbol='600030')` | 巨潮资讯-个股-上市相关; 单次获取指定 symbol 的上市相关数据 |
| `stock_ipo_ths` | `import akshare as ak; ak.stock_ipo_ths(symbol='全部A股')` | 同花顺-数据中心-新股申购与中签; 单次返回指定 symbol 的历史新股申购与中签数据 |
| `stock_ipo_tutor_em` | `import akshare as ak; ak.stock_ipo_tutor_em()` | 东方财富网-数据中心-新股申购-IPO辅导信息; 单次获取所有数据 |
| `stock_irm_ans_cninfo` | `import akshare as ak; ak.stock_irm_ans_cninfo(symbol='1495108801386602496')` | 互动易-回答; 单次返回指定 symbol 的回答数据 |
| `stock_irm_cninfo` | `import akshare as ak; ak.stock_irm_cninfo(symbol='002594')` | 互动易-提问; 单次返回近期 10000 条提问数据 |
| `stock_jgdy_detail_em` | `import akshare as ak; ak.stock_jgdy_detail_em(date='20241211')` | 东方财富网-数据中心-特色数据-机构调研-机构调研详细; 单次所有历史数据，由于数据量比较大需要等待一定时间 |
| `stock_jgdy_tj_em` | `import akshare as ak; ak.stock_jgdy_tj_em(date='20210128')` | 东方财富网-数据中心-特色数据-机构调研-机构调研统计; 单次返回所有历史数据 |
| `stock_js_weibo_nlp_time` | `import akshare as ak; ak.stock_js_weibo_nlp_time()` |  |
| `stock_kc_a_spot_em` | `import akshare as ak; ak.stock_kc_a_spot_em()` | 东方财富网-科创板-实时行情; 单次返回所有科创板的实时行情数据 |
| `stock_lh_yyb_capital` | `import akshare as ak; ak.stock_lh_yyb_capital()` | 龙虎榜-营业部排行-资金实力最强; 单次返回所有历史数据 |
| `stock_lh_yyb_control` | `import akshare as ak; ak.stock_lh_yyb_control()` | 龙虎榜-营业部排行-抱团操作实力; 单次返回所有历史数据 |
| `stock_lh_yyb_most` | `import akshare as ak; ak.stock_lh_yyb_most()` | 龙虎榜-营业部排行-上榜次数最多; 单次返回所有历史数据 |
| `stock_lhb_detail_daily_sina` | `import akshare as ak; ak.stock_lhb_detail_daily_sina(date='20240222')` | 新浪财经-龙虎榜-每日详情; 单次返回指定 date 的所有数据 |
| `stock_lhb_detail_em` | `import akshare as ak; ak.stock_lhb_detail_em(start_date='20230403', end_date='20230417')` | 东方财富网-数据中心-龙虎榜单-龙虎榜详情; 单次返回所有历史数据 |
| `stock_lhb_ggtj_sina` | `import akshare as ak; ak.stock_lhb_ggtj_sina(symbol='5')` | 新浪财经-龙虎榜-个股上榜统计; 单次返回指定 symbol 的所有历史数据 |
| `stock_lhb_hyyyb_em` | `import akshare as ak; ak.stock_lhb_hyyyb_em(start_date='20220324', end_date='20220324')` | 东方财富网-数据中心-龙虎榜单-每日活跃营业部; 单次返回所有历史数据 |
| `stock_lhb_jgmmtj_em` | `import akshare as ak; ak.stock_lhb_jgmmtj_em(start_date='20240417', end_date='20240430')` | 东方财富网-数据中心-龙虎榜单-机构买卖每日统计; 单次返回所有历史数据 |
| `stock_lhb_jgmx_sina` | `import akshare as ak; ak.stock_lhb_jgmx_sina()` | 新浪财经-龙虎榜-机构席位成交明细; 单次返回所有历史数据 |
| `stock_lhb_jgstatistic_em` | `import akshare as ak; ak.stock_lhb_jgstatistic_em(symbol='近一月')` | 东方财富网-数据中心-龙虎榜单-机构席位追踪; 单次返回所有历史数据 |
| `stock_lhb_jgzz_sina` | `import akshare as ak; ak.stock_lhb_jgzz_sina(symbol='5')` | 新浪财经-龙虎榜-机构席位追踪; 单次返回指定 symbol 的所有历史数据 |
| `stock_lhb_stock_detail_em` | `import akshare as ak; ak.stock_lhb_stock_detail_em(symbol='600077', date='20070416', flag='买入')` | 东方财富网-数据中心-龙虎榜单-个股龙虎榜详情; 单次返回所有历史数据 |
| `stock_lhb_stock_statistic_em` | `import akshare as ak; ak.stock_lhb_stock_statistic_em(symbol='近一月')` | 东方财富网-数据中心-龙虎榜单-个股上榜统计; 单次返回所有历史数据 |
| `stock_lhb_traderstatistic_em` | `import akshare as ak; ak.stock_lhb_traderstatistic_em(symbol='近一月')` | 东方财富网-数据中心-龙虎榜单-营业部统计; 单次返回所有历史数据 |
| `stock_lhb_yyb_detail_em` | `import akshare as ak; ak.stock_lhb_yyb_detail_em(symbol='10188715')` | 东方财富网-数据中心-龙虎榜单-营业部历史交易明细-营业部交易明细; 单次返回指定营业部的所有历史数据 |
| `stock_lhb_yybph_em` | `import akshare as ak; ak.stock_lhb_yybph_em(symbol='近一月')` | 东方财富网-数据中心-龙虎榜单-营业部排行; 单次返回所有历史数据 |
| `stock_lhb_yytj_sina` | `import akshare as ak; ak.stock_lhb_yytj_sina(symbol='5')` | 新浪财经-龙虎榜-营业上榜统计; 单次返回指定 symbol 的所有历史数据 |
| `stock_lrb_em` | `import akshare as ak; ak.stock_lrb_em(date='20240331')` | 东方财富-数据中心-年报季报-业绩快报-利润表; 单次获取指定 date 的利润表数据 |
| `stock_main_fund_flow` | `import akshare as ak; ak.stock_main_fund_flow(symbol='全部股票')` | 东方财富网-数据中心-资金流向-主力净流入排名; 单次获取指定 symbol 的主力净流入排名数据 |
| `stock_main_stock_holder` | `import akshare as ak; ak.stock_main_stock_holder(stock='600004')` | 新浪财经-股本股东-主要股东; 单次获取所有历史数据 |
| `stock_management_change_ths` | `import akshare as ak; ak.stock_management_change_ths(symbol='688981')` | 同花顺-公司大事-高管持股变动; 单次返回所有数据 |
| `stock_margin_account_info` | `import akshare as ak; ak.stock_margin_account_info()` | 东方财富网-数据中心-融资融券-融资融券账户统计-两融账户信息; 单次返回所有历史数据 |
| `stock_margin_bse` | `import akshare as ak; ak.stock_margin_bse(date='20260721')` | 北京证券交易所-融资融券数据-融资融券汇总数据; 单次返回指定交易日的汇总数据 |
| `stock_margin_detail_bse` | `import akshare as ak; ak.stock_margin_detail_bse(date='20260721')` | 北京证券交易所-融资融券数据-融资融券交易明细数据; 单次返回指定交易日的全部明细数据 |
| `stock_margin_detail_sse` | `import akshare as ak; ak.stock_margin_detail_sse(date='20230922')` | 上海证券交易所-融资融券数据-融资融券明细数据; 单次返回交易日的所有历史数据 |
| `stock_margin_detail_szse` | `import akshare as ak; ak.stock_margin_detail_szse(date='20230925')` | 深证证券交易所-融资融券数据-融资融券交易明细数据; 单次返回指定 date 的所有历史数据 |
| `stock_margin_ratio_pa` | `import akshare as ak; ak.stock_margin_ratio_pa(symbol='沪市', date='20260113')` | 融资融券-标的证券名单及保证金比例查询; 单次返回指定交易所和交易日的所有历史数据 |
| `stock_margin_sse` | `import akshare as ak; ak.stock_margin_sse(start_date='20010106', end_date='20210208')` | 上海证券交易所-融资融券数据-融资融券汇总数据; 单次返回指定时间段内的所有历史数据 |
| `stock_margin_szse` | `import akshare as ak; ak.stock_margin_szse(date='20240411')` | 深圳证券交易所-融资融券数据-融资融券汇总数据; 单次返回指定时间内的所有历史数据 |
| `stock_margin_underlying_info_bse` | `import akshare as ak; ak.stock_margin_underlying_info_bse(date='20260722')` | 北京证券交易所-融资融券数据-标的证券信息; 单次返回指定交易日的全部标的证券信息 |
| `stock_margin_underlying_info_szse` | `import akshare as ak; ak.stock_margin_underlying_info_szse(date='20210727')` | 深圳证券交易所-融资融券数据-标的证券信息; 单次返回交易日的所有历史数据 |
| `stock_market_activity_legu` | `import akshare as ak; ak.stock_market_activity_legu()` | 乐咕乐股网-赚钱效应分析数据; 单次返回当前赚钱效应分析数据 |
| `stock_market_fund_flow` | `import akshare as ak; ak.stock_market_fund_flow()` | 东方财富网-数据中心-资金流向-大盘; 单次获取大盘资金流向历史数据 |
| `stock_market_pb_lg` | `import akshare as ak; ak.stock_market_pb_lg(symbol='上证')` | 乐咕乐股-主板市净率; 单次获取指定 symbol 的所有数据 |
| `stock_market_pe_lg` | `import akshare as ak; ak.stock_market_pe_lg(symbol='上证')` | 乐咕乐股-主板市盈率; 单次获取指定 symbol 的所有数据 |
| `stock_new_a_spot_em` | `import akshare as ak; ak.stock_new_a_spot_em()` | 东方财富网-新股-实时行情数据; 单次返回所有新股上市公司的实时行情数据 |
| `stock_new_gh_cninfo` | `import akshare as ak; ak.stock_new_gh_cninfo()` | 巨潮资讯-数据中心-新股数据-新股过会; 单次获取近一年所有新股过会的数据 |
| `stock_new_ipo_cninfo` | `import akshare as ak; ak.stock_new_ipo_cninfo()` | 巨潮资讯-数据中心-新股数据-新股发行; 单次获取近三年所有新股发行的数据 |
| `stock_news_em` | `import akshare as ak; ak.stock_news_em(symbol='603777')` | 东方财富指定个股的新闻资讯数据; 指定 symbol 当日最近 100 条新闻资讯数据 |
| `stock_news_main_cx` | `import akshare as ak; ak.stock_news_main_cx()` | 财新网-财新数据通-最新; 返回最新 100 条新闻数据 |
| `stock_notice_report` | `import akshare as ak; ak.stock_notice_report(symbol='财务报告', date='20240613')` | 东方财富网-数据中心-公告大全-沪深京 A 股公告; 单次获取指定 symbol 和 date 的数据 |
| `stock_pg_em` | `import akshare as ak; ak.stock_pg_em()` | 东方财富网-数据中心-新股数据-配股; 单次返回所有历史数据 |
| `stock_price_js` | `import akshare as ak; ak.stock_price_js(symbol='us')` | 美港电讯-美港目标价数据; 单次获取所有数据，数据从 2019-至今；该接口暂时不能使用 |
| `stock_profile_cninfo` | `import akshare as ak; ak.stock_profile_cninfo(symbol='600030')` | 巨潮资讯-个股-公司概况; 单次获取指定 symbol 的公司概况 |
| `stock_profit_forecast_em` | `import akshare as ak; ak.stock_profit_forecast_em()` | 东方财富网-数据中心-研究报告-盈利预测；该数据源网页端返回数据有异常，本接口已修复该异常; 单次返回指定 symbol 的数据 |
| `stock_profit_forecast_ths` | `import akshare as ak; ak.stock_profit_forecast_ths(symbol='600519', indicator='预测年报每股收益')` | 同花顺-盈利预测; 单次返回指定 symbol 和 indicator 的数据 |
| `stock_profit_sheet_by_quarterly_em` | `import akshare as ak; ak.stock_profit_sheet_by_quarterly_em(symbol='SH600519')` | 东方财富-股票-财务分析-利润表-按单季度; 单次获取指定 symbol 的利润表-按单季度数据 |
| `stock_profit_sheet_by_report_delisted_em` | `import akshare as ak; ak.stock_profit_sheet_by_report_delisted_em(symbol='SZ000013')` | 东方财富-股票-财务分析-利润表-已退市股票-按报告期; 单次获取指定 symbol 的利润表-按报告期数据 |
| `stock_profit_sheet_by_report_em` | `import akshare as ak; ak.stock_profit_sheet_by_report_em(symbol='SH600519')` | 东方财富-股票-财务分析-利润表-报告期; 单次获取指定 symbol 的利润表-报告期数据 |
| `stock_profit_sheet_by_yearly_em` | `import akshare as ak; ak.stock_profit_sheet_by_yearly_em(symbol='SH600519')` | 东方财富-股票-财务分析-利润表-按年度; 单次获取指定 symbol 的利润表-按年度数据 |
| `stock_qbzf_em` | `import akshare as ak; ak.stock_qbzf_em()` | 东方财富网-数据中心-新股数据-增发-全部增发; 单次返回所有历史数据 |
| `stock_qsjy_em` | `import akshare as ak; ak.stock_qsjy_em(date='20200430')` | 东方财富网-数据中心-特色数据-券商业绩月报; 单次获取所有数据，数据从 201006-202007，月频率 |
| `stock_rank_cxd_ths` | `import akshare as ak; ak.stock_rank_cxd_ths(symbol='创月新低')` | 同花顺-数据中心-技术选股-创新低; 单次指定 symbol 的所有数据 |
| `stock_rank_cxfl_ths` | `import akshare as ak; ak.stock_rank_cxfl_ths()` | 同花顺-数据中心-技术选股-持续放量; 单次返回所有数据 |
| `stock_rank_cxg_ths` | `import akshare as ak; ak.stock_rank_cxg_ths(symbol='创月新高')` | 同花顺-数据中心-技术选股-创新高; 单次指定 symbol 的所有数据 |
| `stock_rank_cxsl_ths` | `import akshare as ak; ak.stock_rank_cxsl_ths()` | 同花顺-数据中心-技术选股-持续缩量; 单次返回所有数据 |
| `stock_rank_forecast_cninfo` | `import akshare as ak; ak.stock_rank_forecast_cninfo(date='20230817')` | 巨潮资讯-数据中心-评级预测-投资评级; 单次获取指定交易日的所有数据 |
| `stock_rank_ljqd_ths` | `import akshare as ak; ak.stock_rank_ljqd_ths()` | 同花顺-数据中心-技术选股-量价齐跌; 单次返回所有数据 |
| `stock_rank_ljqs_ths` | `import akshare as ak; ak.stock_rank_ljqs_ths()` | 同花顺-数据中心-技术选股-量价齐升; 单次返回所有数据 |
| `stock_rank_lxsz_ths` | `import akshare as ak; ak.stock_rank_lxsz_ths()` | 同花顺-数据中心-技术选股-连续上涨; 单次返回所有数据 |
| `stock_rank_lxxd_ths` | `import akshare as ak; ak.stock_rank_lxxd_ths()` | 同花顺-数据中心-技术选股-连续下跌; 单次返回所有数据 |
| `stock_rank_xstp_ths` | `import akshare as ak; ak.stock_rank_xstp_ths(symbol='500日均线')` | 同花顺-数据中心-技术选股-向上突破; 单次返回所有数据 |
| `stock_rank_xxtp_ths` | `import akshare as ak; ak.stock_rank_xxtp_ths(symbol='500日均线')` | 同花顺-数据中心-技术选股-向下突破; 单次返回所有数据 |
| `stock_rank_xzjp_ths` | `import akshare as ak; ak.stock_rank_xzjp_ths()` | 同花顺-数据中心-技术选股-险资举牌; 单次返回所有数据 |
| `stock_register_all_em` | `import akshare as ak; ak.stock_register_all_em()` | 东方财富网-数据中心-新股数据-IPO审核信息-全部; 单次返回所有历史数据 |
| `stock_register_bj` | `import akshare as ak; ak.stock_register_bj()` | 东方财富网-数据中心-新股数据-IPO审核信息-北交所; 单次返回所有历史数据 |
| `stock_register_cyb` | `import akshare as ak; ak.stock_register_cyb()` | 东方财富网-数据中心-新股数据-IPO审核信息-创业板; 单次返回所有历史数据 |
| `stock_register_db` | `import akshare as ak; ak.stock_register_db()` | 东方财富网-数据中心-新股数据-注册制审核-达标企业; 单次返回所有历史数据 |
| `stock_register_kcb` | `import akshare as ak; ak.stock_register_kcb()` | 东方财富网-数据中心-新股数据-IPO审核信息-科创板; 单次返回所有历史数据 |
| `stock_register_sh` | `import akshare as ak; ak.stock_register_sh()` | 东方财富网-数据中心-新股数据-IPO审核信息-上海主板; 单次返回所有历史数据 |
| `stock_register_sz` | `import akshare as ak; ak.stock_register_sz()` | 东方财富网-数据中心-新股数据-IPO审核信息-深圳主板; 单次返回所有历史数据 |
| `stock_report_disclosure` | `import akshare as ak; ak.stock_report_disclosure(market='沪深京', period='2022年报')` | 巨潮资讯-数据-预约披露的数据; 单次获取指定 market 和 period 的预约披露数据 |
| `stock_report_fund_hold` | `import akshare as ak; ak.stock_report_fund_hold(symbol='基金持仓', date='20200630')` | 东方财富网-数据中心-主力数据-基金持仓; 单次返回指定 symbol 和 date 的所有历史数据 |
| `stock_report_fund_hold_detail` | `import akshare as ak; ak.stock_report_fund_hold_detail(symbol='005827', date='20201231')` | 东方财富网-数据中心-主力数据-基金持仓-基金持仓明细表; 单次返回指定 symbol 和 date 的所有历史数据 |
| `stock_repurchase_em` | `import akshare as ak; ak.stock_repurchase_em()` | 东方财富网-数据中心-股票回购-股票回购数据; 单次返回所有历史数据 |
| `stock_research_report_em` | `import akshare as ak; ak.stock_research_report_em(symbol='000001')` | 东方财富网-数据中心-研究报告-个股研报; 单次返回指定 symbol 的所有数据 |
| `stock_restricted_release_detail_em` | `import akshare as ak; ak.stock_restricted_release_detail_em(start_date='20221202', end_date='20221204')` | 东方财富网-数据中心-限售股解禁-解禁详情一览; 单次获取指定时间段限售股解禁数据 |
| `stock_restricted_release_queue_em` | `import akshare as ak; ak.stock_restricted_release_queue_em(symbol='600000')` | 东方财富网-数据中心-个股限售解禁-解禁批次; 单次获取指定 symbol 的解禁批次数据 |
| `stock_restricted_release_queue_sina` | `import akshare as ak; ak.stock_restricted_release_queue_sina(symbol='600000')` | 新浪财经-发行分配-限售解禁; 单次获取指定 symbol 的限售解禁数据 |
| `stock_restricted_release_stockholder_em` | `import akshare as ak; ak.stock_restricted_release_stockholder_em(symbol='600000', date='20200904')` | 东方财富网-数据中心-个股限售解禁-解禁股东; 单次获取指定 symbol 的解禁批次数据 |
| `stock_restricted_release_summary_em` | `import akshare as ak; ak.stock_restricted_release_summary_em(symbol='全部股票', start_date='20221108', end_date='20221209')` | 东方财富网-数据中心-特色数据-限售股解禁; 单次获取指定 symbol 在近期限售股解禁数据 |
| `stock_sector_detail` | `import akshare as ak; ak.stock_sector_detail(sector='hangye_ZL01')` | 新浪行业-板块行情-成份详情，由于新浪网页提供的统计数据有误，部分行业数量大于统计数; 单次获取指定的新浪行业-板块行情-成份详情 |
| `stock_sector_fund_flow_hist` | `import akshare as ak; ak.stock_sector_fund_flow_hist(symbol='汽车服务')` | 东方财富网-数据中心-资金流向-行业资金流-行业历史资金流; 单次获取指定行业的行业历史资金流数据 |
| `stock_sector_fund_flow_rank` | `import akshare as ak; ak.stock_sector_fund_flow_rank(indicator='今日', sector_type='行业资金流')` | 东方财富网-数据中心-资金流向-板块资金流-排名; 单次获取指定板块的指定期限的资金流排名数据 |
| `stock_sector_fund_flow_summary` | `import akshare as ak; ak.stock_sector_fund_flow_summary(symbol='电源设备', indicator='今日')` | 东方财富网-数据中心-资金流向-行业资金流-xx行业个股资金流; 单次获取指定 symbol 的个股资金流 |
| `stock_sector_spot` | `import akshare as ak; ak.stock_sector_spot(indicator='新浪行业')` | 新浪行业-板块行情; 单次获取指定的板块行情实时数据 |
| `stock_sgt_reference_exchange_rate_sse` | `import akshare as ak; ak.stock_sgt_reference_exchange_rate_sse()` | 沪港通-港股通信息披露-参考汇率; 单次获取所有沪港通参考汇率数据 |
| `stock_sgt_reference_exchange_rate_szse` | `import akshare as ak; ak.stock_sgt_reference_exchange_rate_szse()` | 深港通-港股通业务信息-参考汇率; 单次获取所有深港通参考汇率数据 |
| `stock_sgt_settlement_exchange_rate_sse` | `import akshare as ak; ak.stock_sgt_settlement_exchange_rate_sse()` | 沪港通-港股通信息披露-结算汇兑; 单次获取所有沪港通结算汇率数据 |
| `stock_sgt_settlement_exchange_rate_szse` | `import akshare as ak; ak.stock_sgt_settlement_exchange_rate_szse()` | 深港通-港股通业务信息-结算汇率; 单次获取所有深港通结算汇率数据 |
| `stock_sh_a_spot_em` | `import akshare as ak; ak.stock_sh_a_spot_em()` | 东方财富网-沪 A 股-实时行情数据; 单次返回所有沪 A 股上市公司的实时行情数据 |
| `stock_share_change_cninfo` | `import akshare as ak; ak.stock_share_change_cninfo(symbol='002594', start_date='20091227', end_date='20241021')` | 巨潮资讯-数据-公司股本变动; 单次获取指定 symbol 在 start_date 和 end_date 之间的公司股本变动数据 |
| `stock_share_hold_change_bse` | `import akshare as ak; ak.stock_share_hold_change_bse(symbol='430489')` | 北京证券交易所-信息披露-监管信息-董监高及相关人员持股变动; 单次获取指定 symbol 的数据 |
| `stock_share_hold_change_sse` | `import akshare as ak; ak.stock_share_hold_change_sse(symbol='600000')` | 上海证券交易所-披露-监管信息公开-公司监管-董董监高人员股份变动; 单次获取指定 symbol 的数据 |
| `stock_share_hold_change_szse` | `import akshare as ak; ak.stock_share_hold_change_szse(symbol='001308')` | 深圳证券交易所-信息披露-监管信息公开-董监高人员股份变动; 单次获取指定 symbol 的数据 |
| `stock_shareholder_change_ths` | `import akshare as ak; ak.stock_shareholder_change_ths(symbol='688981')` | 同花顺-公司大事-股东持股变动; 单次返回所有数据 |
| `stock_sns_sseinfo` | `import akshare as ak; ak.stock_sns_sseinfo(symbol='603119')` | 上证e互动-提问与回答; 单次返回指定 symbol 的提问与回答数据 |
| `stock_sse_deal_daily` | `import akshare as ak; ak.stock_sse_deal_daily(date='20250221')` | 上海证券交易所-数据-股票数据-成交概况-股票成交概况-每日股票情况; 单次返回指定日期的每日概况数据，当前交易日数据需要在收盘后获取；注意仅支持获取在 20211227（包含）之后的数据 |
| `stock_sse_summary` | `import akshare as ak; ak.stock_sse_summary()` | 上海证券交易所-股票数据总貌; 单次返回最近交易日的股票数据总貌（当前交易日的数据需要交易所收盘后统计） |
| `stock_staq_net_stop` | `import akshare as ak; ak.stock_staq_net_stop()` | 东方财富网-行情中心-沪深个股-两网及退市; 单次获取所有两网及退市的股票数据 |
| `stock_sy_em` | `import akshare as ak; ak.stock_sy_em(date='20240630')` | 东方财富网-数据中心-特色数据-商誉-个股商誉明细; 单次返回所有历史数据 |
| `stock_sy_hy_em` | `import akshare as ak; ak.stock_sy_hy_em(date='20240930')` | 东方财富网-数据中心-特色数据-商誉-行业商誉; 单次返回所有历史数据 |
| `stock_sy_jz_em` | `import akshare as ak; ak.stock_sy_jz_em(date='20230331')` | 东方财富网-数据中心-特色数据-商誉-个股商誉减值明细; 单次返回所有历史数据 |
| `stock_sy_profile_em` | `import akshare as ak; ak.stock_sy_profile_em()` | 东方财富网-数据中心-特色数据-商誉-A股商誉市场概况; 单次所有历史数据 |
| `stock_sy_yq_em` | `import akshare as ak; ak.stock_sy_yq_em(date='20221231')` | 东方财富网-数据中心-特色数据-商誉-商誉减值预期明细; 单次所有历史数据 |
| `stock_sz_a_spot_em` | `import akshare as ak; ak.stock_sz_a_spot_em()` | 东方财富网-深 A 股-实时行情数据; 单次返回所有深 A 股上市公司的实时行情数据 |
| `stock_szse_area_summary` | `import akshare as ak; ak.stock_szse_area_summary(date='202412')` | 深圳证券交易所-市场总貌-地区交易排序; 单次返回指定 date 的市场总貌数据-地区交易排序数据 |
| `stock_szse_sector_summary` | `import akshare as ak; ak.stock_szse_sector_summary(symbol='当年', date='202501')` | 深圳证券交易所-统计资料-股票行业成交数据; 单次返回指定 symbol 和 date 的统计资料-股票行业成交数据 |
| `stock_szse_summary` | `import akshare as ak; ak.stock_szse_summary(date='20200619')` | 深圳证券交易所-市场总貌-证券类别统计; 单次返回指定 date 的市场总貌数据-证券类别统计（当前交易日的数据需要交易所收盘后统计） |
| `stock_tfp_em` | `import akshare as ak; ak.stock_tfp_em(date='20240426')` | 东方财富网-数据中心-特色数据-停复牌信息; 单次获取指定 date 的停复牌数据，具体更新逻辑跟目标网页统一 |
| `stock_us_daily` | `import akshare as ak; ak.stock_us_daily(symbol='AAPL', adjust='')` | 美股历史行情数据，设定 adjust="qfq" 则返回前复权后的数据，默认 adjust=""，则返回未复权的数据，历史数据按日频率更新; 单次返回指定上市公司的指定 adjust 后的所有历史行情数据 |
| `stock_us_famous_spot_em` | `import akshare as ak; ak.stock_us_famous_spot_em(symbol='科技类')` | 美股-知名美股的实时行情数据; 单次返回指定 symbol 的行情数据 |
| `stock_us_hist` | `import akshare as ak; ak.stock_us_hist(symbol='106.TTE', period='daily', start_date='20200101', end_date='20240214', adjust='qfq')` | 东方财富网-行情-美股-每日行情; 单次返回指定上市公司的指定 adjust 后的所有历史行情数据；注意其中复权参数是否生效！ |
| `stock_us_hist_min_em` | `import akshare as ak; ak.stock_us_hist_min_em(symbol='105.ATER')` | 东方财富网-行情首页-美股-每日分时行情; 单次返回指定上市公司最近 5 个交易日分钟数据，注意美股数据更新有延时 |
| `stock_us_pink_spot_em` | `import akshare as ak; ak.stock_us_pink_spot_em()` | 美股粉单市场的实时行情数据; 单次返回指定所有粉单市场的行情数据 |
| `stock_us_spot` | `import akshare as ak; ak.stock_us_spot()` | 新浪财经-美股；获取的数据有 15 分钟延迟；建议使用 ak.stock_us_spot_em() 来获取数据; 单次返回美股所有上市公司的实时行情数据 |
| `stock_us_spot_em` | `import akshare as ak; ak.stock_us_spot_em()` | 东方财富网-美股-实时行情; 单次返回美股所有上市公司的实时行情数据 |
| `stock_us_valuation_baidu` | `import akshare as ak; ak.stock_us_valuation_baidu(symbol='NVDA', indicator='总市值', period='近一年')` | 百度股市通-美股-财务报表-估值数据; 单次获取指定 symbol 的指定 indicator 的特定 period 的历史数据 |
| `stock_value_em` | `import akshare as ak; ak.stock_value_em(symbol='300766')` | 东方财富网-数据中心-估值分析-每日互动-每日互动-估值分析; 单次获取指定 symbol 的所有历史数据 |
| `stock_xgsglb_em` | `import akshare as ak; ak.stock_xgsglb_em(symbol='全部股票')` | 东方财富网-数据中心-新股数据-新股申购-新股申购与中签查询; 单次获取指定 market 的新股申购与中签查询数据 |
| `stock_xgsr_ths` | `import akshare as ak; ak.stock_xgsr_ths()` | 同花顺-数据中心-新股数据-新股上市首日; 单次返回当前交易日的所有数据 |
| `stock_xjll_em` | `import akshare as ak; ak.stock_xjll_em(date='20240331')` | 东方财富-数据中心-年报季报-业绩快报-现金流量表; 单次获取指定 date 的现金流量表数据 |
| `stock_yjbb_em` | `import akshare as ak; ak.stock_yjbb_em(date='20220331')` | 东方财富-数据中心-年报季报-业绩报表; 单次获取指定 date 的业绩报告数据 |
| `stock_yjkb_em` | `import akshare as ak; ak.stock_yjkb_em(date='20200331')` | 东方财富-数据中心-年报季报-业绩快报; 单次获取指定 date 的业绩快报数据 |
| `stock_yjyg_em` | `import akshare as ak; ak.stock_yjyg_em(date='20190331')` | 东方财富-数据中心-年报季报-业绩预告; 单次获取指定 date 的业绩预告数据 |
| `stock_yysj_em` | `import akshare as ak; ak.stock_yysj_em(symbol='沪深A股', date='20211231')` | 东方财富-数据中心-年报季报-预约披露时间; 单次获取指定 symbol 和 date 的预约披露时间数据 |
| `stock_yzxdr_em` | `import akshare as ak; ak.stock_yzxdr_em(date='20210331')` | 东方财富网-数据中心-特色数据-一致行动人; 单次返回所有历史数据 |
| `stock_zcfz_bj_em` | `import akshare as ak; ak.stock_zcfz_bj_em(date='20240331')` | 东方财富-数据中心-年报季报-业绩快报-资产负债表; 单次获取指定 date 的资产负债表数据 |
| `stock_zcfz_em` | `import akshare as ak; ak.stock_zcfz_em(date='20240331')` | 东方财富-数据中心-年报季报-业绩快报-资产负债表; 单次获取指定 date 的资产负债表数据 |
| `stock_zdhtmx_em` | `import akshare as ak; ak.stock_zdhtmx_em(start_date='20220819', end_date='20230819')` | 东方财富网-数据中心-重大合同-重大合同明细; 单次返回指定 start_date 和 end_date 的所有数据 |
| `stock_zh_a_cdr_daily` | `import akshare as ak; ak.stock_zh_a_cdr_daily(symbol='sh689009', start_date='20201103', end_date='20201116')` | 上海证券交易所-科创板-CDR; 单次返回指定 CDR 的日频率数据，分钟历史行情数据可以通过 stock_zh_a_minute 获取 |
| `stock_zh_a_daily` | `import akshare as ak; ak.stock_zh_a_daily(symbol='sz000001', start_date='19910403', end_date='20231027', adjust='qfq')` | 新浪财经-沪深京 A 股的数据，历史数据按日频率更新；注意其中的 **sh689009** 为 CDR，请 通过 **ak.stock_zh_a_cdr_daily** 接口获取; 单次返回指定沪深京 A 股上市公司指定日期间的历史行情日频率数据，多次获取容易封禁 IP |
| `stock_zh_a_disclosure_relation_cninfo` | `import akshare as ak; ak.stock_zh_a_disclosure_relation_cninfo(symbol='000001', market='沪深京', start_date='20230619', end_date='20231220')` | 巨潮资讯-首页-公告查询-信息披露调研; 单次获取指定 symbol 的信息披露调研数据；无数据时返回空的 pandas.DataFrame |
| `stock_zh_a_disclosure_report_cninfo` | `import akshare as ak; ak.stock_zh_a_disclosure_report_cninfo(symbol='000001', market='沪深京', category='公司治理', start_date='20230619', end_date='20231220')` | 巨潮资讯-首页-公告查询-信息披露公告; 单次获取指定 symbol 的信息披露公告数据；无数据时返回空的 pandas.DataFrame |
| `stock_zh_a_gbjg_em` | `import akshare as ak; ak.stock_zh_a_gbjg_em(symbol='603392.SH')` | 东方财富-A股数据-股本结构; 单次返回所有历史数据 |
| `stock_zh_a_gdhs` | `import akshare as ak; ak.stock_zh_a_gdhs(symbol='20230930')` | 东方财富网-数据中心-特色数据-股东户数数据; 单次获取返回所有数据 |
| `stock_zh_a_gdhs_detail_em` | `import akshare as ak; ak.stock_zh_a_gdhs_detail_em(symbol='000001')` | 东方财富网-数据中心-特色数据-股东户数详情; 单次获取指定 symbol 的所有数据 |
| `stock_zh_a_hist` | `import akshare as ak; ak.stock_zh_a_hist(symbol='000001', period='daily', start_date='20170301', end_date='20240528', adjust='')` | 东方财富-沪深京 A 股日频率数据；历史行情数据按日频率更新，当日收盘价请在收盘后获取; 单次返回指定沪深京 A 股上市公司、指定周期和指定日期间的历史行情日频率数据 |
| `stock_zh_a_hist_min_em` | `import akshare as ak; ak.stock_zh_a_hist_min_em(symbol='000001', start_date='2024-03-20 09:30:00', end_date='2024-03-20 15:00:00', period='1', adjust='')` | 东方财富网-行情首页-沪深京 A 股-每日分时行情；该接口只能获取近期的分时数据，注意时间周期的设置; 单次返回指定股票、频率、复权调整和时间区间的分时数据，其中 1 分钟数据只返回近 5 个交易日数据且不复权 |
| `stock_zh_a_hist_pre_min_em` | `import akshare as ak; ak.stock_zh_a_hist_pre_min_em(symbol='000001', start_time='09:00:00', end_time='15:40:00')` | 东方财富-股票行情-盘前数据; 单次返回指定 symbol 的最近一个交易日的股票分钟数据，包含盘前分钟数据 |
| `stock_zh_a_hist_tx` | `import akshare as ak; ak.stock_zh_a_hist_tx(symbol='sz000001', start_date='20200101', end_date='20231027', adjust='')` | 腾讯证券-日频-股票历史数据；历史数据按日频率更新，当日收盘价请在收盘后获取; 单次返回指定沪深京 A 股上市公司、指定周期和指定日期间的历史行情日频率数据 |
| `stock_zh_a_minute` | `import akshare as ak; ak.stock_zh_a_minute(symbol='sh600751', period='1', adjust='qfq')` | 新浪财经-沪深京 A 股股票或者指数的分时数据，目前可以获取 1, 5, 15, 30, 60 分钟的数据频率，可以指定是否复权; 单次返回指定股票或指数的指定频率的最近交易日的历史分时行情数据；注意调用频率 |
| `stock_zh_a_new` | `import akshare as ak; ak.stock_zh_a_new()` | 新浪财经-行情中心-沪深股市-次新股; 单次返回所有次新股行情数据，由于次新股名单随着交易日变化而变化，只能获取最近交易日的数据 |
| `stock_zh_a_new_em` | `import akshare as ak; ak.stock_zh_a_new_em()` | 东方财富网-行情中心-沪深个股-新股; 单次返回当前交易日新股板块的所有股票的行情数据 |
| `stock_zh_a_spot` | `import akshare as ak; ak.stock_zh_a_spot()` | 新浪财经-沪深京 A 股数据，重复运行本函数会被新浪暂时封 IP，建议增加时间间隔; 单次返回沪深京 A 股上市公司的实时行情数据 |
| `stock_zh_a_spot_em` | `import akshare as ak; ak.stock_zh_a_spot_em()` | 东方财富网-沪深京 A 股-实时行情数据; 单次返回所有沪深京 A 股上市公司的实时行情数据 |
| `stock_zh_a_spot_tx` | `import akshare as ak; ak.stock_zh_a_spot_tx()` |  |
| `stock_zh_a_st_em` | `import akshare as ak; ak.stock_zh_a_st_em()` | 东方财富网-行情中心-沪深个股-风险警示板; 单次返回当前交易日风险警示板的所有股票的行情数据 |
| `stock_zh_a_stop_em` | `import akshare as ak; ak.stock_zh_a_stop_em()` | 东方财富网-行情中心-沪深个股-两网及退市; 单次返回当前交易日两网及退市的所有股票的行情数据 |
| `stock_zh_a_tick_tx_js` | `import akshare as ak; ak.stock_zh_a_tick_tx_js()` |  |
| `stock_zh_ab_comparison_em` | `import akshare as ak; ak.stock_zh_ab_comparison_em()` | 东方财富网-行情中心-沪深京个股-AB股比价-全部AB股比价; 单次返回全部 AB 股比价的实时行情数据 |
| `stock_zh_ah_daily` | `import akshare as ak; ak.stock_zh_ah_daily(symbol='02318', start_year='2022', end_year='2024', adjust='')` | 腾讯财经-A+H 股数据; 单次返回指定参数的 A+H 上市公司的历史行情数据 |
| `stock_zh_ah_name` | `import akshare as ak; ak.stock_zh_ah_name()` | A+H 股数据是从腾讯财经获取的数据，历史数据按日频率更新; 单次返回所有 A+H 上市公司的代码和名称 |
| `stock_zh_ah_spot` | `import akshare as ak; ak.stock_zh_ah_spot()` | A+H 股数据是从腾讯财经获取的数据，延迟 15 分钟更新; 单次返回所有 A+H 上市公司的实时行情数据 |
| `stock_zh_ah_spot_em` | `import akshare as ak; ak.stock_zh_ah_spot_em()` | 东方财富网-行情中心-沪深港通-AH股比价-实时行情，延迟 15 分钟更新; 单次返回所有 A+H 上市公司的实时行情数据 |
| `stock_zh_b_daily` | `import akshare as ak; ak.stock_zh_b_daily(symbol='sh900901', start_date='19900103', end_date='20240722', adjust='qfq')` | B 股数据是从新浪财经获取的数据，历史数据按日频率更新; 单次返回指定 B 股上市公司指定日期间的历史行情日频率数据 |
| `stock_zh_b_minute` | `import akshare as ak; ak.stock_zh_b_minute(symbol='sh900901', period='1', adjust='qfq')` | 新浪财经 B 股股票或者指数的分时数据，目前可以获取 1, 5, 15, 30, 60 分钟的数据频率，可以指定是否复权; 单次返回指定股票或指数的指定频率的最近交易日的历史分时行情数据 |
| `stock_zh_b_spot` | `import akshare as ak; ak.stock_zh_b_spot()` | B 股数据是从新浪财经获取的数据，重复运行本函数会被新浪暂时封 IP，建议增加时间间隔; 单次返回所有 B 股上市公司的实时行情数据 |
| `stock_zh_b_spot_em` | `import akshare as ak; ak.stock_zh_b_spot_em()` | 东方财富网-实时行情数据; 单次返回所有 B 股上市公司的实时行情数据 |
| `stock_zh_dupont_comparison_em` | `import akshare as ak; ak.stock_zh_dupont_comparison_em(symbol='SZ000895')` | 东方财富-行情中心-同行比较-杜邦分析比较; 单次返回全部数据 |
| `stock_zh_growth_comparison_em` | `import akshare as ak; ak.stock_zh_growth_comparison_em(symbol='SZ000895')` | 东方财富-行情中心-同行比较-成长性比较; 单次返回全部数据 |
| `stock_zh_kcb_daily` | `import akshare as ak; ak.stock_zh_kcb_daily(symbol='sh688399', adjust='hfq')` | 新浪财经-科创板股票历史行情数据; 单次返回指定 symbol 和 adjust 的所有历史行情数据；请控制采集的频率，大量抓取容易封IP |
| `stock_zh_kcb_report_em` | `import akshare as ak; ak.stock_zh_kcb_report_em(from_page=1, to_page=100)` | 东方财富-科创板报告数据; 单次返回所有科创板上市公司的报告数据 |
| `stock_zh_kcb_spot` | `import akshare as ak; ak.stock_zh_kcb_spot()` | 新浪财经-科创板股票实时行情数据; 单次返回所有科创板上市公司的实时行情数据；请控制采集的频率，大量抓取容易封IP |
| `stock_zh_scale_comparison_em` | `import akshare as ak; ak.stock_zh_scale_comparison_em(symbol='SZ000895')` | 东方财富-行情中心-同行比较-公司规模; 单次返回全部数据 |
| `stock_zh_valuation_baidu` | `import akshare as ak; ak.stock_zh_valuation_baidu(symbol='002044', indicator='总市值', period='近一年')` | 百度股市通-A 股-财务报表-估值数据; 单次获取指定 symbol 和 indicator 的所有历史数据 |
| `stock_zh_valuation_comparison_em` | `import akshare as ak; ak.stock_zh_valuation_comparison_em(symbol='SZ000895')` | 东方财富-行情中心-同行比较-估值比较; 单次返回全部数据 |
| `stock_zh_vote_baidu` | `import akshare as ak; ak.stock_zh_vote_baidu(symbol='000001', indicator='指数')` | 百度股市通- A 股或指数-股评-投票; 单次获取指定 symbol 和 indicator 的所有数据 |
| `stock_zt_pool_dtgc_em` | `import akshare as ak; ak.stock_zt_pool_dtgc_em(date='20241011')` | 东方财富网-行情中心-涨停板行情-跌停股池; 单次返回指定 date 的跌停股池数据；该接口只能获取近期的数据 |
| `stock_zt_pool_em` | `import akshare as ak; ak.stock_zt_pool_em(date='20241008')` | 东方财富网-行情中心-涨停板行情-涨停股池; 单次返回指定 date 的涨停股池数据；该接口只能获取近期的数据 |
| `stock_zt_pool_previous_em` | `import akshare as ak; ak.stock_zt_pool_previous_em(date='20240415')` | 东方财富网-行情中心-涨停板行情-昨日涨停股池; 单次返回指定 date 的昨日涨停股池数据；该接口只能获取近期的数据 |
| `stock_zt_pool_strong_em` | `import akshare as ak; ak.stock_zt_pool_strong_em(date='20241231')` | 东方财富网-行情中心-涨停板行情-强势股池; 单次返回指定 date 的强势股池数据；该接口只能获取近期的数据 |
| `stock_zt_pool_sub_new_em` | `import akshare as ak; ak.stock_zt_pool_sub_new_em(date='20241231')` | 东方财富网-行情中心-涨停板行情-次新股池; 单次返回指定 date 的次新股池数据；该接口只能获取近期的数据 |
| `stock_zt_pool_zbgc_em` | `import akshare as ak; ak.stock_zt_pool_zbgc_em(date='20241011')` | 东方财富网-行情中心-涨停板行情-炸板股池; 单次返回指定 date 的炸板股池数据；该接口只能获取近期的数据 |
| `stock_zygc_em` | `import akshare as ak; ak.stock_zygc_em(symbol='SH688041')` | 东方财富网-个股-主营构成; 单次返回所有历史数据 |
| `stock_zyjs_ths` | `import akshare as ak; ak.stock_zyjs_ths(symbol='000066')` | 同花顺-主营介绍; 单次返回所有数据 |

### stock_feature (6)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `stock_board_concept_name_ths` | `import akshare as ak; ak.stock_board_concept_name_ths()` |  |
| `stock_board_concept_summary_ths` | `import akshare as ak; ak.stock_board_concept_summary_ths()` |  |
| `stock_board_industry_info_ths` | `import akshare as ak; ak.stock_board_industry_info_ths()` |  |
| `stock_board_industry_name_ths` | `import akshare as ak; ak.stock_board_industry_name_ths()` |  |
| `stock_classify_sina` | `import akshare as ak; ak.stock_classify_sina()` |  |
| `stock_lhb_stock_detail_date_em` | `import akshare as ak; ak.stock_lhb_stock_detail_date_em()` |  |

### stock_fundamental (4)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `stock_financial_abstract_ths` | `import akshare as ak; ak.stock_financial_abstract_ths()` |  |
| `stock_financial_benefit_ths` | `import akshare as ak; ak.stock_financial_benefit_ths()` |  |
| `stock_financial_cash_ths` | `import akshare as ak; ak.stock_financial_cash_ths()` |  |
| `stock_financial_debt_ths` | `import akshare as ak; ak.stock_financial_debt_ths()` |  |

### tool (1)

| 接口 | 一行请求 | 简述/限制 |
|---|---|---|
| `tool_trade_date_hist_sina` | `import akshare as ak; ak.tool_trade_date_hist_sina()` | 新浪财经-股票交易日历数据; 单次返回从 1990-12-19 到 2024-12-31 之间的股票交易日历数据，这里补充 1992-05-04 进入交易日 |

## AKShare 请求/返回样例

代表性只读请求 **8** 个：成功 **5**，失败 **3**。每行均为独立 JSON。

```jsonl
{"category":"stock","request":"import akshare as ak; ak.stock_individual_info_em(symbol=\"000001\")","status":"failure","response":null,"error":"requests.exceptions.ProxyError: HTTPSConnectionPool(host='push2.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/stock/get?fltt=2&invt=2&fields=f120%2Cf121%2Cf122%2Cf174%2Cf175%2Cf59%2Cf163%2Cf43%2Cf57%2Cf58%2Cf169%2Cf170%2Cf46%2Cf44%2Cf51%2Cf168%2Cf47%2Cf164%2Cf116%2Cf60%2Cf45%2Cf52%2Cf50%2Cf48%2Cf167%2Cf117%2Cf71%2Cf161%2Cf49%2C…"}
{"category":"fund","request":"import akshare as ak; ak.fund_open_fund_info_em(symbol=\"710001\", indicator=\"单位净值走势\")","status":"success","response":{"type":"DataFrame","row_count":3629,"columns":["净值日期","单位净值"],"records":[{"净值日期":"2011-09-21T00:00:00.000","单位净值":1.0,"日增长率":0.0},{"净值日期":"2011-09-23T00:00:00.000","单位净值":1.0,"日增长率":0.0}]},"error":null}
{"category":"futures","request":"import akshare as ak; ak.futures_zh_spot(symbol=\"RB0\", market=\"CF\", adjust=\"0\")","status":"success","response":{"type":"DataFrame","row_count":1,"columns":["symbol","time"],"records":[{"symbol":"螺纹钢连续","time":"230000","open":3164.0,"high":3183.0,"low":3161.0,"current_price":3173.0,"bid_price":3172.0,"ask_price":3173.0,"buy_vol":218,"sell_vol":7}]},"error":null}
{"category":"option","request":"import akshare as ak; ak.option_current_em()","status":"failure","response":null,"error":"requests.exceptions.ProxyError: HTTPSConnectionPool(host='23.push2.eastmoney.com', port=443): Max retries exceeded with url: /api/qt/clist/get?pn=1&pz=100&po=1&np=1&ut=bd1d9ddb04089700cf9c27f6f7426281&fltt=2&invt=2&fid=f3&fs=m%3A10%2Cm%3A12%2Cm%3A140%2Cm%3A141%2Cm%3A151%2Cm%3A163%2Cm%3A226&fields=f1%2Cf2%2Cf3%2Cf4%2Cf5%2Cf6%2Cf7%2Cf8%2Cf9%2Cf10%2C…"}
{"category":"bond","request":"import akshare as ak; ak.bond_zh_hs_spot(start_page=\"1\", end_page=\"1\")","status":"failure","response":null,"error":"akshare.utils.demjson.JSONDecodeError: No value to decode"}
{"category":"macro","request":"import akshare as ak; ak.macro_china_gdp()","status":"success","response":{"type":"DataFrame","row_count":82,"columns":["季度","国内生产总值-绝对值"],"records":[{"季度":"2026年第1-2季度","国内生产总值-绝对值":695704.0,"国内生产总值-同比增长":4.7,"第一产业-绝对值":31521.8,"第一产业-同比增长":3.7,"第二产业-绝对值":250472.9,"第二产业-同比增长":3.9,"第三产业-绝对值":413709.2,"第三产业-同比增长":5.2},{"季度":"2026年第1季度","国内生产总值-绝对值":334192.9,"国内生产总值-同比增长":5.0,"第一产业-绝对值":11940.8,"第一产业-同比增长":3.8,"第二产业-绝对值":116134.9,"第二产业-同比增长":4.9,"第三产业-绝对值":206117.2,"第三产业-同比增长":5.2}]},"error":null}
{"category":"fx","request":"import akshare as ak; ak.fx_spot_quote()","status":"success","response":{"type":"DataFrame","row_count":25,"columns":["货币对","买报价"],"records":[{"货币对":"USD/CNY","买报价":null,"卖报价":null},{"货币对":"EUR/CNY","买报价":null,"卖报价":null}]},"error":null}
{"category":"crypto","request":"import akshare as ak; ak.crypto_js_spot()","status":"success","response":{"type":"DataFrame","row_count":10,"columns":["市场","交易品种"],"records":[{"市场":"Bitfinex(香港)","交易品种":"LTCUSD","最近报价":67.465,"涨跌额":0.59,"涨跌幅":0.87,"24小时最高":68.867,"24小时最低":66.259,"24小时成交量":6893.13,"更新时间":"2023-10-02 22:45:09"},{"市场":"Bitflyer(日本)","交易品种":"BTCJPY","最近报价":4244238.0,"涨跌额":191147.0,"涨跌幅":4.72,"24小时最高":4278000.0,"24小时最低":4042615.0,"24小时成交量":1803.99,"更新时间":"2023-10-02 22:45:09"}]},"error":null}
```

## OpenBB Platform

共 **432** 条目录记录；分类：`cftc` 4、`commodity` 7、`crypto` 4、`currency` 7、`derivatives` 16、`econometrics` 15、`economy` 54、`equity` 146、`etf` 31、`famafrench` 7、`federal_reserve` 3、`fixedincome` 34、`imf_utils` 10、`index` 16、`news` 11、`quantitative` 19、`regulators` 8、`technical` 27、`uscongress` 13。

### cftc (4)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `cftc.apps.json` | `` | `requests.get("http://127.0.0.1:6900/api/v1/cftc/apps.json", params={}, timeout=30).json()` | Get the IMF apps.json file. This endpoint serves the apps.json file containing OpenBB Wor…; method=GET |
| `cftc.cot` | `cftc` | `obb.cftc.cot(code="CODE", provider="cftc")` | Get Commitment of Traders Reports.; method=GET; model=COT; required=code; credential fields=cftc_app_toke… |
| `cftc.cot_search` | `cftc` | `obb.cftc.cot_search(provider="cftc")` | Search current Commitment of Traders Reports.; method=GET; model=COTSearch; credential fields=cftc_app_token; provid… |
| `cftc.get_cot_choices` | `` | `requests.get("http://127.0.0.1:6900/api/v1/cftc/get_cot_choices", params={}, timeout=30).json()` | Get the choices for the COT command in Workspace.; method=GET |

### commodity (7)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `commodity.petroleum_status_report` | `eia` | `obb.commodity.petroleum_status_report(provider="eia")` | EIA Weekly Petroleum Status Report.; method=GET; model=PetroleumStatusReport; credential fields=eia_api_ke… |
| `commodity.price.spot` | `fred` | `obb.commodity.price.spot(provider="fred")` | Commodity Spot Prices.; method=GET; model=CommoditySpotPrices; credential fields=fred_api_key… |
| `commodity.psd_data` | `government_us` | `obb.commodity.psd_data(provider="government_us")` | Get data tables and historical time series from the USDA FAS Production, Supply, and Dist…; method=GET; model=CommodityPsdData; credential fields=none; provider … |
| `commodity.psd_report` | `government_us` | `obb.commodity.psd_report(commodity="VALUE", year=1, month="VALUE", provider="government_us")` | Agriculture commodity production, supply, and distribution PDF reports (World Agricultura…; method=GET; model=CommodityPsdReport; required=commodity,year,month; … |
| `commodity.short_term_energy_outlook` | `eia` | `obb.commodity.short_term_energy_outlook(provider="eia")` | Monthly short term (18 month) projections using EIA's STEO model. Source: www.eia.gov/ste…; method=GET; model=ShortTermEnergyOutlook; credential fields=eia_api_k… |
| `commodity.weather_bulletins` | `government_us` | `obb.commodity.weather_bulletins(provider="government_us")` | Get current and historical weather bulletins with their PDF links. This command returns o…; method=GET; model=WeatherBulletin; paging/size defaults=year:2026; cr… |
| `commodity.weather_bulletins_download` | `government_us` | `obb.commodity.weather_bulletins_download(urls=["VALUE"], provider="government_us")` | Download one, or more, weather bulletin documents. This command returns only the results …; method=POST; model=WeatherBulletinDownload; required=urls; credential… |

### crypto (4)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `crypto.price.historical` | `fmp` | `obb.crypto.price.historical(symbol="AAPL", provider="fmp")` | Get historical price data for cryptocurrency pair(s) within a provider.; method=GET; model=CryptoHistorical; required=symbol; credential field… |
| `crypto.price.historical` | `tiingo` | `obb.crypto.price.historical(symbol="AAPL", provider="tiingo")` | Get historical price data for cryptocurrency pair(s) within a provider.; method=GET; model=CryptoHistorical; required=symbol; credential field… |
| `crypto.price.historical` | `yfinance` | `obb.crypto.price.historical(symbol="AAPL", provider="yfinance")` | Get historical price data for cryptocurrency pair(s) within a provider.; method=GET; model=CryptoHistorical; required=symbol; credential field… |
| `crypto.search` | `fmp` | `obb.crypto.search(provider="fmp")` | Search available cryptocurrency pairs within a provider.; method=GET; model=CryptoSearch; credential fields=fmp_api_key; provid… |

### currency (7)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `currency.price.historical` | `fmp` | `obb.currency.price.historical(symbol="AAPL", provider="fmp")` | Currency Historical Price. Currency historical data. Currency historical prices refer to …; method=GET; model=CurrencyHistorical; required=symbol; credential fie… |
| `currency.price.historical` | `tiingo` | `obb.currency.price.historical(symbol="AAPL", provider="tiingo")` | Currency Historical Price. Currency historical data. Currency historical prices refer to …; method=GET; model=CurrencyHistorical; required=symbol; credential fie… |
| `currency.price.historical` | `yfinance` | `obb.currency.price.historical(symbol="AAPL", provider="yfinance")` | Currency Historical Price. Currency historical data. Currency historical prices refer to …; method=GET; model=CurrencyHistorical; required=symbol; credential fie… |
| `currency.reference_rates` | `ecb` | `obb.currency.reference_rates(provider="ecb")` | Get current, official, currency reference rates. Foreign exchange reference rates are the…; method=GET; model=CurrencyReferenceRates; credential fields=none; pro… |
| `currency.search` | `fmp` | `obb.currency.search(provider="fmp")` | Currency Search. Search available currency pairs. Currency pairs are the national currenc…; method=GET; model=CurrencyPairs; credential fields=fmp_api_key; provi… |
| `currency.search` | `intrinio` | `obb.currency.search(provider="intrinio")` | Currency Search. Search available currency pairs. Currency pairs are the national currenc…; method=GET; model=CurrencyPairs; credential fields=intrinio_api_key; … |
| `currency.snapshots` | `fmp` | `obb.currency.snapshots(provider="fmp")` | Snapshots of currency exchange rates from an indirect or direct perspective of a base cur…; method=GET; model=CurrencySnapshots; credential fields=fmp_api_key; p… |

### derivatives (16)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `derivatives.futures.curve` | `cboe` | `obb.derivatives.futures.curve(symbol="AAPL", provider="cboe")` | Futures Term Structure, current or historical.; method=GET; model=FuturesCurve; required=symbol; credential fields=no… |
| `derivatives.futures.curve` | `deribit` | `obb.derivatives.futures.curve(symbol="AAPL", provider="deribit")` | Futures Term Structure, current or historical.; method=GET; model=FuturesCurve; required=symbol; credential fields=no… |
| `derivatives.futures.curve` | `yfinance` | `obb.derivatives.futures.curve(symbol="AAPL", provider="yfinance")` | Futures Term Structure, current or historical.; method=GET; model=FuturesCurve; required=symbol; credential fields=no… |
| `derivatives.futures.historical` | `deribit` | `obb.derivatives.futures.historical(symbol="AAPL", provider="deribit")` | Historical futures prices.; method=GET; model=FuturesHistorical; required=symbol; credential fiel… |
| `derivatives.futures.historical` | `yfinance` | `obb.derivatives.futures.historical(symbol="AAPL", provider="yfinance")` | Historical futures prices.; method=GET; model=FuturesHistorical; required=symbol; credential fiel… |
| `derivatives.futures.info` | `deribit` | `obb.derivatives.futures.info(provider="deribit")` | Get current trading statistics by futures contract symbol.; method=GET; model=FuturesInfo; credential fields=none; provider rate/… |
| `derivatives.futures.instruments` | `deribit` | `obb.derivatives.futures.instruments(provider="deribit")` | Get reference data for available futures instruments by provider.; method=GET; model=FuturesInstruments; credential fields=none; provide… |
| `derivatives.options.chains` | `cboe` | `obb.derivatives.options.chains(symbol="AAPL", provider="cboe")` | Get the complete options chain for a ticker.; method=GET; model=OptionsChains; required=symbol; credential fields=n… |
| `derivatives.options.chains` | `deribit` | `obb.derivatives.options.chains(symbol="AAPL", provider="deribit")` | Get the complete options chain for a ticker.; method=GET; model=OptionsChains; required=symbol; credential fields=n… |
| `derivatives.options.chains` | `intrinio` | `obb.derivatives.options.chains(symbol="AAPL", provider="intrinio")` | Get the complete options chain for a ticker.; method=GET; model=OptionsChains; required=symbol; credential fields=i… |
| `derivatives.options.chains` | `tmx` | `obb.derivatives.options.chains(symbol="AAPL", provider="tmx")` | Get the complete options chain for a ticker.; method=GET; model=OptionsChains; required=symbol; credential fields=n… |
| `derivatives.options.chains` | `tradier` | `obb.derivatives.options.chains(symbol="AAPL", provider="tradier")` | Get the complete options chain for a ticker.; method=GET; model=OptionsChains; required=symbol; credential fields=t… |
| `derivatives.options.chains` | `yfinance` | `obb.derivatives.options.chains(symbol="AAPL", provider="yfinance")` | Get the complete options chain for a ticker.; method=GET; model=OptionsChains; required=symbol; credential fields=n… |
| `derivatives.options.snapshots` | `intrinio` | `obb.derivatives.options.snapshots(provider="intrinio")` | Get a snapshot of the options market universe.; method=GET; model=OptionsSnapshots; credential fields=intrinio_api_ke… |
| `derivatives.options.surface` | `` | `obb.derivatives.options.surface(data=[{"date":"2026-01-01","close":100.0}])` | Filter and process the options chains data for volatility. Data posted can be an instance…; method=POST; required=data; read/retrieval or analytic POST; not a st… |
| `derivatives.options.unusual` | `intrinio` | `obb.derivatives.options.unusual(provider="intrinio")` | Get the complete options chain for a ticker.; method=GET; model=OptionsUnusual; credential fields=intrinio_api_key;… |

### econometrics (15)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `econometrics.autocorrelation` | `` | `obb.econometrics.autocorrelation(data=[{"date":"2026-01-01","close":100.0}], y_column="y", x_columns=["x"])` | Perform Durbin-Watson test for autocorrelation. The Durbin-Watson test is a widely used m…; method=POST; required=data,y_column,x_columns; read/retrieval or anal… |
| `econometrics.causality` | `` | `obb.econometrics.causality(data=[{"date":"2026-01-01","close":100.0}], y_column="y", x_column="x")` | Perform Granger causality test to determine if X 'causes' y. The Granger causality test i…; method=POST; required=data,y_column,x_column; read/retrieval or analy… |
| `econometrics.cointegration` | `` | `obb.econometrics.cointegration(data=[{"date":"2026-01-01","close":100.0}], columns=["VALUE"])` | Show co-integration between two timeseries using the two step Engle-Granger test. The two…; method=POST; required=data,columns; read/retrieval or analytic POST; … |
| `econometrics.correlation_matrix` | `` | `obb.econometrics.correlation_matrix(data=[{"date":"2026-01-01","close":100.0}])` | Get the correlation matrix of an input dataset. The correlation matrix provides a view of…; method=POST; required=data; read/retrieval or analytic POST; not a st… |
| `econometrics.ols_regression` | `` | `obb.econometrics.ols_regression(data=[{"date":"2026-01-01","close":100.0}], y_column="y", x_columns=["x"])` | Perform Ordinary Least Squares (OLS) regression. OLS regression is a fundamental statisti…; method=POST; required=data,y_column,x_columns; read/retrieval or anal… |
| `econometrics.ols_regression_summary` | `` | `obb.econometrics.ols_regression_summary(data=[{"date":"2026-01-01","close":100.0}], y_column="y", x_columns=["x"])` | Perform Ordinary Least Squares (OLS) regression. This returns the summary object from sta…; method=POST; required=data,y_column,x_columns; read/retrieval or anal… |
| `econometrics.panel_between` | `` | `obb.econometrics.panel_between(data=[{"date":"2026-01-01","close":100.0}], y_column="y", x_columns=["x"])` | Perform a Between estimator regression on panel data. The Between estimator for regressio…; method=POST; required=data,y_column,x_columns; read/retrieval or anal… |
| `econometrics.panel_first_difference` | `` | `obb.econometrics.panel_first_difference(data=[{"date":"2026-01-01","close":100.0}], y_column="y", x_columns=["x"])` | Perform a first-difference estimate for panel data. The First-Difference estimator for pa…; method=POST; required=data,y_column,x_columns; read/retrieval or anal… |
| `econometrics.panel_fixed` | `` | `obb.econometrics.panel_fixed(data=[{"date":"2026-01-01","close":100.0}], y_column="y", x_columns=["x"])` | One- and two-way fixed effects estimator for panel data. The Fixed Effects estimator to p…; method=POST; required=data,y_column,x_columns; read/retrieval or anal… |
| `econometrics.panel_fmac` | `` | `obb.econometrics.panel_fmac(data=[{"date":"2026-01-01","close":100.0}], y_column="y", x_columns=["x"])` | Fama-MacBeth estimator for panel data. The Fama-MacBeth estimator, a two-step procedure r…; method=POST; required=data,y_column,x_columns; read/retrieval or anal… |
| `econometrics.panel_pooled` | `` | `obb.econometrics.panel_pooled(data=[{"date":"2026-01-01","close":100.0}], y_column="y", x_columns=["x"])` | Perform a Pooled coefficient estimator regression on panel data. The Pooled coefficient e…; method=POST; required=data,y_column,x_columns; read/retrieval or anal… |
| `econometrics.panel_random_effects` | `` | `obb.econometrics.panel_random_effects(data=[{"date":"2026-01-01","close":100.0}], y_column="y", x_columns=["x"])` | Perform One-way Random Effects model for panel data. One-way Random Effects model to pane…; method=POST; required=data,y_column,x_columns; read/retrieval or anal… |
| `econometrics.residual_autocorrelation` | `` | `obb.econometrics.residual_autocorrelation(data=[{"date":"2026-01-01","close":100.0}], y_column="y", x_columns=["x"])` | Perform Breusch-Godfrey Lagrange Multiplier tests for residual autocorrelation. The Breus…; method=POST; required=data,y_column,x_columns; read/retrieval or anal… |
| `econometrics.unit_root` | `` | `obb.econometrics.unit_root(data=[{"date":"2026-01-01","close":100.0}], column="VALUE")` | Perform Augmented Dickey-Fuller (ADF) unit root test. The ADF test is a popular method fo…; method=POST; required=data,column; read/retrieval or analytic POST; n… |
| `econometrics.variance_inflation_factor` | `` | `obb.econometrics.variance_inflation_factor(data=[{"date":"2026-01-01","close":100.0}])` | Calculate VIF (variance inflation factor), which tests for collinearity. It quantifies th…; method=POST; required=data; read/retrieval or analytic POST; not a st… |

### economy (54)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `economy.available_indicators` | `econdb` | `obb.economy.available_indicators(provider="econdb")` | Get the available economic indicators for a provider.; method=GET; model=AvailableIndicators; credential fields=econdb_api_k… |
| `economy.available_indicators` | `imf` | `obb.economy.available_indicators(provider="imf")` | Get the available economic indicators for a provider.; method=GET; model=AvailableIndicators; credential fields=none; provid… |
| `economy.balance_of_payments` | `ecb` | `obb.economy.balance_of_payments(provider="ecb")` | Balance of Payments Reports.; method=GET; model=BalanceOfPayments; credential fields=none; provider… |
| `economy.balance_of_payments` | `fred` | `obb.economy.balance_of_payments(provider="fred")` | Balance of Payments Reports.; method=GET; model=BalanceOfPayments; credential fields=fred_api_key; … |
| `economy.calendar` | `fmp` | `obb.economy.calendar(provider="fmp")` | Get the upcoming, or historical, economic calendar of global events.; method=GET; model=EconomicCalendar; credential fields=fmp_api_key; pr… |
| `economy.calendar` | `fred` | `obb.economy.calendar(provider="fred")` | Get the upcoming, or historical, economic calendar of global events.; method=GET; model=EconomicCalendar; credential fields=fred_api_key; p… |
| `economy.calendar` | `nasdaq` | `obb.economy.calendar(provider="nasdaq")` | Get the upcoming, or historical, economic calendar of global events.; method=GET; model=EconomicCalendar; credential fields=nasdaq_api_key;… |
| `economy.calendar` | `tradingeconomics` | `obb.economy.calendar(provider="tradingeconomics")` | Get the upcoming, or historical, economic calendar of global events.; method=GET; model=EconomicCalendar; credential fields=tradingeconomic… |
| `economy.central_bank_holdings` | `federal_reserve` | `obb.economy.central_bank_holdings(provider="federal_reserve")` | Get the balance sheet holdings of a central bank.; method=GET; model=CentralBankHoldings; credential fields=none; provid… |
| `economy.composite_leading_indicator` | `oecd` | `obb.economy.composite_leading_indicator(provider="oecd")` | Get the composite leading indicator (CLI). It is designed to provide early signals of tur…; method=GET; model=CompositeLeadingIndicator; credential fields=none; … |
| `economy.country_profile` | `econdb` | `obb.economy.country_profile(country="united_states", provider="econdb")` | Get a profile of country statistics and economic indicators.; method=GET; model=CountryProfile; required=country; credential fields… |
| `economy.cpi` | `fred` | `obb.economy.cpi(provider="fred")` | Get Consumer Price Index (CPI) data by country.; method=GET; model=ConsumerPriceIndex; credential fields=fred_api_key;… |
| `economy.cpi` | `imf` | `obb.economy.cpi(provider="imf")` | Get Consumer Price Index (CPI) data by country.; method=GET; model=ConsumerPriceIndex; credential fields=none; provide… |
| `economy.cpi` | `oecd` | `obb.economy.cpi(provider="oecd")` | Get Consumer Price Index (CPI) data by country.; method=GET; model=ConsumerPriceIndex; credential fields=none; provide… |
| `economy.direction_of_trade` | `imf` | `obb.economy.direction_of_trade(provider="imf")` | Get Direction Of Trade Statistics from the IMF database. The Direction of Trade Statistic…; method=GET; model=DirectionOfTrade; credential fields=none; provider … |
| `economy.export_destinations` | `econdb` | `obb.economy.export_destinations(country="united_states", provider="econdb")` | Get top export destinations by country from the UN Comtrade International Trade Statistic…; method=GET; model=ExportDestinations; required=country; credential fi… |
| `economy.fomc_documents` | `federal_reserve` | `obb.economy.fomc_documents(provider="federal_reserve")` | Get lists of FOMC documents by year and document type. Source: https://www.federalreserve…; method=GET; model=FomcDocuments; credential fields=none; provider rat… |
| `economy.fred_regional` | `fred` | `obb.economy.fred_regional(symbol="AAPL", provider="fred")` | Query the Geo Fred API for regional economic data by series group. The series group ID is…; method=GET; model=FredRegional; required=symbol; paging/size defaults… |
| `economy.fred_release_table` | `fred` | `obb.economy.fred_release_table(release_id="VALUE", provider="fred")` | Get economic release data by ID and/or element from FRED.; method=GET; model=FredReleaseTable; required=release_id; credential f… |
| `economy.fred_search` | `fred` | `obb.economy.fred_search(provider="fred")` | Search for FRED series or economic releases by ID or string. This does not return the obs…; method=GET; model=FredSearch; credential fields=fred_api_key; provide… |
| `economy.fred_series` | `fred` | `obb.economy.fred_series(symbol="AAPL", provider="fred")` | Get data by series ID from FRED.; method=GET; model=FredSeries; required=symbol; paging/size defaults=l… |
| `economy.fred_series` | `intrinio` | `obb.economy.fred_series(symbol="AAPL", provider="intrinio")` | Get data by series ID from FRED.; method=GET; model=FredSeries; required=symbol; paging/size defaults=l… |
| `economy.gdp.forecast` | `oecd` | `obb.economy.gdp.forecast(provider="oecd")` | Get Forecasted GDP Data.; method=GET; model=GdpForecast; credential fields=none; provider rate/… |
| `economy.gdp.nominal` | `econdb` | `obb.economy.gdp.nominal(provider="econdb")` | Get Nominal GDP Data.; method=GET; model=GdpNominal; credential fields=econdb_api_key; provi… |
| `economy.gdp.nominal` | `oecd` | `obb.economy.gdp.nominal(provider="oecd")` | Get Nominal GDP Data.; method=GET; model=GdpNominal; credential fields=none; provider rate/h… |
| `economy.gdp.real` | `econdb` | `obb.economy.gdp.real(provider="econdb")` | Get Real GDP Data.; method=GET; model=GdpReal; credential fields=econdb_api_key; provider… |
| `economy.gdp.real` | `oecd` | `obb.economy.gdp.real(provider="oecd")` | Get Real GDP Data.; method=GET; model=GdpReal; credential fields=none; provider rate/hist… |
| `economy.house_price_index` | `oecd` | `obb.economy.house_price_index(provider="oecd")` | Get the House Price Index by country from the OECD Short-Term Economics Statistics.; method=GET; model=HousePriceIndex; credential fields=none; provider r… |
| `economy.indicators` | `econdb` | `obb.economy.indicators(symbol="AAPL", provider="econdb")` | Get economic indicators by country and indicator.; method=GET; model=EconomicIndicators; required=symbol; credential fie… |
| `economy.indicators` | `imf` | `obb.economy.indicators(symbol="AAPL", provider="imf")` | Get economic indicators by country and indicator.; method=GET; model=EconomicIndicators; required=symbol; credential fie… |
| `economy.interest_rates` | `oecd` | `obb.economy.interest_rates(provider="oecd")` | Get interest rates by country(s) and duration. Most OECD countries publish short-term, a …; method=GET; model=CountryInterestRates; credential fields=none; provi… |
| `economy.money_measures` | `federal_reserve` | `obb.economy.money_measures(provider="federal_reserve")` | Get Money Measures (M1/M2 and components). The Federal Reserve publishes as part of the H…; method=GET; model=MoneyMeasures; credential fields=none; provider rat… |
| `economy.pce` | `fred` | `obb.economy.pce(provider="fred")` | Get Personal Consumption Expenditures (PCE) reports.; method=GET; model=PersonalConsumptionExpenditures; credential fields=… |
| `economy.primary_dealer_fails` | `federal_reserve` | `obb.economy.primary_dealer_fails(provider="federal_reserve")` | Primary Dealer Statistics for Fails to Deliver and Fails to Receive. Data from the NY Fed…; method=GET; model=PrimaryDealerFails; credential fields=none; provide… |
| `economy.primary_dealer_positioning` | `federal_reserve` | `obb.economy.primary_dealer_positioning(provider="federal_reserve")` | Get Primary dealer positioning statistics.; method=GET; model=PrimaryDealerPositioning; credential fields=none; p… |
| `economy.retail_prices` | `fred` | `obb.economy.retail_prices(provider="fred")` | Get retail prices for common items.; method=GET; model=RetailPrices; credential fields=fred_api_key; provi… |
| `economy.risk_premium` | `fmp` | `obb.economy.risk_premium(provider="fmp")` | Get Market Risk Premium by country.; method=GET; model=RiskPremium; credential fields=fmp_api_key; provide… |
| `economy.share_price_index` | `oecd` | `obb.economy.share_price_index(provider="oecd")` | Get the Share Price Index by country from the OECD Short-Term Economics Statistics.; method=GET; model=SharePriceIndex; credential fields=none; provider r… |
| `economy.shipping.chokepoint_info` | `imf` | `obb.economy.shipping.chokepoint_info(provider="imf")` | Get general metadata and statistics for all maritime chokepoint locations from a given pr…; method=GET; model=MaritimeChokePointInfo; credential fields=none; pro… |
| `economy.shipping.chokepoint_volume` | `imf` | `obb.economy.shipping.chokepoint_volume(provider="imf")` | Daily transit calls and estimates of transit trade volumes for shipping lane chokepoints …; method=GET; model=MaritimeChokePointVolume; credential fields=none; p… |
| `economy.shipping.port_info` | `imf` | `obb.economy.shipping.port_info(provider="imf")` | Get general metadata and statistics for all ports from a given provider.; method=GET; model=PortInfo; credential fields=none; provider rate/his… |
| `economy.shipping.port_volume` | `econdb` | `obb.economy.shipping.port_volume(provider="econdb")` | Daily port calls and estimates of trading volumes for ports around the world.; method=GET; model=PortVolume; credential fields=econdb_api_key; provi… |
| `economy.shipping.port_volume` | `imf` | `obb.economy.shipping.port_volume(provider="imf")` | Daily port calls and estimates of trading volumes for ports around the world.; method=GET; model=PortVolume; credential fields=none; provider rate/h… |
| `economy.survey.bls_search` | `bls` | `obb.economy.survey.bls_search(provider="bls")` | Search BLS surveys by category and keyword or phrase to identify BLS series IDs.; method=GET; model=BlsSearch; credential fields=bls_api_key; provider … |
| `economy.survey.bls_series` | `bls` | `obb.economy.survey.bls_series(symbol="AAPL", provider="bls")` | Get time series data for one, or more, BLS series IDs.; method=GET; model=BlsSeries; required=symbol; credential fields=bls_a… |
| `economy.survey.economic_conditions_chicago` | `fred` | `obb.economy.survey.economic_conditions_chicago(provider="fred")` | Get The Survey Of Economic Conditions For The Chicago Region.; method=GET; model=SurveyOfEconomicConditionsChicago; credential field… |
| `economy.survey.inflation_expectations` | `federal_reserve` | `obb.economy.survey.inflation_expectations(provider="federal_reserve")` | Survey of forward inflation expectations from the Survey of Professional Forecasters.; method=GET; model=InflationExpectations; credential fields=none; prov… |
| `economy.survey.manufacturing_outlook_ny` | `fred` | `obb.economy.survey.manufacturing_outlook_ny(provider="fred")` | Get the Empire State Manufacturing Survey. It is a monthly survey of manufacturers in New…; method=GET; model=ManufacturingOutlookNY; credential fields=fred_api_… |
| `economy.survey.manufacturing_outlook_texas` | `fred` | `obb.economy.survey.manufacturing_outlook_texas(provider="fred")` | Get The Manufacturing Outlook Survey For The Texas Region.; method=GET; model=ManufacturingOutlookTexas; credential fields=fred_a… |
| `economy.survey.nonfarm_payrolls` | `fred` | `obb.economy.survey.nonfarm_payrolls(provider="fred")` | Get Nonfarm Payrolls Survey.; method=GET; model=NonFarmPayrolls; credential fields=fred_api_key; pr… |
| `economy.survey.sloos` | `fred` | `obb.economy.survey.sloos(provider="fred")` | Get Senior Loan Officers Opinion Survey.; method=GET; model=SeniorLoanOfficerSurvey; credential fields=fred_api… |
| `economy.survey.university_of_michigan` | `fred` | `obb.economy.survey.university_of_michigan(provider="fred")` | Get University of Michigan Consumer Sentiment and Inflation Expectations Surveys.; method=GET; model=UniversityOfMichigan; credential fields=fred_api_ke… |
| `economy.total_factor_productivity` | `federal_reserve` | `obb.economy.total_factor_productivity(provider="federal_reserve")` | Total Factor Productivity (TFP) A real-time, quarterly series on total factor productivit…; method=GET; model=TotalFactorProductivity; credential fields=none; pr… |
| `economy.unemployment` | `oecd` | `obb.economy.unemployment(provider="oecd")` | Get global unemployment data.; method=GET; model=Unemployment; credential fields=none; provider rate… |

### equity (146)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `equity.calendar.dividend` | `fmp` | `obb.equity.calendar.dividend(provider="fmp")` | Get historical and upcoming dividend payments. Includes dividend amount, ex-dividend and …; method=GET; model=CalendarDividend; credential fields=fmp_api_key; pr… |
| `equity.calendar.dividend` | `nasdaq` | `obb.equity.calendar.dividend(provider="nasdaq")` | Get historical and upcoming dividend payments. Includes dividend amount, ex-dividend and …; method=GET; model=CalendarDividend; credential fields=nasdaq_api_key;… |
| `equity.calendar.earnings` | `fmp` | `obb.equity.calendar.earnings(provider="fmp")` | Get historical and upcoming company earnings releases. Includes earnings per share (EPS) …; method=GET; model=CalendarEarnings; credential fields=fmp_api_key; pr… |
| `equity.calendar.earnings` | `nasdaq` | `obb.equity.calendar.earnings(provider="nasdaq")` | Get historical and upcoming company earnings releases. Includes earnings per share (EPS) …; method=GET; model=CalendarEarnings; credential fields=nasdaq_api_key;… |
| `equity.calendar.earnings` | `seeking_alpha` | `obb.equity.calendar.earnings(provider="seeking_alpha")` | Get historical and upcoming company earnings releases. Includes earnings per share (EPS) …; method=GET; model=CalendarEarnings; credential fields=none; provider … |
| `equity.calendar.earnings` | `tmx` | `obb.equity.calendar.earnings(provider="tmx")` | Get historical and upcoming company earnings releases. Includes earnings per share (EPS) …; method=GET; model=CalendarEarnings; credential fields=none; provider … |
| `equity.calendar.events` | `fmp` | `obb.equity.calendar.events(provider="fmp")` | Get historical and upcoming company events, such as Investor Day, Conference Call, Earnin…; method=GET; model=CalendarEvents; credential fields=fmp_api_key; prov… |
| `equity.calendar.ipo` | `fmp` | `obb.equity.calendar.ipo(provider="fmp")` | Get historical and upcoming initial public offerings (IPOs).; method=GET; model=CalendarIpo; paging/size defaults=limit:100; creden… |
| `equity.calendar.ipo` | `intrinio` | `obb.equity.calendar.ipo(provider="intrinio")` | Get historical and upcoming initial public offerings (IPOs).; method=GET; model=CalendarIpo; paging/size defaults=limit:100; creden… |
| `equity.calendar.ipo` | `nasdaq` | `obb.equity.calendar.ipo(provider="nasdaq")` | Get historical and upcoming initial public offerings (IPOs).; method=GET; model=CalendarIpo; paging/size defaults=limit:100; creden… |
| `equity.calendar.splits` | `fmp` | `obb.equity.calendar.splits(provider="fmp")` | Get historical and upcoming stock split operations.; method=GET; model=CalendarSplits; credential fields=fmp_api_key; prov… |
| `equity.compare.company_facts` | `sec` | `obb.equity.compare.company_facts(provider="sec")` | Compare reported company facts and fundamental data points.; method=GET; model=CompareCompanyFacts; credential fields=none; provid… |
| `equity.compare.groups` | `finviz` | `obb.equity.compare.groups(provider="finviz")` | Get company data grouped by sector, industry or country and display either performance or…; method=GET; model=CompareGroups; credential fields=none; provider rat… |
| `equity.compare.peers` | `fmp` | `obb.equity.compare.peers(symbol="AAPL", provider="fmp")` | Get the closest peers for a given company. Peers consist of companies trading on the same…; method=GET; model=EquityPeers; required=symbol; credential fields=fmp… |
| `equity.darkpool.otc` | `finra` | `obb.equity.darkpool.otc(provider="finra")` | Get the weekly aggregate trade data for Over The Counter deals. ATS and non-ATS trading d…; method=GET; model=OTCAggregate; credential fields=none; provider rate… |
| `equity.discovery.active` | `fmp` | `obb.equity.discovery.active(provider="fmp")` | Get the most actively traded stocks based on volume.; method=GET; model=EquityActive; credential fields=fmp_api_key; provid… |
| `equity.discovery.active` | `yfinance` | `obb.equity.discovery.active(provider="yfinance")` | Get the most actively traded stocks based on volume.; method=GET; model=EquityActive; credential fields=none; provider rate… |
| `equity.discovery.aggressive_small_caps` | `yfinance` | `obb.equity.discovery.aggressive_small_caps(provider="yfinance")` | Get top small cap stocks based on earnings growth.; method=GET; model=EquityAggressiveSmallCaps; credential fields=none; … |
| `equity.discovery.filings` | `fmp` | `obb.equity.discovery.filings(provider="fmp")` | Get the URLs to SEC filings reported to EDGAR database, such as 10-K, 10-Q, 8-K, and more…; method=GET; model=DiscoveryFilings; constraints=limit(ge=0); paging/s… |
| `equity.discovery.gainers` | `fmp` | `obb.equity.discovery.gainers(provider="fmp")` | Get the top price gainers in the stock market.; method=GET; model=EquityGainers; credential fields=fmp_api_key; provi… |
| `equity.discovery.gainers` | `tmx` | `obb.equity.discovery.gainers(provider="tmx")` | Get the top price gainers in the stock market.; method=GET; model=EquityGainers; credential fields=none; provider rat… |
| `equity.discovery.gainers` | `yfinance` | `obb.equity.discovery.gainers(provider="yfinance")` | Get the top price gainers in the stock market.; method=GET; model=EquityGainers; credential fields=none; provider rat… |
| `equity.discovery.growth_tech` | `yfinance` | `obb.equity.discovery.growth_tech(provider="yfinance")` | Get top tech stocks based on revenue and earnings growth.; method=GET; model=GrowthTechEquities; credential fields=none; provide… |
| `equity.discovery.latest_financial_reports` | `sec` | `obb.equity.discovery.latest_financial_reports(provider="sec")` | Get the newest quarterly, annual, and current reports for all companies.; method=GET; model=LatestFinancialReports; credential fields=none; pro… |
| `equity.discovery.losers` | `fmp` | `obb.equity.discovery.losers(provider="fmp")` | Get the top price losers in the stock market.; method=GET; model=EquityLosers; credential fields=fmp_api_key; provid… |
| `equity.discovery.losers` | `yfinance` | `obb.equity.discovery.losers(provider="yfinance")` | Get the top price losers in the stock market.; method=GET; model=EquityLosers; credential fields=none; provider rate… |
| `equity.discovery.top_retail` | `nasdaq` | `obb.equity.discovery.top_retail(provider="nasdaq")` | Track over $30B USD/day of individual investors trades. It gives a daily view into retail…; method=GET; model=TopRetail; paging/size defaults=limit:5; credential… |
| `equity.discovery.undervalued_growth` | `yfinance` | `obb.equity.discovery.undervalued_growth(provider="yfinance")` | Get potentially undervalued growth stocks.; method=GET; model=EquityUndervaluedGrowth; credential fields=none; pr… |
| `equity.discovery.undervalued_large_caps` | `yfinance` | `obb.equity.discovery.undervalued_large_caps(provider="yfinance")` | Get potentially undervalued large cap stocks.; method=GET; model=EquityUndervaluedLargeCaps; credential fields=none;… |
| `equity.estimates.analyst_search` | `benzinga` | `obb.equity.estimates.analyst_search(provider="benzinga")` | Search for specific analysts and get their forecast track record.; method=GET; model=AnalystSearch; credential fields=benzinga_api_key; … |
| `equity.estimates.consensus` | `fmp` | `obb.equity.estimates.consensus(provider="fmp")` | Get consensus price target and recommendation.; method=GET; model=PriceTargetConsensus; credential fields=fmp_api_key… |
| `equity.estimates.consensus` | `intrinio` | `obb.equity.estimates.consensus(provider="intrinio")` | Get consensus price target and recommendation.; method=GET; model=PriceTargetConsensus; credential fields=intrinio_ap… |
| `equity.estimates.consensus` | `tmx` | `obb.equity.estimates.consensus(provider="tmx")` | Get consensus price target and recommendation.; method=GET; model=PriceTargetConsensus; credential fields=none; provi… |
| `equity.estimates.consensus` | `yfinance` | `obb.equity.estimates.consensus(provider="yfinance")` | Get consensus price target and recommendation.; method=GET; model=PriceTargetConsensus; credential fields=none; provi… |
| `equity.estimates.forward_ebitda` | `fmp` | `obb.equity.estimates.forward_ebitda(provider="fmp")` | Get forward EBITDA estimates.; method=GET; model=ForwardEbitdaEstimates; credential fields=fmp_api_k… |
| `equity.estimates.forward_ebitda` | `intrinio` | `obb.equity.estimates.forward_ebitda(provider="intrinio")` | Get forward EBITDA estimates.; method=GET; model=ForwardEbitdaEstimates; credential fields=intrinio_… |
| `equity.estimates.forward_eps` | `fmp` | `obb.equity.estimates.forward_eps(provider="fmp")` | Get forward EPS estimates.; method=GET; model=ForwardEpsEstimates; credential fields=fmp_api_key;… |
| `equity.estimates.forward_eps` | `intrinio` | `obb.equity.estimates.forward_eps(provider="intrinio")` | Get forward EPS estimates.; method=GET; model=ForwardEpsEstimates; credential fields=intrinio_api… |
| `equity.estimates.forward_eps` | `seeking_alpha` | `obb.equity.estimates.forward_eps(provider="seeking_alpha")` | Get forward EPS estimates.; method=GET; model=ForwardEpsEstimates; credential fields=none; provid… |
| `equity.estimates.forward_pe` | `intrinio` | `obb.equity.estimates.forward_pe(provider="intrinio")` | Get forward PE estimates.; method=GET; model=ForwardPeEstimates; credential fields=intrinio_api_… |
| `equity.estimates.forward_sales` | `intrinio` | `obb.equity.estimates.forward_sales(provider="intrinio")` | Get forward sales estimates.; method=GET; model=ForwardSalesEstimates; credential fields=intrinio_a… |
| `equity.estimates.forward_sales` | `seeking_alpha` | `obb.equity.estimates.forward_sales(provider="seeking_alpha")` | Get forward sales estimates.; method=GET; model=ForwardSalesEstimates; credential fields=none; prov… |
| `equity.estimates.historical` | `fmp` | `obb.equity.estimates.historical(symbol="AAPL", provider="fmp")` | Get historical analyst estimates for earnings and revenue.; method=GET; model=AnalystEstimates; required=symbol; credential field… |
| `equity.estimates.price_target` | `benzinga` | `obb.equity.estimates.price_target(provider="benzinga")` | Get analyst price targets by company.; method=GET; model=PriceTarget; paging/size defaults=limit:None; crede… |
| `equity.estimates.price_target` | `finviz` | `obb.equity.estimates.price_target(provider="finviz")` | Get analyst price targets by company.; method=GET; model=PriceTarget; paging/size defaults=limit:None; crede… |
| `equity.estimates.price_target` | `fmp` | `obb.equity.estimates.price_target(provider="fmp")` | Get analyst price targets by company.; method=GET; model=PriceTarget; paging/size defaults=limit:None; crede… |
| `equity.fundamental.balance` | `fmp` | `obb.equity.fundamental.balance(symbol="AAPL", provider="fmp")` | Get the balance sheet for a given company.; method=GET; model=BalanceSheet; required=symbol; constraints=limit(ge… |
| `equity.fundamental.balance` | `intrinio` | `obb.equity.fundamental.balance(symbol="AAPL", provider="intrinio")` | Get the balance sheet for a given company.; method=GET; model=BalanceSheet; required=symbol; constraints=limit(ge… |
| `equity.fundamental.balance` | `sec` | `obb.equity.fundamental.balance(symbol="AAPL", provider="sec")` | Get the balance sheet for a given company.; method=GET; model=BalanceSheet; required=symbol; constraints=limit(ge… |
| `equity.fundamental.balance` | `yfinance` | `obb.equity.fundamental.balance(symbol="AAPL", provider="yfinance")` | Get the balance sheet for a given company.; method=GET; model=BalanceSheet; required=symbol; constraints=limit(ge… |
| `equity.fundamental.balance_growth` | `fmp` | `obb.equity.fundamental.balance_growth(symbol="AAPL", provider="fmp")` | Get the growth of a company's balance sheet items over time.; method=GET; model=BalanceSheetGrowth; required=symbol; paging/size de… |
| `equity.fundamental.balance_growth` | `sec` | `obb.equity.fundamental.balance_growth(symbol="AAPL", provider="sec")` | Get the growth of a company's balance sheet items over time.; method=GET; model=BalanceSheetGrowth; required=symbol; paging/size de… |
| `equity.fundamental.cash` | `fmp` | `obb.equity.fundamental.cash(symbol="AAPL", provider="fmp")` | Get the cash flow statement for a given company.; method=GET; model=CashFlowStatement; required=symbol; constraints=lim… |
| `equity.fundamental.cash` | `intrinio` | `obb.equity.fundamental.cash(symbol="AAPL", provider="intrinio")` | Get the cash flow statement for a given company.; method=GET; model=CashFlowStatement; required=symbol; constraints=lim… |
| `equity.fundamental.cash` | `sec` | `obb.equity.fundamental.cash(symbol="AAPL", provider="sec")` | Get the cash flow statement for a given company.; method=GET; model=CashFlowStatement; required=symbol; constraints=lim… |
| `equity.fundamental.cash` | `yfinance` | `obb.equity.fundamental.cash(symbol="AAPL", provider="yfinance")` | Get the cash flow statement for a given company.; method=GET; model=CashFlowStatement; required=symbol; constraints=lim… |
| `equity.fundamental.cash_growth` | `fmp` | `obb.equity.fundamental.cash_growth(symbol="AAPL", provider="fmp")` | Get the growth of a company's cash flow statement items over time.; method=GET; model=CashFlowStatementGrowth; required=symbol; paging/si… |
| `equity.fundamental.cash_growth` | `sec` | `obb.equity.fundamental.cash_growth(symbol="AAPL", provider="sec")` | Get the growth of a company's cash flow statement items over time.; method=GET; model=CashFlowStatementGrowth; required=symbol; paging/si… |
| `equity.fundamental.dividends` | `fmp` | `obb.equity.fundamental.dividends(symbol="AAPL", provider="fmp")` | Get historical dividend data for a given company.; method=GET; model=HistoricalDividends; required=symbol; credential fi… |
| `equity.fundamental.dividends` | `intrinio` | `obb.equity.fundamental.dividends(symbol="AAPL", provider="intrinio")` | Get historical dividend data for a given company.; method=GET; model=HistoricalDividends; required=symbol; credential fi… |
| `equity.fundamental.dividends` | `nasdaq` | `obb.equity.fundamental.dividends(symbol="AAPL", provider="nasdaq")` | Get historical dividend data for a given company.; method=GET; model=HistoricalDividends; required=symbol; credential fi… |
| `equity.fundamental.dividends` | `tmx` | `obb.equity.fundamental.dividends(symbol="AAPL", provider="tmx")` | Get historical dividend data for a given company.; method=GET; model=HistoricalDividends; required=symbol; credential fi… |
| `equity.fundamental.dividends` | `yfinance` | `obb.equity.fundamental.dividends(symbol="AAPL", provider="yfinance")` | Get historical dividend data for a given company.; method=GET; model=HistoricalDividends; required=symbol; credential fi… |
| `equity.fundamental.employee_count` | `fmp` | `obb.equity.fundamental.employee_count(symbol="AAPL", provider="fmp")` | Get historical employee count data for a given company.; method=GET; model=HistoricalEmployees; required=symbol; credential fi… |
| `equity.fundamental.esg_score` | `fmp` | `obb.equity.fundamental.esg_score(symbol="AAPL", provider="fmp")` | Get ESG (Environmental, Social, and Governance) scores from company disclosures.; method=GET; model=EsgScore; required=symbol; credential fields=fmp_ap… |
| `equity.fundamental.filings` | `fmp` | `obb.equity.fundamental.filings(provider="fmp")` | Get public company filings.; method=GET; model=CompanyFilings; credential fields=fmp_api_key; prov… |
| `equity.fundamental.filings` | `intrinio` | `obb.equity.fundamental.filings(provider="intrinio")` | Get public company filings.; method=GET; model=CompanyFilings; credential fields=intrinio_api_key;… |
| `equity.fundamental.filings` | `nasdaq` | `obb.equity.fundamental.filings(provider="nasdaq")` | Get public company filings.; method=GET; model=CompanyFilings; credential fields=nasdaq_api_key; p… |
| `equity.fundamental.filings` | `sec` | `obb.equity.fundamental.filings(provider="sec")` | Get public company filings.; method=GET; model=CompanyFilings; credential fields=none; provider ra… |
| `equity.fundamental.filings` | `tmx` | `obb.equity.fundamental.filings(provider="tmx")` | Get public company filings.; method=GET; model=CompanyFilings; credential fields=none; provider ra… |
| `equity.fundamental.historical_attributes` | `intrinio` | `obb.equity.fundamental.historical_attributes(symbol="AAPL", tag="VALUE", provider="intrinio")` | Get the historical values of a data tag from Intrinio.; method=GET; model=HistoricalAttributes; required=symbol,tag; paging/s… |
| `equity.fundamental.historical_eps` | `alpha_vantage` | `obb.equity.fundamental.historical_eps(symbol="AAPL", provider="alpha_vantage")` | Get historical earnings per share data for a given company.; method=GET; model=HistoricalEps; required=symbol; credential fields=a… |
| `equity.fundamental.historical_eps` | `fmp` | `obb.equity.fundamental.historical_eps(symbol="AAPL", provider="fmp")` | Get historical earnings per share data for a given company.; method=GET; model=HistoricalEps; required=symbol; credential fields=f… |
| `equity.fundamental.historical_splits` | `fmp` | `obb.equity.fundamental.historical_splits(symbol="AAPL", provider="fmp")` | Get historical stock splits for a given company.; method=GET; model=HistoricalSplits; required=symbol; credential field… |
| `equity.fundamental.income` | `fmp` | `obb.equity.fundamental.income(symbol="AAPL", provider="fmp")` | Get the income statement for a given company.; method=GET; model=IncomeStatement; required=symbol; constraints=limit… |
| `equity.fundamental.income` | `intrinio` | `obb.equity.fundamental.income(symbol="AAPL", provider="intrinio")` | Get the income statement for a given company.; method=GET; model=IncomeStatement; required=symbol; constraints=limit… |
| `equity.fundamental.income` | `sec` | `obb.equity.fundamental.income(symbol="AAPL", provider="sec")` | Get the income statement for a given company.; method=GET; model=IncomeStatement; required=symbol; constraints=limit… |
| `equity.fundamental.income` | `yfinance` | `obb.equity.fundamental.income(symbol="AAPL", provider="yfinance")` | Get the income statement for a given company.; method=GET; model=IncomeStatement; required=symbol; constraints=limit… |
| `equity.fundamental.income_growth` | `fmp` | `obb.equity.fundamental.income_growth(symbol="AAPL", provider="fmp")` | Get the growth of a company's income statement items over time.; method=GET; model=IncomeStatementGrowth; required=symbol; paging/size… |
| `equity.fundamental.income_growth` | `sec` | `obb.equity.fundamental.income_growth(symbol="AAPL", provider="sec")` | Get the growth of a company's income statement items over time.; method=GET; model=IncomeStatementGrowth; required=symbol; paging/size… |
| `equity.fundamental.latest_attributes` | `intrinio` | `obb.equity.fundamental.latest_attributes(symbol="AAPL", tag="VALUE", provider="intrinio")` | Get the latest value of a data tag from Intrinio.; method=GET; model=LatestAttributes; required=symbol,tag; credential f… |
| `equity.fundamental.management` | `fmp` | `obb.equity.fundamental.management(symbol="AAPL", provider="fmp")` | Get executive management team data for a given company.; method=GET; model=KeyExecutives; required=symbol; credential fields=f… |
| `equity.fundamental.management` | `yfinance` | `obb.equity.fundamental.management(symbol="AAPL", provider="yfinance")` | Get executive management team data for a given company.; method=GET; model=KeyExecutives; required=symbol; credential fields=n… |
| `equity.fundamental.management_compensation` | `fmp` | `obb.equity.fundamental.management_compensation(symbol="AAPL", provider="fmp")` | Get executive management team compensation for a given company over time.; method=GET; model=ExecutiveCompensation; required=symbol; credential … |
| `equity.fundamental.management_discussion_analysis` | `sec` | `obb.equity.fundamental.management_discussion_analysis(symbol="AAPL", provider="sec")` | Get the Management Discussion & Analysis section from the financial statements for a give…; method=GET; model=ManagementDiscussionAnalysis; required=symbol; cred… |
| `equity.fundamental.metrics` | `finviz` | `obb.equity.fundamental.metrics(symbol="AAPL", provider="finviz")` | Get fundamental metrics for a given company.; method=GET; model=KeyMetrics; required=symbol; credential fields=none… |
| `equity.fundamental.metrics` | `fmp` | `obb.equity.fundamental.metrics(symbol="AAPL", provider="fmp")` | Get fundamental metrics for a given company.; method=GET; model=KeyMetrics; required=symbol; credential fields=fmp_… |
| `equity.fundamental.metrics` | `intrinio` | `obb.equity.fundamental.metrics(symbol="AAPL", provider="intrinio")` | Get fundamental metrics for a given company.; method=GET; model=KeyMetrics; required=symbol; credential fields=intr… |
| `equity.fundamental.metrics` | `yfinance` | `obb.equity.fundamental.metrics(symbol="AAPL", provider="yfinance")` | Get fundamental metrics for a given company.; method=GET; model=KeyMetrics; required=symbol; credential fields=none… |
| `equity.fundamental.ratios` | `fmp` | `obb.equity.fundamental.ratios(symbol="AAPL", provider="fmp")` | Get an extensive set of financial and accounting ratios for a given company over time.; method=GET; model=FinancialRatios; required=symbol; paging/size defau… |
| `equity.fundamental.ratios` | `intrinio` | `obb.equity.fundamental.ratios(symbol="AAPL", provider="intrinio")` | Get an extensive set of financial and accounting ratios for a given company over time.; method=GET; model=FinancialRatios; required=symbol; paging/size defau… |
| `equity.fundamental.reported_financials` | `intrinio` | `obb.equity.fundamental.reported_financials(symbol="AAPL", provider="intrinio")` | Get financial statements as reported by the company.; method=GET; model=ReportedFinancials; required=symbol; paging/size de… |
| `equity.fundamental.revenue_per_geography` | `fmp` | `obb.equity.fundamental.revenue_per_geography(symbol="AAPL", provider="fmp")` | Get the geographic breakdown of revenue for a given company over time.; method=GET; model=RevenueGeographic; required=symbol; credential fiel… |
| `equity.fundamental.revenue_per_segment` | `fmp` | `obb.equity.fundamental.revenue_per_segment(symbol="AAPL", provider="fmp")` | Get the revenue breakdown by business segment for a given company over time.; method=GET; model=RevenueBusinessLine; required=symbol; credential fi… |
| `equity.fundamental.search_attributes` | `intrinio` | `obb.equity.fundamental.search_attributes(query="search term", provider="intrinio")` | Search Intrinio data tags to search in latest or historical attributes.; method=GET; model=SearchAttributes; required=query; paging/size defau… |
| `equity.fundamental.trailing_dividend_yield` | `tiingo` | `obb.equity.fundamental.trailing_dividend_yield(symbol="AAPL", provider="tiingo")` | Get the 1 year trailing dividend yield for a given company over time.; method=GET; model=TrailingDividendYield; required=symbol; paging/size… |
| `equity.fundamental.transcript` | `fmp` | `obb.equity.fundamental.transcript(symbol="AAPL", provider="fmp")` | Get earnings call transcripts for a given company.; method=GET; model=EarningsCallTranscript; required=symbol; paging/siz… |
| `equity.historical_market_cap` | `fmp` | `obb.equity.historical_market_cap(symbol="AAPL", provider="fmp")` | Get the historical market cap of a ticker symbol.; method=GET; model=HistoricalMarketCap; required=symbol; credential fi… |
| `equity.historical_market_cap` | `intrinio` | `obb.equity.historical_market_cap(symbol="AAPL", provider="intrinio")` | Get the historical market cap of a ticker symbol.; method=GET; model=HistoricalMarketCap; required=symbol; credential fi… |
| `equity.market_snapshots` | `fmp` | `obb.equity.market_snapshots(provider="fmp")` | Get an updated equity market snapshot. This includes price data for thousands of stocks.; method=GET; model=MarketSnapshots; credential fields=fmp_api_key; pro… |
| `equity.market_snapshots` | `intrinio` | `obb.equity.market_snapshots(provider="intrinio")` | Get an updated equity market snapshot. This includes price data for thousands of stocks.; method=GET; model=MarketSnapshots; credential fields=intrinio_api_key… |
| `equity.ownership.form_13f` | `sec` | `obb.equity.ownership.form_13f(symbol="AAPL", provider="sec")` | Get the form 13F. The Securities and Exchange Commission's (SEC) Form 13F is a quarterly …; method=GET; model=Form13FHR; required=symbol; paging/size defaults=li… |
| `equity.ownership.government_trades` | `fmp` | `obb.equity.ownership.government_trades(provider="fmp")` | Obtain government transaction data, including data from the Senate and the House of Repre…; method=GET; model=GovernmentTrades; paging/size defaults=limit:None; … |
| `equity.ownership.insider_trading` | `fmp` | `obb.equity.ownership.insider_trading(symbol="AAPL", provider="fmp")` | Get data about trading by a company's management team and board of directors.; method=GET; model=InsiderTrading; required=symbol; paging/size defaul… |
| `equity.ownership.insider_trading` | `intrinio` | `obb.equity.ownership.insider_trading(symbol="AAPL", provider="intrinio")` | Get data about trading by a company's management team and board of directors.; method=GET; model=InsiderTrading; required=symbol; paging/size defaul… |
| `equity.ownership.insider_trading` | `sec` | `obb.equity.ownership.insider_trading(symbol="AAPL", provider="sec")` | Get data about trading by a company's management team and board of directors.; method=GET; model=InsiderTrading; required=symbol; paging/size defaul… |
| `equity.ownership.insider_trading` | `tmx` | `obb.equity.ownership.insider_trading(symbol="AAPL", provider="tmx")` | Get data about trading by a company's management team and board of directors.; method=GET; model=InsiderTrading; required=symbol; paging/size defaul… |
| `equity.ownership.institutional` | `fmp` | `obb.equity.ownership.institutional(symbol="AAPL", provider="fmp")` | Net statistics on institutional ownership for a given company, reported on 13-F filings.; method=GET; model=InstitutionalOwnership; required=symbol; credential… |
| `equity.ownership.major_holders` | `fmp` | `obb.equity.ownership.major_holders(symbol="AAPL", provider="fmp")` | Get data about major holders for a given company over time.; method=GET; model=EquityOwnership; required=symbol; credential fields… |
| `equity.ownership.share_statistics` | `fmp` | `obb.equity.ownership.share_statistics(symbol="AAPL", provider="fmp")` | Get data about share float for a given company.; method=GET; model=ShareStatistics; required=symbol; credential fields… |
| `equity.ownership.share_statistics` | `intrinio` | `obb.equity.ownership.share_statistics(symbol="AAPL", provider="intrinio")` | Get data about share float for a given company.; method=GET; model=ShareStatistics; required=symbol; credential fields… |
| `equity.ownership.share_statistics` | `yfinance` | `obb.equity.ownership.share_statistics(symbol="AAPL", provider="yfinance")` | Get data about share float for a given company.; method=GET; model=ShareStatistics; required=symbol; credential fields… |
| `equity.price.historical` | `alpha_vantage` | `obb.equity.price.historical(symbol="AAPL", provider="alpha_vantage")` | Get historical price data for a given stock. This includes open, high, low, close, and vo…; method=GET; model=EquityHistorical; required=symbol; credential field… |
| `equity.price.historical` | `cboe` | `obb.equity.price.historical(symbol="AAPL", provider="cboe")` | Get historical price data for a given stock. This includes open, high, low, close, and vo…; method=GET; model=EquityHistorical; required=symbol; credential field… |
| `equity.price.historical` | `fmp` | `obb.equity.price.historical(symbol="AAPL", provider="fmp")` | Get historical price data for a given stock. This includes open, high, low, close, and vo…; method=GET; model=EquityHistorical; required=symbol; credential field… |
| `equity.price.historical` | `intrinio` | `obb.equity.price.historical(symbol="AAPL", provider="intrinio")` | Get historical price data for a given stock. This includes open, high, low, close, and vo…; method=GET; model=EquityHistorical; required=symbol; credential field… |
| `equity.price.historical` | `tiingo` | `obb.equity.price.historical(symbol="AAPL", provider="tiingo")` | Get historical price data for a given stock. This includes open, high, low, close, and vo…; method=GET; model=EquityHistorical; required=symbol; credential field… |
| `equity.price.historical` | `tmx` | `obb.equity.price.historical(symbol="AAPL", provider="tmx")` | Get historical price data for a given stock. This includes open, high, low, close, and vo…; method=GET; model=EquityHistorical; required=symbol; credential field… |
| `equity.price.historical` | `tradier` | `obb.equity.price.historical(symbol="AAPL", provider="tradier")` | Get historical price data for a given stock. This includes open, high, low, close, and vo…; method=GET; model=EquityHistorical; required=symbol; credential field… |
| `equity.price.historical` | `yfinance` | `obb.equity.price.historical(symbol="AAPL", provider="yfinance")` | Get historical price data for a given stock. This includes open, high, low, close, and vo…; method=GET; model=EquityHistorical; required=symbol; credential field… |
| `equity.price.performance` | `finviz` | `obb.equity.price.performance(symbol="AAPL", provider="finviz")` | Get price performance data for a given stock. This includes price changes for different t…; method=GET; model=PricePerformance; required=symbol; credential field… |
| `equity.price.performance` | `fmp` | `obb.equity.price.performance(symbol="AAPL", provider="fmp")` | Get price performance data for a given stock. This includes price changes for different t…; method=GET; model=PricePerformance; required=symbol; credential field… |
| `equity.price.quote` | `cboe` | `obb.equity.price.quote(symbol="AAPL", provider="cboe")` | Get the latest quote for a given stock. Quote includes price, volume, and other data.; method=GET; model=EquityQuote; required=symbol; credential fields=non… |
| `equity.price.quote` | `fmp` | `obb.equity.price.quote(symbol="AAPL", provider="fmp")` | Get the latest quote for a given stock. Quote includes price, volume, and other data.; method=GET; model=EquityQuote; required=symbol; credential fields=fmp… |
| `equity.price.quote` | `intrinio` | `obb.equity.price.quote(symbol="AAPL", provider="intrinio")` | Get the latest quote for a given stock. Quote includes price, volume, and other data.; method=GET; model=EquityQuote; required=symbol; credential fields=int… |
| `equity.price.quote` | `tmx` | `obb.equity.price.quote(symbol="AAPL", provider="tmx")` | Get the latest quote for a given stock. Quote includes price, volume, and other data.; method=GET; model=EquityQuote; required=symbol; credential fields=non… |
| `equity.price.quote` | `tradier` | `obb.equity.price.quote(symbol="AAPL", provider="tradier")` | Get the latest quote for a given stock. Quote includes price, volume, and other data.; method=GET; model=EquityQuote; required=symbol; credential fields=tra… |
| `equity.price.quote` | `yfinance` | `obb.equity.price.quote(symbol="AAPL", provider="yfinance")` | Get the latest quote for a given stock. Quote includes price, volume, and other data.; method=GET; model=EquityQuote; required=symbol; credential fields=non… |
| `equity.profile` | `finviz` | `obb.equity.profile(symbol="AAPL", provider="finviz")` | Get general information about a company. This includes company name, industry, sector and…; method=GET; model=EquityInfo; required=symbol; credential fields=none… |
| `equity.profile` | `fmp` | `obb.equity.profile(symbol="AAPL", provider="fmp")` | Get general information about a company. This includes company name, industry, sector and…; method=GET; model=EquityInfo; required=symbol; credential fields=fmp_… |
| `equity.profile` | `intrinio` | `obb.equity.profile(symbol="AAPL", provider="intrinio")` | Get general information about a company. This includes company name, industry, sector and…; method=GET; model=EquityInfo; required=symbol; credential fields=intr… |
| `equity.profile` | `tmx` | `obb.equity.profile(symbol="AAPL", provider="tmx")` | Get general information about a company. This includes company name, industry, sector and…; method=GET; model=EquityInfo; required=symbol; credential fields=none… |
| `equity.profile` | `yfinance` | `obb.equity.profile(symbol="AAPL", provider="yfinance")` | Get general information about a company. This includes company name, industry, sector and…; method=GET; model=EquityInfo; required=symbol; credential fields=none… |
| `equity.screener` | `finviz` | `obb.equity.screener(provider="finviz")` | Screen for companies meeting various criteria. These criteria include market cap, price, …; method=GET; model=EquityScreener; credential fields=none; provider ra… |
| `equity.screener` | `fmp` | `obb.equity.screener(provider="fmp")` | Screen for companies meeting various criteria. These criteria include market cap, price, …; method=GET; model=EquityScreener; credential fields=fmp_api_key; prov… |
| `equity.screener` | `nasdaq` | `obb.equity.screener(provider="nasdaq")` | Screen for companies meeting various criteria. These criteria include market cap, price, …; method=GET; model=EquityScreener; credential fields=nasdaq_api_key; p… |
| `equity.screener` | `yfinance` | `obb.equity.screener(provider="yfinance")` | Screen for companies meeting various criteria. These criteria include market cap, price, …; method=GET; model=EquityScreener; credential fields=none; provider ra… |
| `equity.search` | `cboe` | `obb.equity.search(provider="cboe")` | Search for stock symbol, CIK, LEI, or company name.; method=GET; model=EquitySearch; credential fields=none; provider rate… |
| `equity.search` | `intrinio` | `obb.equity.search(provider="intrinio")` | Search for stock symbol, CIK, LEI, or company name.; method=GET; model=EquitySearch; credential fields=intrinio_api_key; p… |
| `equity.search` | `nasdaq` | `obb.equity.search(provider="nasdaq")` | Search for stock symbol, CIK, LEI, or company name.; method=GET; model=EquitySearch; credential fields=nasdaq_api_key; pro… |
| `equity.search` | `sec` | `obb.equity.search(provider="sec")` | Search for stock symbol, CIK, LEI, or company name.; method=GET; model=EquitySearch; credential fields=none; provider rate… |
| `equity.search` | `tmx` | `obb.equity.search(provider="tmx")` | Search for stock symbol, CIK, LEI, or company name.; method=GET; model=EquitySearch; credential fields=none; provider rate… |
| `equity.search` | `tradier` | `obb.equity.search(provider="tradier")` | Search for stock symbol, CIK, LEI, or company name.; method=GET; model=EquitySearch; credential fields=tradier_api_key,tra… |
| `equity.shorts.fails_to_deliver` | `sec` | `obb.equity.shorts.fails_to_deliver(symbol="AAPL", provider="sec")` | Get reported Fail-to-deliver (FTD) data.; method=GET; model=EquityFTD; required=symbol; credential fields=none;… |
| `equity.shorts.short_interest` | `finra` | `obb.equity.shorts.short_interest(symbol="AAPL", provider="finra")` | Get reported short volume and days to cover data.; method=GET; model=EquityShortInterest; required=symbol; credential fi… |
| `equity.shorts.short_volume` | `stockgrid` | `obb.equity.shorts.short_volume(symbol="AAPL", provider="stockgrid")` | Get reported Fail-to-deliver (FTD) data.; method=GET; model=ShortVolume; required=symbol; credential fields=non… |

### etf (31)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `etf.countries` | `fmp` | `obb.etf.countries(symbol="AAPL", provider="fmp")` | ETF Country weighting.; method=GET; model=EtfCountries; required=symbol; credential fields=fm… |
| `etf.countries` | `tmx` | `obb.etf.countries(symbol="AAPL", provider="tmx")` | ETF Country weighting.; method=GET; model=EtfCountries; required=symbol; credential fields=no… |
| `etf.discovery.active` | `wsj` | `obb.etf.discovery.active(provider="wsj")` | Get the most active ETFs.; method=GET; model=ETFActive; paging/size defaults=limit:10; credentia… |
| `etf.discovery.gainers` | `wsj` | `obb.etf.discovery.gainers(provider="wsj")` | Get the top ETF gainers.; method=GET; model=ETFGainers; paging/size defaults=limit:10; credenti… |
| `etf.discovery.losers` | `wsj` | `obb.etf.discovery.losers(provider="wsj")` | Get the top ETF losers.; method=GET; model=ETFLosers; paging/size defaults=limit:10; credentia… |
| `etf.equity_exposure` | `fmp` | `obb.etf.equity_exposure(symbol="AAPL", provider="fmp")` | Get the exposure to ETFs for a specific stock.; method=GET; model=EtfEquityExposure; required=symbol; credential fiel… |
| `etf.historical` | `alpha_vantage` | `obb.etf.historical(symbol="AAPL", provider="alpha_vantage")` | ETF Historical Market Price.; method=GET; model=EtfHistorical; required=symbol; credential fields=a… |
| `etf.historical` | `cboe` | `obb.etf.historical(symbol="AAPL", provider="cboe")` | ETF Historical Market Price.; method=GET; model=EtfHistorical; required=symbol; credential fields=n… |
| `etf.historical` | `fmp` | `obb.etf.historical(symbol="AAPL", provider="fmp")` | ETF Historical Market Price.; method=GET; model=EtfHistorical; required=symbol; credential fields=f… |
| `etf.historical` | `intrinio` | `obb.etf.historical(symbol="AAPL", provider="intrinio")` | ETF Historical Market Price.; method=GET; model=EtfHistorical; required=symbol; credential fields=i… |
| `etf.historical` | `tiingo` | `obb.etf.historical(symbol="AAPL", provider="tiingo")` | ETF Historical Market Price.; method=GET; model=EtfHistorical; required=symbol; credential fields=t… |
| `etf.historical` | `tmx` | `obb.etf.historical(symbol="AAPL", provider="tmx")` | ETF Historical Market Price.; method=GET; model=EtfHistorical; required=symbol; credential fields=n… |
| `etf.historical` | `tradier` | `obb.etf.historical(symbol="AAPL", provider="tradier")` | ETF Historical Market Price.; method=GET; model=EtfHistorical; required=symbol; credential fields=t… |
| `etf.historical` | `yfinance` | `obb.etf.historical(symbol="AAPL", provider="yfinance")` | ETF Historical Market Price.; method=GET; model=EtfHistorical; required=symbol; credential fields=n… |
| `etf.holdings` | `fmp` | `obb.etf.holdings(symbol="AAPL", provider="fmp")` | Get the holdings for an individual ETF.; method=GET; model=EtfHoldings; required=symbol; credential fields=fmp… |
| `etf.holdings` | `intrinio` | `obb.etf.holdings(symbol="AAPL", provider="intrinio")` | Get the holdings for an individual ETF.; method=GET; model=EtfHoldings; required=symbol; credential fields=int… |
| `etf.holdings` | `tmx` | `obb.etf.holdings(symbol="AAPL", provider="tmx")` | Get the holdings for an individual ETF.; method=GET; model=EtfHoldings; required=symbol; credential fields=non… |
| `etf.info` | `fmp` | `obb.etf.info(symbol="AAPL", provider="fmp")` | ETF Information Overview.; method=GET; model=EtfInfo; required=symbol; credential fields=fmp_api… |
| `etf.info` | `intrinio` | `obb.etf.info(symbol="AAPL", provider="intrinio")` | ETF Information Overview.; method=GET; model=EtfInfo; required=symbol; credential fields=intrini… |
| `etf.info` | `tmx` | `obb.etf.info(symbol="AAPL", provider="tmx")` | ETF Information Overview.; method=GET; model=EtfInfo; required=symbol; credential fields=none; p… |
| `etf.info` | `yfinance` | `obb.etf.info(symbol="AAPL", provider="yfinance")` | ETF Information Overview.; method=GET; model=EtfInfo; required=symbol; credential fields=none; p… |
| `etf.nport_disclosure` | `fmp` | `obb.etf.nport_disclosure(symbol="AAPL", provider="fmp")` | Get SEC NPORT-P disclosure filings for a given ETF or mutual fund (US only).; method=GET; model=NportDisclosure; required=symbol; paging/size defau… |
| `etf.nport_disclosure` | `sec` | `obb.etf.nport_disclosure(symbol="AAPL", provider="sec")` | Get SEC NPORT-P disclosure filings for a given ETF or mutual fund (US only).; method=GET; model=NportDisclosure; required=symbol; paging/size defau… |
| `etf.price_performance` | `finviz` | `obb.etf.price_performance(symbol="AAPL", provider="finviz")` | Price performance as a return, over different periods.; method=GET; model=EtfPricePerformance; required=symbol; credential fi… |
| `etf.price_performance` | `fmp` | `obb.etf.price_performance(symbol="AAPL", provider="fmp")` | Price performance as a return, over different periods.; method=GET; model=EtfPricePerformance; required=symbol; credential fi… |
| `etf.price_performance` | `intrinio` | `obb.etf.price_performance(symbol="AAPL", provider="intrinio")` | Price performance as a return, over different periods.; method=GET; model=EtfPricePerformance; required=symbol; credential fi… |
| `etf.search` | `fmp` | `obb.etf.search(provider="fmp")` | Search for ETFs. An empty query returns the full list of ETFs from the provider.; method=GET; model=EtfSearch; credential fields=fmp_api_key; provider … |
| `etf.search` | `intrinio` | `obb.etf.search(provider="intrinio")` | Search for ETFs. An empty query returns the full list of ETFs from the provider.; method=GET; model=EtfSearch; credential fields=intrinio_api_key; prov… |
| `etf.search` | `tmx` | `obb.etf.search(provider="tmx")` | Search for ETFs. An empty query returns the full list of ETFs from the provider.; method=GET; model=EtfSearch; credential fields=none; provider rate/hi… |
| `etf.sectors` | `fmp` | `obb.etf.sectors(symbol="AAPL", provider="fmp")` | ETF Sector weighting.; method=GET; model=EtfSectors; required=symbol; credential fields=fmp_… |
| `etf.sectors` | `tmx` | `obb.etf.sectors(symbol="AAPL", provider="tmx")` | ETF Sector weighting.; method=GET; model=EtfSectors; required=symbol; credential fields=none… |

### famafrench (7)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `famafrench.breakpoints` | `famafrench` | `obb.famafrench.breakpoints(provider="famafrench")` | Fama-French breakpoints. Metadata for the selected dataset are returned in the 'extra['re…; method=GET; model=FamaFrenchBreakpoints; credential fields=none; prov… |
| `famafrench.country_portfolio_returns` | `famafrench` | `obb.famafrench.country_portfolio_returns(provider="famafrench")` | Country portfolio returns. Metadata for the selected dataset are returned in the 'extra['…; method=GET; model=FamaFrenchCountryPortfolioReturns; credential field… |
| `famafrench.factor_choices` | `` | `requests.get("http://127.0.0.1:6900/api/v1/famafrench/factor_choices", params={}, timeout=30).json()` | Endpoint (optionsEndpoint) for providing dynamic menu choices to OpenBB Workspace widgets…; method=GET |
| `famafrench.factors` | `famafrench` | `obb.famafrench.factors(provider="famafrench")` | Fama-French factors. Metadata for the selected dataset are returned in the 'extra['result…; method=GET; model=FamaFrenchFactors; credential fields=none; provider… |
| `famafrench.international_index_returns` | `famafrench` | `obb.famafrench.international_index_returns(provider="famafrench")` | International index returns. Metadata for the selected dataset are returned in the 'extra…; method=GET; model=FamaFrenchInternationalIndexReturns; credential fie… |
| `famafrench.regional_portfolio_returns` | `famafrench` | `obb.famafrench.regional_portfolio_returns(provider="famafrench")` | Regional portfolio returns. Metadata for the selected dataset are returned in the 'extra[…; method=GET; model=FamaFrenchRegionalPortfolioReturns; credential fiel… |
| `famafrench.us_portfolio_returns` | `famafrench` | `obb.famafrench.us_portfolio_returns(provider="famafrench")` | US Portfolio returns. Metadata for the selected dataset are returned in the 'extra['resul…; method=GET; model=FamaFrenchUSPortfolioReturns; credential fields=non… |

### federal_reserve (3)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `federal_reserve.apps.json` | `` | `requests.get("http://127.0.0.1:6900/api/v1/federal_reserve/apps.json", params={}, timeout=30).json()` | Get the apps.json for the Federal Reserve provider.; method=GET |
| `federal_reserve.fomc_documents_choices` | `` | `requests.get("http://127.0.0.1:6900/api/v1/federal_reserve/fomc_documents_choices", params={}, timeout=30).json()` | Get the available choices for FOMC document types. Returns ------- list A list of availab…; method=GET; paging/size defaults=year:None |
| `federal_reserve.fomc_documents_download` | `` | `requests.post("http://127.0.0.1:6900/api/v1/federal_reserve/fomc_documents_download", json={"url": ["URL"]}, timeout=30).json()` | Download FOMC documents from the Federal Reserve's website. PDFs are base64 encoded under…; method=POST; required=params; read/retrieval or analytic POST; not a … |

### fixedincome (34)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `fixedincome.bond_indices` | `fred` | `obb.fixedincome.bond_indices(provider="fred")` | Bond Indices.; method=GET; model=BondIndices; credential fields=fred_api_key; provid… |
| `fixedincome.corporate.bond_prices` | `tmx` | `obb.fixedincome.corporate.bond_prices(provider="tmx")` | Corporate Bond Prices.; method=GET; model=BondPrices; credential fields=none; provider rate/h… |
| `fixedincome.corporate.commercial_paper` | `fred` | `obb.fixedincome.corporate.commercial_paper(provider="fred")` | Commercial Paper. Commercial paper (CP) consists of short-term, promissory notes issued p…; method=GET; model=CommercialPaper; credential fields=fred_api_key; pr… |
| `fixedincome.corporate.hqm` | `fred` | `obb.fixedincome.corporate.hqm(provider="fred")` | High Quality Market Corporate Bond. The HQM yield curve represents the high quality corpo…; method=GET; model=HighQualityMarketCorporateBond; credential fields=f… |
| `fixedincome.corporate.spot_rates` | `fred` | `obb.fixedincome.corporate.spot_rates(provider="fred")` | Spot Rates. The spot rates for any maturity is the yield on a bond that provides a single…; method=GET; model=SpotRate; credential fields=fred_api_key; provider … |
| `fixedincome.government.svensson_yield_curve` | `federal_reserve` | `obb.fixedincome.government.svensson_yield_curve(provider="federal_reserve")` | Svensson Nominal Yield Curve Data. Source: https://www.federalreserve.gov/data/nominal-yi…; method=GET; model=SvenssonYieldCurve; credential fields=none; provide… |
| `fixedincome.government.tips_yields` | `fred` | `obb.fixedincome.government.tips_yields(provider="fred")` | Get current Treasury inflation-protected securities yields.; method=GET; model=TipsYields; credential fields=fred_api_key; provide… |
| `fixedincome.government.treasury_auctions` | `government_us` | `obb.fixedincome.government.treasury_auctions(provider="government_us")` | Government Treasury Auctions.; method=GET; model=TreasuryAuctions; paging/size defaults=page_size:No… |
| `fixedincome.government.treasury_prices` | `government_us` | `obb.fixedincome.government.treasury_prices(provider="government_us")` | Government Treasury Prices by date.; method=GET; model=TreasuryPrices; credential fields=none; provider ra… |
| `fixedincome.government.treasury_prices` | `tmx` | `obb.fixedincome.government.treasury_prices(provider="tmx")` | Government Treasury Prices by date.; method=GET; model=TreasuryPrices; credential fields=none; provider ra… |
| `fixedincome.government.treasury_rates` | `federal_reserve` | `obb.fixedincome.government.treasury_rates(provider="federal_reserve")` | Government Treasury Rates.; method=GET; model=TreasuryRates; credential fields=none; provider rat… |
| `fixedincome.government.treasury_rates` | `fmp` | `obb.fixedincome.government.treasury_rates(provider="fmp")` | Government Treasury Rates.; method=GET; model=TreasuryRates; credential fields=fmp_api_key; provi… |
| `fixedincome.government.yield_curve` | `ecb` | `obb.fixedincome.government.yield_curve(provider="ecb")` | Get yield curve data by country and date.; method=GET; model=YieldCurve; credential fields=none; provider rate/h… |
| `fixedincome.government.yield_curve` | `econdb` | `obb.fixedincome.government.yield_curve(provider="econdb")` | Get yield curve data by country and date.; method=GET; model=YieldCurve; credential fields=econdb_api_key; provi… |
| `fixedincome.government.yield_curve` | `federal_reserve` | `obb.fixedincome.government.yield_curve(provider="federal_reserve")` | Get yield curve data by country and date.; method=GET; model=YieldCurve; credential fields=none; provider rate/h… |
| `fixedincome.government.yield_curve` | `fmp` | `obb.fixedincome.government.yield_curve(provider="fmp")` | Get yield curve data by country and date.; method=GET; model=YieldCurve; credential fields=fmp_api_key; provider… |
| `fixedincome.government.yield_curve` | `fred` | `obb.fixedincome.government.yield_curve(provider="fred")` | Get yield curve data by country and date.; method=GET; model=YieldCurve; credential fields=fred_api_key; provide… |
| `fixedincome.mortgage_indices` | `fred` | `obb.fixedincome.mortgage_indices(provider="fred")` | Mortgage Indices.; method=GET; model=MortgageIndices; credential fields=fred_api_key; pr… |
| `fixedincome.rate.ameribor` | `fred` | `obb.fixedincome.rate.ameribor(provider="fred")` | AMERIBOR. AMERIBOR (short for the American interbank offered rate) is a benchmark interes…; method=GET; model=Ameribor; credential fields=fred_api_key; provider … |
| `fixedincome.rate.dpcredit` | `fred` | `obb.fixedincome.rate.dpcredit(provider="fred")` | Discount Window Primary Credit Rate. A bank rate is the interest rate a nation's central …; method=GET; model=DiscountWindowPrimaryCreditRate; credential fields=… |
| `fixedincome.rate.ecb` | `fred` | `obb.fixedincome.rate.ecb(provider="fred")` | European Central Bank Interest Rates. The Governing Council of the ECB sets the key inter…; method=GET; model=EuropeanCentralBankInterestRates; credential fields… |
| `fixedincome.rate.effr` | `federal_reserve` | `obb.fixedincome.rate.effr(provider="federal_reserve")` | Fed Funds Rate. Get Effective Federal Funds Rate data. A bank rate is the interest rate a…; method=GET; model=FederalFundsRate; credential fields=none; provider … |
| `fixedincome.rate.effr` | `fred` | `obb.fixedincome.rate.effr(provider="fred")` | Fed Funds Rate. Get Effective Federal Funds Rate data. A bank rate is the interest rate a…; method=GET; model=FederalFundsRate; credential fields=fred_api_key; p… |
| `fixedincome.rate.effr_forecast` | `fred` | `obb.fixedincome.rate.effr_forecast(provider="fred")` | Fed Funds Rate Projections. The projections for the federal funds rate are the value of t…; method=GET; model=PROJECTIONS; credential fields=fred_api_key; provid… |
| `fixedincome.rate.estr` | `fred` | `obb.fixedincome.rate.estr(provider="fred")` | Euro Short-Term Rate. The euro short-term rate (€STR) reflects the wholesale euro unsecur…; method=GET; model=EuroShortTermRate; credential fields=fred_api_key; … |
| `fixedincome.rate.iorb` | `fred` | `obb.fixedincome.rate.iorb(provider="fred")` | Interest on Reserve Balances. Get Interest Rate on Reserve Balances data A bank rate is t…; method=GET; model=IORB; credential fields=fred_api_key; provider rate… |
| `fixedincome.rate.overnight_bank_funding` | `federal_reserve` | `obb.fixedincome.rate.overnight_bank_funding(provider="federal_reserve")` | Overnight Bank Funding. For the United States, the overnight bank funding rate (OBFR) is …; method=GET; model=OvernightBankFundingRate; credential fields=none; p… |
| `fixedincome.rate.overnight_bank_funding` | `fred` | `obb.fixedincome.rate.overnight_bank_funding(provider="fred")` | Overnight Bank Funding. For the United States, the overnight bank funding rate (OBFR) is …; method=GET; model=OvernightBankFundingRate; credential fields=fred_ap… |
| `fixedincome.rate.sofr` | `federal_reserve` | `obb.fixedincome.rate.sofr(provider="federal_reserve")` | Secured Overnight Financing Rate. The Secured Overnight Financing Rate (SOFR) is a broad …; method=GET; model=SOFR; credential fields=none; provider rate/history… |
| `fixedincome.rate.sofr` | `fred` | `obb.fixedincome.rate.sofr(provider="fred")` | Secured Overnight Financing Rate. The Secured Overnight Financing Rate (SOFR) is a broad …; method=GET; model=SOFR; credential fields=fred_api_key; provider rate… |
| `fixedincome.rate.sonia` | `fred` | `obb.fixedincome.rate.sonia(provider="fred")` | Sterling Overnight Index Average. SONIA (Sterling Overnight Index Average) is an importan…; method=GET; model=SONIA; credential fields=fred_api_key; provider rat… |
| `fixedincome.spreads.tcm` | `fred` | `obb.fixedincome.spreads.tcm(provider="fred")` | Treasury Constant Maturity. Get data for 10-Year Treasury Constant Maturity Minus Selecte…; method=GET; model=TreasuryConstantMaturity; credential fields=fred_ap… |
| `fixedincome.spreads.tcm_effr` | `fred` | `obb.fixedincome.spreads.tcm_effr(provider="fred")` | Select Treasury Constant Maturity. Get data for Selected Treasury Constant Maturity Minus…; method=GET; model=SelectedTreasuryConstantMaturity; credential fields… |
| `fixedincome.spreads.treasury_effr` | `fred` | `obb.fixedincome.spreads.treasury_effr(provider="fred")` | Select Treasury Bill. Get Selected Treasury Bill Minus Federal Funds Rate. Constant matur…; method=GET; model=SelectedTreasuryBill; credential fields=fred_api_ke… |

### imf_utils (10)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `imf_utils.apps.json` | `` | `requests.get("http://127.0.0.1:6900/api/v1/imf_utils/apps.json", params={}, timeout=30).json()` | Get the IMF apps.json file. This endpoint serves the apps.json file containing OpenBB Wor…; method=GET |
| `imf_utils.get_dataflow_dimensions` | `` | `obb.imf_utils.get_dataflow_dimensions(dataflow_id="VALUE")` | Dataflow parameters and possible values. Returns an OBBject containing either a JSON dict…; method=GET; required=dataflow_id |
| `imf_utils.indicator_choices` | `` | `requests.get("http://127.0.0.1:6900/api/v1/imf_utils/indicator_choices", params={}, timeout=30).json()` | Get progressive indicator choices for IMF data retrieval. This endpoint works progressive…; method=GET |
| `imf_utils.list_dataflow_choices` | `` | `obb.imf_utils.list_dataflow_choices()` | Get dataflow choices for IMF data retrieval.; method=GET |
| `imf_utils.list_dataflows` | `` | `obb.imf_utils.list_dataflows()` | List all available IMF dataflows. Returns an OBBject containing either a JSON dictionary …; method=GET |
| `imf_utils.list_port_id_choices` | `` | `obb.imf_utils.list_port_id_choices()` | Get port ID choices for IMF Port Watch.; method=GET |
| `imf_utils.list_table_choices` | `` | `obb.imf_utils.list_table_choices()` | Get presentation table choices for IMF data retrieval.; method=GET |
| `imf_utils.list_tables` | `` | `obb.imf_utils.list_tables()` | Get the list of presentation tables available from the IMF.; method=GET |
| `imf_utils.presentation_table` | `` | `obb.imf_utils.presentation_table()` | Get a formatted presentation table from the IMF database. Returns as HTML or JSON list.; method=GET; paging/size defaults=limit:1 |
| `imf_utils.presentation_table_choices` | `` | `obb.imf_utils.presentation_table_choices()` | Get presentation table choices for IMF data retrieval. This endpoint provides dynamic cho…; method=GET |

### index (16)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `index.available` | `cboe` | `obb.index.available(provider="cboe")` | All indices available from a given provider.; method=GET; model=AvailableIndices; credential fields=none; provider … |
| `index.available` | `fmp` | `obb.index.available(provider="fmp")` | All indices available from a given provider.; method=GET; model=AvailableIndices; credential fields=fmp_api_key; pr… |
| `index.available` | `tmx` | `obb.index.available(provider="tmx")` | All indices available from a given provider.; method=GET; model=AvailableIndices; credential fields=none; provider … |
| `index.available` | `yfinance` | `obb.index.available(provider="yfinance")` | All indices available from a given provider.; method=GET; model=AvailableIndices; credential fields=none; provider … |
| `index.constituents` | `cboe` | `obb.index.constituents(symbol="AAPL", provider="cboe")` | Get Index Constituents.; method=GET; model=IndexConstituents; required=symbol; credential fiel… |
| `index.constituents` | `fmp` | `obb.index.constituents(symbol="AAPL", provider="fmp")` | Get Index Constituents.; method=GET; model=IndexConstituents; required=symbol; credential fiel… |
| `index.constituents` | `tmx` | `obb.index.constituents(symbol="AAPL", provider="tmx")` | Get Index Constituents.; method=GET; model=IndexConstituents; required=symbol; credential fiel… |
| `index.price.historical` | `cboe` | `obb.index.price.historical(symbol="AAPL", provider="cboe")` | Historical Index Levels.; method=GET; model=IndexHistorical; required=symbol; credential fields… |
| `index.price.historical` | `fmp` | `obb.index.price.historical(symbol="AAPL", provider="fmp")` | Historical Index Levels.; method=GET; model=IndexHistorical; required=symbol; credential fields… |
| `index.price.historical` | `intrinio` | `obb.index.price.historical(symbol="AAPL", provider="intrinio")` | Historical Index Levels.; method=GET; model=IndexHistorical; required=symbol; credential fields… |
| `index.price.historical` | `yfinance` | `obb.index.price.historical(symbol="AAPL", provider="yfinance")` | Historical Index Levels.; method=GET; model=IndexHistorical; required=symbol; credential fields… |
| `index.search` | `cboe` | `obb.index.search(provider="cboe")` | Filter indices for rows containing the query.; method=GET; model=IndexSearch; credential fields=none; provider rate/… |
| `index.sectors` | `tmx` | `obb.index.sectors(symbol="AAPL", provider="tmx")` | Get Index Sectors. Sector weighting of an index.; method=GET; model=IndexSectors; required=symbol; credential fields=no… |
| `index.snapshots` | `cboe` | `obb.index.snapshots(provider="cboe")` | Index Snapshots. Current levels for all indices from a provider, grouped by 'region'.; method=GET; model=IndexSnapshots; credential fields=none; provider ra… |
| `index.snapshots` | `tmx` | `obb.index.snapshots(provider="tmx")` | Index Snapshots. Current levels for all indices from a provider, grouped by 'region'.; method=GET; model=IndexSnapshots; credential fields=none; provider ra… |
| `index.sp500_multiples` | `multpl` | `obb.index.sp500_multiples(provider="multpl")` | Get historical S&P 500 multiples and Shiller PE ratios.; method=GET; model=SP500Multiples; credential fields=none; provider ra… |

### news (11)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `news.company` | `benzinga` | `obb.news.company(provider="benzinga")` | Company News. Get news for one or more companies.; method=GET; model=CompanyNews; constraints=limit(ge=0); paging/size d… |
| `news.company` | `fmp` | `obb.news.company(provider="fmp")` | Company News. Get news for one or more companies.; method=GET; model=CompanyNews; constraints=limit(ge=0); paging/size d… |
| `news.company` | `intrinio` | `obb.news.company(provider="intrinio")` | Company News. Get news for one or more companies.; method=GET; model=CompanyNews; constraints=limit(ge=0); paging/size d… |
| `news.company` | `tiingo` | `obb.news.company(provider="tiingo")` | Company News. Get news for one or more companies.; method=GET; model=CompanyNews; constraints=limit(ge=0); paging/size d… |
| `news.company` | `tmx` | `obb.news.company(provider="tmx")` | Company News. Get news for one or more companies.; method=GET; model=CompanyNews; constraints=limit(ge=0); paging/size d… |
| `news.company` | `yfinance` | `obb.news.company(provider="yfinance")` | Company News. Get news for one or more companies.; method=GET; model=CompanyNews; constraints=limit(ge=0); paging/size d… |
| `news.world` | `benzinga` | `obb.news.world(provider="benzinga")` | World News. Global news data.; method=GET; model=WorldNews; constraints=limit(ge=0); paging/size def… |
| `news.world` | `biztoc` | `obb.news.world(provider="biztoc")` | World News. Global news data.; method=GET; model=WorldNews; constraints=limit(ge=0); paging/size def… |
| `news.world` | `fmp` | `obb.news.world(provider="fmp")` | World News. Global news data.; method=GET; model=WorldNews; constraints=limit(ge=0); paging/size def… |
| `news.world` | `intrinio` | `obb.news.world(provider="intrinio")` | World News. Global news data.; method=GET; model=WorldNews; constraints=limit(ge=0); paging/size def… |
| `news.world` | `tiingo` | `obb.news.world(provider="tiingo")` | World News. Global news data.; method=GET; model=WorldNews; constraints=limit(ge=0); paging/size def… |

### quantitative (19)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `quantitative.capm` | `` | `obb.quantitative.capm(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Get Capital Asset Pricing Model (CAPM). CAPM offers a streamlined way to assess the expec…; method=POST; required=data,target; read/retrieval or analytic POST; n… |
| `quantitative.normality` | `` | `obb.quantitative.normality(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Get Normality Statistics. - **Kurtosis**: whether the kurtosis of a sample differs from t…; method=POST; required=data,target; read/retrieval or analytic POST; n… |
| `quantitative.performance.omega_ratio` | `` | `obb.quantitative.performance.omega_ratio(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Calculate the Omega Ratio. The Omega Ratio is a sophisticated metric that goes beyond tra…; method=POST; required=data,target; read/retrieval or analytic POST; n… |
| `quantitative.performance.sharpe_ratio` | `` | `obb.quantitative.performance.sharpe_ratio(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Get Rolling Sharpe Ratio. This function calculates the Sharpe Ratio, a metric used to ass…; method=POST; required=data,target; paging/size defaults=window:252; r… |
| `quantitative.performance.sortino_ratio` | `` | `obb.quantitative.performance.sortino_ratio(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Get rolling Sortino Ratio. The Sortino Ratio enhances the evaluation of investment return…; method=POST; required=data,target; paging/size defaults=window:252; r… |
| `quantitative.rolling.kurtosis` | `` | `obb.quantitative.rolling.kurtosis(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Calculate the rolling kurtosis of a target column within a given window size. Kurtosis me…; method=POST; required=data,target; paging/size defaults=window:21; re… |
| `quantitative.rolling.mean` | `` | `obb.quantitative.rolling.mean(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Calculate the rolling average of a target column within a given window size. The rolling …; method=POST; required=data,target; paging/size defaults=window:21; re… |
| `quantitative.rolling.quantile` | `` | `obb.quantitative.rolling.quantile(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Calculate the rolling quantile of a target column within a given window size at a specifi…; method=POST; required=data,target; paging/size defaults=window:21; re… |
| `quantitative.rolling.skew` | `` | `obb.quantitative.rolling.skew(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Get Rolling Skew. Skew is a statistical measure that reveals the degree of asymmetry of a…; method=POST; required=data,target; paging/size defaults=window:21; re… |
| `quantitative.rolling.stdev` | `` | `obb.quantitative.rolling.stdev(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Calculate the rolling standard deviation of a target column within a given window size. S…; method=POST; required=data,target; paging/size defaults=window:21; re… |
| `quantitative.rolling.variance` | `` | `obb.quantitative.rolling.variance(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Calculate the rolling variance of a target column within a given window size. Variance me…; method=POST; required=data,target; paging/size defaults=window:21; re… |
| `quantitative.stats.kurtosis` | `` | `obb.quantitative.stats.kurtosis(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Calculate the rolling kurtosis of a target column. Kurtosis measures the "tailedness" of …; method=POST; required=data,target; read/retrieval or analytic POST; n… |
| `quantitative.stats.mean` | `` | `obb.quantitative.stats.mean(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Calculate the average of a target column. The rolling mean is a simple moving average tha…; method=POST; required=data,target; read/retrieval or analytic POST; n… |
| `quantitative.stats.quantile` | `` | `obb.quantitative.stats.quantile(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Calculate the quantile of a target column at a specified quantile percentage. Quantiles a…; method=POST; required=data,target; read/retrieval or analytic POST; n… |
| `quantitative.stats.skew` | `` | `obb.quantitative.stats.skew(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Get the skew of the data set. Skew is a statistical measure that reveals the degree of as…; method=POST; required=data,target; read/retrieval or analytic POST; n… |
| `quantitative.stats.stdev` | `` | `obb.quantitative.stats.stdev(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Calculate the rolling standard deviation of a target column. Standard deviation is a meas…; method=POST; required=data,target; read/retrieval or analytic POST; n… |
| `quantitative.stats.variance` | `` | `obb.quantitative.stats.variance(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Calculate the variance of a target column. Variance measures the dispersion of a set of d…; method=POST; required=data,target; read/retrieval or analytic POST; n… |
| `quantitative.summary` | `` | `obb.quantitative.summary(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Get Summary Statistics. The summary that offers a snapshot of its central tendencies, var…; method=POST; required=data,target; read/retrieval or analytic POST; n… |
| `quantitative.unitroot_test` | `` | `obb.quantitative.unitroot_test(data=[{"date":"2026-01-01","close":100.0}], target="close")` | Get Unit Root Test. This function applies two renowned tests to assess whether your data …; method=POST; required=data,target; read/retrieval or analytic POST; n… |

### regulators (8)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `regulators.sec.cik_map` | `sec` | `obb.regulators.sec.cik_map(symbol="AAPL", provider="sec")` | Map a ticker symbol to a CIK number.; method=GET; model=CikMap; required=symbol; credential fields=none; pr… |
| `regulators.sec.filing_headers` | `sec` | `obb.regulators.sec.filing_headers(provider="sec")` | Download the index headers, and cover page if available, for any SEC filing.; method=GET; model=SecFiling; credential fields=none; provider rate/hi… |
| `regulators.sec.htm_file` | `sec` | `obb.regulators.sec.htm_file(provider="sec")` | Download a raw HTML object from the SEC website.; method=GET; model=SecHtmFile; credential fields=none; provider rate/h… |
| `regulators.sec.institutions_search` | `sec` | `obb.regulators.sec.institutions_search(provider="sec")` | Search SEC-regulated institutions by name and return a list of results with CIK numbers.; method=GET; model=InstitutionsSearch; credential fields=none; provide… |
| `regulators.sec.rss_litigation` | `sec` | `obb.regulators.sec.rss_litigation(provider="sec")` | Get the RSS feed that provides links to litigation releases concerning civil lawsuits bro…; method=GET; model=RssLitigation; credential fields=none; provider rat… |
| `regulators.sec.schema_files` | `sec` | `obb.regulators.sec.schema_files(provider="sec")` | Explore SEC and FASB XBRL taxonomy schemas, labels, and presentation structures. - No par…; method=GET; model=SchemaFiles; credential fields=none; provider rate/… |
| `regulators.sec.sic_search` | `sec` | `obb.regulators.sec.sic_search(provider="sec")` | Search for Industry Titles, Reporting Office, and SIC Codes. An empty query string return…; method=GET; model=SicSearch; credential fields=none; provider rate/hi… |
| `regulators.sec.symbol_map` | `sec` | `obb.regulators.sec.symbol_map(query="search term", provider="sec")` | Map a CIK number to a ticker symbol, leading 0s can be omitted or included.; method=GET; model=SymbolMap; required=query; credential fields=none; … |

### technical (27)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `technical.ad` | `` | `obb.technical.ad(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Accumulation/Distribution Line. Similar to the On Balance Volume (OBV). Sum…; method=POST; required=data; paging/size defaults=offset:0; read/retri… |
| `technical.adosc` | `` | `obb.technical.adosc(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Accumulation/Distribution Oscillator. Also known as the Chaikin Oscillator.…; method=POST; required=data; paging/size defaults=offset:0; read/retri… |
| `technical.adx` | `` | `obb.technical.adx(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Average Directional Index (ADX). The ADX is a Welles Wilder style moving av…; method=POST; required=data; paging/size defaults=length:50; read/retr… |
| `technical.aroon` | `` | `obb.technical.aroon(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Aroon Indicator. The word aroon is Sanskrit for "dawn's early light." The A…; method=POST; required=data; paging/size defaults=length:25; read/retr… |
| `technical.atr` | `` | `obb.technical.atr(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Average True Range. Used to measure volatility, especially volatility cause…; method=POST; required=data; paging/size defaults=length:14,offset:0; … |
| `technical.bbands` | `` | `obb.technical.bbands(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Bollinger Bands. Consist of three lines. The middle band is a simple moving…; method=POST; required=data; paging/size defaults=length:50,offset:0; … |
| `technical.cci` | `` | `obb.technical.cci(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Commodity Channel Index (CCI). The CCI is designed to detect beginning and …; method=POST; required=data; paging/size defaults=length:14; read/retr… |
| `technical.cg` | `` | `obb.technical.cg(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Center of Gravity. The Center of Gravity indicator, in short, is used to an…; method=POST; required=data; paging/size defaults=length:14; read/retr… |
| `technical.clenow` | `` | `obb.technical.clenow(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Clenow Volatility Adjusted Momentum. The Clenow Volatility Adjusted Momentu…; method=POST; required=data; read/retrieval or analytic POST; not a st… |
| `technical.cones` | `` | `obb.technical.cones(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the realized volatility quantiles over rolling windows of time. The cones indic…; method=POST; required=data; read/retrieval or analytic POST; not a st… |
| `technical.demark` | `` | `obb.technical.demark(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Demark sequential indicator. This indicator offers a strategic way to spot …; method=POST; required=data; paging/size defaults=offset:0; read/retri… |
| `technical.donchian` | `` | `obb.technical.donchian(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Donchian Channels. Three lines generated by moving average calculations tha…; method=POST; required=data; paging/size defaults=offset:0; read/retri… |
| `technical.ema` | `` | `obb.technical.ema(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Exponential Moving Average (EMA). EMA is a cumulative calculation, includin…; method=POST; required=data; paging/size defaults=length:50,offset:0; … |
| `technical.fib` | `` | `obb.technical.fib(data=[{"date":"2026-01-01","close":100.0}])` | Create Fibonacci Retracement Levels. This method draws from a classic technique to pinpoi…; method=POST; required=data; read/retrieval or analytic POST; not a st… |
| `technical.fisher` | `` | `obb.technical.fisher(data=[{"date":"2026-01-01","close":100.0}])` | Perform the Fisher Transform. A technical indicator created by John F. Ehlers that conver…; method=POST; required=data; paging/size defaults=length:14; read/retr… |
| `technical.hma` | `` | `obb.technical.hma(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Hull Moving Average (HMA). Solves the age old dilemma of making a moving av…; method=POST; required=data; paging/size defaults=length:50,offset:0; … |
| `technical.ichimoku` | `` | `obb.technical.ichimoku(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Ichimoku Cloud. Also known as Ichimoku Kinko Hyo, is a versatile indicator …; method=POST; required=data; paging/size defaults=offset:26; read/retr… |
| `technical.kc` | `` | `obb.technical.kc(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Keltner Channels. Keltner Channels are volatility-based bands that are plac…; method=POST; required=data; paging/size defaults=length:20,offset:0; … |
| `technical.macd` | `` | `obb.technical.macd(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Moving Average Convergence Divergence (MACD). Difference between two Expone…; method=POST; required=data; read/retrieval or analytic POST; not a st… |
| `technical.obv` | `` | `obb.technical.obv(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the On Balance Volume (OBV). Is a cumulative total of the up and down volume. W…; method=POST; required=data; paging/size defaults=offset:0; read/retri… |
| `technical.relative_rotation` | `` | `obb.technical.relative_rotation(data=[{"date":"2026-01-01","close":100.0}], benchmark="VALUE")` | Calculate the Relative Strength Ratio and Relative Strength Momentum for a group of symbo…; method=POST; required=data,benchmark; paging/size defaults=window:21;… |
| `technical.rsi` | `` | `obb.technical.rsi(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Relative Strength Index (RSI). RSI calculates a ratio of the recent upward …; method=POST; required=data; paging/size defaults=length:14; read/retr… |
| `technical.sma` | `` | `obb.technical.sma(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Simple Moving Average (SMA). Moving Averages are used to smooth the data in…; method=POST; required=data; paging/size defaults=length:50,offset:0; … |
| `technical.stoch` | `` | `obb.technical.stoch(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Stochastic Oscillator. The Stochastic Oscillator measures where the close i…; method=POST; required=data; read/retrieval or analytic POST; not a st… |
| `technical.vwap` | `` | `obb.technical.vwap(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Volume Weighted Average Price (VWAP). Measures the average typical price by…; method=POST; required=data; paging/size defaults=offset:0; read/retri… |
| `technical.wma` | `` | `obb.technical.wma(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the Weighted Moving Average (WMA). A Weighted Moving Average puts more weight o…; method=POST; required=data; paging/size defaults=length:50,offset:0; … |
| `technical.zlma` | `` | `obb.technical.zlma(data=[{"date":"2026-01-01","close":100.0}])` | Calculate the zero lag exponential moving average (ZLEMA). Created by John Ehlers and Ric…; method=POST; required=data; paging/size defaults=length:50,offset:0; … |

### uscongress (13)

| 接口 | Provider | 一行请求 | 简述/限制 |
|---|---|---|---|
| `uscongress.amendment_info` | `congress_gov` | `obb.uscongress.amendment_info(provider="congress_gov")` | Get details for a specific amendment. Enter the amendment identifier as: {congress}/{type…; method=GET; model=CongressAmendmentInfo; credential fields=congress_g… |
| `uscongress.amendment_text` | `congress_gov` | `obb.uscongress.amendment_text(provider="congress_gov")` | Download amendment document(s) from Congress.gov. Note: This endpoint returns only the re…; method=POST; model=CongressAmendmentText; credential fields=congress_… |
| `uscongress.amendment_text_urls` | `` | `obb.uscongress.amendment_text_urls(amendment_url="119/samdt/1")` | Get document choices for a specific amendment. This function is used by the Congressional…; method=GET; required=amendment_url |
| `uscongress.amendments` | `congress_gov` | `obb.uscongress.amendments(provider="congress_gov")` | Get and filter lists of Congressional Amendments.; method=GET; model=CongressAmendments; credential fields=congress_gov_… |
| `uscongress.apps.json` | `` | `requests.get("http://127.0.0.1:6900/api/v1/uscongress/apps.json", params={}, timeout=30).json()` | Get the IMF apps.json file. This endpoint serves the apps.json file containing OpenBB Wor…; method=GET |
| `uscongress.bill_info` | `congress_gov` | `obb.uscongress.bill_info(provider="congress_gov")` | Get summary, status, and other metadata for a specific bill. Enter the URL of the bill as…; method=GET; model=CongressBillInfo; credential fields=congress_gov_ap… |
| `uscongress.bill_text` | `congress_gov` | `obb.uscongress.bill_text(provider="congress_gov")` | Download the content of bill(s) from a Congress.gov file. Note: This endpoint returns onl…; method=POST; model=CongressBillText; credential fields=congress_gov_a… |
| `uscongress.bill_text_urls` | `` | `obb.uscongress.bill_text_urls(bill_url="119/s/1")` | Get document choices for a specific bill. This function is used by the Congressional Bill…; method=GET; required=bill_url |
| `uscongress.bills` | `congress_gov` | `obb.uscongress.bills(provider="congress_gov")` | Get and filter lists of Congressional Bills.; method=GET; model=CongressBills; credential fields=congress_gov_api_k… |
| `uscongress.committee_choices` | `` | `obb.uscongress.committee_choices()` | Get committee or subcommittee choices for cascading dropdowns.; method=GET |
| `uscongress.committee_document_urls` | `` | `obb.uscongress.committee_document_urls(chamber="VALUE", committee="VALUE")` | Get document choices for a Congressional Committee. This endpoint populates the Committee…; method=GET; required=chamber,committee |
| `uscongress.committee_documents` | `congress_gov` | `obb.uscongress.committee_documents(provider="congress_gov")` | Get documents (reports, hearings, prints, meetings) produced by a single Congressional Co…; method=GET; model=CongressCommitteeDocuments; credential fields=congr… |
| `uscongress.committee_info` | `congress_gov` | `obb.uscongress.committee_info(provider="congress_gov")` | Get metadata and membership for a single U.S. Congressional Committee. Fetches the commit…; method=GET; model=CongressCommitteeInfo; credential fields=congress_g… |

## OpenBB Platform 请求/返回样例

代表性只读请求 **16** 个：成功 **14**，失败 **2**。每行均为独立 JSON。

```jsonl
{"category":"equity","request":"obb.equity.price.historical(symbol=\"AAPL\", start_date=\"2025-01-02\", end_date=\"2025-01-03\", provider=\"yfinance\")","status":"success","response":{"row_count":2,"records":[{"date":"2025-01-02","open":248.92999267578125,"high":249.10000610351562,"low":241.82000732421875,"close":243.85000610351562,"volume":55740700,"vwap":null,"split_ratio":null,"dividend":null},{"date":"2025-01-03","open":243.36000061035156,"high":244.17999267578125,"low":241.88999938964844,"close":243.36000061035156,"volume":40244100,"vwap":null,"split_ratio":null,"dividend":null}]},"error":null}
{"category":"etf","request":"obb.etf.historical(symbol=\"SPY\", start_date=\"2025-01-02\", end_date=\"2025-01-03\", provider=\"yfinance\")","status":"success","response":{"row_count":2,"records":[{"date":"2025-01-02","open":589.3900146484375,"high":591.1300048828125,"low":580.5,"close":584.6400146484375,"volume":50204000,"vwap":null,"split_ratio":null,"dividend":null},{"date":"2025-01-03","open":587.530029296875,"high":592.5999755859375,"low":586.4299926757812,"close":591.9500122070312,"volume":37888500,"vwap":null,"split_ratio":null,"dividend":null}]},"error":null}
{"category":"index","request":"obb.index.price.historical(symbol=\"^GSPC\", start_date=\"2025-01-02\", end_date=\"2025-01-03\", provider=\"yfinance\")","status":"success","response":{"row_count":2,"records":[{"date":"2025-01-02","symbol":null,"open":5903.259765625,"high":5935.08984375,"low":5829.52978515625,"close":5868.5498046875,"volume":3621680000},{"date":"2025-01-03","symbol":null,"open":5891.06982421875,"high":5949.33984375,"low":5888.66015625,"close":5942.47021484375,"volume":3667340000}]},"error":null}
{"category":"crypto","request":"obb.crypto.price.historical(symbol=\"BTC-USD\", start_date=\"2025-01-02\", end_date=\"2025-01-03\", provider=\"yfinance\")","status":"success","response":{"row_count":2,"records":[{"date":"2025-01-02","open":94416.2890625,"high":97739.8203125,"low":94201.5703125,"close":96886.875,"volume":46009564411.0,"vwap":null},{"date":"2025-01-03","open":96881.7265625,"high":98956.9140625,"low":96034.6171875,"close":98107.4296875,"volume":35611391163.0,"vwap":null}]},"error":null}
{"category":"currency","request":"obb.currency.price.historical(symbol=\"EURUSD\", start_date=\"2025-01-02\", end_date=\"2025-01-03\", provider=\"yfinance\")","status":"success","response":{"row_count":2,"records":[{"date":"2025-01-02","open":1.0351860523223877,"high":1.0375596284866333,"low":1.0231853723526,"close":1.0351860523223877,"volume":0.0,"vwap":null},{"date":"2025-01-03","open":1.0268205404281616,"high":1.0305347442626953,"low":1.0265464782714844,"close":1.0268205404281616,"volume":0.0,"vwap":null}]},"error":null}
{"category":"derivatives","request":"obb.derivatives.futures.historical(symbol=\"ES\", start_date=\"2025-01-02\", end_date=\"2025-01-03\", provider=\"yfinance\")","status":"success","response":{"row_count":2,"records":[{"date":"2025-01-02 00:00:00","open":5949.25,"high":5995.25,"low":5874.75,"close":5916.5,"volume":1826031.0},{"date":"2025-01-03 00:00:00","open":5921.0,"high":5996.75,"low":5911.25,"close":5989.5,"volume":1206570.0}]},"error":null}
{"category":"economy","request":"obb.economy.gdp.real(start_date=\"2024-01-01\", end_date=\"2024-12-31\", provider=\"oecd\")","status":"success","response":{"row_count":4,"records":[{"date":"2024-01-01","value":24323340000000,"country":"United States"},{"date":"2024-04-01","value":24538719900000,"country":"United States"}]},"error":null}
{"category":"fixedincome","request":"obb.fixedincome.government.treasury_rates(start_date=\"2025-01-02\", end_date=\"2025-01-03\", provider=\"federal_reserve\")","status":"success","response":{"row_count":2,"records":[{"date":"2025-01-02","week_4":null,"month_1":0.044500000000000005,"month_2":null,"month_3":0.0436,"month_6":0.0425,"year_1":0.0417,"year_2":0.0425,"year_3":0.0429,"year_5":0.0438},{"date":"2025-01-03","week_4":null,"month_1":0.0444,"month_2":null,"month_3":0.0434,"month_6":0.0425,"year_1":0.0418,"year_2":0.042800000000000005,"year_3":0.0432,"year_5":0.0441}]},"error":null}
{"category":"regulators","request":"obb.regulators.sec.sic_search(query=\"software\", provider=\"sec\")","status":"failure","response":null,"error":"OpenBBError: [Unexpected Error] -> KeyError -> 'SIC Code'"}
{"category":"famafrench","request":"obb.famafrench.factors(provider=\"famafrench\")","status":"success","response":{"row_count":1201,"records":[{"date":"1926-07-01","mkt_rf":2.89,"smb":-2.42,"hml":-2.75,"rmw":null,"cma":null,"rf":0.22,"mom":null,"wml":null,"lt_rev":null},{"date":"1926-08-01","mkt_rf":2.64,"smb":-1.44,"hml":4.13,"rmw":null,"cma":null,"rf":0.25,"mom":null,"wml":null,"lt_rev":null}]},"error":null}
{"category":"imf_utils","request":"obb.imf_utils.list_dataflows()","status":"success","response":{"row_count":67,"records":{"MFS_MA":{"name":"Monetary and Financial Statistics (MFS), Monetary Aggregates","urn":"urn:sdmx:org.sdmx.infomodel.datastructure.Dataflow=IMF.STA:MFS_MA(10.0.1)","agencyID":"IMF.STA","id":"MFS_MA","version":"10.0.1","description":"The Monetary and Financial Statistics (MFS), Monetary Aggregates dataset presents monetary aggregates based on standardized SRF data, while also reflecting country-specific components aligned with national definitions.","structureRef":{"agencyID":"IMF.STA","id":"DSD_MFS_MA","version":"10.0.0","package":"datastructure","class":"DataStructure"},"presentations":[{"summary":"2 keys"}]},"FSICDM":{"name":"Financial Soundness Indicators (FSI), Concentration and Distribution Measures","urn":"urn:sdmx:org.sdmx.infomodel.datastructure.Dataflow=IMF.STA:FSICDM(7.0.0)","agencyID":"IMF.STA","id":"FSICDM","version":"7.0.0","description":"The Financial Soundness Indicators (FSIs), developed by the IMF together with the international community, are aimed at supporting macroprudential analysis—the surveillance and assessment of the strengths and vulnerabilities of financial systems. FSIs are macroprudential statistics aimed at filling…","structureRef":{"agencyID":"IMF.STA","id":"DSD_FSICDM","version":"8.0.0","package":"datastructure","class":"DataStructure"}},"MFS_NSRF":{"name":"Monetary and Financial Statistics (MFS_NSRF): Non-Standard Data","urn":"urn:sdmx:org.sdmx.infomodel.datastructure.Dataflow=IMF.STA:MFS_NSRF(1.0.1)","agencyID":"IMF.STA","id":"MFS_NSRF","version":"1.0.1","description":"The Non-Standardized Monetary and Financial Statistics dataset includes aggregate statistics on transactions and positions in financial and nonfinancial assets, and liabilities for all institutional sectors within an economy. Monetary statistics cover the stocks and flow of the assets and liabiliti…","structureRef":{"agencyID":"IMF.STA","id":"DSD_MFS_NSRF","version":"1.0.1","package":"datastructure","class":"DataStructure"}}}},"error":null}
{"category":"technical","request":"obb.technical.sma(data=[{\"date\":\"2025-01-01\",\"close\":100.0},{\"date\":\"2025-01-02\",\"close\":102.0},{\"date\":\"2025-01-03\",\"close\":101.0}], length=2)","status":"success","response":{"row_count":3,"records":[{"date":"2025-01-01","close":100.0,"close_SMA_2":null},{"date":"2025-01-02","close":102.0,"close_SMA_2":101.0}]},"error":null}
{"category":"quantitative","request":"obb.quantitative.summary(data=[{\"ret\":0.01},{\"ret\":-0.02},{\"ret\":0.03},{\"ret\":0.01}], target=\"ret\")","status":"success","response":{"row_count":1,"records":[{"count":4,"mean":0.0075,"std":0.0206155281280883,"var":0.0004249999999999999,"min":-0.02,"max":0.03,"p_25":0.0025000000000000005,"p_50":0.01,"p_75":0.015}]},"error":null}
{"category":"econometrics","request":"obb.econometrics.correlation_matrix(data=[{\"x\":1,\"y\":2},{\"x\":2,\"y\":4},{\"x\":3,\"y\":5}])","status":"success","response":{"row_count":2,"records":[{"x":1.0,"y":0.9819805060619656,"comp_to":"x"},{"x":0.9819805060619656,"y":1.0,"comp_to":"y"}]},"error":null}
{"category":"news","request":"obb.news.world(limit=1, provider=\"biztoc\")","status":"failure","response":null,"error":"OpenBBError: [Error] -> Missing credential 'biztoc_api_key'. Check https://api.biztoc.com to get it. Refer to the documentation for setting provider credentials at https://docs.openbb.co/platform/settings/user_settings/api_keys."}
{"category":"cftc","request":"obb.cftc.cot_search(query=\"gold\", provider=\"cftc\")","status":"success","response":{"row_count":4,"records":[{"code":"CFTC_088691","name":"GOLD","category":"NATURAL RESOURCES","subcategory":"PRECIOUS METALS","units":"(CONTRACTS OF 100 TROY OUNCES)","symbol":null,"commodity":"GOLD"},{"code":"CFTC_088LM1","name":"GOLD -1 TROY OUNCE","category":"NATURAL RESOURCES","subcategory":"PRECIOUS METALS","units":"(1 troy ounce x $2,300)","symbol":null,"commodity":"GOLD"}]},"error":null}
```
