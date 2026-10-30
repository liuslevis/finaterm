---
name: us-supply-demand
description: 刷新或修改 dashboard「美股供需」tab（美股净股权供给 vs 增量资金、供需差 z-score、S&P500 月涨幅、IPO 情绪）。用户提到 美股供需、US supply demand、美股净供给、刷新美股供需面板时使用。
---

# 美股供需面板：设计与刷新手册

## 核心思路

IPO 单独看解释力很弱。要把全部股权供给加总，再和增量资金比较：

```
净股权供给 = IPO + 增发/大宗 + 可转债 + 内部人卖出 − 回购 − 现金分红 − 内部人买入
增量资金   = 美股 ETF 净流入 + 融资余额变化 (+ 美股共同基金净流入，数据完整时才计入)
供需差     = 增量资金 − 净股权供给
标准化     = 供需差 / 美股总市值(^W5000，bp)，再做 3/6 个月滚动 z-score
```

- 美股和 A 股最大的不同：回购和分红（S&P 500 约 $150B/月）长期大于发行，所以**净供给常年为负**。供需差的水平没什么意义，要看 **z-score 的边际变化**。
- `gap_ex_div`（扣分红口径）：分红多数会再投资回指数，扣掉更能反映「主动」资金面。
- 情绪（同步或滞后）：IPO 家数（剔除 SPAC）、新递表数、撤回数、首日涨幅中位数、首日破发率。美股没有网下询价倍数。
- 参考列（不进公式）：`lockup_ref` = 6 个月前的 IPO 募资（锁定期到期的代理指标），`insider_sell_10pct` = 纯 10% 股东卖出（和大宗交易重叠），`free_credit` = 券商客户现金余额变化（相当于 A 股的银证转账）。
- 风格：极简，只有一张图（供需差 bp 柱 + S&P500 折线）、一张表和一段 AI 结论。

## 文件

| 文件 | 说明 |
|---|---|
| `build_panel.py` | 下载 → 计算 → 输出。`--refresh` 重新下载自动数据源；`--start/--end YYYY-MM` 控制展示区间（默认当年 1 月到上一个完整月） |
| `manual.json` | **AI 手工维护**的数据：月度 ETF/共同基金、季度增发/可转债/回购/分红、FINRA 兜底表、`sources`、`caveats`、`commentary` |
| `raw/` | 自动数据缓存（不提交） |
| `panel.csv` | 从 `HISTORY_START=2025-10` 开始的全部中间列，用于核对 |
| `panel.json` | 前端读取的文件；`/api/us-supply-demand` 只读这个文件，不缓存 |

## 数据源

| 列 | 来源 | 方式 | 口径 |
|---|---|---|---|
| ipo, ipo_count, spac_count, filed, withdrawn | `api.nasdaq.com/api/ipo/calendar?date=YYYY-MM` | 自动 | priced 行 `dollarValueOfSharesOffered`。价格是区间时取中值。SPAC 用 `is_spac()` 识别（$10 + 名称/U 结尾），不能用 "Space" 正则（会误杀 SpaceX） |
| first_day_median, break_rate | Yahoo v8 chart 日线 | 自动 | 首日收盘 / 发行价 − 1。必须带 `events=split` 还原拆合股（否则会出现 +15000% 这种值） |
| insider_sell / insider_buy | openinsider screener（S / P 类型） | 自动 | 每月约 5 页 × 1000 行，按交易日期归月。纯 10% 股东另列 |
| margin, free_credit | FINRA margin statistics | 自动，被 403 时用 `manual.json.finra` 兜底 | 月末差分。单位 $M → $B |
| spx_ret, mcap | Yahoo `^GSPC`、`^W5000` | 自动 | ^W5000 点位 ≈ 美股总市值（$B） |
| etf_us_equity | First Trust「ETF Data Watch: Asset Flows Monitor」月报（FactSet） | 手工 | 每月约 8–12 日发布上月数据，PDF 本地可下载 |
| mf_domestic_equity | ICI Trends in Mutual Fund Investing | 手工 | ici.org 403；只能从 PR Newswire 或搜索摘要获取。不完整时自动不计入需求 |
| follow_on, convertible | ICR 季度 ECM review（icrinc.com） | 手工，季度值 ÷ 3 | 增发包含大宗交易 |
| buyback, dividend | S&P DJI（Howard Silverblatt）季度报告 | 手工，季度值 ÷ 3 | 最新季度缺失时沿用上季度，并在 caveats 里标注为估算 |

不可用：SEC、ICI、etf.com、ycharts、spglobal 直连（403/405），FRED 超时。web_fetch 可以访问 FINRA 和 icrinc.com。

## 刷新步骤（每月 10 日后）

1. **补 manual.json**（web_search / web_fetch）：
   - `monthly.etf_us_equity[上月]`：搜索 "ftportfolios asset flows monitor {月份} edition"，取 "U.S. equity ETFs net inflows"
   - `monthly.mf_domestic_equity`：搜索 "ICI trends in mutual fund investing {月份} domestic equity"
   - 季度结束后：ICR "Q? 20?? equity capital markets review" 提供增发+大宗、可转债；S&P DJI "S&P 500 Q? buybacks" 提供回购、分红
   - FINRA：用 web_fetch 访问 `FINRA_URL`，补 `finra` 表（本地 urllib 常被 403）
   - 每个数值都写进 `sources`；估算值写进 `caveats`
2. 运行：
   ```powershell
   cd dashboard
   $env:PYTHONIOENCODING="utf-8"
   uv run python tab/us-supply-demand/build_panel.py --refresh   # 约 5 分钟（openinsider 较慢）
   ```
3. 合理性检查：季度 IPO 合计要和 ICR 的数字对得上（2026Q2 ≈ $105B，含 SpaceX；Q3 ≈ $35B）。打印的 `demand parts` 和 `estimated` 要符合预期。
4. 更新 `manual.json.commentary`（`as_of` + 一段中文结论：最近 3 个月供需差和 z6、主要驱动、情绪、需要留意的事件），然后不带 `--refresh` 再跑一次。
5. 截图验证（先启动服务：`cd dashboard; uv run python dashboard_server.py --port 8799 --no-browser`）：
   `node dashboard/skill/dashboard-tab/scripts/screenshot_tab.cjs 8799 us-supply-demand $env:TEMP "ussdState.data" "[data-ussd-mode=gap_ex_div]"`

## 已知缺口

- 没有新开户数（券商不公开）。`free_credit` 只作为参考，不进公式。
- 分母是总市值（^W5000），不是自由流通市值。
- 解禁只有「6 个月前 IPO」代理，没有逐只锁定期和实际减持；内部人卖出覆盖了一部分。
- 回购和分红是季度均摊，最新季度要滞后约 3 个月才有官方值。
- 历史从 2025-10 开始（FINRA 网页只列 12 个月），z6 前期不稳定。延长历史需要补 `manual.json.finra` 和 ETF 月度数据。

## 前端（index.html 工作区 + `js/us-supply-demand.js` + `css/us-supply-demand.css`）

- tab `data-workspace-tab="us-supply-demand"`，工作区 `#ussdWorkspace`，复用 `.asd-chart/.asd-table*` 样式。
- JS：`ussdState`、`loadUssd()`、`renderUssd()`；`data-ussd-mode="gap|gap_ex_div"` 切换口径。
- `USSD_KEY_COLUMNS` 控制高亮列，`USSD_SIGNED_COLUMNS` 控制绿正红负着色。新增指标只需改 `build_panel.py` 的 `COLUMNS`。
- `#ussdCommentary` 显示 `panel.json.commentary`（为空时隐藏）。
